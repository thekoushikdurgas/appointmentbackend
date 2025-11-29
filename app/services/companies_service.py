"""Service layer orchestrating company repository operations and transformations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.repositories.companies import CompanyRepository
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanyCreate, CompanyDetail, CompanyListItem, CompanyMetadataOut, CompanyUpdate
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.utils.batch_lookup import batch_fetch_company_metadata_by_uuids
from app.utils.cursor import encode_offset_cursor
from app.utils.normalization import (
    PLACEHOLDER_VALUE,
    coalesce_text,
    normalize_sequence,
    normalize_text,
)
from app.utils.pagination import build_cursor_link, build_pagination_link
from app.utils.query_cache import get_query_cache
from app.core.config import get_settings

settings = get_settings()


class CompaniesService:
    """Business logic for retrieving and shaping company data."""

    def __init__(self, repository: Optional[CompanyRepository] = None) -> None:
        """Initialize the service with its repository dependency."""
        self.logger = get_logger(__name__)
        self.logger.debug("Entering CompaniesService.__init__ repository=%s", repository)
        self.repository = repository or CompanyRepository()
        self.logger.debug("Exiting CompaniesService.__init__ repository=%s", self.repository.__class__.__name__)

    async def create_company(
        self,
        session: AsyncSession,
        payload: CompanyCreate,
    ) -> CompanyDetail:
        """Create a new company and return the hydrated detail schema."""
        data = payload.model_dump()
        normalized_uuid = normalize_text(data.get("uuid"), allow_placeholder=False)
        data["uuid"] = normalized_uuid or uuid4().hex

        for field in (
            "name",
            "address",
            "text_search",
        ):
            data[field] = normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if data.get(field) is not None and data[field] < 0:
                data[field] = None

        industries = normalize_sequence(data.get("industries"))
        data["industries"] = industries or None

        keywords = normalize_sequence(data.get("keywords"))
        data["keywords"] = keywords or None

        technologies = normalize_sequence(data.get("technologies"))
        data["technologies"] = technologies or None

        now = datetime.now(UTC).replace(tzinfo=None)
        data["created_at"] = now
        data["updated_at"] = now

        # self.logger.info("Service creating company: uuid=%s name=%s", data["uuid"], data.get("name"))
        company = await self.repository.create_company(session, data)
        await session.commit()
        self.logger.debug("Created company persisted: uuid=%s", company.uuid)
        
        # Invalidate companies list cache on creation
        if settings.ENABLE_QUERY_CACHING:
            cache = get_query_cache()
            try:
                await cache.invalidate_pattern("query_cache:companies:list:*")
            except Exception as exc:
                self.logger.warning("Failed to invalidate companies cache: %s", exc)
        
        detail = await self.get_company_by_uuid(session, company.uuid)
        self.logger.debug("Returning created company detail: uuid=%s", company.uuid)
        return detail

    async def update_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        payload: CompanyUpdate,
    ) -> CompanyDetail:
        """Update an existing company and return the hydrated detail schema."""
        data = payload.model_dump(exclude_unset=True)
        
        for field in ("name", "address", "text_search"):
            if field in data:
                data[field] = normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if field in data and data[field] is not None and data[field] < 0:
                data[field] = None

        if "industries" in data:
            industries = normalize_sequence(data.get("industries"))
            data["industries"] = industries or None

        if "keywords" in data:
            keywords = normalize_sequence(data.get("keywords"))
            data["keywords"] = keywords or None

        if "technologies" in data:
            technologies = normalize_sequence(data.get("technologies"))
            data["technologies"] = technologies or None

        data["updated_at"] = datetime.now(UTC).replace(tzinfo=None)

        # self.logger.info("Service updating company: company_uuid=%s", company_uuid)
        company = await self.repository.update_company(session, company_uuid, data)
        if not company:
            # self.logger.info("Company not found for update: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        self.logger.debug("Updated company persisted: uuid=%s", company.uuid)
        
        # Invalidate companies list cache on update
        if settings.ENABLE_QUERY_CACHING:
            cache = get_query_cache()
            try:
                await cache.invalidate_pattern("query_cache:companies:list:*")
            except Exception as exc:
                self.logger.warning("Failed to invalidate companies cache: %s", exc)
        
        detail = await self.get_company_by_uuid(session, company.uuid)
        self.logger.debug("Returning updated company detail: uuid=%s", company.uuid)
        return detail

    async def delete_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> None:
        """Delete a company by UUID."""
        # self.logger.info("Service deleting company: company_uuid=%s", company_uuid)
        deleted = await self.repository.delete_company(session, company_uuid)
        if not deleted:
            # self.logger.info("Company not found for deletion: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        self.logger.debug("Deleted company: company_uuid=%s", company_uuid)
        
        # Invalidate companies list cache on deletion
        if settings.ENABLE_QUERY_CACHING:
            cache = get_query_cache()
            try:
                await cache.invalidate_pattern("query_cache:companies:list:*")
            except Exception as exc:
                self.logger.warning("Failed to invalidate companies cache: %s", exc)

    async def list_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        *,
        limit: Optional[int],
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[CompanyListItem]:
        """List companies and build pagination metadata."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing companies: limit=%s offset=%d use_cursor=%s filters=%s",
            limit,
            offset,
            use_cursor,
            active_filter_keys,
        )
        
        # Check cache if enabled and query is cacheable (has limit and reasonable offset)
        cache = get_query_cache()
        cache_key_args = {
            "filters": filters.model_dump(exclude_none=True),
            "limit": limit,
            "offset": offset,
            "use_cursor": use_cursor,
        }
        cached_result = None
        if settings.ENABLE_QUERY_CACHING and limit is not None and limit <= 1000:
            cached_result = await cache.get("companies:list", **cache_key_args)
            if cached_result:
                self.logger.debug("Cache hit for companies list query")
                return CursorPage(**cached_result)
        
        if limit is None:
            self.logger.warning(
                "Unlimited query requested for companies - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        try:
            companies = await self.repository.list_companies(session, filters, limit, offset)
        except ValueError as exc:
            # self.logger.info("List companies request rejected: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.logger.debug("Repository returned %d companies", len(companies))

        # Extract company UUIDs
        company_uuids = {c.uuid for c in companies}
        
        # Batch fetch metadata
        company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
        
        # Reconstruct tuples and hydrate companies
        results = [
            self._hydrate_company(company, company_meta_dict.get(company.uuid))
            for company in companies
        ]

        next_link = None
        # Only show next link if we have a limit and returned exactly that many results
        if limit is not None and len(results) == limit:
            if use_cursor:
                next_cursor = encode_offset_cursor(offset + limit)
                next_link = build_cursor_link(request_url, next_cursor)
            else:
                next_link = build_pagination_link(
                    request_url,
                    limit=limit,
                    offset=offset + limit,
                )
        previous_link = None
        if offset > 0:
            if use_cursor:
                prev_offset = max(offset - (limit or 0), 0)
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_cursor_link(request_url, prev_cursor)
            else:
                prev_offset = max(offset - (limit or 0), 0)
                previous_link = build_pagination_link(request_url, limit=limit, offset=prev_offset)
        self.logger.info(
            "List companies pagination prepared: next=%s previous=%s",
            bool(next_link),
            bool(previous_link),
        )
        self.logger.debug(
            "Exiting CompaniesService.list_companies results=%d next_link=%s previous_link=%s",
            len(results),
            bool(next_link),
            bool(previous_link),
        )
        page = CursorPage(next=next_link, previous=previous_link, results=results)
        
        # Cache result if enabled and query is cacheable
        if settings.ENABLE_QUERY_CACHING and limit is not None and limit <= 1000:
            try:
                await cache.set("companies:list", page.model_dump(), **cache_key_args)
            except Exception as exc:
                self.logger.warning("Failed to cache companies list result: %s", exc)
        
        return page

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
    ) -> CountResponse:
        """Count companies that match the provided filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # self.logger.info("Service counting companies: filters=%s", active_filter_keys)
        total = await self.repository.count_companies(session, filters)
        # self.logger.info("Service counted companies: total=%d", total)
        self.logger.debug("Exiting CompaniesService.count_companies")
        return CountResponse(count=total)

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[str]:
        """Return company UUIDs that match the supplied filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service getting company UUIDs: offset=%d limit=%s filters=%s",
            offset,
            limit,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited UUID query requested - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        uuids = await self.repository.get_uuids_by_filters(session, filters, limit, offset)
        # self.logger.info("Service retrieved %d company UUIDs", len(uuids))
        return uuids

    async def get_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company with related data."""
        # self.logger.info("Service retrieving company: company_uuid=%s", company_uuid)
        result = await self.repository.get_company_with_metadata(session, company_uuid)
        if not result:
            # self.logger.info("Company not found: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        company, company_meta = result
        item = self._hydrate_company(company, company_meta)
        self.logger.debug("Hydrated company detail for company_uuid=%s", company_uuid)
        detail = CompanyDetail(
            **item.model_dump(),
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
        self.logger.debug("Exiting CompaniesService.get_company company_uuid=%s", company_uuid)
        return detail

    async def get_company_by_uuid(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company by UUID with related data."""
        # self.logger.info("Service retrieving company: company_uuid=%s", company_uuid)
        row = await self.repository.get_company_by_uuid_with_metadata(session, company_uuid)
        if not row:
            # self.logger.info("Company not found: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        company, company_meta = row
        item = self._hydrate_company(company, company_meta)
        self.logger.debug("Hydrated company detail for company_uuid=%s", company_uuid)
        detail = CompanyDetail(
            **item.model_dump(),
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
        self.logger.debug("Exiting CompaniesService.get_company_by_uuid company_uuid=%s", company_uuid)
        return detail

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        params: AttributeListParams,
        column_factory: Callable[[Company, CompanyMetadata], Iterable],
        *,
        array_mode: bool = False,
    ) -> List[str]:
        """Return a list of attribute values for companies."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing attribute values: limit=%s offset=%d distinct=%s filters=%s",
            params.limit,
            params.offset,
            params.distinct,
            active_filter_keys,
        )
        if params.limit is None:
            self.logger.warning(
                "Unlimited attribute query requested - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        try:
            values = await self.repository.list_attribute_values(
                session,
                filters,
                params,
                array_mode=array_mode,
                column_factory=column_factory,
            )
        except ValueError as exc:
            self.logger.warning("Service attribute list rejected: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.logger.debug("Service received %d attribute values", len(values))
        self.logger.debug("Exiting CompaniesService.list_attribute_values")
        return values

    def _hydrate_company(
        self,
        company: Company,
        company_meta: Optional[CompanyMetadata],
    ) -> CompanyListItem:
        """Construct a company list item schema from ORM entities."""
        self.logger.debug(
            "Entering CompaniesService._hydrate_company company_id=%s",
            getattr(company, "id", None),
        )
        industries = normalize_sequence(company.industries)
        keywords = normalize_sequence(company.keywords)
        technologies = normalize_sequence(company.technologies)

        industry = ", ".join(industries) if industries else None

        item = CompanyListItem(
            uuid=company.uuid,
            name=normalize_text(company.name),
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=industry,
            city=normalize_text(company_meta.city if company_meta else None),
            state=normalize_text(company_meta.state if company_meta else None),
            country=normalize_text(company_meta.country if company_meta else None),
            website=normalize_text(company_meta.website if company_meta else None),
            linkedin_url=normalize_text(company_meta.linkedin_url if company_meta else None),
            phone_number=normalize_text(company_meta.phone_number if company_meta else None),
            technologies=technologies or None,
            keywords=keywords or None,
            metadata=self._company_metadata(company_meta),
        )
        self.logger.debug(
            "Exiting CompaniesService._hydrate_company company_id=%s",
            getattr(company, "id", None),
        )
        return item

    def _company_metadata(
        self,
        company_meta: Optional[CompanyMetadata],
    ):
        """Convert company metadata ORM instance into a response schema."""
        self.logger.debug(
            "Entering CompaniesService._company_metadata company_uuid=%s",
            getattr(company_meta, "uuid", None) if company_meta else None,
        )
        if not company_meta:
            self.logger.debug("Exiting CompaniesService._company_metadata (no metadata)")
            return None
        metadata = CompanyMetadataOut(
            uuid=company_meta.uuid,
            linkedin_url=normalize_text(company_meta.linkedin_url),
            facebook_url=normalize_text(company_meta.facebook_url),
            twitter_url=normalize_text(company_meta.twitter_url),
            website=normalize_text(company_meta.website),
            company_name_for_emails=normalize_text(company_meta.company_name_for_emails),
            phone_number=normalize_text(company_meta.phone_number),
            latest_funding=normalize_text(company_meta.latest_funding),
            latest_funding_amount=company_meta.latest_funding_amount,
            last_raised_at=normalize_text(company_meta.last_raised_at),
            city=normalize_text(company_meta.city),
            state=normalize_text(company_meta.state),
            country=normalize_text(company_meta.country),
        )
        self.logger.debug(
            "Exiting CompaniesService._company_metadata company_uuid=%s",
            company_meta.uuid,
        )
        return metadata

