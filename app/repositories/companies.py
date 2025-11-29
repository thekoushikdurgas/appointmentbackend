"""Repository providing company-specific query utilities."""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from sqlalchemy import Select, and_, cast, distinct, func, or_, select, text, true, exists
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import lateral

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.repositories.base import AsyncRepository
from app.schemas.filters import AttributeListParams, CompanyFilterParams
from app.utils.batch_lookup import fetch_company_metadata_by_uuid
from app.utils.query import (
    apply_ilike_filter,
    apply_numeric_range_filter,
    apply_ordering,
    apply_search,
)
from app.utils.query_batch import QueryBatcher

logger = get_logger(__name__)


class CompanyRepository(AsyncRepository[Company]):
    """Data access helpers for company-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the Company model."""
        logger.debug("Entering CompanyRepository.__init__")
        super().__init__(Company)
        logger.debug("Exiting CompanyRepository.__init__")

    @staticmethod
    def _needs_company_metadata_exists_subquery(filters: CompanyFilterParams) -> bool:
        """Determine if CompanyMetadata table EXISTS subquery is needed based on filters."""
        company_meta_fields = [
            filters.city, filters.state, filters.country, filters.phone_number,
            filters.website, filters.linkedin_url, filters.facebook_url,
            filters.twitter_url, filters.latest_funding, filters.latest_funding_amount_min,
            filters.latest_funding_amount_max,
        ]
        return any(field is not None for field in company_meta_fields)

    @staticmethod
    def _needs_company_metadata_exists_subquery_for_search(search: Optional[str]) -> bool:
        """Determine if CompanyMetadata EXISTS subquery is needed for search term."""
        return search is not None and bool(search.strip())

    def base_query_minimal(self) -> Select:
        """Construct minimal query with only Company table (no joins)."""
        logger.debug("Entering CompanyRepository.base_query_minimal")
        stmt: Select = select(Company)
        logger.debug("Exiting CompanyRepository.base_query_minimal")
        return stmt


    def apply_filters(
        self,
        stmt: Select,
        filters: CompanyFilterParams,
        company_meta: CompanyMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement.
        
        DEPRECATED: This method is deprecated. The company_meta parameter is ignored.
        Use _apply_filters_with_exists() directly instead.
        
        This method now delegates to _apply_filters_with_exists() which uses EXISTS subqueries
        instead of JOINs for better performance.
        """
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

    def _build_ordering_map_with_subqueries(
        self,
        ordering: Optional[str],
        *,
        dialect_name: str | None = None,
    ) -> dict[str, Any]:
        """Build ordering map using subqueries for CompanyMetadata columns."""
        from sqlalchemy import select as sql_select
        
        ordering_map = {
            "created_at": Company.created_at,
            "updated_at": Company.updated_at,
            "name": Company.name,
            "employees_count": Company.employees_count,
            "employees": Company.employees_count,
            "annual_revenue": Company.annual_revenue,
            "total_funding": Company.total_funding,
            "industries": cast(Company.industries, Text),
            "keywords": cast(Company.keywords, Text),
            "technologies": cast(Company.technologies, Text),
        }
        
        if not ordering:
            return ordering_map
        
        ordering_lower = ordering.lower()
        
        # CompanyMetadata fields - use subqueries
        if any(field in ordering_lower for field in ["latest_funding_amount", "city", "state", "country", "phone_number", "website", "linkedin_url", "latest_funding", "last_raised_at"]):
            if "city" in ordering_lower:
                ordering_map["city"] = (
                    sql_select(CompanyMetadata.city)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "state" in ordering_lower:
                ordering_map["state"] = (
                    sql_select(CompanyMetadata.state)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "country" in ordering_lower:
                ordering_map["country"] = (
                    sql_select(CompanyMetadata.country)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "latest_funding_amount" in ordering_lower:
                ordering_map["latest_funding_amount"] = (
                    sql_select(CompanyMetadata.latest_funding_amount)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "phone_number" in ordering_lower:
                ordering_map["phone_number"] = (
                    sql_select(CompanyMetadata.phone_number)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "website" in ordering_lower:
                ordering_map["website"] = (
                    sql_select(CompanyMetadata.website)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "linkedin_url" in ordering_lower:
                ordering_map["linkedin_url"] = (
                    sql_select(CompanyMetadata.linkedin_url)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "latest_funding" in ordering_lower:
                ordering_map["latest_funding"] = (
                    sql_select(CompanyMetadata.latest_funding)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
            if "last_raised_at" in ordering_lower:
                ordering_map["last_raised_at"] = (
                    sql_select(CompanyMetadata.last_raised_at)
                    .where(CompanyMetadata.uuid == Company.uuid)
                    .scalar_subquery()
                )
        
        return ordering_map

    async def list_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: Optional[int],
        offset: int,
    ) -> Sequence[Company]:
        """Return companies matching the filters.
        
        Uses EXISTS subqueries instead of JOINs for filtering on CompanyMetadata.
        Returns only Company objects - metadata should be fetched separately.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug(
            "Listing companies: limit=%s offset=%d ordering=%s filters=%s",
            limit,
            offset,
            filters.ordering,
            active_filter_keys,
        )
        
        # Use minimal query (no joins)
        stmt = self.base_query_minimal()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        
        # Apply filters using EXISTS subqueries
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms using EXISTS subqueries
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        # Build ordering map using subqueries for CompanyMetadata columns
        ordering_map = self._build_ordering_map_with_subqueries(filters.ordering, dialect_name=dialect_name)
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        
        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        
        # Use streaming for large result sets to reduce memory usage
        if limit and limit > 10000:
            logger.debug("Using batched query for large result set limit=%d", limit)
            batcher = QueryBatcher(session, stmt, batch_size=5000)
            rows = await batcher.fetch_all()
        else:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        
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
        logger.debug("Created company: uuid=%s", company.uuid)
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
        logger.debug("Updated company: uuid=%s", company.uuid)
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

    def _apply_filters_with_exists(
        self,
        stmt: Select,
        filters: CompanyFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filters using EXISTS subqueries instead of joins for better performance in count queries."""
        from sqlalchemy import exists
        
        logger.debug("Applying filters with EXISTS subqueries")
        dialect = (dialect_name or "").lower()
        
        # Company-only filters (no EXISTS needed)
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
        
        # CompanyMetadata filters using EXISTS
        if self._needs_company_metadata_exists_subquery(filters):
            company_meta_subq = (
                select(1)
                .select_from(CompanyMetadata)
                .where(CompanyMetadata.uuid == Company.uuid)
            )
            
            if filters.city:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.city, filters.city
                )
            if filters.state:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.state, filters.state
                )
            if filters.country:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.country, filters.country
                )
            if filters.phone_number:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.phone_number, filters.phone_number
                )
            if filters.website:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.website, filters.website
                )
            if filters.linkedin_url:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.linkedin_url, filters.linkedin_url
                )
            if filters.facebook_url:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.facebook_url, filters.facebook_url
                )
            if filters.twitter_url:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.twitter_url, filters.twitter_url
                )
            if filters.latest_funding:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.latest_funding, filters.latest_funding
                )
            if filters.latest_funding_amount_min is not None:
                company_meta_subq = company_meta_subq.where(
                    CompanyMetadata.latest_funding_amount >= filters.latest_funding_amount_min
                )
            if filters.latest_funding_amount_max is not None:
                company_meta_subq = company_meta_subq.where(
                    CompanyMetadata.latest_funding_amount <= filters.latest_funding_amount_max
                )
            
            stmt = stmt.where(exists(company_meta_subq))
        
        # Temporal filters
        if filters.created_at_after is not None:
            stmt = stmt.where(Company.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Company.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Company.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Company.updated_at <= filters.updated_at_before)
        
        return stmt

    def _apply_search_terms_with_exists(
        self,
        stmt: Select,
        search: str,
        filters: CompanyFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply search terms using EXISTS subqueries when needed."""
        from sqlalchemy import exists
        
        search_stripped = search.strip()
        if not search_stripped:
            return stmt
        
        pattern = f"%{search_stripped}%"
        dialect = (dialect_name or "").lower()
        
        # Company columns (no EXISTS needed)
        company_conditions = [
            Company.name.ilike(pattern),
            Company.address.ilike(pattern),
            Company.text_search.ilike(pattern),
            self._array_column_as_text(Company.industries, dialect).ilike(pattern),
            self._array_column_as_text(Company.keywords, dialect).ilike(pattern),
            self._array_column_as_text(Company.technologies, dialect).ilike(pattern),
        ]
        
        # CompanyMetadata search using EXISTS
        if self._needs_company_metadata_exists_subquery(filters) or self._needs_company_metadata_exists_subquery_for_search(search):
            company_meta_search_subq = (
                select(1)
                .select_from(CompanyMetadata)
                .where(CompanyMetadata.uuid == Company.uuid)
                .where(
                    or_(
                        CompanyMetadata.city.ilike(pattern),
                        CompanyMetadata.state.ilike(pattern),
                        CompanyMetadata.country.ilike(pattern),
                        CompanyMetadata.phone_number.ilike(pattern),
                        CompanyMetadata.website.ilike(pattern),
                        CompanyMetadata.linkedin_url.ilike(pattern),
                    )
                )
            )
            company_conditions.append(exists(company_meta_search_subq))
        
        if company_conditions:
            stmt = stmt.where(or_(*company_conditions))
        
        return stmt

    async def count_companies(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        *,
        use_approximate: bool = False,
    ) -> int:
        """
        Count companies that match the supplied filters.
        
        Optimized for large datasets by using EXISTS subqueries instead of joins
        when filters don't require data from joined tables.
        
        Args:
            session: Database session
            filters: Filter parameters
            use_approximate: If True, use approximate count from pg_class for very large result sets
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug("Counting companies with filters=%s use_approximate=%s", active_filter_keys, use_approximate)
        
        # For very large unfiltered queries, use approximate count
        if use_approximate and not active_filter_keys:
            dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
            if dialect_name == "postgresql":
                try:
                    result = await session.execute(
                        text("SELECT COALESCE(reltuples::bigint, 0) FROM pg_class WHERE relname = 'companies'")
                    )
                    total = result.scalar_one() or 0
                    logger.debug("Counted companies (approximate) total=%d", total)
                    return int(total)
                except Exception as e:
                    logger.debug("Could not use approximate count, falling back to exact: %s", e)
        
        # Use minimal query with EXISTS subqueries instead of joins
        stmt = select(func.count(Company.id)).select_from(Company)
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms if needed
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        result = await session.execute(stmt)
        total = result.scalar_one() or 0
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

        # Convert column_expression to scalar subquery if it references CompanyMetadata
        from sqlalchemy import select as sql_select
        
        # Check if column is from CompanyMetadata
        column_expression = column_factory(Company, None)
        # Try to detect if column_factory returns a CompanyMetadata column
        # If so, convert to scalar subquery
        if hasattr(column_expression, 'table'):
            table = column_expression.table
            if hasattr(table, '__tablename__') and table.__tablename__ == 'companies_metadata':
                # Column is from CompanyMetadata - use scalar subquery
                column_name = getattr(column_expression, 'key', None) or getattr(column_expression, 'name', None)
                if column_name and hasattr(CompanyMetadata, column_name):
                    company_meta_column = getattr(CompanyMetadata, column_name)
                    column_expression = (
                        sql_select(company_meta_column)
                        .where(CompanyMetadata.uuid == Company.uuid)
                        .scalar_subquery()
                    )
        
        stmt = select(column_expression).select_from(Company)

        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        # Apply filters using EXISTS subqueries (no JOINs)
        # For company metadata filters, use EXISTS subqueries
        if self._needs_company_metadata_exists_subquery(filters):
            company_meta_subq = (
                select(1)
                .select_from(CompanyMetadata)
                .where(CompanyMetadata.uuid == Company.uuid)
            )
            
            # Apply company metadata filters to subquery
            if filters.city:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.city, filters.city
                )
            if filters.state:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.state, filters.state
                )
            if filters.country:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.country, filters.country
                )
            if filters.phone_number:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.phone_number, filters.phone_number
                )
            if filters.website:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.website, filters.website
                )
            if filters.linkedin_url:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.linkedin_url, filters.linkedin_url
                )
            if filters.latest_funding:
                company_meta_subq = self._apply_multi_value_filter(
                    company_meta_subq, CompanyMetadata.latest_funding, filters.latest_funding
                )
            if filters.latest_funding_amount_min is not None:
                company_meta_subq = company_meta_subq.where(
                    CompanyMetadata.latest_funding_amount >= filters.latest_funding_amount_min
                )
            if filters.latest_funding_amount_max is not None:
                company_meta_subq = company_meta_subq.where(
                    CompanyMetadata.latest_funding_amount <= filters.latest_funding_amount_max
                )
            
            stmt = stmt.where(exists(company_meta_subq))
        
        # Apply company table filters directly
        stmt = self.apply_filters(stmt, filters, None, dialect_name=dialect_name)
        
        # Apply search terms
        search_term = params.search or filters.search
        if search_term:
            search_stripped = search_term.strip()
            if search_stripped:
                pattern = f"%{search_stripped}%"
                search_conditions = [
                    Company.name.ilike(pattern),
                    Company.address.ilike(pattern),
                    Company.text_search.ilike(pattern),
                ]
                # Add CompanyMetadata search using EXISTS if needed
                if self._needs_company_metadata_exists_subquery(filters):
                    company_meta_search_subq = (
                        select(1)
                        .select_from(CompanyMetadata)
                        .where(CompanyMetadata.uuid == Company.uuid)
                        .where(
                            or_(
                                CompanyMetadata.city.ilike(pattern),
                                CompanyMetadata.state.ilike(pattern),
                                CompanyMetadata.country.ilike(pattern),
                                CompanyMetadata.phone_number.ilike(pattern),
                                CompanyMetadata.website.ilike(pattern),
                                CompanyMetadata.linkedin_url.ilike(pattern),
                            )
                        )
                    )
                    search_conditions.append(exists(company_meta_search_subq))
                
                if search_conditions:
                    stmt = stmt.where(or_(*search_conditions))
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
        
        stmt = stmt.offset(params.offset)
        if params.limit is not None:
            stmt = stmt.limit(params.limit)
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
        # Use minimal query with EXISTS subqueries for filtering
        stmt = self.base_query_minimal()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)

        # Get company UUIDs from filtered query
        filtered_company_uuids_subq = (
            stmt.with_only_columns(Company.uuid)
            .where(Company.uuid.isnot(None))
            .distinct()
        )
        
        # Execute to get company UUIDs
        company_uuids_result = await session.execute(filtered_company_uuids_subq)
        company_uuids = {row[0] for row in company_uuids_result if row[0]}
        
        if not company_uuids:
            logger.debug("No companies match filters, returning empty array attribute list")
            return []
        
        source_company = aliased(Company, name="array_company")
        # Array columns are from Company, so only pass Company to column_factory
        array_column = column_factory(source_company, None)

        # Use subquery to unnest arrays without lateral join
        # Create a subquery that unnests arrays for all matching companies
        unnest_subq = (
            select(
                func.unnest(array_column).label("value"),
                source_company.uuid.label("company_uuid")
            )
            .select_from(source_company)
            .where(source_company.uuid.in_(company_uuids))
            .where(array_column.isnot(None))
        ).subquery()
        
        # Main query selects from the unnested subquery
        attr_stmt = select(unnest_subq.c.value)
        value_column = unnest_subq.c.value

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

        attr_stmt = attr_stmt.offset(params.offset)
        if params.limit is not None:
            attr_stmt = attr_stmt.limit(params.limit)
        result = await session.execute(attr_stmt)
        values = [value for (value,) in result.fetchall() if value]
        return values

    async def get_company_with_metadata(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[tuple[Company, CompanyMetadata]]:
        """Fetch a company and its related metadata using separate queries."""
        logger.debug("Getting company with metadata: company_uuid=%s", company_uuid)
        company = await self.get_by_uuid(session, company_uuid)
        if not company:
            logger.debug("Company not found: company_uuid=%s", company_uuid)
            return None
        
        company_meta = await fetch_company_metadata_by_uuid(session, company_uuid)
        
        logger.debug(
            "Company with metadata %sfound for company_uuid=%s",
            "" if company_meta else "not ",
            company_uuid,
        )
        return (company, company_meta)

    async def get_company_by_uuid_with_metadata(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[tuple[Company, CompanyMetadata]]:
        """Fetch a company and its related metadata by UUID using separate queries."""
        return await self.get_company_with_metadata(session, company_uuid)

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

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: CompanyFilterParams,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[str]:
        """Return company UUIDs that match the supplied filters (efficient UUID-only query).
        
        Optimized to use EXISTS subqueries instead of joins for better performance.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        logger.debug(
            "Getting company UUIDs: limit=%s filters=%s",
            limit,
            active_filter_keys,
        )

        # Use minimal query with EXISTS subqueries instead of joins
        stmt = select(Company.uuid).select_from(Company)
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms if needed
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        stmt = stmt.where(Company.uuid.isnot(None))
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        uuids = [uuid for (uuid,) in result.fetchall() if uuid]
        logger.debug("Retrieved %d company UUIDs", len(uuids))
        return uuids

    @staticmethod
    def _array_column_as_text(column, dialect: str):
        """Return an expression suitable for ILIKE matching across dialects."""
        if dialect == "postgresql":
            return func.array_to_string(column, ",")
        return cast(column, Text)

