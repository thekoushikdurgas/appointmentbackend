"""Repository providing contact-specific query utilities."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from sqlalchemy import Select, and_, cast, distinct, func, or_, select, true
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import lateral

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
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement."""
        logger.debug(
            "Entering ContactRepository.apply_filters filters=%s",
            sorted(filters.model_dump(exclude_none=True).keys()),
        )
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.title, filters.title)
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, company.name, filters.company)
        stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_location)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        if filters.employees_count is not None:
            stmt = stmt.where(company.employees_count == filters.employees_count)
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority)
        if filters.exclude_company_locations:
            stmt = self._apply_multi_value_exclusion(stmt, company.text_search, filters.exclude_company_locations)
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        if filters.exclude_titles:
            lowered_titles = tuple(title.lower() for title in filters.exclude_titles if title)
            if lowered_titles:
                stmt = stmt.where(
                    or_(
                        Contact.title.is_(None),
                        func.lower(Contact.title).notin_(lowered_titles),
                    )
                )
        if filters.exclude_company_ids:
            exclusion_values = tuple(filters.exclude_company_ids)
            exclusion_condition = ~Contact.company_id.in_(exclusion_values)
            stmt = stmt.where(or_(Contact.company_id.is_(None), exclusion_condition))
        if company_meta is not None:
            if filters.latest_funding_amount_min is not None:
                stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
            if filters.latest_funding_amount_max is not None:
                stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)
        stmt = apply_numeric_range_filter(
            stmt,
            company.employees_count,
            filters.employees_min,
            filters.employees_max,
        )
        if filters.annual_revenue is not None:
            stmt = stmt.where(company.annual_revenue == filters.annual_revenue)
        stmt = apply_numeric_range_filter(
            stmt,
            company.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
        )
        if filters.total_funding is not None:
            stmt = stmt.where(company.total_funding == filters.total_funding)
        stmt = apply_numeric_range_filter(
            stmt,
            company.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
        )

        dialect = (dialect_name or "").lower()

        if filters.technologies:
            stmt = self._apply_array_text_filter(
                stmt,
                company.technologies,
                filters.technologies,
                dialect=dialect,
            )
        if filters.exclude_technologies:
            stmt = self._apply_array_text_exclusion(
                stmt,
                company.technologies,
                filters.exclude_technologies,
                dialect=dialect,
            )
        if filters.keywords:
            stmt = self._apply_array_text_filter(
                stmt,
                company.keywords,
                filters.keywords,
                dialect=dialect,
            )
        if filters.exclude_keywords:
            stmt = self._apply_array_text_exclusion(
                stmt,
                company.keywords,
                filters.exclude_keywords,
                dialect=dialect,
            )
        if filters.industries:
            stmt = self._apply_array_text_filter(
                stmt,
                company.industries,
                filters.industries,
                dialect=dialect,
            )
        if filters.exclude_industries:
            stmt = self._apply_array_text_exclusion(
                stmt,
                company.industries,
                filters.exclude_industries,
                dialect=dialect,
            )

        if filters.department:
            stmt = self._apply_array_text_filter(
                stmt,
                Contact.departments,
                filters.department,
                dialect=dialect,
            )
        if filters.exclude_departments:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Contact.departments,
                filters.exclude_departments,
                dialect=dialect,
            )

        if filters.company_address:
            stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_address)
        stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
        if contact_meta is not None:
            stmt = self._apply_multi_value_filter(
                stmt,
                contact_meta.work_direct_phone,
                filters.work_direct_phone,
            )
            stmt = self._apply_multi_value_filter(stmt, contact_meta.home_phone, filters.home_phone)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.other_phone, filters.other_phone)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.city, filters.city)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.state, filters.state)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.country, filters.country)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.linkedin_url, filters.person_linkedin_url)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.website, filters.website)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.stage, filters.stage)
        if company_meta is not None:
            stmt = self._apply_multi_value_filter(
                stmt,
                company_meta.company_name_for_emails,
                filters.company_name_for_emails,
            )
            stmt = self._apply_multi_value_filter(stmt, company_meta.phone_number, filters.corporate_phone)
            stmt = self._apply_multi_value_filter(stmt, company_meta.phone_number, filters.company_phone)
            stmt = self._apply_multi_value_filter(stmt, company_meta.city, filters.company_city)
            stmt = self._apply_multi_value_filter(stmt, company_meta.state, filters.company_state)
            stmt = self._apply_multi_value_filter(stmt, company_meta.country, filters.company_country)
            stmt = self._apply_multi_value_filter(stmt, company_meta.linkedin_url, filters.company_linkedin_url)

        if filters.facebook_url and (contact_meta is not None or company_meta is not None):
            facebook_tokens = self._split_filter_values(filters.facebook_url) or [filters.facebook_url.strip()]
            facebook_tokens = [token for token in facebook_tokens if token]
            if facebook_tokens:
                or_conditions = []
                for token in facebook_tokens:
                    like_expression = f"%{token}%"
                    column_conditions = []
                    if contact_meta is not None:
                        column_conditions.append(contact_meta.facebook_url.ilike(like_expression))
                    if company_meta is not None:
                        column_conditions.append(company_meta.facebook_url.ilike(like_expression))
                    if column_conditions:
                        or_conditions.append(or_(*column_conditions))
                if or_conditions:
                    stmt = stmt.where(or_(*or_conditions))

        if filters.twitter_url and (contact_meta is not None or company_meta is not None):
            twitter_tokens = self._split_filter_values(filters.twitter_url) or [filters.twitter_url.strip()]
            twitter_tokens = [token for token in twitter_tokens if token]
            if twitter_tokens:
                or_conditions = []
                for token in twitter_tokens:
                    like_expression = f"%{token}%"
                    column_conditions = []
                    if contact_meta is not None:
                        column_conditions.append(contact_meta.twitter_url.ilike(like_expression))
                    if company_meta is not None:
                        column_conditions.append(company_meta.twitter_url.ilike(like_expression))
                    if column_conditions:
                        or_conditions.append(or_(*column_conditions))
                if or_conditions:
                    stmt = stmt.where(or_(*or_conditions))

        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)

        logger.debug("Exiting ContactRepository.apply_filters")
        return stmt

    def apply_search_terms(
        self,
        stmt: Select,
        search: Optional[str],
        company: Company,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply case-insensitive search across selected text columns."""
        logger.debug(
            "Entering ContactRepository.apply_search_terms search_present=%s",
            bool(search),
        )
        if not search:
            logger.debug("Exiting ContactRepository.apply_search_terms (no search provided)")
            return stmt
        dialect = (dialect_name or "").lower()
        columns: list[Any] = [
            Contact.first_name,
            Contact.last_name,
            Contact.email,
            Contact.title,
            Contact.seniority,
            Contact.text_search,
            company.name,
            company.address,
            self._array_column_as_text(company.industries, dialect),
            self._array_column_as_text(company.keywords, dialect),
        ]
        if company_meta is not None:
            columns.extend(
                [
                    company_meta.city,
                    company_meta.state,
                    company_meta.country,
                    company_meta.phone_number,
                    company_meta.website,
                ]
            )
        if contact_meta is not None:
            columns.extend(
                [
                    contact_meta.city,
                    contact_meta.state,
                    contact_meta.country,
                    contact_meta.linkedin_url,
                    contact_meta.twitter_url,
                ]
            )
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
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )
        ordering_map = {
            "created_at": Contact.created_at,
            "updated_at": Contact.updated_at,
            "employees": company_alias.employees_count,
            "annual_revenue": company_alias.annual_revenue,
            "total_funding": company_alias.total_funding,
            "latest_funding_amount": company_meta_alias.latest_funding_amount,
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "company": company_alias.name,
            "company_name_for_emails": company_meta_alias.company_name_for_emails,
            "email": Contact.email,
            "email_status": Contact.email_status,
            "primary_email_catch_all_status": getattr(
                Contact, "primary_email_catch_all_status", Contact.email_status
            ),
            "seniority": Contact.seniority,
            "departments": cast(Contact.departments, Text),
            "work_direct_phone": contact_meta_alias.work_direct_phone,
            "home_phone": contact_meta_alias.home_phone,
            "mobile_phone": Contact.mobile_phone,
            "corporate_phone": company_meta_alias.phone_number,
            "company_phone": company_meta_alias.phone_number,
            "other_phone": contact_meta_alias.other_phone,
            "stage": contact_meta_alias.stage,
            "industry": cast(company_alias.industries, Text),
            "keywords": cast(company_alias.keywords, Text),
            "technologies": cast(company_alias.technologies, Text),
            "person_linkedin_url": contact_meta_alias.linkedin_url,
            "website": contact_meta_alias.website,
            "company_linkedin_url": company_meta_alias.linkedin_url,
            "facebook_url": func.coalesce(
                contact_meta_alias.facebook_url, company_meta_alias.facebook_url
            ),
            "twitter_url": func.coalesce(
                contact_meta_alias.twitter_url, company_meta_alias.twitter_url
            ),
            "city": contact_meta_alias.city,
            "state": contact_meta_alias.state,
            "country": contact_meta_alias.country,
            "company_address": company_alias.address,
            "company_city": company_meta_alias.city,
            "company_state": company_meta_alias.state,
            "company_country": company_meta_alias.country,
            "latest_funding": company_meta_alias.latest_funding,
            "last_raised_at": company_meta_alias.last_raised_at,
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
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(stmt, filters, company_alias, dialect_name=dialect_name)
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_alias,
            dialect_name=dialect_name,
        )
        result = await session.execute(stmt)
        total = result.scalar_one()
        logger.debug("Counted contacts total=%d", total)
        return total

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        *,
        array_mode: bool = False,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Any] | None = None,
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
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        use_array_optimization = array_mode and dialect_name == "postgresql"

        if use_array_optimization and column_factory is not None:
            values = await self._list_array_attribute_values(session, column_factory, filters, params)
            logger.debug("Retrieved %d array attribute values (optimized)", len(values))
            return values

        if column_factory is None:
            raise ValueError("column_factory must be provided for attribute value queries.")

        company_alias = aliased(Company, name="company_attribute")
        contact_meta_alias = aliased(ContactMetadata, name="contact_meta_attribute")
        company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")

        column_expression = column_factory(Contact, company_alias, contact_meta_alias, company_meta_alias)
        selectable_column = distinct(column_expression) if params.distinct else column_expression

        stmt = select(selectable_column).select_from(Contact)
        stmt = stmt.outerjoin(company_alias, Contact.company_id == company_alias.uuid)
        stmt = stmt.outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
        stmt = stmt.outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)

        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            params.search or filters.search,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )
        ordering_map = {"value": column_expression}
        stmt = apply_ordering(
            stmt,
            params.ordering,
            ordering_map,
        )
        stmt = stmt.where(column_expression.isnot(None))
        stmt = stmt.limit(params.limit).offset(params.offset)
        result = await session.execute(stmt)
        values = []
        for (value,) in result.fetchall():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            values.append(value)
        logger.debug("Retrieved %d attribute values", len(values))
        return values

    async def _list_array_attribute_values(
        self,
        session: AsyncSession,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Any],
        filters: ContactFilterParams,
        params: AttributeListParams,
    ) -> list[str]:
        """Optimized array attribute extraction using lateral unnesting."""
        stmt, company_alias, contact_meta_alias, company_meta_alias = self.base_query()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_alias,
            company_meta_alias,
            contact_meta_alias,
            dialect_name=dialect_name,
        )

        filtered_companies = (
            stmt.with_only_columns(company_alias.uuid)
            .where(company_alias.uuid.isnot(None))
            .distinct()
            .subquery()
        )

        source_company = aliased(Company, name="array_company")
        source_contact_meta = aliased(ContactMetadata, name="array_contact_meta")
        source_company_meta = aliased(CompanyMetadata, name="array_company_meta")
        array_column = column_factory(Contact, source_company, source_contact_meta, source_company_meta)

        value_selectable = lateral(
            select(func.unnest(array_column).label("value"))
        ).alias("attribute_values")
        value_column = value_selectable.c.value

        attr_stmt = (
            select(distinct(value_column) if params.distinct else value_column)
            .select_from(filtered_companies)
            .join(source_company, source_company.uuid == filtered_companies.c.uuid)
            .join(value_selectable, true())
        )

        trimmed_value = func.nullif(func.trim(value_column), "")
        attr_stmt = attr_stmt.where(value_column.isnot(None))
        attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
        search_term = params.search or filters.search
        if search_term:
            attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_term}%"))

        ordering_map = {"value": value_column}
        attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
        if params.ordering is None:
            attr_stmt = attr_stmt.order_by(value_column.asc())

        attr_stmt = attr_stmt.limit(params.limit).offset(params.offset)
        result = await session.execute(attr_stmt)
        values = [value for (value,) in result.fetchall() if value]
        return values

    @staticmethod
    def _split_filter_values(raw_value: str) -> list[str]:
        """Normalize comma-delimited filter strings into a list of tokens."""
        return [token.strip() for token in raw_value.split(",") if token.strip()]

    @staticmethod
    def _apply_multi_value_filter(
        stmt: Select,
        column,
        raw_value: str | None,
    ) -> Select:
        """Apply substring matching supporting comma-separated values with OR semantics."""
        if raw_value is None:
            return stmt

        values = ContactRepository._split_filter_values(raw_value)
        if not values:
            return apply_ilike_filter(stmt, column, raw_value.strip())

        if len(values) == 1:
            return apply_ilike_filter(stmt, column, values[0])

        conditions = [column.ilike(f"%{value}%") for value in values]
        return stmt.where(or_(*conditions))

    @staticmethod
    def _apply_array_text_filter(
        stmt: Select,
        column,
        raw_value: str,
        *,
        dialect: str,
    ) -> Select:
        """Apply substring matching to a text-array column by collapsing into comma-delimited text."""
        normalized_values = ContactRepository._split_filter_values(raw_value)
        search_terms = normalized_values or ([raw_value] if raw_value else [])
        if not search_terms:
            return stmt

        array_text = ContactRepository._array_column_as_text(column, dialect)
        conditions = [array_text.ilike(f"%{value}%") for value in search_terms]
        return stmt.where(or_(*conditions))

    @staticmethod
    def _apply_multi_value_exclusion(
        stmt: Select,
        column,
        values: list[str] | None,
    ) -> Select:
        """Exclude rows whose column matches any provided substring (case-insensitive)."""
        if not values:
            return stmt
        tokens = [token.strip() for token in values if isinstance(token, str) and token.strip()]
        if not tokens:
            return stmt
        negative_conditions = [~column.ilike(f"%{token}%") for token in tokens]
        combined_negative = and_(*negative_conditions)
        return stmt.where(or_(column.is_(None), combined_negative))

    @staticmethod
    def _apply_array_text_exclusion(
        stmt: Select,
        column,
        values: list[str] | None,
        *,
        dialect: str,
    ) -> Select:
        """Exclude rows whose array text representation matches any provided substring."""
        if not values:
            return stmt
        tokens = [token.strip() for token in values if isinstance(token, str) and token.strip()]
        if not tokens:
            return stmt
        array_text = ContactRepository._array_column_as_text(column, dialect)
        negative_conditions = [~array_text.ilike(f"%{token}%") for token in tokens]
        combined_negative = and_(*negative_conditions)
        return stmt.where(or_(column.is_(None), combined_negative))

    @staticmethod
    def _array_column_as_text(column, dialect: str):
        """Return an expression suitable for ILIKE matching across dialects."""
        if dialect == "postgresql":
            return func.array_to_string(column, ",")
        return cast(column, Text)

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

