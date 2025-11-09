"""Service layer orchestrating contact repository operations and transformations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.contacts import ContactRepository
from app.schemas.common import CountResponse, CursorPage
from app.schemas.companies import CompanySummary
from app.schemas.contacts import ContactCreate, ContactDetail, ContactListItem
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.schemas.metadata import ContactMetadataOut
from app.utils.cursor import encode_offset_cursor
from app.utils.pagination import build_cursor_link, build_pagination_link


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
        data["uuid"] = data.get("uuid") or uuid4().hex
        seniority = data.get("seniority")
        if not seniority:
            data["seniority"] = "_"
        now = datetime.now(timezone.utc)
        data["created_at"] = now
        data["updated_at"] = now

        self.logger.info("Service creating contact: uuid=%s email=%s", data["uuid"], data.get("email"))
        contact = await self.repository.create_contact(session, data)
        await session.commit()
        self.logger.debug("Created contact persisted: id=%s uuid=%s", contact.id, contact.uuid)
        detail = await self.get_contact(session, contact.id)
        self.logger.debug("Returning created contact detail: id=%s", contact.id)
        return detail

    async def list_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        *,
        limit: int,
        offset: int,
        request_url: str,
        use_cursor: bool = False,
    ) -> CursorPage[ContactListItem]:
        """List contacts and build pagination metadata."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing contacts: limit=%d offset=%d use_cursor=%s filters=%s",
            limit,
            offset,
            use_cursor,
            active_filter_keys,
        )
        rows = await self.repository.list_contacts(session, filters, limit, offset)
        self.logger.debug("Repository returned %d rows for contact list", len(rows))

        results = [
            self._hydrate_contact(contact, company, contact_meta, company_meta)
            for contact, company, contact_meta, company_meta in rows
        ]

        next_link = None
        if len(results) == limit:
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
                prev_offset = max(offset - limit, 0)
                prev_cursor = encode_offset_cursor(prev_offset)
                previous_link = build_cursor_link(request_url, prev_cursor)
            else:
                prev_offset = max(offset - limit, 0)
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

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
    ) -> CountResponse:
        """Count contacts that match the provided filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info("Service counting contacts: filters=%s", active_filter_keys)
        total = await self.repository.count_contacts(session, filters)
        self.logger.info("Service counted contacts: total=%d", total)
        self.logger.debug("Exiting ContactsService.count_contacts")
        return CountResponse(count=total)

    async def get_contact(
        self,
        session: AsyncSession,
        contact_id: int,
    ) -> ContactDetail:
        """Fetch a single contact with related data."""
        self.logger.info("Service retrieving contact: contact_id=%d", contact_id)
        row = await self.repository.get_contact_with_relations(session, contact_id)
        if not row:
            self.logger.warning("Contact not found: contact_id=%d", contact_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        contact, company, contact_meta, company_meta = row
        item = self._hydrate_contact(contact, company, contact_meta, company_meta)
        self.logger.debug("Hydrated contact detail for contact_id=%d", contact_id)
        detail = ContactDetail(
            **item.model_dump(),
            company_detail=self._company_summary(company, company_meta),
            metadata=self._contact_metadata(contact_meta),
        )
        self.logger.debug("Exiting ContactsService.get_contact contact_id=%d", contact_id)
        return detail

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Iterable],
    ) -> List[str]:
        """Return a list of attribute values for contacts."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        self.logger.info(
            "Service listing attribute values: limit=%d offset=%d distinct=%s filters=%s",
            params.limit,
            params.offset,
            params.distinct,
            active_filter_keys,
        )
        column: ColumnElement = column_factory(Contact, Company, ContactMetadata, CompanyMetadata)
        values = await self.repository.list_attribute_values(session, column, filters, params)
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
        company_keywords = (company.keywords or []) if company else []
        company_technologies = (company.technologies or []) if company else []
        industries = (company.industries or []) if company else []

        departments = ", ".join(contact.departments or []) if contact.departments else None
        keywords = ", ".join(company_keywords) if company_keywords else None
        technologies = ", ".join(company_technologies) if company_technologies else None
        industry = ", ".join(industries) if industries else None

        metadata_dict = {}
        if company_meta and company_meta.latest_funding_amount is not None:
            metadata_dict["latest_funding_amount"] = str(company_meta.latest_funding_amount)

        item = ContactListItem(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            title=contact.title,
            company=company.name if company else None,
            company_name_for_emails=company_meta.company_name_for_emails if company_meta else None,
            email=contact.email,
            email_status=contact.email_status,
            primary_email_catch_all_status=None,
            seniority=contact.seniority,
            departments=departments,
            work_direct_phone=contact_meta.work_direct_phone if contact_meta else None,
            home_phone=contact_meta.home_phone if contact_meta else None,
            mobile_phone=contact.mobile_phone,
            corporate_phone=company_meta.phone_number if company_meta else None,
            other_phone=contact_meta.other_phone if contact_meta else None,
            stage=contact_meta.stage if contact_meta else None,
            employees=company.employees_count if company else None,
            industry=industry,
            keywords=keywords,
            person_linkedin_url=contact_meta.linkedin_url if contact_meta else None,
            website=contact_meta.website if contact_meta else None,
            company_linkedin_url=company_meta.linkedin_url if company_meta else None,
            facebook_url=company_meta.facebook_url if company_meta else contact_meta.facebook_url if contact_meta else None,
            twitter_url=company_meta.twitter_url if company_meta else contact_meta.twitter_url if contact_meta else None,
            city=contact_meta.city if contact_meta else None,
            state=contact_meta.state if contact_meta else None,
            country=contact_meta.country if contact_meta else None,
            company_address=company.address if company else None,
            company_city=company_meta.city if company_meta else None,
            company_state=company_meta.state if company_meta else None,
            company_country=company_meta.country if company_meta else None,
            company_phone=company_meta.phone_number if company_meta else None,
            technologies=technologies,
            annual_revenue=company.annual_revenue if company else None,
            total_funding=company.total_funding if company else None,
            latest_funding=company_meta.latest_funding if company_meta else None,
            latest_funding_amount=company_meta.latest_funding_amount if company_meta else None,
            last_raised_at=company_meta.last_raised_at if company_meta else None,
            meta_data=metadata_dict or None,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
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
        summary = CompanySummary(
            uuid=company.uuid,
            name=company.name,
            employees_count=company.employees_count,
            annual_revenue=company.annual_revenue,
            total_funding=company.total_funding,
            industry=", ".join(company.industries or []) if company.industries else None,
            city=company_meta.city if company_meta else None,
            state=company_meta.state if company_meta else None,
            country=company_meta.country if company_meta else None,
            website=company_meta.website if company_meta else None,
            linkedin_url=company_meta.linkedin_url if company_meta else None,
            phone_number=company_meta.phone_number if company_meta else None,
            technologies=company.technologies or None,
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
            linkedin_url=contact_meta.linkedin_url,
            facebook_url=contact_meta.facebook_url,
            twitter_url=contact_meta.twitter_url,
            website=contact_meta.website,
            work_direct_phone=contact_meta.work_direct_phone,
            home_phone=contact_meta.home_phone,
            city=contact_meta.city,
            state=contact_meta.state,
            country=contact_meta.country,
            other_phone=contact_meta.other_phone,
            stage=contact_meta.stage,
        )
        self.logger.debug(
            "Exiting ContactsService._contact_metadata contact_uuid=%s",
            contact_meta.uuid,
        )
        return metadata

