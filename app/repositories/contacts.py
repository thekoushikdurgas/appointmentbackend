"""Repository providing contact-specific query utilities."""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.schemas.filters import AttributeListParams, ContactFilterParams
from app.utils.query import (
    apply_ilike_filter,
    apply_numeric_range_filter,
    apply_ordering,
    apply_search,
)

logger = get_logger(__name__)


class ContactRepository(AsyncRepository[Contact]):
    """Data access helpers for contact-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the Contact model."""
        logger.debug("Entering ContactRepository.__init__")
        super().__init__(Contact)
        logger.debug("Exiting ContactRepository.__init__")

    def base_query(self) -> tuple[Select, Company, ContactMetadata, CompanyMetadata]:
        """Construct the base query with joins to related company and metadata tables."""
        logger.debug("Entering ContactRepository.base_query")
        company_alias = aliased(Company, name="company")
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")

        stmt: Select = (
            select(Contact, company_alias, contact_meta_alias, company_meta_alias)
            .select_from(Contact)
            .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
        )
        logger.debug("Exiting ContactRepository.base_query")
        return stmt, company_alias, contact_meta_alias, company_meta_alias

    def apply_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        company: Company,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement."""
        logger.debug(
            "Entering ContactRepository.apply_filters filters=%s",
            sorted(filters.model_dump(exclude_none=True).keys()),
        )
        stmt = apply_ilike_filter(stmt, Contact.first_name, filters.first_name)
        stmt = apply_ilike_filter(stmt, Contact.last_name, filters.last_name)
        stmt = apply_ilike_filter(stmt, Contact.email, filters.email)
        stmt = apply_ilike_filter(stmt, Contact.title, filters.title)
        stmt = apply_ilike_filter(stmt, Contact.company_id, filters.company_id)
        stmt = apply_ilike_filter(stmt, company.name, filters.company)
        if filters.seniority:
            stmt = apply_ilike_filter(stmt, Contact.seniority, filters.seniority)

        if company_meta is not None:
            stmt = apply_ilike_filter(stmt, company_meta.country, filters.country)
            stmt = apply_ilike_filter(stmt, company_meta.state, filters.state)
            stmt = apply_ilike_filter(stmt, company_meta.city, filters.city)
            stmt = apply_ilike_filter(stmt, company_meta.company_name_for_emails, filters.company_name_for_emails)
            if filters.company_country:
                stmt = apply_ilike_filter(stmt, company_meta.country, filters.company_country)
            if filters.company_state:
                stmt = apply_ilike_filter(stmt, company_meta.state, filters.company_state)
            if filters.company_city:
                stmt = apply_ilike_filter(stmt, company_meta.city, filters.company_city)
            if filters.latest_funding_amount_min is not None:
                stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
            if filters.latest_funding_amount_max is not None:
                stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)
        if contact_meta is not None:
            stmt = apply_ilike_filter(stmt, contact_meta.city, filters.city)
            stmt = apply_ilike_filter(stmt, contact_meta.state, filters.state)
            stmt = apply_ilike_filter(stmt, contact_meta.country, filters.country)
            if filters.stage:
                stmt = apply_ilike_filter(stmt, contact_meta.stage, filters.stage)

        stmt = apply_numeric_range_filter(
            stmt,
            company.employees_count,
            filters.employees_min,
            filters.employees_max,
        )
        stmt = apply_numeric_range_filter(
            stmt,
            company.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
        )
        stmt = apply_numeric_range_filter(
            stmt,
            company.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
        )

        if filters.technologies:
            stmt = stmt.where(func.array_to_string(company.technologies, ",").ilike(f"%{filters.technologies}%"))
        if filters.keywords:
            stmt = stmt.where(func.array_to_string(company.keywords, ",").ilike(f"%{filters.keywords}%"))
        if filters.industries:
            stmt = stmt.where(func.array_to_string(company.industries, ",").ilike(f"%{filters.industries}%"))

        if filters.department:
            stmt = stmt.where(
                func.array_to_string(Contact.departments, ",").ilike(f"%{filters.department}%")
            )

        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)

        logger.debug("Exiting ContactRepository.apply_filters")
        return stmt

    def apply_search_terms(
        self,
        stmt: Select,
        search: Optional[str],
        company: Company,
    ) -> Select:
        """Apply case-insensitive search across selected text columns."""
        logger.debug(
            "Entering ContactRepository.apply_search_terms search_present=%s",
            bool(search),
        )
        if not search:
            logger.debug("Exiting ContactRepository.apply_search_terms (no search provided)")
            return stmt
        columns: Iterable = [
            Contact.first_name,
            Contact.last_name,
            Contact.email,
            Contact.title,
            Contact.seniority,
            Contact.text_search,
            company.name,
            company.address,
            company.city,
            company.state,
            company.country,
            func.array_to_string(company.industries, ","),
            func.array_to_string(company.keywords, ","),
        ]
        stmt = apply_search(stmt, search, columns)
        logger.debug("Exiting ContactRepository.apply_search_terms")
        return stmt

    async def list_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        """Return contacts with associated company and metadata rows."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug(
            "Listing contacts: limit=%d offset=%d ordering=%s filters=%s",
            limit,
            offset,
            filters.ordering,
            active_filter_keys,
        )
        stmt, company_alias, contact_meta_alias, company_meta_alias = self.base_query()
        stmt = self.apply_filters(stmt, filters, company_alias, company_meta_alias, contact_meta_alias)
        stmt = self.apply_search_terms(stmt, filters.search, company_alias)
        ordering_map = {
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "email": Contact.email,
            "company": company_alias.name,
            "employees": company_alias.employees_count,
            "annual_revenue": company_alias.annual_revenue,
            "total_funding": company_alias.total_funding,
            "seniority": Contact.seniority,
            "created_at": Contact.created_at,
        }
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        rows = result.fetchall()
        logger.debug("Retrieved %d contacts from repository query", len(rows))
        return rows

    async def create_contact(self, session: AsyncSession, data: dict[str, Any]) -> Contact:
        """Persist a new contact record."""
        logger.debug("Creating contact with fields: %s", sorted(data.keys()))
        contact = Contact(**data)
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            result = await session.execute(select(func.max(Contact.id)))
            next_id = (result.scalar_one_or_none() or 0) + 1
            contact.id = next_id
        session.add(contact)
        await session.flush()
        await session.refresh(contact)
        logger.debug("Created contact: id=%s uuid=%s", contact.id, contact.uuid)
        return contact

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
    ) -> int:
        """Count contacts that match the supplied filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug("Counting contacts with filters=%s", active_filter_keys)
        company_alias = aliased(Company, name="company_for_count")
        stmt = select(func.count(Contact.id)).select_from(Contact).outerjoin(
            company_alias, Contact.company_id == company_alias.uuid
        )
        stmt = self.apply_filters(stmt, filters, company_alias)
        stmt = self.apply_search_terms(stmt, filters.search, company_alias)
        result = await session.execute(stmt)
        total = result.scalar_one()
        logger.debug("Counted contacts total=%d", total)
        return total

    async def list_attribute_values(
        self,
        session: AsyncSession,
        column,
        filters: ContactFilterParams,
        params: AttributeListParams,
    ) -> list[str]:
        """Return attribute values for autocomplete/dropdown endpoints."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug(
            "Listing attribute values: limit=%d offset=%d ordering=%s filters=%s",
            params.limit,
            params.offset,
            params.ordering,
            active_filter_keys,
        )
        stmt = select(distinct(column)).select_from(Contact)
        company_alias = aliased(Company, name="company_attribute")
        contact_meta_alias = aliased(ContactMetadata, name="contact_meta_attribute")
        company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")

        stmt = stmt.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
        stmt = stmt.outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
        stmt = stmt.outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)

        stmt = self.apply_filters(
            stmt,
            filters,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
        )
        stmt = self.apply_search_terms(stmt, params.search or filters.search, company_alias)
        stmt = apply_ordering(
            stmt,
            params.ordering,
            {"value": column},
        )
        stmt = stmt.limit(params.limit).offset(params.offset)
        result = await session.execute(stmt)
        values = [value for (value,) in result.fetchall() if value]
        logger.debug("Retrieved %d attribute values", len(values))
        return values

    async def get_contact_with_relations(
        self,
        session: AsyncSession,
        contact_id: int,
    ) -> Optional[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        """Fetch a contact and its related company metadata."""
        logger.debug("Getting contact with relations: contact_id=%d", contact_id)
        stmt, _, _, _ = self.base_query()
        stmt = stmt.where(Contact.id == contact_id)
        result = await session.execute(stmt)
        row = result.first()
        logger.debug(
            "Contact with relations %sfound for contact_id=%d",
            "" if row else "not ",
            contact_id,
        )
        return row

