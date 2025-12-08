"""Service layer orchestrating company repository operations and transformations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.repositories.companies import CompanyRepository
from app.services.base import BaseService
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanyCreate, CompanyDetail, CompanyListItem, CompanyMetadataOut, CompanyUpdate
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.utils.batch_lookup import batch_fetch_company_metadata_by_uuids
from app.utils.normalization import (
    normalize_sequence,
    normalize_text,
)
from app.utils.pagination_cache import (
    build_list_meta,
    build_pagination_links,
    cache_list_result,
    get_cached_list_result,
)
from app.core.config import get_settings

settings = get_settings()


class CompaniesService(BaseService[CompanyRepository]):
    """Business logic for retrieving and shaping company data."""

    def __init__(self, repository: Optional[CompanyRepository] = None) -> None:
        """Initialize the service with its repository dependency."""
        super().__init__(repository or CompanyRepository())

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

        company = await self.repository.create_company(session, data)
        await session.commit()
        
        # Invalidate companies list cache on creation
        await self._invalidate_on_create("companies")
        
        detail = await self.get_company_by_uuid(session, company.uuid)
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

        company = await self.repository.update_company(session, company_uuid, data)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        
        # Invalidate companies list cache on update
        await self._invalidate_on_update("companies")
        
        detail = await self.get_company_by_uuid(session, company.uuid)
        return detail

    async def delete_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> None:
        """Delete a company by UUID."""
        deleted = await self.repository.delete_company(session, company_uuid)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        
        # Invalidate companies list cache on deletion
        await self._invalidate_on_delete("companies")

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
        
        # Check cache if enabled and query is cacheable
        cached_result = await get_cached_list_result(
            "companies", filters, limit, offset, use_cursor
        )
        if cached_result:
            return CursorPage(**cached_result)
        
        try:
            companies = await self.repository.list_companies(session, filters, limit, offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        # Extract company UUIDs
        company_uuids = {c.uuid for c in companies}
        
        # Batch fetch metadata
        company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
        
        # Reconstruct tuples and hydrate companies
        results = [
            self._hydrate_company(company, company_meta_dict.get(company.uuid))
            for company in companies
        ]

        # Build pagination links
        next_link, previous_link = build_pagination_links(
            request_url, limit, offset, len(results), use_cursor
        )
        
        # Build meta information
        meta = build_list_meta(filters, use_cursor, len(results), limit, self._is_using_replica())
        
        page = CursorPage(next=next_link, previous=previous_link, results=results, meta=meta)
        
        # Cache result if enabled and query is cacheable
        await cache_list_result("companies", page, filters, limit, offset, use_cursor)
        
        return page

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
    ) -> CountResponse:
        """Count companies that match the provided filters."""
        total = await self.repository.count_companies(session, filters)
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
        uuids = await self.repository.get_uuids_by_filters(session, filters, limit, offset)
        return uuids

    async def get_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company with related data."""
        result = await self.repository.get_company_with_metadata(session, company_uuid)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        company, company_meta = result
        item = self._hydrate_company(company, company_meta)
        detail = CompanyDetail(
            **item.model_dump(),
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
        return detail

    async def get_company_by_uuid(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company by UUID with related data."""
        row = await self.repository.get_company_by_uuid_with_metadata(session, company_uuid)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        company, company_meta = row
        item = self._hydrate_company(company, company_meta)
        detail = CompanyDetail(
            **item.model_dump(),
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
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
        try:
            values = await self.repository.list_attribute_values(
                session,
                filters,
                params,
                array_mode=array_mode,
                column_factory=column_factory,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return values

    def _hydrate_company(
        self,
        company: Company,
        company_meta: Optional[CompanyMetadata],
    ) -> CompanyListItem:
        """Construct a company list item schema from ORM entities."""
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
        return item

    def _company_metadata(
        self,
        company_meta: Optional[CompanyMetadata],
    ):
        """Convert company metadata ORM instance into a response schema."""
        if not company_meta:
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
        return metadata

