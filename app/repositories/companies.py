"""Repository providing company-specific query utilities."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from sqlalchemy import Select, and_, cast, distinct, func, or_, select, true
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import lateral

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.repositories.base import AsyncRepository
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.utils.query import (
    apply_ilike_filter,
    apply_numeric_range_filter,
    apply_ordering,
    apply_search,
)

logger = get_logger(__name__)


class CompanyRepository(AsyncRepository[Company]):
    """Data access helpers for company-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the Company model."""
        logger.debug("Entering CompanyRepository.__init__")
        super().__init__(Company)
        logger.debug("Exiting CompanyRepository.__init__")

    def base_query(self) -> tuple[Select, CompanyMetadata]:
        """Construct the base query with joins to company metadata table."""
        logger.debug("Entering CompanyRepository.base_query")
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")

        stmt: Select = (
            select(Company, company_meta_alias)
            .select_from(Company)
            .outerjoin(company_meta_alias, Company.uuid == company_meta_alias.uuid)
        )
        logger.debug("Exiting CompanyRepository.base_query")
        return stmt, company_meta_alias

    def apply_filters(
        self,
        stmt: Select,
        filters: CompanyFilterParams,
        company_meta: CompanyMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement."""
        logger.debug(
            "Entering CompanyRepository.apply_filters filters=%s",
            sorted(filters.model_dump(exclude_none=True).keys()),
        )
        stmt = self._apply_multi_value_filter(stmt, Company.name, filters.name)
        stmt = self._apply_multi_value_filter(stmt, Company.address, filters.address)
        stmt = self._apply_multi_value_filter(stmt, Company.text_search, filters.company_location)
        
        if filters.employees_count is not None:
            stmt = stmt.where(Company.employees_count == filters.employees_count)
        stmt = apply_numeric_range_filter(
            stmt,
            Company.employees_count,
            filters.employees_min,
            filters.employees_max,
        )
        
        if filters.annual_revenue is not None:
            stmt = stmt.where(Company.annual_revenue == filters.annual_revenue)
        stmt = apply_numeric_range_filter(
            stmt,
            Company.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
        )
        
        if filters.total_funding is not None:
            stmt = stmt.where(Company.total_funding == filters.total_funding)
        stmt = apply_numeric_range_filter(
            stmt,
            Company.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
        )

        dialect = (dialect_name or "").lower()

        if filters.technologies:
            stmt = self._apply_array_text_filter(
                stmt,
                Company.technologies,
                filters.technologies,
                dialect=dialect,
            )
        if filters.exclude_technologies:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.technologies,
                filters.exclude_technologies,
                dialect=dialect,
            )
        if filters.keywords:
            stmt = self._apply_array_text_filter(
                stmt,
                Company.keywords,
                filters.keywords,
                dialect=dialect,
            )
        if filters.exclude_keywords:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.keywords,
                filters.exclude_keywords,
                dialect=dialect,
            )
        if filters.industries:
            stmt = self._apply_array_text_filter(
                stmt,
                Company.industries,
                filters.industries,
                dialect=dialect,
            )
        if filters.exclude_industries:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.industries,
                filters.exclude_industries,
                dialect=dialect,
            )

        if filters.exclude_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Company.text_search, filters.exclude_locations)

        if company_meta is not None:
            stmt = self._apply_multi_value_filter(stmt, company_meta.city, filters.city)
            stmt = self._apply_multi_value_filter(stmt, company_meta.state, filters.state)
            stmt = self._apply_multi_value_filter(stmt, company_meta.country, filters.country)
            stmt = self._apply_multi_value_filter(stmt, company_meta.phone_number, filters.phone_number)
            stmt = self._apply_multi_value_filter(stmt, company_meta.website, filters.website)
            stmt = self._apply_multi_value_filter(stmt, company_meta.linkedin_url, filters.linkedin_url)
            stmt = self._apply_multi_value_filter(stmt, company_meta.facebook_url, filters.facebook_url)
            stmt = self._apply_multi_value_filter(stmt, company_meta.twitter_url, filters.twitter_url)
            stmt = self._apply_multi_value_filter(stmt, company_meta.latest_funding, filters.latest_funding)
            
            if filters.latest_funding_amount_min is not None:
                stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
            if filters.latest_funding_amount_max is not None:
                stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)

        if filters.created_at_after is not None:
            stmt = stmt.where(Company.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Company.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Company.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Company.updated_at <= filters.updated_at_before)

        logger.debug("Exiting CompanyRepository.apply_filters")
        return stmt

    def apply_search_terms(
        self,
        stmt: Select,
        search: Optional[str],
        company_meta: CompanyMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply case-insensitive search across selected text columns."""
        logger.debug(
            "Entering CompanyRepository.apply_search_terms search_present=%s",
            bool(search),
        )
        if not search:
            logger.debug("Exiting CompanyRepository.apply_search_terms (no search provided)")
            return stmt
        dialect = (dialect_name or "").lower()
        columns: list[Any] = [
            Company.name,
            Company.address,
            Company.text_search,
            self._array_column_as_text(Company.industries, dialect),
            self._array_column_as_text(Company.keywords, dialect),
            self._array_column_as_text(Company.technologies, dialect),
        ]
        if company_meta is not None:
            columns.extend(
                [
                    company_meta.city,
                    company_meta.state,
                    company_meta.country,
                    company_meta.phone_number,
                    company_meta.website,
                    company_meta.linkedin_url,
                ]
            )
        stmt = apply_search(stmt, search, columns)
        logger.debug("Exiting CompanyRepository.apply_search_terms")
        return stmt

    async def list_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[Company, CompanyMetadata]]:
        """Return companies with associated metadata rows."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug(
            "Listing companies: limit=%d offset=%d ordering=%s filters=%s",
            limit,
            offset,
            filters.ordering,
            active_filter_keys,
        )
        stmt, company_meta_alias = self.base_query()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        ordering_map = {
            "created_at": Company.created_at,
            "updated_at": Company.updated_at,
            "name": Company.name,
            "employees_count": Company.employees_count,
            "employees": Company.employees_count,
            "annual_revenue": Company.annual_revenue,
            "total_funding": Company.total_funding,
            "city": company_meta_alias.city,
            "state": company_meta_alias.state,
            "country": company_meta_alias.country,
            "latest_funding_amount": company_meta_alias.latest_funding_amount,
            "industries": cast(Company.industries, Text),
            "keywords": cast(Company.keywords, Text),
            "technologies": cast(Company.technologies, Text),
        }
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        rows = result.fetchall()
        logger.debug("Retrieved %d companies from repository query", len(rows))
        return rows

    async def create_company(self, session: AsyncSession, data: dict[str, Any]) -> Company:
        """Persist a new company record."""
        logger.debug("Creating company with fields: %s", sorted(data.keys()))
        company = Company(**data)
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            result = await session.execute(select(func.max(Company.id)))
            next_id = (result.scalar_one_or_none() or 0) + 1
            company.id = next_id
        session.add(company)
        await session.flush()
        await session.refresh(company)
        logger.debug("Created company: id=%s uuid=%s", company.id, company.uuid)
        return company

    async def update_company(
        self, session: AsyncSession, company_uuid: str, data: dict[str, Any]
    ) -> Optional[Company]:
        """Update an existing company record."""
        logger.debug("Updating company: company_uuid=%s fields=%s", company_uuid, sorted(data.keys()))
        company = await self.get_by_uuid(session, company_uuid)
        if not company:
            logger.debug("Company not found for update: company_uuid=%s", company_uuid)
            return None
        for key, value in data.items():
            if hasattr(company, key):
                setattr(company, key, value)
        await session.flush()
        await session.refresh(company)
        logger.debug("Updated company: id=%s uuid=%s", company.id, company.uuid)
        return company

    async def delete_company(self, session: AsyncSession, company_uuid: str) -> bool:
        """Delete a company record."""
        logger.debug("Deleting company: company_uuid=%s", company_uuid)
        company = await self.get_by_uuid(session, company_uuid)
        if not company:
            logger.debug("Company not found for deletion: company_uuid=%s", company_uuid)
            return False
        await session.delete(company)
        await session.flush()
        logger.debug("Deleted company: company_uuid=%s", company_uuid)
        return True

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
    ) -> int:
        """Count companies that match the supplied filters."""
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug("Counting companies with filters=%s", active_filter_keys)
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata_for_count")

        stmt = (
            select(func.count(Company.id))
            .select_from(Company)
            .outerjoin(company_meta_alias, Company.uuid == company_meta_alias.uuid)
        )
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        result = await session.execute(stmt)
        total = result.scalar_one()
        logger.debug("Counted companies total=%d", total)
        return total

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        params: AttributeListParams,
        *,
        array_mode: bool = False,
        column_factory: Callable[[Company, CompanyMetadata], Any] | None = None,
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

        company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")

        column_expression = column_factory(Company, company_meta_alias)

        stmt = select(column_expression).select_from(Company)
        stmt = stmt.outerjoin(company_meta_alias, Company.uuid == company_meta_alias.uuid)

        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            params.search or filters.search,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = stmt.where(column_expression.isnot(None))
        
        # Apply distinct BEFORE ordering to avoid SQL issues
        if params.distinct:
            stmt = stmt.distinct()
        
        # Apply ordering after distinct - only order by the selected column
        ordering_map = {"value": column_expression}
        stmt = apply_ordering(
            stmt,
            params.ordering,
            ordering_map,
        )
        
        # When using DISTINCT, ensure there's always an explicit ORDER BY
        if params.distinct and not params.ordering:
            stmt = stmt.order_by(column_expression.asc())
        
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
        column_factory: Callable[[Company, CompanyMetadata], Any],
        filters: CompanyFilterParams,
        params: AttributeListParams,
    ) -> list[str]:
        """Optimized array attribute extraction using lateral unnesting."""
        stmt, company_meta_alias = self.base_query()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self.apply_filters(
            stmt,
            filters,
            company_meta_alias,
            dialect_name=dialect_name,
        )
        stmt = self.apply_search_terms(
            stmt,
            filters.search,
            company_meta_alias,
            dialect_name=dialect_name,
        )

        filtered_companies = (
            stmt.with_only_columns(Company.uuid)
            .where(Company.uuid.isnot(None))
            .distinct()
            .subquery()
        )

        source_company = aliased(Company, name="array_company")
        source_company_meta = aliased(CompanyMetadata, name="array_company_meta")
        array_column = column_factory(source_company, source_company_meta)

        value_selectable = lateral(
            select(func.unnest(array_column).label("value"))
        ).alias("attribute_values")
        value_column = value_selectable.c.value

        attr_stmt = (
            select(value_column)
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
        
        # Apply distinct to the statement if requested
        if params.distinct:
            attr_stmt = attr_stmt.distinct()

        attr_stmt = attr_stmt.limit(params.limit).offset(params.offset)
        result = await session.execute(attr_stmt)
        values = [value for (value,) in result.fetchall() if value]
        return values

    async def get_company_with_metadata(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[tuple[Company, CompanyMetadata]]:
        """Fetch a company and its related metadata."""
        logger.debug("Getting company with metadata: company_uuid=%s", company_uuid)
        stmt, _ = self.base_query()
        stmt = stmt.where(Company.uuid == company_uuid)
        result = await session.execute(stmt)
        row = result.first()
        logger.debug(
            "Company with metadata %sfound for company_uuid=%s",
            "" if row else "not ",
            company_uuid,
        )
        return row

    async def get_company_by_uuid_with_metadata(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[tuple[Company, CompanyMetadata]]:
        """Fetch a company and its related metadata by UUID."""
        logger.debug("Getting company with metadata: company_uuid=%s", company_uuid)
        stmt, _ = self.base_query()
        stmt = stmt.where(Company.uuid == company_uuid)
        result = await session.execute(stmt)
        row = result.first()
        logger.debug(
            "Company with metadata %sfound for company_uuid=%s",
            "" if row else "not ",
            company_uuid,
        )
        return row

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

        values = CompanyRepository._split_filter_values(raw_value)
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
        normalized_values = CompanyRepository._split_filter_values(raw_value)
        search_terms = normalized_values or ([raw_value] if raw_value else [])
        if not search_terms:
            return stmt

        array_text = CompanyRepository._array_column_as_text(column, dialect)
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
        array_text = CompanyRepository._array_column_as_text(column, dialect)
        negative_conditions = [~array_text.ilike(f"%{token}%") for token in tokens]
        combined_negative = and_(*negative_conditions)
        return stmt.where(or_(column.is_(None), combined_negative))

    @staticmethod
    def _array_column_as_text(column, dialect: str):
        """Return an expression suitable for ILIKE matching across dialects."""
        if dialect == "postgresql":
            return func.array_to_string(column, ",")
        return cast(column, Text)

