"""Service layer orchestrating contact repository operations and transformations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.contacts import ContactRepository
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanySummary
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem, ContactSimpleItem, ContactLocation
from app.schemas.filters import AttributeListParams, CompanyContactFilterParams, ContactFilterParams
from app.schemas.metadata import ContactMetadataOut
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


class ContactsService:
    """Business logic for retrieving and shaping contact data."""

    def __init__(self, repository: Optional[ContactRepository] = None) -> None:
        """Initialize the service with its repository dependency."""
        self.logger = get_logger(__name__)
        self.logger.debug("Entering ContactsService.__init__ repository=%s", repository)
        self.repository = repository or ContactRepository()
        self.logger.debug("Exiting ContactsService.__init__ repository=%s", self.repository.__class__.__name__)

    async def create_contact(
        self,
        session: AsyncSession,
        payload: ContactCreate,
    ) -> ContactDetail:
        """Create a new contact and return the hydrated detail schema."""
        data = payload.model_dump()
        normalized_uuid = _normalize_text(data.get("uuid"), allow_placeholder=False)
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
            data[field] = _normalize_text(data.get(field))

        departments = _normalize_sequence(data.get("departments"))
        data["departments"] = departments or None

        seniority = _normalize_text(data.get("seniority"), allow_placeholder=False)
        data["seniority"] = seniority or PLACEHOLDER_VALUE

        now = datetime.now(UTC).replace(tzinfo=None)
        data["created_at"] = now
        data["updated_at"] = now

        # self.logger.info("Service creating contact: uuid=%s email=%s", data["uuid"], data.get("email"))
        contact = await self.repository.create_contact(session, data)
        await session.commit()
        self.logger.debug("Created contact persisted: id=%s uuid=%s", contact.id, contact.uuid)
        detail = await self.get_contact(session, contact.uuid)
        self.logger.debug("Returning created contact detail: uuid=%s", contact.uuid)
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
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing contacts: limit=%s offset=%d use_cursor=%s filters=%s",
            limit,
            offset,
            use_cursor,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited query requested for contacts - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        try:
            rows = await self.repository.list_contacts(session, filters, limit, offset)
        except ValueError as exc:
            # self.logger.info("List contacts request rejected: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.logger.debug("Repository returned %d rows for contact list", len(rows))

        results = [
            self._hydrate_contact(contact, company, contact_meta, company_meta)
            for contact, company, contact_meta, company_meta in rows
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
            "List contacts pagination prepared: next=%s previous=%s",
            bool(next_link),
            bool(previous_link),
        )
        self.logger.debug(
            "Exiting ContactsService.list_contacts results=%d next_link=%s previous_link=%s",
            len(results),
            bool(next_link),
            bool(previous_link),
        )
        return CursorPage(next=next_link, previous=previous_link, results=results)

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
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing contacts (simple): limit=%s offset=%d use_cursor=%s filters=%s",
            limit,
            offset,
            use_cursor,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited query requested for contacts (simple) - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        try:
            rows = await self.repository.list_contacts(session, filters, limit, offset)
        except ValueError as exc:
            # self.logger.info("List contacts (simple) request rejected: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.logger.debug("Repository returned %d rows for contact simple list", len(rows))

        simple_results: list[ContactSimpleItem] = []
        for contact, company, contact_meta, company_meta in rows:
            location = ContactLocation(
                city=_normalize_text(contact_meta.city if contact_meta else None),
                state=_normalize_text(contact_meta.state if contact_meta else None),
                country=_normalize_text(contact_meta.country if contact_meta else None),
            )
            # When all location fields are None, keep location as None
            location_value = location if any([location.city, location.state, location.country]) else None
            simple_results.append(
                ContactSimpleItem(
                    uuid=contact.uuid,
                    first_name=_normalize_text(contact.first_name),
                    last_name=_normalize_text(contact.last_name),
                    title=_normalize_text(contact.title),
                    location=location_value,
                    company_name=_normalize_text(company.name if company else None),
                    person_linkedin_url=_normalize_text(contact_meta.linkedin_url if contact_meta else None),
                    company_domain=_normalize_text(contact_meta.website if contact_meta else None),
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
        self.logger.info(
            "List contacts (simple) pagination prepared: next=%s previous=%s",
            bool(next_link),
            bool(previous_link),
        )
        return CursorPage(next=next_link, previous=previous_link, results=simple_results)

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
    ) -> CountResponse:
        """Count contacts that match the provided filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # self.logger.info("Service counting contacts: filters=%s", active_filter_keys)
        total = await self.repository.count_contacts(session, filters)
        # self.logger.info("Service counted contacts: total=%d", total)
        self.logger.debug("Exiting ContactsService.count_contacts")
        return CountResponse(count=total)

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs that match the supplied filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service getting contact UUIDs: limit=%s filters=%s",
            limit,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited UUID query requested - this may return a large dataset. filters=%s",
                active_filter_keys,
            )
        uuids = await self.repository.get_uuids_by_filters(session, filters, limit)
        # self.logger.info("Service retrieved %d contact UUIDs", len(uuids))
        return uuids

    async def get_uuids_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs for a specific company that match the supplied filters."""
        from app.schemas.filters import CompanyContactFilterParams
        from app.repositories.companies import CompanyRepository
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service getting contact UUIDs for company %s: limit=%s filters=%s",
            company_uuid,
            limit,
            active_filter_keys,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited UUID query requested for company contacts - this may return a large dataset. company_uuid=%s",
                company_uuid,
            )
        
        # Verify company exists
        company_repo = CompanyRepository()
        company = await company_repo.get_by_uuid(session, company_uuid)
        if not company:
            self.logger.warning("Company not found: %s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        uuids = await self.repository.get_uuids_by_company(session, company_uuid, filters, limit)
        # self.logger.info("Service retrieved %d contact UUIDs for company %s", len(uuids), company_uuid)
        return uuids

    async def get_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> ContactDetail:
        """Fetch a single contact with related data."""
        # self.logger.info("Service retrieving contact: contact_uuid=%s", contact_uuid)
        row = await self.repository.get_contact_with_relations(session, contact_uuid)
        if not row:
            # self.logger.info("Contact not found: contact_uuid=%s", contact_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        contact, company, contact_meta, company_meta = row
        item = self._hydrate_contact(contact, company, contact_meta, company_meta)
        self.logger.debug("Hydrated contact detail for contact_uuid=%s", contact_uuid)
        detail = ContactDetail(
            **item.model_dump(),
            company_detail=self._company_summary(company, company_meta),
            metadata=self._contact_metadata(contact_meta),
        )
        self.logger.debug("Exiting ContactsService.get_contact contact_uuid=%s", contact_uuid)
        return detail

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
        self.logger.debug("Exiting ContactsService.list_attribute_values")
        return values

    def _hydrate_contact(
        self,
        contact: Contact,
        company: Optional[Company],
        contact_meta: Optional[ContactMetadata],
        company_meta: Optional[CompanyMetadata],
    ) -> ContactListItem:
        """Construct a contact list item schema from ORM entities."""
        self.logger.debug(
            "Entering ContactsService._hydrate_contact contact_id=%s",
            getattr(contact, "id", None),
        )
        
        # Safely access attributes - handle both ORM objects and Row objects
        def safe_getattr(obj, attr, default=None):
            """Safely get attribute from object or Row.
            
            SQLAlchemy may return Row objects instead of ORM instances when
            selecting multiple entities. This function handles both cases.
            """
            if obj is None:
                return default
            
            # First, try to detect if it's a SQLAlchemy Row object
            # Row objects have _mapping or _fields attributes
            is_row = (
                hasattr(obj, '_mapping') or 
                hasattr(obj, '_fields') or
                (hasattr(obj, '__class__') and 'Row' in str(type(obj)))
            )
            
            if is_row:
                # It's a Row object - try key access first
                try:
                    # Try accessing as a key (Row objects support key access)
                    return obj[attr]
                except (KeyError, IndexError, AttributeError, TypeError):
                    # If key access fails, try to access via entity name
                    # For select(Contact, Company), we might access as Contact.departments
                    try:
                        # Try accessing via the Contact entity
                        if hasattr(obj, 'Contact'):
                            return getattr(obj.Contact, attr, default)
                    except (AttributeError, TypeError):
                        pass
                    return default
            
            # For ORM instances, try attribute access
            # Use getattr with default to avoid raising AttributeError
            # But also catch any exceptions from SQLAlchemy C extensions
            try:
                # Check if attribute exists first
                if hasattr(obj, attr):
                    value = getattr(obj, attr)
                    return value
                return default
            except AttributeError as e:
                # AttributeError from SQLAlchemy C extension - try key access
                if hasattr(obj, '__getitem__'):
                    try:
                        return obj[attr]
                    except (KeyError, IndexError, TypeError):
                        return default
                return default
            except Exception:
                # Catch any other exceptions (including from SQLAlchemy C extensions)
                return default
        
        company_keywords = _normalize_sequence(safe_getattr(company, "keywords") if company else None)
        company_technologies = _normalize_sequence(safe_getattr(company, "technologies") if company else None)
        industries = _normalize_sequence(safe_getattr(company, "industries") if company else None)
        contact_departments = _normalize_sequence(safe_getattr(contact, "departments"))

        departments = ", ".join(contact_departments) if contact_departments else None
        keywords = ", ".join(company_keywords) if company_keywords else None
        technologies = ", ".join(company_technologies) if company_technologies else None
        industry = ", ".join(industries) if industries else None

        metadata_dict = {}
        if company_meta and safe_getattr(company_meta, "latest_funding_amount") is not None:
            metadata_dict["latest_funding_amount"] = str(safe_getattr(company_meta, "latest_funding_amount"))
        
        item = ContactListItem(
            uuid=safe_getattr(contact, "uuid"),
            first_name=_normalize_text(safe_getattr(contact, "first_name")),
            last_name=_normalize_text(safe_getattr(contact, "last_name")),
            title=_normalize_text(safe_getattr(contact, "title")),
            company=_normalize_text(safe_getattr(company, "name") if company else None),
            company_name_for_emails=_normalize_text(
                safe_getattr(company_meta, "company_name_for_emails") if company_meta else None
            ),
            email=_normalize_text(safe_getattr(contact, "email")),
            email_status=_normalize_text(safe_getattr(contact, "email_status")),
            primary_email_catch_all_status=None,
            seniority=_normalize_text(safe_getattr(contact, "seniority"), allow_placeholder=True),
            departments=departments,
            work_direct_phone=_normalize_text(safe_getattr(contact_meta, "work_direct_phone") if contact_meta else None),
            home_phone=_normalize_text(safe_getattr(contact_meta, "home_phone") if contact_meta else None),
            mobile_phone=_normalize_text(safe_getattr(contact, "mobile_phone")),
            corporate_phone=_normalize_text(safe_getattr(company_meta, "phone_number") if company_meta else None),
            other_phone=_normalize_text(safe_getattr(contact_meta, "other_phone") if contact_meta else None),
            stage=_normalize_text(safe_getattr(contact_meta, "stage") if contact_meta else None),
            employees=safe_getattr(company, "employees_count") if company else None,
            industry=industry,
            keywords=keywords,
            person_linkedin_url=_normalize_text(safe_getattr(contact_meta, "linkedin_url") if contact_meta else None),
            website=_normalize_text(safe_getattr(contact_meta, "website") if contact_meta else None),
            company_linkedin_url=_normalize_text(safe_getattr(company_meta, "linkedin_url") if company_meta else None),
            facebook_url=_coalesce_text(
                safe_getattr(company_meta, "facebook_url") if company_meta else None,
                safe_getattr(contact_meta, "facebook_url") if contact_meta else None,
            ),
            twitter_url=_coalesce_text(
                safe_getattr(company_meta, "twitter_url") if company_meta else None,
                safe_getattr(contact_meta, "twitter_url") if contact_meta else None,
            ),
            city=_normalize_text(safe_getattr(contact_meta, "city") if contact_meta else None),
            state=_normalize_text(safe_getattr(contact_meta, "state") if contact_meta else None),
            country=_normalize_text(safe_getattr(contact_meta, "country") if contact_meta else None),
            company_address=_normalize_text(safe_getattr(company, "address") if company else None),
            company_city=_normalize_text(safe_getattr(company_meta, "city") if company_meta else None),
            company_state=_normalize_text(safe_getattr(company_meta, "state") if company_meta else None),
            company_country=_normalize_text(safe_getattr(company_meta, "country") if company_meta else None),
            company_phone=_normalize_text(safe_getattr(company_meta, "phone_number") if company_meta else None),
            technologies=technologies,
            annual_revenue=safe_getattr(company, "annual_revenue") if company else None,
            total_funding=safe_getattr(company, "total_funding") if company else None,
            latest_funding=_normalize_text(safe_getattr(company_meta, "latest_funding") if company_meta else None),
            latest_funding_amount=safe_getattr(company_meta, "latest_funding_amount") if company_meta else None,
            last_raised_at=_normalize_text(safe_getattr(company_meta, "last_raised_at") if company_meta else None),
            meta_data=metadata_dict or None,
            created_at=safe_getattr(contact, "created_at"),
            updated_at=safe_getattr(contact, "updated_at"),
        )
        self.logger.debug(
            "Exiting ContactsService._hydrate_contact contact_id=%s",
            getattr(contact, "id", None),
        )
        return item

    def _company_summary(
        self,
        company: Optional[Company],
        company_meta: Optional[CompanyMetadata],
    ):
        """Build a compact company summary for contact detail responses."""
        self.logger.debug(
            "Entering ContactsService._company_summary company_uuid=%s",
            getattr(company, "uuid", None) if company else None,
        )
        if not company:
            self.logger.debug("Exiting ContactsService._company_summary (no company)")
            return None
        industries = _normalize_sequence(company.industries)
        technologies = _normalize_sequence(company.technologies)
        summary = CompanySummary(
            uuid=company.uuid,
            name=_normalize_text(company.name) or company.name,
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=", ".join(industries) if industries else None,
            city=_normalize_text(company_meta.city if company_meta else None),
            state=_normalize_text(company_meta.state if company_meta else None),
            country=_normalize_text(company_meta.country if company_meta else None),
            website=_normalize_text(company_meta.website if company_meta else None),
            linkedin_url=_normalize_text(company_meta.linkedin_url if company_meta else None),
            phone_number=_normalize_text(company_meta.phone_number if company_meta else None),
            technologies=technologies or None,
        )
        self.logger.debug(
            "Exiting ContactsService._company_summary company_uuid=%s",
            company.uuid,
        )
        return summary

    def _contact_metadata(
        self,
        contact_meta: Optional[ContactMetadata],
    ):
        """Convert contact metadata ORM instance into a response schema."""
        self.logger.debug(
            "Entering ContactsService._contact_metadata contact_uuid=%s",
            getattr(contact_meta, "uuid", None) if contact_meta else None,
        )
        if not contact_meta:
            self.logger.debug("Exiting ContactsService._contact_metadata (no metadata)")
            return None
        metadata = ContactMetadataOut(
            uuid=contact_meta.uuid,
            linkedin_url=_normalize_text(contact_meta.linkedin_url),
            facebook_url=_normalize_text(contact_meta.facebook_url),
            twitter_url=_normalize_text(contact_meta.twitter_url),
            website=_normalize_text(contact_meta.website),
            work_direct_phone=_normalize_text(contact_meta.work_direct_phone),
            home_phone=_normalize_text(contact_meta.home_phone),
            city=_normalize_text(contact_meta.city),
            state=_normalize_text(contact_meta.state),
            country=_normalize_text(contact_meta.country),
            other_phone=_normalize_text(contact_meta.other_phone),
            stage=_normalize_text(contact_meta.stage),
        )
        self.logger.debug(
            "Exiting ContactsService._contact_metadata contact_uuid=%s",
            contact_meta.uuid,
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
        from app.schemas.filters import CompanyContactFilterParams
        from app.repositories.companies import CompanyRepository
        from app.utils.pagination import build_cursor_link, build_pagination_link
        
        self.logger.info(
            "Listing contacts for company %s: limit=%s offset=%d use_cursor=%s",
            company_uuid,
            limit,
            offset,
            use_cursor,
        )
        if limit is None:
            self.logger.warning(
                "Unlimited query requested for company contacts - this may return a large dataset. company_uuid=%s",
                company_uuid,
            )
        
        # Verify company exists
        company_repo = CompanyRepository()
        company = await company_repo.get_by_uuid(session, company_uuid)
        if not company:
            self.logger.warning("Company not found: %s", company_uuid)
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
        
        self.logger.info(
            "Listed %d contacts for company %s (offset=%d, next=%s, previous=%s)",
            len(items),
            company_uuid,
            offset,
            bool(next_link),
            bool(previous_link),
        )
        
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
        from app.schemas.filters import CompanyContactFilterParams
        from app.repositories.companies import CompanyRepository
        
        # self.logger.info("Counting contacts for company %s", company_uuid)
        
        # Verify company exists
        company_repo = CompanyRepository()
        company = await company_repo.get_by_uuid(session, company_uuid)
        if not company:
            self.logger.warning("Company not found: %s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Count contacts
        count = await self.repository.count_contacts_by_company(
            session,
            company_uuid,
            filters,
        )
        
        # self.logger.info("Counted %d contacts for company %s", count, company_uuid)
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
        from app.schemas.filters import CompanyContactFilterParams
        from app.repositories.companies import CompanyRepository
        
        self.logger.info(
            "Listing attribute %s values for company %s",
            attribute,
            company_uuid,
        )
        
        # Verify company exists
        company_repo = CompanyRepository()
        company = await company_repo.get_by_uuid(session, company_uuid)
        if not company:
            self.logger.warning("Company not found: %s", company_uuid)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        
        # Fetch attribute values
        values = await self.repository.list_attribute_values_by_company(
            session,
            company_uuid,
            attribute,
            filters,
            params,
        )
        
        self.logger.info(
            "Listed %d distinct %s values for company %s",
            len(values),
            attribute,
            company_uuid,
        )
        return list(values)

