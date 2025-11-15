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
from app.utils.cursor import encode_offset_cursor
from app.utils.pagination import build_cursor_link, build_pagination_link


PLACEHOLDER_VALUE = "_"


def _normalize_text(value: Any, *, allow_placeholder: bool = False) -> Optional[str]:
    """Coerce raw string-like values to cleaned text or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not allow_placeholder and text == PLACEHOLDER_VALUE:
        return None

    # Remove wrapping quotes that leak from CSV exports (e.g., "'+123", '"value"').
    while len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
        if not text:
            return None
        if not allow_placeholder and text == PLACEHOLDER_VALUE:
            return None

    if text.startswith("'+") and len(text) > 2:
        text = text[1:].strip()

    if not text:
        return None
    if not allow_placeholder and text == PLACEHOLDER_VALUE:
        return None
    return text


def _normalize_sequence(values: Optional[Iterable[Any]], *, allow_placeholder: bool = False) -> list[str]:
    """Clean an iterable of values, returning only meaningful text tokens."""
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        normalized = _normalize_text(value, allow_placeholder=allow_placeholder)
        if normalized:
            cleaned.append(normalized)
    return cleaned


def _coalesce_text(*values: Any, allow_placeholder: bool = False) -> Optional[str]:
    """Return the first non-empty normalized text value from the provided options."""
    for value in values:
        normalized = _normalize_text(value, allow_placeholder=allow_placeholder)
        if normalized is not None:
            return normalized
    return None


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
        normalized_uuid = _normalize_text(data.get("uuid"), allow_placeholder=False)
        data["uuid"] = normalized_uuid or uuid4().hex

        for field in (
            "name",
            "address",
            "text_search",
        ):
            data[field] = _normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if data.get(field) is not None and data[field] < 0:
                data[field] = None

        industries = _normalize_sequence(data.get("industries"))
        data["industries"] = industries or None

        keywords = _normalize_sequence(data.get("keywords"))
        data["keywords"] = keywords or None

        technologies = _normalize_sequence(data.get("technologies"))
        data["technologies"] = technologies or None

        now = datetime.now(UTC).replace(tzinfo=None)
        data["created_at"] = now
        data["updated_at"] = now

        self.logger.info("Service creating company: uuid=%s name=%s", data["uuid"], data.get("name"))
        company = await self.repository.create_company(session, data)
        await session.commit()
        self.logger.debug("Created company persisted: id=%s uuid=%s", company.id, company.uuid)
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
                data[field] = _normalize_text(data.get(field))

        for field in ("employees_count", "annual_revenue", "total_funding"):
            if field in data and data[field] is not None and data[field] < 0:
                data[field] = None

        if "industries" in data:
            industries = _normalize_sequence(data.get("industries"))
            data["industries"] = industries or None

        if "keywords" in data:
            keywords = _normalize_sequence(data.get("keywords"))
            data["keywords"] = keywords or None

        if "technologies" in data:
            technologies = _normalize_sequence(data.get("technologies"))
            data["technologies"] = technologies or None

        data["updated_at"] = datetime.now(UTC).replace(tzinfo=None)

        self.logger.info("Service updating company: company_uuid=%s", company_uuid)
        company = await self.repository.update_company(session, company_uuid, data)
        if not company:
            self.logger.info("Company not found for update: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        self.logger.debug("Updated company persisted: id=%s uuid=%s", company.id, company.uuid)
        detail = await self.get_company_by_uuid(session, company.uuid)
        self.logger.debug("Returning updated company detail: uuid=%s", company.uuid)
        return detail

    async def delete_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> None:
        """Delete a company by UUID."""
        self.logger.info("Service deleting company: company_uuid=%s", company_uuid)
        deleted = await self.repository.delete_company(session, company_uuid)
        if not deleted:
            self.logger.info("Company not found for deletion: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        await session.commit()
        self.logger.debug("Deleted company: company_uuid=%s", company_uuid)

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
        if limit is None:
            self.logger.warning(
                "Unlimited query requested for companies - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        try:
            rows = await self.repository.list_companies(session, filters, limit, offset)
        except ValueError as exc:
            self.logger.info("List companies request rejected: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.logger.debug("Repository returned %d rows for company list", len(rows))

        results = [
            self._hydrate_company(company, company_meta)
            for company, company_meta in rows
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
        return CursorPage(next=next_link, previous=previous_link, results=results)

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
    ) -> CountResponse:
        """Count companies that match the provided filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info("Service counting companies: filters=%s", active_filter_keys)
        total = await self.repository.count_companies(session, filters)
        self.logger.info("Service counted companies: total=%d", total)
        self.logger.debug("Exiting CompaniesService.count_companies")
        return CountResponse(count=total)

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return company UUIDs that match the supplied filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service getting company UUIDs: limit=%s filters=%s",
            limit,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited UUID query requested - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        uuids = await self.repository.get_uuids_by_filters(session, filters, limit)
        self.logger.info("Service retrieved %d company UUIDs", len(uuids))
        return uuids

    async def get_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> CompanyDetail:
        """Fetch a single company with related data."""
        self.logger.info("Service retrieving company: company_uuid=%s", company_uuid)
        row = await self.repository.get_company_with_metadata(session, company_uuid)
        if not row:
            self.logger.info("Company not found: company_uuid=%s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        company, company_meta = row
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
        self.logger.info("Service retrieving company: company_uuid=%s", company_uuid)
        row = await self.repository.get_company_by_uuid_with_metadata(session, company_uuid)
        if not row:
            self.logger.info("Company not found: company_uuid=%s", company_uuid)
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
        industries = _normalize_sequence(company.industries)
        keywords = _normalize_sequence(company.keywords)
        technologies = _normalize_sequence(company.technologies)

        industry = ", ".join(industries) if industries else None

        item = CompanyListItem(
            uuid=company.uuid,
            name=_normalize_text(company.name),
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=industry,
            city=_normalize_text(company_meta.city if company_meta else None),
            state=_normalize_text(company_meta.state if company_meta else None),
            country=_normalize_text(company_meta.country if company_meta else None),
            website=_normalize_text(company_meta.website if company_meta else None),
            linkedin_url=_normalize_text(company_meta.linkedin_url if company_meta else None),
            phone_number=_normalize_text(company_meta.phone_number if company_meta else None),
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
            linkedin_url=_normalize_text(company_meta.linkedin_url),
            facebook_url=_normalize_text(company_meta.facebook_url),
            twitter_url=_normalize_text(company_meta.twitter_url),
            website=_normalize_text(company_meta.website),
            company_name_for_emails=_normalize_text(company_meta.company_name_for_emails),
            phone_number=_normalize_text(company_meta.phone_number),
            latest_funding=_normalize_text(company_meta.latest_funding),
            latest_funding_amount=company_meta.latest_funding_amount,
            last_raised_at=_normalize_text(company_meta.last_raised_at),
            city=_normalize_text(company_meta.city),
            state=_normalize_text(company_meta.state),
            country=_normalize_text(company_meta.country),
        )
        self.logger.debug(
            "Exiting CompaniesService._company_metadata company_uuid=%s",
            company_meta.uuid,
        )
        return metadata

