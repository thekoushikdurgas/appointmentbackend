"""Service layer orchestrating contact repository operations and transformations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.companies import CompanyRepository
from app.repositories.contacts import ContactRepository
from app.services.base import BaseService
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanySummary
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem, ContactSimpleItem, ContactLocation
from app.schemas.filters import AttributeListParams, CompanyContactFilterParams, ContactFilterParams
from app.schemas.metadata import ContactMetadataOut
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_company_metadata_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
)
from app.utils.cursor import encode_offset_cursor
from app.utils.normalization import (
    PLACEHOLDER_VALUE,
    coalesce_text,
    normalize_sequence,
    normalize_text,
)
from app.utils.pagination import (
    build_cursor_link,
    build_pagination_link,
    build_paginated_attribute_list,
    build_simple_list_pagination_links,
)
from app.utils.pagination_cache import (
    build_list_meta,
    build_pagination_links,
    cache_list_result,
    get_cached_list_result,
)
from app.utils.hydration import safe_getattr

settings = get_settings()


class ContactsService(BaseService[ContactRepository]):
    """Business logic for retrieving and shaping contact data."""

    def __init__(
        self,
        repository: Optional[ContactRepository] = None,
        company_repository: Optional[CompanyRepository] = None,
    ) -> None:
        """Initialize the service with its repository dependencies."""
        super().__init__(repository or ContactRepository())
        self.company_repository = company_repository or CompanyRepository()

    async def create_contact(
        self,
        session: AsyncSession,
        payload: ContactCreate,
    ) -> ContactDetail:
        """Create a new contact and return the hydrated detail schema."""
        data = payload.model_dump()
        normalized_uuid = normalize_text(data.get("uuid"), allow_placeholder=False)
        data["uuid"] = normalized_uuid or uuid4().hex

        for field in (
            "first_name",
            "last_name",
            "email",
            "title",
            "mobile_phone",
            "email_status",
            "text_search",
            "company_id",
        ):
            data[field] = normalize_text(data.get(field))

        departments = normalize_sequence(data.get("departments"))
        data["departments"] = departments or None

        seniority = normalize_text(data.get("seniority"), allow_placeholder=False)
        data["seniority"] = seniority or PLACEHOLDER_VALUE

        now = datetime.now(UTC).replace(tzinfo=None)
        data["created_at"] = now
        data["updated_at"] = now

        contact = await self.repository.create_contact(session, data)
        await session.commit()
        
        # Invalidate contacts list cache on creation
        await self._invalidate_on_create("contacts")
        
        detail = await self.get_contact(session, contact.uuid)
        return detail

    async def list_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        *,
        limit: Optional[int],
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[ContactListItem]:
        """List contacts and build pagination metadata."""
        
        # Check cache if enabled and query is cacheable
        cached_result = await get_cached_list_result(
            "contacts", filters, limit, offset, use_cursor
        )
        if cached_result:
            return CursorPage(**cached_result)
        
        try:
            contacts = await self.repository.list_contacts(session, filters, limit, offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        # Extract foreign keys
        company_ids = {c.company_id for c in contacts if c.company_id}
        contact_uuids = {c.uuid for c in contacts}
        
        # Batch fetch related entities
        companies_dict = await batch_fetch_companies_by_uuids(session, company_ids)
        contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
        
        # Extract company UUIDs from fetched companies
        company_uuids = {c.uuid for c in companies_dict.values()}
        company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
        
        # Reconstruct tuples and hydrate contacts
        results = []
        for contact in contacts:
            company = companies_dict.get(contact.company_id) if contact.company_id else None
            contact_meta = contact_meta_dict.get(contact.uuid)
            company_meta = company_meta_dict.get(company.uuid) if company else None
            results.append(self._hydrate_contact(contact, company, contact_meta, company_meta))

        # Build pagination links
        next_link, previous_link = build_pagination_links(
            request_url, limit, offset, len(results), use_cursor
        )
        
        # Build meta information
        meta = build_list_meta(filters, use_cursor, len(results), limit, self._is_using_replica())
        
        page = CursorPage(next=next_link, previous=previous_link, results=results, meta=meta)
        
        # Cache result if enabled and query is cacheable
        await cache_list_result("contacts", page, filters, limit, offset, use_cursor)
        
        return page

    async def list_contacts_simple(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        *,
        limit: Optional[int],
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[ContactSimpleItem]:
        """List contacts in simplified projection for view=simple."""
        try:
            contacts = await self.repository.list_contacts(session, filters, limit, offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        # Extract foreign keys
        company_ids = {c.company_id for c in contacts if c.company_id}
        contact_uuids = {c.uuid for c in contacts}
        
        # Batch fetch related entities
        companies_dict = await batch_fetch_companies_by_uuids(session, company_ids)
        contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
        
        simple_results: list[ContactSimpleItem] = []
        for contact in contacts:
            company = companies_dict.get(contact.company_id) if contact.company_id else None
            contact_meta = contact_meta_dict.get(contact.uuid)
            location = ContactLocation(
                city=normalize_text(contact_meta.city if contact_meta else None),
                state=normalize_text(contact_meta.state if contact_meta else None),
                country=normalize_text(contact_meta.country if contact_meta else None),
            )
            # When all location fields are None, keep location as None
            location_value = location if any([location.city, location.state, location.country]) else None
            simple_results.append(
                ContactSimpleItem(
                    uuid=contact.uuid,
                    first_name=normalize_text(contact.first_name),
                    last_name=normalize_text(contact.last_name),
                    title=normalize_text(contact.title),
                    location=location_value,
                    company_name=normalize_text(company.name if company else None),
                    person_linkedin_url=normalize_text(contact_meta.linkedin_url if contact_meta else None),
                    company_domain=normalize_text(contact_meta.website if contact_meta else None),
                )
            )

        next_link = None
        if limit is not None and len(simple_results) == limit:
            if use_cursor:
                next_cursor = encode_offset_cursor(offset + limit)
                next_link = build_cursor_link(request_url, next_cursor)
            else:
                next_link = build_pagination_link(request_url, limit=limit, offset=offset + limit)
        previous_link = None
        if offset > 0:
            if use_cursor:
                prev_offset = max(offset - limit, 0)
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_cursor_link(request_url, prev_cursor)
            else:
                prev_offset = max(offset - limit, 0)
                previous_link = build_pagination_link(request_url, limit=limit, offset=prev_offset)
        
        # Build meta information
        meta = {
            "strategy": "cursor" if use_cursor else "limit-offset",
            "count_mode": "estimated" if not active_filter_keys else "actual",
            "filters_applied": len(active_filter_keys) > 0,
            "ordering": filters.ordering or "-created_at",
            "returned_records": len(simple_results),
            "page_size": limit,
            "page_size_cap": settings.MAX_PAGE_SIZE,
            "using_replica": self._is_using_replica(),
        }
        
        return CursorPage(next=next_link, previous=previous_link, results=simple_results, meta=meta)

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
    ) -> CountResponse:
        """Count contacts that match the provided filters."""
        total = await self.repository.count_contacts(session, filters)
        return CountResponse(count=total)

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs that match the supplied filters."""
        uuids = await self.repository.get_uuids_by_filters(session, filters, limit)
        return uuids

    async def get_uuids_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs for a specific company that match the supplied filters."""
        # Verify company exists
        company = await self.company_repository.get_by_uuid(session, company_uuid)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        uuids = await self.repository.get_uuids_by_company(session, company_uuid, filters, limit)
        return uuids

    async def get_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> ContactDetail:
        """Fetch a single contact with related data."""
        result = await self.repository.get_contact_with_relations(session, contact_uuid)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        contact, company, contact_meta, company_meta = result
        item = self._hydrate_contact(contact, company, contact_meta, company_meta)
        detail = ContactDetail(
            **item.model_dump(),
            company_detail=self._company_summary(company, company_meta),
            metadata=self._contact_metadata(contact_meta),
        )
        return detail

    async def list_company_names_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        request_url: str,
    ) -> CursorPage[str]:
        """List company names directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search parameters.
        
        Returns paginated response with next and previous URLs.
        """
        values = await self.repository.list_company_names_simple(session, params)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_company_domains_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        request_url: str,
    ) -> CursorPage[str]:
        """List company domains extracted from CompanyMetadata.website.
        
        This method queries ONLY the CompanyMetadata table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search parameters.
        
        Extracts domain from website URLs (removes protocol, www, port, converts to lowercase).
        
        Returns paginated response with next and previous URLs.
        """
        values = await self.repository.list_company_domains_simple(session, params)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_industries_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]],
        separated: bool,
        request_url: str,
    ) -> CursorPage[str]:
        """List industry values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company, separated parameters.
        
        Returns paginated response with next and previous URLs.
        """
        values = await self.repository.list_industries_simple(session, params, company, separated)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_keywords_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]],
        request_url: str,
    ) -> CursorPage[str]:
        """List keyword values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company parameters.
        
        Always uses: separated=True, distinct=True (hardcoded for optimal performance)
        
        Returns paginated response with next and previous URLs.
        """
        # Always use separated=True for optimal performance
        values = await self.repository.list_keywords_simple(session, params, company, separated=True)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_departments_simple(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        separated: bool,
        request_url: str,
    ) -> CursorPage[str]:
        """List department values from Contact.departments array field.
        
        This method queries Contact.departments and supports all ContactFilterParams.
        Only uses: distinct, limit, offset, ordering, search, separated parameters.
        
        Always uses: separated=true, distinct=true (hardcoded for optimal performance)
        
        Returns paginated response with next and previous URLs.
        """
        # Always use separated=True for optimal performance
        values = await self.repository.list_departments_simple(session, filters, params, separated=True)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_technologies_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]],
        request_url: str,
    ) -> CursorPage[str]:
        """List technology values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company parameters.
        
        Always uses: separated=True, distinct=True (hardcoded for optimal performance)
        
        Returns paginated response with next and previous URLs.
        """
        # Always use separated=True for optimal performance
        values = await self.repository.list_technologies_simple(session, params, company, separated=True)
        
        # Build pagination links
        next_link, previous_link = build_simple_list_pagination_links(
            request_url, params.limit, params.offset, len(values)
        )
        return CursorPage(next=next_link, previous=previous_link, results=values)

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Iterable],
        *,
        array_mode: bool = False,
    ) -> List[str]:
        """Return a list of attribute values for contacts."""
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

    async def list_company_addresses_paginated(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        request_url: str,
    ) -> CursorPage[str]:
        """List company address values with pagination URLs.
        
        Returns paginated response with next and previous URLs.
        Addresses are sourced from Company.text_search column.
        Uses limit+1 pattern to accurately detect if more results exist.
        """
        import time
        start_time = time.time()
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        try:
            # Use limit+1 pattern to accurately detect if more results exist
            # Request limit+1 from repository, then check if we got more than limit
            modified_params = params
            if params.limit is not None:
                modified_params = params.model_copy(update={"limit": params.limit + 1})
            
            # Get values using the attribute endpoint logic
            column_factory = lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.text_search
            
            repository_start_time = time.time()
            try:
                values = await self.repository.list_attribute_values(
                    session,
                    filters,
                    modified_params,
                    array_mode=False,
                    column_factory=column_factory,
                )
                repository_time = time.time() - repository_start_time
            except ValueError as exc:
                repository_time = time.time() - repository_start_time
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            except Exception as exc:
                repository_time = time.time() - repository_start_time
                raise
            
            # Use helper function for pagination logic
            page = build_paginated_attribute_list(
                request_url,
                params,  # original params
                values,
                fetch_limit=modified_params.limit if params.limit is not None else None,
            )
            
            total_time = time.time() - start_time
            raw_count = len(values)  # Before helper processes it
            
            return page
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            total_time = time.time() - start_time
            raise

    async def list_contact_addresses_paginated(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        request_url: str,
    ) -> CursorPage[str]:
        """List contact address values with pagination URLs.
        
        Returns paginated response with next and previous URLs.
        Addresses are sourced from Contact.text_search column.
        Uses limit+1 pattern to accurately detect if more results exist.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        # Use limit+1 pattern to accurately detect if more results exist
        # Request limit+1 from repository, then check if we got more than limit
        modified_params = params
        if params.limit is not None:
            modified_params = params.model_copy(update={"limit": params.limit + 1})
        
        # Get values using the attribute endpoint logic
        column_factory = lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.text_search
        try:
            values = await self.repository.list_attribute_values(
                session,
                filters,
                modified_params,
                array_mode=False,
                column_factory=column_factory,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        
        # Use helper function for pagination logic
        page = build_paginated_attribute_list(
            request_url,
            params,  # original params
            values,
            fetch_limit=modified_params.limit if params.limit is not None else None,
        )
        
        raw_count = len(values)  # Before helper processes it
        return page

    def _has_alphanumeric(self, value: Any) -> bool:
        """Return True when the value contains at least one alphanumeric character."""
        if value is None:
            return False
        text = str(value).strip()
        if not text:
            return False
        return any(char.isalnum() for char in text)

    async def list_titles_paginated(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        request_url: str,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Iterable],
    ) -> CursorPage[str]:
        """Return paginated contact titles with next/previous URLs.
        
        This method applies title-specific filtering (alphanumeric check) and
        deduplication logic, then builds pagination links.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        # Validate parameters
        if params.limit is not None and params.limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit must be a positive integer",
            )
        if params.offset is not None and params.offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="offset must be zero or greater",
            )
        
        # Get values from repository
        effective_params = params
        
        try:
            values = await self.repository.list_attribute_values(
                session,
                filters,
                effective_params,
                array_mode=False,
                column_factory=column_factory,
                apply_title_alphanumeric_filter=True,  # Apply SQL-level filter for titles
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        
        # Track count BEFORE post-processing to determine if there are more results
        # This is critical for pagination: if SQL returned exactly 'limit' rows,
        # there might be more results even if post-processing reduces the count
        raw_count = len(values)
        has_more_results = params.limit is not None and raw_count == params.limit
        
        # Note: Alphanumeric filtering is now applied at SQL level via apply_title_alphanumeric_filter
        # This ensures LIMIT works correctly. We keep a Python-level check as a safety net,
        # but it should rarely filter out additional values now.
        # Apply title-specific filtering (alphanumeric check) as safety net
        values = [value for value in values if self._has_alphanumeric(value)]
        after_alphanumeric_count = len(values)
        
        # Apply deduplication if needed
        distinct_requested = effective_params.distinct
        if distinct_requested:
            seen = set()
            unique_values = []
            for value in values:
                if value is None:
                    continue
                normalized = value.lower() if isinstance(value, str) else str(value)
                if normalized not in seen:
                    seen.add(normalized)
                    unique_values.append(value)
            values = unique_values
        
        # Build pagination links
        # Use raw_count (before post-processing) to determine if there are more results
        # This ensures we show next link even if deduplication reduces the final count
        next_link = None
        if has_more_results:
            # If SQL returned exactly 'limit' results, there might be more
            next_offset = params.offset + params.limit
            next_link = build_pagination_link(request_url, limit=params.limit, offset=next_offset)
        
        previous_link = None
        if params.offset > 0:
            # If we're not at the start, there's a previous page
            prev_offset = max(params.offset - (params.limit or 0), 0)
            previous_link = build_pagination_link(request_url, limit=params.limit or 25, offset=prev_offset)
        return CursorPage(next=next_link, previous=previous_link, results=values)

    def _hydrate_contact(
        self,
        contact: Contact,
        company: Optional[Company],
        contact_meta: Optional[ContactMetadata],
        company_meta: Optional[CompanyMetadata],
    ) -> ContactListItem:
        """Construct a contact list item schema from ORM entities."""
        company_keywords = normalize_sequence(safe_getattr(company, "keywords") if company else None)
        company_technologies = normalize_sequence(safe_getattr(company, "technologies") if company else None)
        industries = normalize_sequence(safe_getattr(company, "industries") if company else None)
        contact_departments = normalize_sequence(safe_getattr(contact, "departments"))

        departments = ", ".join(contact_departments) if contact_departments else None
        keywords = ", ".join(company_keywords) if company_keywords else None
        technologies = ", ".join(company_technologies) if company_technologies else None
        industry = ", ".join(industries) if industries else None

        metadata_dict = {}
        if company_meta and safe_getattr(company_meta, "latest_funding_amount") is not None:
            metadata_dict["latest_funding_amount"] = str(safe_getattr(company_meta, "latest_funding_amount"))
        
        item = ContactListItem(
            id=safe_getattr(contact, "id"),
            uuid=safe_getattr(contact, "uuid"),
            first_name=normalize_text(safe_getattr(contact, "first_name")),
            last_name=normalize_text(safe_getattr(contact, "last_name")),
            title=normalize_text(safe_getattr(contact, "title")),
            company=normalize_text(safe_getattr(company, "name") if company else None),
            company_name_for_emails=normalize_text(
                safe_getattr(company_meta, "company_name_for_emails") if company_meta else None
            ),
            email=normalize_text(safe_getattr(contact, "email")),
            email_status=normalize_text(safe_getattr(contact, "email_status")),
            primary_email_catch_all_status=None,
            seniority=normalize_text(safe_getattr(contact, "seniority"), allow_placeholder=True),
            departments=departments,
            work_direct_phone=normalize_text(safe_getattr(contact_meta, "work_direct_phone") if contact_meta else None),
            home_phone=normalize_text(safe_getattr(contact_meta, "home_phone") if contact_meta else None),
            mobile_phone=normalize_text(safe_getattr(contact, "mobile_phone")),
            corporate_phone=normalize_text(safe_getattr(company_meta, "phone_number") if company_meta else None),
            other_phone=normalize_text(safe_getattr(contact_meta, "other_phone") if contact_meta else None),
            stage=normalize_text(safe_getattr(contact_meta, "stage") if contact_meta else None),
            employees=safe_getattr(company, "employees_count") if company else None,
            industry=industry,
            keywords=keywords,
            person_linkedin_url=normalize_text(safe_getattr(contact_meta, "linkedin_url") if contact_meta else None),
            website=normalize_text(safe_getattr(contact_meta, "website") if contact_meta else None),
            company_linkedin_url=normalize_text(safe_getattr(company_meta, "linkedin_url") if company_meta else None),
            facebook_url=coalesce_text(
                safe_getattr(company_meta, "facebook_url") if company_meta else None,
                safe_getattr(contact_meta, "facebook_url") if contact_meta else None,
            ),
            twitter_url=coalesce_text(
                safe_getattr(company_meta, "twitter_url") if company_meta else None,
                safe_getattr(contact_meta, "twitter_url") if contact_meta else None,
            ),
            city=normalize_text(safe_getattr(contact_meta, "city") if contact_meta else None),
            state=normalize_text(safe_getattr(contact_meta, "state") if contact_meta else None),
            country=normalize_text(safe_getattr(contact_meta, "country") if contact_meta else None),
            company_address=normalize_text(safe_getattr(company, "address") if company else None),
            company_city=normalize_text(safe_getattr(company_meta, "city") if company_meta else None),
            company_state=normalize_text(safe_getattr(company_meta, "state") if company_meta else None),
            company_country=normalize_text(safe_getattr(company_meta, "country") if company_meta else None),
            company_phone=normalize_text(safe_getattr(company_meta, "phone_number") if company_meta else None),
            technologies=technologies,
            annual_revenue=safe_getattr(company, "annual_revenue") if company else None,
            total_funding=safe_getattr(company, "total_funding") if company else None,
            latest_funding=normalize_text(safe_getattr(company_meta, "latest_funding") if company_meta else None),
            latest_funding_amount=safe_getattr(company_meta, "latest_funding_amount") if company_meta else None,
            last_raised_at=normalize_text(safe_getattr(company_meta, "last_raised_at") if company_meta else None),
            meta_data=metadata_dict or None,
            created_at=safe_getattr(contact, "created_at"),
            updated_at=safe_getattr(contact, "updated_at"),
        )
        return item

    def _company_summary(
        self,
        company: Optional[Company],
        company_meta: Optional[CompanyMetadata],
    ):
        """Build a compact company summary for contact detail responses."""
        if not company:
            return None
        industries = normalize_sequence(company.industries)
        technologies = normalize_sequence(company.technologies)
        summary = CompanySummary(
            uuid=company.uuid,
            name=normalize_text(company.name) or company.name,
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=", ".join(industries) if industries else None,
            city=normalize_text(company_meta.city if company_meta else None),
            state=normalize_text(company_meta.state if company_meta else None),
            country=normalize_text(company_meta.country if company_meta else None),
            website=normalize_text(company_meta.website if company_meta else None),
            linkedin_url=normalize_text(company_meta.linkedin_url if company_meta else None),
            phone_number=normalize_text(company_meta.phone_number if company_meta else None),
            technologies=technologies or None,
        )
        return summary

    def _contact_metadata(
        self,
        contact_meta: Optional[ContactMetadata],
    ):
        """Convert contact metadata ORM instance into a response schema."""
        if not contact_meta:
            return None
        metadata = ContactMetadataOut(
            uuid=contact_meta.uuid,
            linkedin_url=normalize_text(contact_meta.linkedin_url),
            facebook_url=normalize_text(contact_meta.facebook_url),
            twitter_url=normalize_text(contact_meta.twitter_url),
            website=normalize_text(contact_meta.website),
            work_direct_phone=normalize_text(contact_meta.work_direct_phone),
            home_phone=normalize_text(contact_meta.home_phone),
            city=normalize_text(contact_meta.city),
            state=normalize_text(contact_meta.state),
            country=normalize_text(contact_meta.country),
            other_phone=normalize_text(contact_meta.other_phone),
            stage=normalize_text(contact_meta.stage),
        )
        return metadata

    async def list_contacts_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        limit: Optional[int],
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[ContactListItem]:
        """List contacts for a specific company with pagination."""
        # Verify company exists
        company = await self.company_repository.get_by_uuid(session, company_uuid)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Fetch contacts
        rows = await self.repository.list_contacts_by_company(
            session,
            company_uuid,
            filters,
            limit,
            offset,
        )
        
        # Transform to schemas
        items: list[ContactListItem] = []
        for contact, company_row, contact_meta, company_meta in rows:
            item = self._hydrate_contact(contact, company_row, contact_meta, company_meta)
            items.append(item)
        
        # Build pagination URLs
        next_link = None
        if limit is not None and len(items) == limit:
            if use_cursor:
                next_offset = offset + limit
                next_cursor = encode_offset_cursor(next_offset)
                next_link = build_cursor_link(request_url, next_cursor)
            else:
                next_offset = offset + limit
                next_link = build_pagination_link(request_url, limit=limit, offset=next_offset)
        
        previous_link = None
        if offset > 0:
            if use_cursor:
                prev_offset = max(offset - (limit or 0), 0)
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_cursor_link(request_url, prev_cursor)
            else:
                prev_offset = max(offset - (limit or 0), 0)
                previous_link = build_pagination_link(request_url, limit=limit, offset=prev_offset)
        
        return CursorPage(
            next=next_link,
            previous=previous_link,
            results=items,
        )

    async def count_contacts_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
    ) -> CountResponse:
        """Count contacts for a specific company matching filters."""
        
        # Verify company exists
        company = await self.company_repository.get_by_uuid(session, company_uuid)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Count contacts
        count = await self.repository.count_contacts_by_company(
            session,
            company_uuid,
            filters,
        )
        return CountResponse(count=count)

    async def list_attribute_values_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        attribute: str,
        filters: CompanyContactFilterParams,
        params: AttributeListParams,
    ) -> List[str]:
        """List distinct attribute values for contacts within a specific company."""
        
        # Verify company exists
        company = await self.company_repository.get_by_uuid(session, company_uuid)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Fetch attribute values
        values = await self.repository.list_attribute_values_by_company(
            session,
            company_uuid,
            attribute,
            filters,
            params,
        )
        return list(values)

