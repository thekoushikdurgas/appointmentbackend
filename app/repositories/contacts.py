"""Repository providing contact-specific query utilities."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional, Sequence

from sqlalchemy import Select, and_, cast, distinct, func, or_, select, text, union_all
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.schemas.filters import AttributeListParams, CompanyContactFilterParams, ContactFilterParams
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_company_metadata_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
    fetch_company_by_uuid,
    fetch_company_metadata_by_uuid,
    fetch_contact_metadata_by_uuid,
)
from app.utils.domain import extract_domain_from_url
from app.utils.query import (
    apply_ilike_filter,
    apply_numeric_range_filter,
    apply_ordering,
    apply_search,
)
from app.utils.query_batch import QueryBatcher
from app.utils.exists_subquery_detector import ContactFilterSubqueryDetector


class ContactRepository(AsyncRepository[Contact]):
    """Data access helpers for contact-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the Contact model."""
        super().__init__(Contact)

    @staticmethod
    def _needs_company_exists_subquery(filters: ContactFilterParams) -> bool:
        """Determine if Company table EXISTS subquery is needed based on filters."""
        return ContactFilterSubqueryDetector.needs_company_subquery(filters)

    @staticmethod
    def _needs_contact_metadata_exists_subquery(filters: ContactFilterParams) -> bool:
        """Determine if ContactMetadata table EXISTS subquery is needed based on filters."""
        return ContactFilterSubqueryDetector.needs_contact_metadata_subquery(filters)

    @staticmethod
    def _needs_company_metadata_exists_subquery(filters: ContactFilterParams) -> bool:
        """Determine if CompanyMetadata table EXISTS subquery is needed based on filters."""
        return ContactFilterSubqueryDetector.needs_company_metadata_subquery(filters)

    @staticmethod
    def _needs_company_exists_subquery_for_search(search: Optional[str]) -> bool:
        """Determine if Company EXISTS subquery is needed for search term."""
        return ContactFilterSubqueryDetector.needs_subquery_for_search(search)

    @staticmethod
    def _detect_column_table(
        column_expression: Any,
        company_alias: Company,
        contact_meta_alias: ContactMetadata,
        company_meta_alias: CompanyMetadata,
    ) -> tuple[bool, bool, bool]:
        """Detect which tables are needed based on the column expression.
        
        Returns:
            Tuple of (needs_company, needs_contact_meta, needs_company_meta)
        """
        column_type_name = type(column_expression).__name__
        needs_company = False
        needs_contact_meta = False
        needs_company_meta = False
        
        # Get the underlying column from the expression
        # Handle different SQLAlchemy expression types (functions, casts, etc.)
        column = column_expression
        while hasattr(column, 'column'):
            column = column.column
        while hasattr(column, 'element'):
            column = column.element
        while hasattr(column, 'clauses'):
            # For function expressions, check all clauses
            clauses = column.clauses
            # SQLAlchemy ClauseList doesn't support direct boolean evaluation
            # Convert to list first to check if it has elements
            try:
                clauses_list = list(clauses) if clauses is not None else []
                if len(clauses_list) > 0:
                    column = clauses_list[0]
                else:
                    break
            except (TypeError, AttributeError) as e:
                # If we can't convert to list, break the loop
                # Error handling: Could not process clauses in column detection
                break
        
        # Check if column belongs to a specific table by comparing table references
        if hasattr(column, 'table'):
            table = column.table
            if table is not None:
                # Check by table name
                if hasattr(table, '__tablename__'):
                    tablename = table.__tablename__
                    if tablename == 'companies':
                        needs_company = True
                    elif tablename == 'contacts_metadata':
                        needs_contact_meta = True
                    elif tablename == 'companies_metadata':
                        needs_company_meta = True
                        needs_company = True  # CompanyMetadata requires Company join
                # Check by alias identity (aliases are the same object reference)
                elif table is company_alias:
                    needs_company = True
                elif table is contact_meta_alias:
                    needs_contact_meta = True
                elif table is company_meta_alias:
                    needs_company_meta = True
                    needs_company = True  # CompanyMetadata requires Company join
        
        # Fallback: Check column name against known column sets
        # This is a safety net if table inspection fails
        if not (needs_company or needs_contact_meta or needs_company_meta):
            column_name = None
            if hasattr(column, 'name'):
                column_name = column.name
            elif hasattr(column_expression, 'name'):
                column_name = column_expression.name
            
            if column_name:
                # Contact table columns (no join needed)
                # Company table columns
                if column_name in ('name', 'industries', 'keywords', 'technologies', 'text_search', 
                                   'employees_count', 'annual_revenue', 'total_funding', 'address',
                                   'uuid', 'id', 'created_at', 'updated_at'):
                    needs_company = True
                # ContactMetadata columns (ambiguous with CompanyMetadata for city/state/country)
                # We'll default to ContactMetadata for city/state/country unless context suggests otherwise
                elif column_name in ('city', 'state', 'country', 'work_direct_phone', 'home_phone', 
                                    'other_phone', 'linkedin_url', 'website', 'stage', 
                                    'facebook_url', 'twitter_url', 'uuid', 'id'):
                    # Default to ContactMetadata - if it's actually CompanyMetadata, 
                    # the endpoint will pass company_meta_alias which will be detected above
                    needs_contact_meta = True
                # CompanyMetadata columns
                elif column_name in ('company_name_for_emails', 'phone_number', 'latest_funding',
                                     'latest_funding_amount', 'last_raised_at', 'uuid', 'id'):
                    needs_company_meta = True
                    needs_company = True
        
        return needs_company, needs_contact_meta, needs_company_meta

    @staticmethod
    def _get_contact_only_filters(filters: ContactFilterParams) -> dict[str, Any]:
        """Extract filters that only affect the Contact table."""
        return {
            "first_name": filters.first_name,
            "last_name": filters.last_name,
            "title": filters.title,
            "seniority": filters.seniority,
            "department": filters.department,
            "email": filters.email,
            "email_status": filters.email_status,
            "mobile_phone": filters.mobile_phone,
            "contact_location": filters.contact_location,
            "exclude_titles": filters.exclude_titles,
            "exclude_contact_locations": filters.exclude_contact_locations,
            "exclude_seniorities": filters.exclude_seniorities,
            "exclude_departments": filters.exclude_departments,
            "exclude_company_ids": filters.exclude_company_ids,
            "created_at_after": filters.created_at_after,
            "created_at_before": filters.created_at_before,
            "updated_at_after": filters.updated_at_after,
            "updated_at_before": filters.updated_at_before,
        }

    @staticmethod
    def _get_company_only_filters(filters: ContactFilterParams) -> dict[str, Any]:
        """Extract filters that only affect the Company table."""
        return {
            "company": filters.company,
            "include_company_name": filters.include_company_name,
            "exclude_company_name": filters.exclude_company_name,
            "company_location": filters.company_location,
            "company_address": filters.company_address,
            "employees_count": filters.employees_count,
            "employees_min": filters.employees_min,
            "employees_max": filters.employees_max,
            "annual_revenue": filters.annual_revenue,
            "annual_revenue_min": filters.annual_revenue_min,
            "annual_revenue_max": filters.annual_revenue_max,
            "total_funding": filters.total_funding,
            "total_funding_min": filters.total_funding_min,
            "total_funding_max": filters.total_funding_max,
            "technologies": filters.technologies,
            "technologies_uids": filters.technologies_uids,
            "exclude_technologies": filters.exclude_technologies,
            "industries": filters.industries,
            "exclude_industries": filters.exclude_industries,
            "keywords": filters.keywords,
            "exclude_keywords": filters.exclude_keywords,
            "keywords_and": filters.keywords_and,
            "exclude_company_locations": filters.exclude_company_locations,
        }

    @staticmethod
    def _get_contact_metadata_filters(filters: ContactFilterParams) -> dict[str, Any]:
        """Extract filters that affect the ContactMetadata table."""
        return {
            "work_direct_phone": filters.work_direct_phone,
            "home_phone": filters.home_phone,
            "other_phone": filters.other_phone,
            "city": filters.city,
            "state": filters.state,
            "country": filters.country,
            "person_linkedin_url": filters.person_linkedin_url,
            "website": filters.website,
            "stage": filters.stage,
            "facebook_url": filters.facebook_url,
            "twitter_url": filters.twitter_url,
        }

    @staticmethod
    def _get_company_metadata_filters(filters: ContactFilterParams) -> dict[str, Any]:
        """Extract filters that affect the CompanyMetadata table."""
        return {
            "company_name_for_emails": filters.company_name_for_emails,
            "corporate_phone": filters.corporate_phone,
            "company_phone": filters.company_phone,
            "company_city": filters.company_city,
            "company_state": filters.company_state,
            "company_country": filters.company_country,
            "company_linkedin_url": filters.company_linkedin_url,
            "latest_funding_amount_min": filters.latest_funding_amount_min,
            "latest_funding_amount_max": filters.latest_funding_amount_max,
            "facebook_url": filters.facebook_url,
            "twitter_url": filters.twitter_url,
        }

    @staticmethod
    def _get_special_filters(filters: ContactFilterParams) -> dict[str, Any]:
        """Extract filters that require joined tables (domain, keywords, search)."""
        return {
            "include_domain_list": filters.include_domain_list,
            "exclude_domain_list": filters.exclude_domain_list,
            "keyword_search_fields": filters.keyword_search_fields,
            "keyword_exclude_fields": filters.keyword_exclude_fields,
            "search": filters.search,
        }

    def base_query_minimal(self) -> Select:
        """Construct minimal query with only Contact table (no joins)."""
        stmt: Select = select(Contact)
        return stmt

    def apply_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        company: Company | None = None,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement.
        
        DEPRECATED: This method is deprecated. The company, company_meta, and contact_meta
        parameters are ignored. Use _apply_filters_with_exists() directly instead.
        
        This method now delegates to _apply_filters_with_exists() which uses EXISTS subqueries
        instead of JOINs for better performance.
        """
        # apply_filters() is deprecated. JOIN parameters (company, company_meta, contact_meta) are ignored. Use _apply_filters_with_exists() directly.
        # Delegate to EXISTS-based implementation (ignores JOIN parameters)
        return self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)

    def apply_search_terms(
        self,
        stmt: Select,
        search: Optional[str],
        company: Company | None = None,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply case-insensitive search across selected text columns.
        
        DEPRECATED: This method is deprecated. The company, company_meta, and contact_meta
        parameters are ignored. Use _apply_search_terms_with_exists() directly instead.
        
        This method now delegates to _apply_search_terms_with_exists() which uses EXISTS subqueries
        instead of JOINs for better performance.
        """
        # apply_search_terms() is deprecated. JOIN parameters (company, company_meta, contact_meta) are ignored. Use _apply_search_terms_with_exists() directly.
        if not search:
            return stmt
        # Delegate to EXISTS-based implementation (ignores JOIN parameters)
        # Create empty filters since this method doesn't have access to filters
        from app.schemas.filters import ContactFilterParams
        empty_filters = ContactFilterParams()
        return self._apply_search_terms_with_exists(stmt, search, empty_filters, dialect_name=dialect_name)

    def _apply_contact_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filters that only affect the Contact table (and optionally ContactMetadata)."""
        dialect = (dialect_name or "").lower()
        
        # Contact table filters
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name, dialect_name=dialect_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name, dialect_name=dialect_name)
        # Title filtering: check for jumble_title_words first, then normalize_title_column, then standard filter
        if filters.jumble_title_words:
            # Applying jumble title filter (AND logic)
            stmt = self._apply_jumble_title_filter(
                stmt, Contact.title, filters.jumble_title_words,
                dialect_name=dialect_name
            )
        elif filters.normalize_title_column:
            # Applying normalized title filter
            stmt = self._apply_normalized_title_filter(
                stmt, Contact.title, filters.title,
                dialect_name=dialect_name
            )
        elif filters.title:
            stmt = self._apply_multi_value_filter(
                stmt, Contact.title, filters.title, 
                dialect_name=dialect_name, 
                use_trigram_optimization=True
            )
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = apply_ilike_filter(stmt, Contact.status, filters.status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority)
        stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
        
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        if filters.exclude_titles:
            # Exclude titles are normalized (words sorted alphabetically) in apollo_analysis_service
            # We need to normalize the database column before comparison
            # Applying normalized exclude_titles filter
            stmt = self._apply_normalized_title_exclusion(
                stmt, Contact.title, filters.exclude_titles,
                dialect_name=dialect_name
            )
        if filters.exclude_company_ids:
            exclusion_values = tuple(filters.exclude_company_ids)
            exclusion_condition = ~Contact.company_id.in_(exclusion_values)
            stmt = stmt.where(or_(Contact.company_id.is_(None), exclusion_condition))
        
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
        
        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
        
        # ContactMetadata filters (if joined)
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
            if filters.facebook_url:
                facebook_tokens = self._split_filter_values(filters.facebook_url) or [filters.facebook_url.strip()]
                facebook_tokens = [token for token in facebook_tokens if token]
                if facebook_tokens:
                    or_conditions = []
                    for token in facebook_tokens:
                        like_expression = f"%{token}%"
                        or_conditions.append(contact_meta.facebook_url.ilike(like_expression))
                    if or_conditions:
                        stmt = stmt.where(or_(*or_conditions))
            if filters.twitter_url:
                twitter_tokens = self._split_filter_values(filters.twitter_url) or [filters.twitter_url.strip()]
                twitter_tokens = [token for token in twitter_tokens if token]
                if twitter_tokens:
                    or_conditions = []
                    for token in twitter_tokens:
                        like_expression = f"%{token}%"
                        or_conditions.append(contact_meta.twitter_url.ilike(like_expression))
                    if or_conditions:
                        stmt = stmt.where(or_(*or_conditions))
        
        return stmt

    def _apply_company_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        company: Company,
        company_meta: CompanyMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filters that only affect the Company table (and optionally CompanyMetadata)."""
        # Applying company-only filters
        dialect = (dialect_name or "").lower()
        
        # Company table filters
        stmt = self._apply_multi_value_filter(stmt, company.name, filters.company)
        stmt = self._apply_multi_value_filter(stmt, company.name, filters.include_company_name)
        stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_location)
        stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_address)
        
        if filters.employees_count is not None:
            stmt = stmt.where(company.employees_count == filters.employees_count)
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
        
        if filters.exclude_company_locations:
            stmt = self._apply_multi_value_exclusion(stmt, company.text_search, filters.exclude_company_locations)
        if filters.exclude_company_name:
            stmt = self._apply_multi_value_exclusion(stmt, company.name, filters.exclude_company_name)
        
        if filters.technologies:
            stmt = self._apply_array_text_filter(
                stmt,
                company.technologies,
                filters.technologies,
                dialect=dialect,
            )
        if filters.technologies_uids:
            stmt = self._apply_array_text_filter(
                stmt,
                company.technologies,
                filters.technologies_uids,
                dialect=dialect,
            )
        if filters.exclude_technologies:
            stmt = self._apply_array_text_exclusion(
                stmt,
                company.technologies,
                filters.exclude_technologies,
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
        
        # CompanyMetadata filters (if joined)
        if company_meta is not None:
            if filters.latest_funding_amount_min is not None:
                stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
            if filters.latest_funding_amount_max is not None:
                stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)
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
            
            # Apply URL filters (facebook_url and twitter_url use similar logic)
            if filters.facebook_url:
                stmt = self._apply_url_filter(stmt, company_meta.facebook_url, filters.facebook_url)
            if filters.twitter_url:
                stmt = self._apply_url_filter(stmt, company_meta.twitter_url, filters.twitter_url)
        
        return stmt

    def _apply_special_filters(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        company: Company,
        company_meta: CompanyMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply special filters that require joined tables (domain, keywords, search)."""
        # Applying special filters (domain, keywords, search)
        dialect = (dialect_name or "").lower()
        
        # Domain filtering (requires CompanyMetadata)
        if company_meta is not None:
            if filters.include_domain_list:
                stmt = self._apply_domain_filter(
                    stmt,
                    company_meta.website,
                    filters.include_domain_list,
                    dialect=dialect,
                )
            if filters.exclude_domain_list:
                stmt = self._apply_domain_exclusion(
                    stmt,
                    company_meta.website,
                    filters.exclude_domain_list,
                    dialect=dialect,
                )
        
        # Keyword filters with field control
        if filters.keywords:
            if filters.keyword_search_fields or filters.keyword_exclude_fields:
                stmt = self._apply_keyword_search_with_fields(
                    stmt,
                    filters.keywords,
                    company,
                    filters.keyword_search_fields,
                    filters.keyword_exclude_fields,
                    dialect=dialect,
                )
            else:
                stmt = self._apply_array_text_filter(
                    stmt,
                    company.keywords,
                    filters.keywords,
                    dialect=dialect,
                )
        
        if filters.keywords_and:
            if filters.keyword_search_fields or filters.keyword_exclude_fields:
                stmt = self._apply_keyword_search_with_fields(
                    stmt,
                    filters.keywords_and,
                    company,
                    filters.keyword_search_fields,
                    filters.keyword_exclude_fields,
                    dialect=dialect,
                    use_and_logic=True,
                )
            else:
                stmt = self._apply_array_text_filter_and(
                    stmt,
                    company.keywords,
                    filters.keywords_and,
                    dialect=dialect,
                )
        
        if filters.exclude_keywords:
            stmt = self._apply_array_text_exclusion(
                stmt,
                company.keywords,
                filters.exclude_keywords,
                dialect=dialect,
            )
        
        return stmt

    def _build_company_ordering_subqueries(
        self,
        ordering_lower: str,
        ordering_map: dict[str, Any],
    ) -> None:
        """Add Company table ordering subqueries to ordering_map."""
        from sqlalchemy import select as sql_select
        
        # Define field mappings for company ordering
        field_mappings = [
            (["employees", "employees_count"], Company.employees_count),
            (["annual_revenue"], Company.annual_revenue),
            (["total_funding"], Company.total_funding),
            (["company"], Company.name),
            (["industry"], cast(Company.industries, Text)),
            (["keywords"], cast(Company.keywords, Text)),
            (["technologies"], cast(Company.technologies, Text)),
            (["company_address"], Company.address),
        ]
        
        for field_names, column in field_mappings:
            if any(field in ordering_lower for field in field_names):
                field_key = field_names[0]
                ordering_map[field_key] = (
                    sql_select(column)
                    .where(Company.uuid == Contact.company_id)
                    .scalar_subquery()
                )

    def _build_company_metadata_ordering_subqueries(
        self,
        ordering_lower: str,
        ordering_map: dict[str, Any],
    ) -> None:
        """Add CompanyMetadata ordering subqueries to ordering_map."""
        from sqlalchemy import select as sql_select
        
        company_uuid_subq = sql_select(Company.uuid).where(Company.uuid == Contact.company_id)
        
        # Define field mappings for company metadata ordering
        field_mappings = [
            (["latest_funding_amount"], CompanyMetadata.latest_funding_amount),
            (["company_name_for_emails"], CompanyMetadata.company_name_for_emails),
            (["corporate_phone", "company_phone"], CompanyMetadata.phone_number),
            (["company_city"], CompanyMetadata.city),
            (["company_state"], CompanyMetadata.state),
            (["company_country"], CompanyMetadata.country),
            (["company_linkedin_url"], CompanyMetadata.linkedin_url),
            (["latest_funding"], CompanyMetadata.latest_funding),
            (["last_raised_at"], CompanyMetadata.last_raised_at),
        ]
        
        for field_names, column in field_mappings:
            if any(field in ordering_lower for field in field_names):
                for field_key in field_names:
                    ordering_map[field_key] = (
                        sql_select(column)
                        .where(CompanyMetadata.uuid.in_(company_uuid_subq))
                        .scalar_subquery()
                    )

    def _build_contact_metadata_ordering_subqueries(
        self,
        ordering_lower: str,
        ordering_map: dict[str, Any],
    ) -> None:
        """Add ContactMetadata ordering subqueries to ordering_map."""
        from sqlalchemy import select as sql_select
        
        # Define field mappings for contact metadata ordering
        field_mappings = [
            (["work_direct_phone"], ContactMetadata.work_direct_phone),
            (["home_phone"], ContactMetadata.home_phone),
            (["other_phone"], ContactMetadata.other_phone),
            (["stage"], ContactMetadata.stage),
            (["person_linkedin_url"], ContactMetadata.linkedin_url),
            (["website"], ContactMetadata.website),
            (["city"], ContactMetadata.city),
            (["state"], ContactMetadata.state),
            (["country"], ContactMetadata.country),
        ]
        
        for field_names, column in field_mappings:
            if any(field in ordering_lower for field in field_names):
                field_key = field_names[0]
                ordering_map[field_key] = (
                    sql_select(column)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery()
                )
        
        # Handle URL fields that can come from either contact or company metadata
        if "facebook_url" in ordering_lower or "twitter_url" in ordering_lower:
            company_uuid_subq = sql_select(Company.uuid).where(Company.uuid == Contact.company_id)
            if "facebook_url" in ordering_lower:
                ordering_map["facebook_url"] = func.coalesce(
                    sql_select(ContactMetadata.facebook_url)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery(),
                    sql_select(CompanyMetadata.facebook_url)
                    .where(CompanyMetadata.uuid.in_(company_uuid_subq))
                    .scalar_subquery()
                )
            if "twitter_url" in ordering_lower:
                ordering_map["twitter_url"] = func.coalesce(
                    sql_select(ContactMetadata.twitter_url)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery(),
                    sql_select(CompanyMetadata.twitter_url)
                    .where(CompanyMetadata.uuid.in_(company_uuid_subq))
                    .scalar_subquery()
                )

    def _build_ordering_map_with_subqueries(
        self,
        ordering: Optional[str],
        *,
        dialect_name: str | None = None,
    ) -> dict[str, Any]:
        """Build ordering map using subqueries for related table columns."""
        ordering_map = {
            "created_at": Contact.created_at,
            "updated_at": Contact.updated_at,
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "email": Contact.email,
            "email_status": Contact.email_status,
            "primary_email_catch_all_status": getattr(
                Contact, "primary_email_catch_all_status", Contact.email_status
            ),
            "seniority": Contact.seniority,
            "departments": cast(Contact.departments, Text),
            "mobile_phone": Contact.mobile_phone,
        }
        
        if not ordering:
            return ordering_map
        
        ordering_lower = ordering.lower()
        
        # Company fields - use subqueries
        company_fields = ["employees", "annual_revenue", "total_funding", "company", "industry", "keywords", "technologies", "company_address"]
        if any(field in ordering_lower for field in company_fields):
            self._build_company_ordering_subqueries(ordering_lower, ordering_map)
        
        # CompanyMetadata fields - use subqueries
        company_meta_fields = ["latest_funding_amount", "company_name_for_emails", "corporate_phone", "company_phone", "company_city", "company_state", "company_country", "company_linkedin_url", "latest_funding", "last_raised_at"]
        if any(field in ordering_lower for field in company_meta_fields):
            self._build_company_metadata_ordering_subqueries(ordering_lower, ordering_map)
        
        # ContactMetadata fields - use subqueries
        contact_meta_fields = ["work_direct_phone", "home_phone", "other_phone", "stage", "person_linkedin_url", "website", "city", "state", "country", "facebook_url", "twitter_url"]
        if any(field in ordering_lower for field in contact_meta_fields):
            self._build_contact_metadata_ordering_subqueries(ordering_lower, ordering_map)
        
        return ordering_map

    async def list_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: Optional[int],
        offset: int,
    ) -> Sequence[Contact]:
        """Return contacts matching the filters.
        
        Uses EXISTS subqueries instead of JOINs for filtering on related tables.
        Returns only Contact objects - related entities should be fetched separately.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        # Use minimal query (no joins)
        stmt = self.base_query_minimal()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        
        # Apply filters using EXISTS subqueries
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms using EXISTS subqueries
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        # Build ordering map using subqueries for related table columns
        ordering_map = self._build_ordering_map_with_subqueries(filters.ordering, dialect_name=dialect_name)
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        
        # Ensure deterministic ordering for pagination - add default ordering if none specified
        if not filters.ordering:
            # Always use created_at DESC for default ordering (fast, indexed, no join required)
            stmt = stmt.order_by(Contact.created_at.desc().nulls_last(), Contact.id.desc())
        
        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        
        # SQL query compilation for debugging (if needed)
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": False})
            sql_str = str(compiled)
        except Exception:
            # Could not compile SQL (non-critical)
            pass
        
        # Record query execution start time for performance monitoring
        query_start_time = time.time()
        
        # Use streaming for large result sets to reduce memory usage
        if limit and limit > 10000:
            # Using batched query for large result set
            batcher = QueryBatcher(session, stmt, batch_size=5000)
            rows = await batcher.fetch_all()
        else:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        
        # Calculate query execution time
        query_execution_time = time.time() - query_start_time
        rows_returned = len(rows)
        
        # Slow query detected (>1 second) - consider optimization
        if query_execution_time > 1.0:
            try:
                # Get the dialect to check if it's PostgreSQL
                bind = session.bind
                dialect_name = getattr(bind.dialect, "name", None) if bind else None
                is_postgresql = dialect_name == "postgresql"
                
                if is_postgresql:
                    # Compile the statement to get the SQL
                    compiled = stmt.compile(compile_kwargs={"literal_binds": False})
                    sql_str = str(compiled)
                    
                    # Execute EXPLAIN ANALYZE directly
                    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql_str}"
                    explain_result = await session.execute(text(explain_sql))
                    explain_rows = explain_result.fetchall()
                    explain_text = "\n".join([str(row[0]) for row in explain_rows])
            except Exception:
                # Could not execute EXPLAIN ANALYZE (non-critical)
                pass
        
        return rows

    async def create_contact(self, session: AsyncSession, data: dict[str, Any]) -> Contact:
        """Persist a new contact record."""
        contact = Contact(**data)
        bind = session.get_bind()
        is_sqlite = bind is not None and bind.dialect.name == "sqlite"
        if is_sqlite:
            result = await session.execute(select(func.max(Contact.id)))
            next_id = (result.scalar_one_or_none() or 0) + 1
            contact.id = next_id
        session.add(contact)
        await session.flush()
        await session.refresh(contact)
        return contact

    def _apply_contact_filters_direct(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply contact-only filters directly (no EXISTS needed)."""
        dialect = (dialect_name or "").lower()
        
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name, dialect_name=dialect_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name, dialect_name=dialect_name)
        
        # Title filtering: check for jumble_title_words first, then normalize_title_column, then standard filter
        if filters.jumble_title_words:
            stmt = self._apply_jumble_title_filter(
                stmt, Contact.title, filters.jumble_title_words,
                dialect_name=dialect_name
            )
        elif filters.normalize_title_column:
            stmt = self._apply_normalized_title_filter(
                stmt, Contact.title, filters.title,
                dialect_name=dialect_name
            )
        elif filters.title:
            stmt = self._apply_multi_value_filter(
                stmt, Contact.title, filters.title, 
                dialect_name=dialect_name, 
                use_trigram_optimization=True
            )
        
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority)
        stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
        
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        if filters.exclude_titles:
            stmt = self._apply_normalized_title_exclusion(
                stmt, Contact.title, filters.exclude_titles,
                dialect_name=dialect_name
            )
        if filters.exclude_company_ids:
            exclusion_values = tuple(filters.exclude_company_ids)
            exclusion_condition = ~Contact.company_id.in_(exclusion_values)
            stmt = stmt.where(or_(Contact.company_id.is_(None), exclusion_condition))
        
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
        
        return stmt

    def _apply_company_basic_filters(
        self,
        company_subq: Select,
        filters: ContactFilterParams,
    ) -> Select:
        """Apply basic company filters (name, location, address)."""
        if filters.company:
            company_subq = self._apply_multi_value_filter(company_subq, Company.name, filters.company)
        if filters.include_company_name:
            company_subq = self._apply_multi_value_filter(company_subq, Company.name, filters.include_company_name)
        if filters.company_location:
            company_subq = self._apply_multi_value_filter(company_subq, Company.text_search, filters.company_location)
        if filters.company_address:
            company_subq = self._apply_multi_value_filter(company_subq, Company.text_search, filters.company_address)
        return company_subq

    def _apply_company_numeric_filters(
        self,
        company_subq: Select,
        filters: ContactFilterParams,
    ) -> Select:
        """Apply numeric company filters (employees, revenue, funding)."""
        if filters.employees_count is not None:
            company_subq = company_subq.where(Company.employees_count == filters.employees_count)
        company_subq = apply_numeric_range_filter(
            company_subq,
            Company.employees_count,
            filters.employees_min,
            filters.employees_max,
        )
        if filters.annual_revenue is not None:
            company_subq = company_subq.where(Company.annual_revenue == filters.annual_revenue)
        company_subq = apply_numeric_range_filter(
            company_subq,
            Company.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
        )
        if filters.total_funding is not None:
            company_subq = company_subq.where(Company.total_funding == filters.total_funding)
        company_subq = apply_numeric_range_filter(
            company_subq,
            Company.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
        )
        return company_subq

    def _apply_company_array_filters(
        self,
        company_subq: Select,
        filters: ContactFilterParams,
        dialect: str,
    ) -> Select:
        """Apply array-based company filters (technologies, keywords, industries)."""
        if filters.technologies:
            company_subq = self._apply_array_text_filter(
                company_subq, Company.technologies, filters.technologies, dialect=dialect
            )
        if filters.technologies_uids:
            company_subq = self._apply_array_text_filter(
                company_subq, Company.technologies, filters.technologies_uids, dialect=dialect
            )
        if filters.exclude_technologies:
            company_subq = self._apply_array_text_exclusion(
                company_subq, Company.technologies, filters.exclude_technologies, dialect=dialect
            )
        if filters.keywords:
            company_subq = self._apply_array_text_filter(
                company_subq, Company.keywords, filters.keywords, dialect=dialect
            )
        if filters.keywords_and:
            company_subq = self._apply_array_text_filter_and(
                company_subq, Company.keywords, filters.keywords_and, dialect=dialect
            )
        if filters.exclude_keywords:
            company_subq = self._apply_array_text_exclusion(
                company_subq, Company.keywords, filters.exclude_keywords, dialect=dialect
            )
        if filters.industries:
            company_subq = self._apply_array_text_filter(
                company_subq, Company.industries, filters.industries, dialect=dialect
            )
        if filters.exclude_industries:
            company_subq = self._apply_array_text_exclusion(
                company_subq, Company.industries, filters.exclude_industries, dialect=dialect
            )
        return company_subq

    def _build_company_exists_subquery(
        self,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Build Company EXISTS subquery with all company filters applied."""
        dialect = (dialect_name or "").lower()
        
        company_subq = select(1)
        company_subq = company_subq.select_from(Company)
        company_subq = company_subq.where(Company.uuid == Contact.company_id)
        
        # Apply basic filters (name, location, address)
        company_subq = self._apply_company_basic_filters(company_subq, filters)
        
        # Apply numeric filters (employees, revenue, funding)
        company_subq = self._apply_company_numeric_filters(company_subq, filters)
        
        # Apply array filters (technologies, keywords, industries)
        company_subq = self._apply_company_array_filters(company_subq, filters, dialect)
        
        # Apply exclusion filters
        if filters.exclude_company_locations:
            company_subq = self._apply_multi_value_exclusion(
                company_subq, Company.text_search, filters.exclude_company_locations
            )
        if filters.exclude_company_name:
            company_subq = self._apply_multi_value_exclusion(
                company_subq, Company.name, filters.exclude_company_name
            )
        
        return company_subq

    def _build_company_metadata_exists_subquery(
        self,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Build CompanyMetadata EXISTS subquery with all company metadata filters applied."""
        dialect = (dialect_name or "").lower()
        
        company_meta_subq = select(1)
        company_meta_subq = company_meta_subq.select_from(CompanyMetadata)
        company_uuid_subq = select(Company.uuid).where(Company.uuid == Contact.company_id)
        company_meta_subq = company_meta_subq.where(
            CompanyMetadata.uuid.in_(company_uuid_subq)
        )
        
        if filters.latest_funding_amount_min is not None:
            company_meta_subq = company_meta_subq.where(
                CompanyMetadata.latest_funding_amount >= filters.latest_funding_amount_min
            )
        if filters.latest_funding_amount_max is not None:
            company_meta_subq = company_meta_subq.where(
                CompanyMetadata.latest_funding_amount <= filters.latest_funding_amount_max
            )
        if filters.include_domain_list:
            company_meta_subq = self._apply_domain_filter(
                company_meta_subq,
                CompanyMetadata.website,
                filters.include_domain_list,
                dialect=dialect,
            )
        if filters.exclude_domain_list:
            company_meta_subq = self._apply_domain_exclusion(
                company_meta_subq,
                CompanyMetadata.website,
                filters.exclude_domain_list,
                dialect=dialect,
            )
        # Apply company metadata filters
        filter_mappings = [
            (filters.company_name_for_emails, CompanyMetadata.company_name_for_emails),
            (filters.company_city, CompanyMetadata.city),
            (filters.company_state, CompanyMetadata.state),
            (filters.company_country, CompanyMetadata.country),
            (filters.company_linkedin_url, CompanyMetadata.linkedin_url),
        ]
        for filter_value, column in filter_mappings:
            if filter_value:
                company_meta_subq = self._apply_multi_value_filter(company_meta_subq, column, filter_value)
        
        # Handle phone filters (corporate_phone or company_phone)
        if filters.corporate_phone or filters.company_phone:
            phone_filter = filters.corporate_phone or filters.company_phone
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.phone_number, phone_filter
            )
        
        return company_meta_subq

    def _build_contact_metadata_exists_subquery(
        self,
        filters: ContactFilterParams,
    ) -> Select:
        """Build ContactMetadata EXISTS subquery with all contact metadata filters applied."""
        contact_meta_subq = select(1)
        contact_meta_subq = contact_meta_subq.select_from(ContactMetadata)
        contact_meta_subq = contact_meta_subq.where(ContactMetadata.uuid == Contact.uuid)
        
        # Apply contact metadata filters using mapping
        filter_mappings = [
            (filters.work_direct_phone, ContactMetadata.work_direct_phone),
            (filters.home_phone, ContactMetadata.home_phone),
            (filters.other_phone, ContactMetadata.other_phone),
            (filters.city, ContactMetadata.city),
            (filters.state, ContactMetadata.state),
            (filters.country, ContactMetadata.country),
            (filters.person_linkedin_url, ContactMetadata.linkedin_url),
            (filters.website, ContactMetadata.website),
            (filters.stage, ContactMetadata.stage),
        ]
        for filter_value, column in filter_mappings:
            if filter_value:
                contact_meta_subq = self._apply_multi_value_filter(contact_meta_subq, column, filter_value)
        
        # Apply URL filters (use ILIKE for partial matching)
        if filters.facebook_url:
            contact_meta_subq = contact_meta_subq.where(
                ContactMetadata.facebook_url.ilike(f"%{filters.facebook_url}%")
            )
        if filters.twitter_url:
            contact_meta_subq = contact_meta_subq.where(
                ContactMetadata.twitter_url.ilike(f"%{filters.twitter_url}%")
            )
        
        return contact_meta_subq

    def _apply_filters_with_exists(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply filters using EXISTS subqueries instead of joins for better performance in count queries."""
        from sqlalchemy import exists
        
        active_filters = sorted(filters.model_dump(exclude_none=True).keys())
        # Applying filters with EXISTS subqueries
        
        # Contact-only filters (no EXISTS needed)
        stmt = self._apply_contact_filters_direct(stmt, filters, dialect_name=dialect_name)
        
        # Company filters using EXISTS
        if self._needs_company_exists_subquery(filters):
            company_subq = self._build_company_exists_subquery(filters, dialect_name=dialect_name)
            stmt = stmt.where(exists(company_subq))
        
        # CompanyMetadata filters using EXISTS
        if self._needs_company_metadata_exists_subquery(filters):
            company_meta_subq = self._build_company_metadata_exists_subquery(filters, dialect_name=dialect_name)
            stmt = stmt.where(exists(company_meta_subq))
        
        # ContactMetadata filters using EXISTS
        if self._needs_contact_metadata_exists_subquery(filters):
            contact_meta_subq = self._build_contact_metadata_exists_subquery(filters)
            stmt = stmt.where(exists(contact_meta_subq))
        
        # Temporal filters
        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
        
        return stmt

    async def count_contacts(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        *,
        use_approximate: bool = False,
    ) -> int:
        """
        Count contacts that match the supplied filters.
        
        Optimized for large datasets by using EXISTS subqueries instead of joins
        when filters don't require data from joined tables.
        
        Args:
            session: Database session
            filters: Filter parameters
            use_approximate: If True, use approximate count from pg_class for very large result sets
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        # For very large unfiltered queries, use approximate count
        if use_approximate and not active_filter_keys:
            dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
            if dialect_name == "postgresql":
                try:
                    result = await session.execute(
                        text("SELECT COALESCE(reltuples::bigint, 0) FROM pg_class WHERE relname = 'contacts'")
                    )
                    total = result.scalar_one() or 0
                    return int(total)
                except Exception as e:
                    # Could not use approximate count, falling back to exact
                    error_msg = str(e)
        
        # Always use minimal query with EXISTS subqueries for count (no joins)
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = select(func.count(Contact.id)).select_from(Contact)
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms using EXISTS subqueries
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        # SQL query compilation for debugging (if needed)
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        except Exception:
            # Could not compile SQL (non-critical)
            pass
        
        result = await session.execute(stmt)
        total = result.scalar_one() or 0
        return total
    
    def _apply_search_terms_with_exists(
        self,
        stmt: Select,
        search: str,
        filters: ContactFilterParams,
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
        
        # Contact columns (no EXISTS needed)
        contact_conditions = [
            Contact.first_name.ilike(pattern),
            Contact.last_name.ilike(pattern),
            Contact.email.ilike(pattern),
            Contact.title.ilike(pattern),
            Contact.seniority.ilike(pattern),
            Contact.text_search.ilike(pattern),
        ]
        
        # Company search using EXISTS
        if self._needs_company_exists_subquery_for_search(search):
            company_search_subq = select(1)
            company_search_subq = company_search_subq.select_from(Company)
            company_search_subq = company_search_subq.where(Company.uuid == Contact.company_id)
            company_search_conditions = or_(
                Company.name.ilike(pattern),
                Company.address.ilike(pattern),
                Company.text_search.ilike(pattern),
                self._array_column_as_text(Company.industries, dialect).ilike(pattern),
                self._array_column_as_text(Company.keywords, dialect).ilike(pattern),
                self._array_column_as_text(Company.technologies, dialect).ilike(pattern),
            )
            company_search_subq = company_search_subq.where(company_search_conditions)
            contact_conditions.append(exists(company_search_subq))
        
        # CompanyMetadata search using EXISTS
        if self._needs_company_metadata_exists_subquery(filters) or self._needs_company_exists_subquery_for_search(search):
            company_meta_search_subq = select(1)
            company_meta_search_subq = company_meta_search_subq.select_from(CompanyMetadata)
            company_uuid_subq = select(Company.uuid).where(Company.uuid == Contact.company_id)
            company_meta_search_subq = company_meta_search_subq.where(
                CompanyMetadata.uuid.in_(company_uuid_subq)
            )
            company_meta_search_conditions = or_(
                CompanyMetadata.city.ilike(pattern),
                CompanyMetadata.state.ilike(pattern),
                CompanyMetadata.country.ilike(pattern),
                CompanyMetadata.phone_number.ilike(pattern),
                CompanyMetadata.website.ilike(pattern),
                CompanyMetadata.linkedin_url.ilike(pattern),
            )
            company_meta_search_subq = company_meta_search_subq.where(company_meta_search_conditions)
            contact_conditions.append(exists(company_meta_search_subq))
        
        # ContactMetadata search using EXISTS
        if self._needs_contact_metadata_exists_subquery(filters):
            contact_meta_search_subq = select(1)
            contact_meta_search_subq = contact_meta_search_subq.select_from(ContactMetadata)
            contact_meta_search_subq = contact_meta_search_subq.where(ContactMetadata.uuid == Contact.uuid)
            contact_meta_search_conditions = or_(
                ContactMetadata.city.ilike(pattern),
                ContactMetadata.state.ilike(pattern),
                ContactMetadata.country.ilike(pattern),
                ContactMetadata.linkedin_url.ilike(pattern),
                ContactMetadata.twitter_url.ilike(pattern),
            )
            contact_meta_search_subq = contact_meta_search_subq.where(contact_meta_search_conditions)
            contact_conditions.append(exists(contact_meta_search_subq))
        
        if contact_conditions:
            stmt = stmt.where(or_(*contact_conditions))
        
        return stmt

    @staticmethod
    def _can_optimize_company_query(
        filters: ContactFilterParams,
        params: AttributeListParams,
        column_expression: Any,
        company_alias: Company,
    ) -> bool:
        """Check if query can be optimized by querying companies table directly.
        
        Optimization is possible when:
        1. Querying a company attribute (Company.text_search, Company.name, etc.)
        2. distinct=True (most performance benefit)
        3. No contact-specific filters that require contact table
        4. No contact metadata filters
        """
        # Check if column is from Company table
        column_needs_company, _, _ = ContactRepository._detect_column_table(
            column_expression, company_alias, None, None
        )
        
        if not column_needs_company:
            return False
        
        # Check if contact-specific filters are present
        contact_only_filters = ContactRepository._get_contact_only_filters(filters)
        has_contact_filters = any(v is not None for v in contact_only_filters.values())
        
        # Check if contact metadata filters are present
        contact_meta_filters = ContactRepository._get_contact_metadata_filters(filters)
        has_contact_meta_filters = any(v is not None for v in contact_meta_filters.values())
        
        # Check if search requires contact table (search might include contact fields)
        # For attribute endpoints, search is scoped to the column, so it's usually safe
        # But we'll be conservative and only optimize if no search or search is clearly company-only
        
        # Can optimize if no contact-specific filters
        can_optimize = not has_contact_filters and not has_contact_meta_filters
        
        # Company query optimization check
        
        return can_optimize

    def _clean_company_column_expression(self, column_expression: Any) -> Any:
        """Clean column expression to remove alias references."""
        clean_column = column_expression
        if hasattr(column_expression, 'table'):
            # If column references a table (possibly aliased), get fresh column from Company table
            if hasattr(column_expression, 'key'):
                clean_column = Company.__table__.columns[column_expression.key]
            elif hasattr(column_expression, 'name'):
                clean_column = Company.__table__.columns[column_expression.name]
        return clean_column

    def _apply_company_table_filters_optimized(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply company table filters directly to optimized query."""
        if filters.name:
            stmt = self._apply_multi_value_filter(stmt, Company.name, filters.name)
        if filters.include_company_name:
            stmt = self._apply_multi_value_filter(stmt, Company.name, filters.include_company_name)
        if filters.company_location:
            stmt = self._apply_multi_value_filter(stmt, Company.text_search, filters.company_location)
        if filters.company_address:
            stmt = self._apply_multi_value_filter(stmt, Company.text_search, filters.company_address)
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
                dialect=dialect_name or "",
            )
        if filters.exclude_technologies:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.technologies,
                filters.exclude_technologies,
                dialect=dialect_name or "",
            )
        if filters.keywords:
            stmt = self._apply_array_text_filter(
                stmt,
                Company.keywords,
                filters.keywords,
                dialect=dialect_name or "",
            )
        if filters.exclude_keywords:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.keywords,
                filters.exclude_keywords,
                dialect=dialect_name or "",
            )
        if filters.industries:
            stmt = self._apply_array_text_filter(
                stmt,
                Company.industries,
                filters.industries,
                dialect=dialect_name or "",
            )
        if filters.exclude_industries:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.industries,
                filters.exclude_industries,
                dialect=dialect_name or "",
            )
        if filters.exclude_company_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Company.text_search, filters.exclude_company_locations)
        if filters.exclude_company_name:
            stmt = self._apply_multi_value_exclusion(stmt, Company.name, filters.exclude_company_name)
        return stmt

    def _apply_company_metadata_filters_optimized(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply company metadata filters using EXISTS subquery for optimized query."""
        from sqlalchemy import exists
        
        company_meta_subq = (
            select(1)
            .select_from(CompanyMetadata)
            .where(CompanyMetadata.uuid == Company.uuid)
        )
        
        if filters.latest_funding_amount_min is not None:
            company_meta_subq = company_meta_subq.where(
                CompanyMetadata.latest_funding_amount >= filters.latest_funding_amount_min
            )
        if filters.latest_funding_amount_max is not None:
            company_meta_subq = company_meta_subq.where(
                CompanyMetadata.latest_funding_amount <= filters.latest_funding_amount_max
            )
        if filters.include_domain_list:
            company_meta_subq = self._apply_domain_filter(
                company_meta_subq,
                CompanyMetadata.website,
                filters.include_domain_list,
                dialect=dialect_name or "",
            )
        if filters.exclude_domain_list:
            company_meta_subq = self._apply_domain_exclusion(
                company_meta_subq,
                CompanyMetadata.website,
                filters.exclude_domain_list,
                dialect=dialect_name or "",
            )
        if filters.company_name_for_emails:
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.company_name_for_emails, filters.company_name_for_emails
            )
        if filters.corporate_phone or filters.company_phone:
            phone_filter = filters.corporate_phone or filters.company_phone
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.phone_number, phone_filter
            )
        if filters.company_city:
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.city, filters.company_city
            )
        if filters.company_state:
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.state, filters.company_state
            )
        if filters.company_country:
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.country, filters.company_country
            )
        if filters.company_linkedin_url:
            company_meta_subq = self._apply_multi_value_filter(
                company_meta_subq, CompanyMetadata.linkedin_url, filters.company_linkedin_url
            )
        
        return stmt.where(exists(company_meta_subq))

    def _apply_keyword_filters_optimized(
        self,
        stmt: Select,
        filters: ContactFilterParams,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply keyword filters to optimized company query."""
        if filters.keywords:
            if filters.keyword_search_fields or filters.keyword_exclude_fields:
                stmt = self._apply_keyword_search_with_fields(
                    stmt,
                    filters.keywords,
                    Company,
                    filters.keyword_search_fields,
                    filters.keyword_exclude_fields,
                    dialect=dialect_name or "",
                )
            else:
                stmt = self._apply_array_text_filter(
                    stmt,
                    Company.keywords,
                    filters.keywords,
                    dialect=dialect_name or "",
                )
        
        if filters.keywords_and:
            if filters.keyword_search_fields or filters.keyword_exclude_fields:
                stmt = self._apply_keyword_search_with_fields(
                    stmt,
                    filters.keywords_and,
                    Company,
                    filters.keyword_search_fields,
                    filters.keyword_exclude_fields,
                    dialect=dialect_name or "",
                    use_and_logic=True,
                )
            else:
                stmt = self._apply_array_text_filter_and(
                    stmt,
                    Company.keywords,
                    filters.keywords_and,
                    dialect=dialect_name or "",
                )
        
        if filters.exclude_keywords:
            stmt = self._apply_array_text_exclusion(
                stmt,
                Company.keywords,
                filters.exclude_keywords,
                dialect=dialect_name or "",
            )
        
        return stmt

    async def _list_company_attribute_values_optimized(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        column_expression: Any,
    ) -> list[str]:
        """Optimized method to query company attributes directly from companies table.
        
        This avoids the expensive join from contacts to companies when we only need
        company data and no contact-specific filters are applied.
        """
        import time
        start_time = time.time()
        
        try:
            dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
            
            # Clean column expression to remove alias references
            clean_column = self._clean_company_column_expression(column_expression)
            
            # Start query from Company table directly with clean column
            stmt = select(clean_column).select_from(Company)
            
            # Apply company table filters directly
            stmt = self._apply_company_table_filters_optimized(stmt, filters, dialect_name=dialect_name)
            
            # Apply company metadata filters using EXISTS subqueries
            filter_needs_company_meta = self._needs_company_metadata_exists_subquery(filters)
            if filter_needs_company_meta:
                stmt = self._apply_company_metadata_filters_optimized(stmt, filters, dialect_name=dialect_name)
            
            # Apply keyword filters
            stmt = self._apply_keyword_filters_optimized(stmt, filters, dialect_name=dialect_name)
            
            # Apply search if provided (scoped to clean_column)
            search_term = params.search or filters.search
            if search_term:
                search_stripped = search_term.strip()
                if search_stripped:
                    pattern = f"%{search_stripped}%"
                    stmt = stmt.where(clean_column.ilike(pattern))
            
            # Filter out NULL and empty values
            stmt = stmt.where(clean_column.isnot(None))
            stmt = stmt.where(func.trim(clean_column) != "")
            
            # Apply distinct BEFORE ordering
            if params.distinct:
                stmt = stmt.distinct()
            
            # Apply ordering
            ordering_map = {"value": clean_column}
            stmt = apply_ordering(
                stmt,
                params.ordering,
                ordering_map,
            )
            
            # When using DISTINCT, ensure there's always an explicit ORDER BY
            if params.distinct and not params.ordering:
                stmt = stmt.order_by(clean_column.asc())
            
            # Apply pagination
            stmt = stmt.offset(params.offset)
            if params.limit is not None:
                stmt = stmt.limit(params.limit)
            
            query_start_time = time.time()
            result = await session.execute(stmt)
            query_time = time.time() - query_start_time
            
            raw_values = result.fetchall()
            raw_count = len(raw_values)
            
            # Process results
            values = []
            skipped_none = 0
            skipped_empty = 0
            for (value,) in raw_values:
                if value is None:
                    skipped_none += 1
                    continue
                if isinstance(value, str) and not value.strip():
                    skipped_empty += 1
                    continue
                values.append(value)
            
            final_count = len(values)
            total_time = time.time() - start_time
            
            return values
            
        except Exception as e:
            total_time = time.time() - start_time
            # Error handling: Exception in optimized company query
            raise

    async def list_attribute_values(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        *,
        array_mode: bool = False,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Any] | None = None,
        apply_title_alphanumeric_filter: bool = False,
    ) -> list[str]:
        """Return attribute values for autocomplete/dropdown endpoints.
        
        Optimized to only join tables needed for filtering.
        Uses optimized company query path when possible.
        """
        import time
        start_time = time.time()
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # Listing attribute values
        
        try:
            bind = session.bind
            dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
            use_array_optimization = array_mode and dialect_name == "postgresql"

            if use_array_optimization and column_factory is not None:
                values = await self._list_array_attribute_values(session, column_factory, filters, params)
                return values

            if column_factory is None:
                raise ValueError("column_factory must be provided for attribute value queries.")
            
            # Create aliases for column detection
            company_alias = aliased(Company, name="company_attribute")
            contact_meta_alias = aliased(ContactMetadata, name="contact_meta_attribute")
            company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")
            
            # Get column expression to check if optimization is possible
            column_expression = column_factory(Contact, company_alias, contact_meta_alias, company_meta_alias)
            
            # Check if we can use optimized company query path
            if self._can_optimize_company_query(filters, params, column_expression, company_alias):
                # Use optimized path - query companies table directly
                # Extract the actual Company column from the aliased expression
                # The column_factory returns company_alias.text_search, we need Company.text_search
                actual_column = None
                
                # Try to extract column name from the expression
                column_to_check = column_expression
                # Unwrap if it's a wrapped expression (like func.trim())
                unwrapped = False
                wrapper_func = None
                while hasattr(column_to_check, 'element'):
                    if not unwrapped:
                        # Store wrapper function if any (for reconstruction)
                        wrapper_func = column_to_check.__class__ if hasattr(column_to_check, '__class__') else None
                    column_to_check = column_to_check.element
                    unwrapped = True
                
                # Get the column key/name
                column_key = None
                if hasattr(column_to_check, 'key'):
                    column_key = column_to_check.key
                elif hasattr(column_to_check, 'name'):
                    column_key = column_to_check.name
                
                # Check if this column belongs to company_alias
                is_company_column = False
                if hasattr(column_to_check, 'table'):
                    is_company_column = column_to_check.table is company_alias
                elif hasattr(column_to_check, '__str__'):
                    # Fallback: check string representation
                    col_str = str(column_to_check)
                    is_company_column = 'company' in col_str.lower()
                
                # Map to actual Company column - MUST use fresh Company column to avoid alias references
                if is_company_column and column_key and hasattr(Company, column_key):
                    # Get a fresh column from Company table (not the alias)
                    actual_column = getattr(Company, column_key)
                    # Verify it's not referencing the alias
                    if hasattr(actual_column, 'table'):
                        if actual_column.table is company_alias:
                            # Still referencing alias, force a fresh column
                            # Column still references alias - forcing fresh column
                            # Create a new column expression directly from Company
                            actual_column = Company.__table__.columns[column_key]
                    
                    # Reapply wrapper if there was one (e.g., func.trim())
                    if unwrapped and wrapper_func and hasattr(wrapper_func, '__call__'):
                        try:
                            # Try to reconstruct wrapped expression
                            # For simple cases like func.trim(), this should work
                            if 'trim' in str(wrapper_func).lower() or 'trim' in str(column_expression).lower():
                                actual_column = func.trim(actual_column)
                        except Exception:
                            # If reconstruction fails, use unwrapped column
                            # Wrapped expression could not be reconstructed - using unwrapped column
                            pass
                else:
                    # Fallback: try to extract from string representation
                    if not column_key:
                        col_str = str(column_expression)
                        if 'text_search' in col_str:
                            column_key = 'text_search'
                        elif 'name' in col_str:
                            column_key = 'name'
                        elif 'address' in col_str:
                            column_key = 'address'
                    
                    if column_key and hasattr(Company, column_key):
                        # Use table columns directly to avoid any alias references
                        actual_column = Company.__table__.columns[column_key]
                    else:
                        # Last resort: use the expression as-is and hope SQLAlchemy handles it
                        actual_column = column_expression
                
                
                return await self._list_company_attribute_values_optimized(
                    session,
                    filters,
                    params,
                    actual_column,
                )
            
            # Determine which joins are needed for filters
            filter_needs_company = self._needs_company_exists_subquery(filters) or self._needs_company_exists_subquery_for_search(params.search or filters.search)
            filter_needs_contact_meta = self._needs_contact_metadata_exists_subquery(filters)
            filter_needs_company_meta = self._needs_company_metadata_exists_subquery(filters)
            
            # Create aliases - always create them for column_factory
            company_alias = aliased(Company, name="company_attribute")
            contact_meta_alias = aliased(ContactMetadata, name="contact_meta_attribute")
            company_meta_alias = aliased(CompanyMetadata, name="company_meta_attribute")

            # Get column expression first to check what it references
            column_expression = column_factory(Contact, company_alias, contact_meta_alias, company_meta_alias)
            
            # Detect which tables are needed for the column itself
            column_needs_company, column_needs_contact_meta, column_needs_company_meta = self._detect_column_table(
                column_expression, company_alias, contact_meta_alias, company_meta_alias
            )
            
            # Join tables if needed for column OR filters
            needs_company = column_needs_company or filter_needs_company
            needs_contact_meta = column_needs_contact_meta or filter_needs_contact_meta
            needs_company_meta = column_needs_company_meta or filter_needs_company_meta
            # CompanyMetadata requires Company join
            if needs_company_meta:
                needs_company = True

            # Defensive check: ensure needs_company is True when column references company_alias
            # This prevents cartesian product when column_expression references company_alias
            if column_needs_company and not needs_company:
                # Column references company_alias but needs_company is False - forcing needs_company=True to prevent cartesian product
                needs_company = True

            # Convert column_expression to scalar subquery if it references related tables
            # This avoids JOINs by using subqueries instead
            from sqlalchemy import select as sql_select
            
            # If column is from a related table, convert to scalar subquery
            if column_needs_company:
                # Column is from Company table - use scalar subquery
                # Extract the actual column from Company table
                column_name = None
                if hasattr(column_expression, 'key'):
                    column_name = column_expression.key
                elif hasattr(column_expression, 'name'):
                    column_name = column_expression.name
                
                if column_name and hasattr(Company, column_name):
                    company_column = getattr(Company, column_name)
                    # Use scalar subquery to get company column value for each contact
                    column_expression = (
                        sql_select(company_column)
                        .where(Company.uuid == Contact.company_id)
                        .scalar_subquery()
                    )
                else:
                    # Fallback: try to extract from expression (using as-is if extraction fails)
                    pass
            elif column_needs_contact_meta:
                # Column is from ContactMetadata table - use scalar subquery
                column_name = None
                if hasattr(column_expression, 'key'):
                    column_name = column_expression.key
                elif hasattr(column_expression, 'name'):
                    column_name = column_expression.name
                
                if column_name and hasattr(ContactMetadata, column_name):
                    contact_meta_column = getattr(ContactMetadata, column_name)
                    column_expression = (
                        sql_select(contact_meta_column)
                        .where(ContactMetadata.uuid == Contact.uuid)
                        .scalar_subquery()
                    )
                else:
                    # Could not extract column name from ContactMetadata expression (using as-is)
                    pass
            elif column_needs_company_meta:
                # Column is from CompanyMetadata table - use scalar subquery through Company
                column_name = None
                if hasattr(column_expression, 'key'):
                    column_name = column_expression.key
                elif hasattr(column_expression, 'name'):
                    column_name = column_expression.name
                
                if column_name and hasattr(CompanyMetadata, column_name):
                    company_meta_column = getattr(CompanyMetadata, column_name)
                    column_expression = (
                        sql_select(company_meta_column)
                        .where(
                            CompanyMetadata.uuid.in_(
                                sql_select(Company.uuid).where(Company.uuid == Contact.company_id)
                            )
                        )
                        .scalar_subquery()
                    )
            
            # Build query without JOINs - use Contact table only
            stmt = select(column_expression)
            stmt = stmt.select_from(Contact)

            dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
            
            # Apply filters using EXISTS subqueries (no JOINs needed)
            # This is the same approach used in list_contacts
            stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
            
            # Step 4: Apply search terms
            # For attribute list endpoints, search should only apply to the selected column (column_expression)
            # NOT across all contact/company columns, to ensure search is scoped to the attribute being listed
            search_term = params.search or filters.search
            if search_term:
                search_stripped = search_term.strip()
                if search_stripped:
                    # Apply search ONLY to the column_expression (e.g., Contact.title)
                    # This ensures that when searching for titles, we only get titles containing the search term
                    pattern = f"%{search_stripped}%"
                    stmt = stmt.where(column_expression.ilike(pattern))
            
            stmt = stmt.where(column_expression.isnot(None))
            
            # Filter out placeholder value "_" for seniority column
            # Check if column_expression references Contact.seniority
            # We do this by checking if the column key/name contains "seniority"
            column_key = getattr(column_expression, "key", None) or str(column_expression)
            if "seniority" in column_key.lower():
                stmt = stmt.where(column_expression != "_")
                stmt = stmt.where(func.trim(column_expression) != "_")
            
            # For title column, add SQL-level alphanumeric filter to ensure LIMIT works correctly
            # This prevents post-processing filters from reducing results below the requested limit
            if apply_title_alphanumeric_filter:
                # PostgreSQL: Use regex to check for at least one alphanumeric character
                # Pattern [[:alnum:]] matches any alphanumeric character (POSIX character class)
                if dialect_name == "postgresql":
                    # Use ~ operator for regex matching - checks if column matches pattern
                    # [[:alnum:]] is a POSIX character class that matches any alphanumeric character
                    stmt = stmt.where(column_expression.op('~')(r'[[:alnum:]]'))
                else:
                    # For other databases, use a simpler check
                    # Check that trimmed value is not empty (already handled) and has length > 0
                    stmt = stmt.where(func.length(func.trim(column_expression)) > 0)
            
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
        
            query_start_time = time.time()
            
            result = await session.execute(stmt)
            query_time = time.time() - query_start_time
            
            raw_values = result.fetchall()
            raw_count = len(raw_values)
            
            values = []
            skipped_none = 0
            skipped_empty = 0
            for (value,) in raw_values:
                if value is None:
                    skipped_none += 1
                    continue
                if isinstance(value, str) and not value.strip():
                    skipped_empty += 1
                    continue
                values.append(value)
            
            final_count = len(values)
            total_skipped = skipped_none + skipped_empty
            
            total_time = time.time() - start_time
            # Attribute values query completed
            
            return values
            
        except Exception as e:
            total_time = time.time() - start_time
            # Error handling: Exception in list_attribute_values
            raise

    async def list_company_names_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
    ) -> list[str]:
        """Return company names directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search parameters.
        
        Equivalent to: SELECT DISTINCT name FROM companies WHERE name IS NOT NULL
        """
        # Listing company names (simple)
        
        # Query Company.name directly from companies table
        stmt = select(Company.name).select_from(Company)
        
        # Filter out NULL and empty names
        stmt = stmt.where(Company.name.isnot(None))
        stmt = stmt.where(func.trim(Company.name) != "")
        
        # Apply search if provided
        if params.search:
            search_term = params.search.strip()
            if search_term:
                stmt = stmt.where(Company.name.ilike(f"%{search_term}%"))
        
        # Apply distinct BEFORE ordering to avoid SQL issues
        if params.distinct:
            stmt = stmt.distinct()
        
        # Apply ordering - only order by the name column
        ordering_map = {"value": Company.name, "name": Company.name}
        stmt = apply_ordering(
            stmt,
            params.ordering,
            ordering_map,
        )
        
        # When using DISTINCT, ensure there's always an explicit ORDER BY
        if params.distinct and not params.ordering:
            stmt = stmt.order_by(Company.name.asc())
        elif not params.ordering:
            # Default ordering by name ascending
            stmt = stmt.order_by(Company.name.asc())
        
        # Apply pagination
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
        
        # Company names retrieved
        return values

    async def list_company_domains_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
    ) -> list[str]:
        """Return company domains extracted from CompanyMetadata.website.
        
        This method queries ONLY the CompanyMetadata table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search parameters.
        
        Extracts domain from website URLs using PostgreSQL regex:
        - Removes protocol (http://, https://)
        - Removes www. prefix
        - Removes port numbers
        - Converts to lowercase
        - Filters out NULL and placeholder "_" values
        
        Equivalent to: SELECT DISTINCT extract_domain(website) FROM companies_metadata WHERE website IS NOT NULL
        """
        # Listing company domains with specified limit, offset, ordering, search, and distinct parameters
        
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        is_postgresql = dialect_name == "postgresql"
        
        # Extract domain from website URL using SQL functions
        if is_postgresql:
            # Use PostgreSQL regex to extract domain
            # 1. Remove protocol (http://, https://)
            no_protocol = func.regexp_replace(
                func.coalesce(CompanyMetadata.website, ""),
                r"^https?://",
                "",
                "i"
            )
            # Extract hostname (everything before first /)
            hostname = func.split_part(no_protocol, "/", 1)
            # Remove port
            no_port = func.split_part(hostname, ":", 1)
            # Remove www. prefix and convert to lowercase
            domain_expression = func.lower(
                func.regexp_replace(no_port, r"^www\.", "", "i")
            )
        else:
            # For other databases, use column as-is (fallback)
            domain_expression = func.lower(func.cast(CompanyMetadata.website, Text))
        
        # Query CompanyMetadata.website directly from companies_metadata table
        stmt = select(domain_expression.label("domain")).select_from(CompanyMetadata)
        
        # Filter out NULL and placeholder "_" values
        stmt = stmt.where(CompanyMetadata.website.isnot(None))
        stmt = stmt.where(func.trim(CompanyMetadata.website) != "")
        stmt = stmt.where(CompanyMetadata.website != "_")
        stmt = stmt.where(func.trim(CompanyMetadata.website) != "_")
        
        # Filter out empty domains after extraction
        stmt = stmt.where(domain_expression.isnot(None))
        stmt = stmt.where(func.trim(domain_expression) != "")
        
        # Apply search if provided (search on extracted domain)
        if params.search:
            search_term = params.search.strip()
            if search_term:
                stmt = stmt.where(domain_expression.ilike(f"%{search_term}%"))
        
        # Apply distinct BEFORE ordering to avoid SQL issues
        if params.distinct:
            stmt = stmt.distinct()
        
        # Apply ordering - only order by the domain column
        ordering_map = {"value": domain_expression, "name": domain_expression}
        stmt = apply_ordering(
            stmt,
            params.ordering,
            ordering_map,
        )
        
        # When using DISTINCT, ensure there's always an explicit ORDER BY
        if params.distinct and not params.ordering:
            stmt = stmt.order_by(domain_expression.asc())
        elif not params.ordering:
            # Default ordering by domain ascending
            stmt = stmt.order_by(domain_expression.asc())
        
        # Apply pagination
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
            # Filter out placeholder values
            if value == "_":
                continue
            values.append(value)
        
        return values

    async def list_industries_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]] = None,
        separated: bool = False,
    ) -> list[str]:
        """Return industry values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company, separated parameters.
        
        Args:
            session: Database session
            params: Attribute list parameters (distinct, limit, offset, ordering, search)
            company: Optional list of exact company names to filter by (uses IN clause)
            separated: If True, unnest array into individual values; if False, return comma-separated strings
        
        Returns:
            List of industry values
        """
        # Listing industries (simple)
        
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        is_postgresql = dialect_name == "postgresql"
        
        # Always use unnest for PostgreSQL - it's much faster than array_to_string with DISTINCT
        # For non-PostgreSQL, fall back to array_to_string
        use_array_optimization = (separated or is_postgresql) and is_postgresql
        
        if use_array_optimization:
            # Use unnest with lateral join for PostgreSQL array optimization
            # This is much faster than array_to_string with DISTINCT
            # Optimized approach: unnest first, then filter, then distinct, then paginate
            
            # Build base query to unnest industries efficiently
            source_company = aliased(Company, name="industry_company")
            
            # Start with unnest - this is the most efficient way to handle arrays in PostgreSQL
            # Use a subquery to unnest all industries from companies that have them
            unnest_stmt = select(
                func.unnest(source_company.industries).label("value"),
                source_company.uuid.label("company_uuid")
            )
            unnest_stmt = unnest_stmt.select_from(source_company)
            unnest_stmt = unnest_stmt.where(source_company.industries.isnot(None))
            
            # Filter by exact company name(s) if provided (apply early for better performance)
            if company:
                unnest_stmt = unnest_stmt.where(source_company.name.in_(company))
            
            # Convert to subquery for further processing
            unnested = unnest_stmt.subquery()
            value_column = unnested.c.value
            
            # Build main query from unnested values
            attr_stmt = select(value_column).select_from(unnested)
            
            # Filter out NULL and empty values efficiently
            trimmed_value = func.nullif(func.trim(value_column), "")
            attr_stmt = attr_stmt.where(value_column.isnot(None))
            attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
            
            # Apply search on unnested values (early filtering)
            if params.search:
                search_term = params.search.strip()
                if search_term:
                    attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_term}%"))
            
            # Optimize distinct queries by using subquery approach
            # When distinct=true, use a subquery to get distinct values FIRST (without ordering)
            # Then apply ordering and pagination on the smaller distinct set in the outer query
            if params.distinct:
                # Inner subquery: Get distinct values from the filtered query (no ordering, no pagination)
                distinct_subquery = attr_stmt.distinct()
                
                # Convert to subquery for outer query
                distinct_subquery_alias = distinct_subquery.subquery()
                distinct_value_column = distinct_subquery_alias.c.value
                
                # Outer query: Order and paginate on the distinct set
                attr_stmt = select(distinct_value_column).select_from(distinct_subquery_alias)
                ordering_map = {"value": distinct_value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(distinct_value_column.asc())
            else:
                # No distinct needed - apply ordering directly
                ordering_map = {"value": value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(value_column.asc())
            
            # Apply pagination LAST - this is critical for performance
            # PostgreSQL can use LIMIT to stop processing early if we have an index
            attr_stmt = attr_stmt.offset(params.offset)
            if params.limit is not None:
                attr_stmt = attr_stmt.limit(params.limit)
            
            result = await session.execute(attr_stmt)
            values = []
            for (value,) in result.fetchall():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                values.append(value)
            
            return values
        else:
            # Fallback for non-PostgreSQL databases (e.g., SQLite)
            # SQLite stores arrays as JSON strings, so we need to use JSON functions
            if dialect_name == "sqlite":
                # For SQLite, fetch JSON strings and process in Python
                # This is more reliable than trying to use json_each in SQLAlchemy
                source_company = aliased(Company, name="industry_company_sqlite")
                
                # First, fetch all companies with industries
                base_stmt = select(source_company.industries, source_company.name).select_from(source_company)
                base_stmt = base_stmt.where(source_company.industries.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    base_stmt = base_stmt.where(source_company.name.in_(company))
                
                # Execute to get all industry JSON strings
                result = await session.execute(base_stmt)
                all_industry_strings = []
                
                for (industries_json, company_name) in result.fetchall():
                    if industries_json is None:
                        continue
                    
                    # Parse JSON string to get list
                    try:
                        if isinstance(industries_json, str):
                            industries_list = json.loads(industries_json)
                        else:
                            industries_list = industries_json
                        
                        if not isinstance(industries_list, list):
                            continue
                        
                        # Join with comma
                        industry_string = ",".join(str(i) for i in industries_list if i)
                        if industry_string and industry_string.strip():
                            all_industry_strings.append(industry_string)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Apply search filter in Python
                if params.search:
                    search_term = params.search.strip().lower()
                    all_industry_strings = [
                        s for s in all_industry_strings
                        if search_term in s.lower()
                    ]
                
                # Apply distinct in Python
                if params.distinct:
                    all_industry_strings = list(dict.fromkeys(all_industry_strings))  # Preserves order
                
                # Apply ordering in Python
                reverse = False
                if params.ordering and params.ordering.startswith("-"):
                    reverse = True
                    ordering_field = params.ordering[1:]
                else:
                    ordering_field = params.ordering if params.ordering else None
                
                if ordering_field == "value" or ordering_field is None:
                    all_industry_strings.sort(reverse=reverse)
                
                # Apply pagination in Python
                start = params.offset
                end = start + params.limit if params.limit is not None else None
                paginated_values = all_industry_strings[start:end]
                
            # "Retrieved %d industry values (simple, SQLite, not separated)", len(paginated_values))
                return paginated_values
            else:
                # For other non-PostgreSQL databases, try array_to_string (may fail)
                # This is a fallback for databases that might support it
                column_expression = func.array_to_string(Company.industries, ",")
                
                stmt = select(column_expression).select_from(Company)
                
                # Filter out NULL industries - use GIN index efficiently
                stmt = stmt.where(Company.industries.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    stmt = stmt.where(Company.name.in_(company))
                
                # Filter out empty strings from array_to_string
                stmt = stmt.where(column_expression != "")
                stmt = stmt.where(func.trim(column_expression) != "")
                
                # Apply search on comma-separated string
                if params.search:
                    search_term = params.search.strip()
                    if search_term:
                        stmt = stmt.where(column_expression.ilike(f"%{search_term}%"))
                
                # Apply distinct - but this is still slow on large datasets
                # Consider using unnest even when separated=False for PostgreSQL
                if params.distinct:
                    stmt = stmt.distinct()
                
                # Apply ordering
                ordering_map = {"value": column_expression}
                stmt = apply_ordering(stmt, params.ordering, ordering_map)
                if params.distinct and not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                elif not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                
                # Apply pagination
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
            
            return values

    async def list_keywords_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]] = None,
        separated: bool = False,
    ) -> list[str]:
        """Return keyword values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company, separated parameters.
        
        Args:
            session: Database session
            params: Attribute list parameters (distinct, limit, offset, ordering, search)
            company: Optional list of exact company names to filter by (uses IN clause)
            separated: If True, unnest array into individual values; if False, return comma-separated strings
        
        Returns:
            List of keyword values
        """
        # Listing keywords (simple)
        
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        is_postgresql = dialect_name == "postgresql"
        
        # Always use unnest for PostgreSQL - it's much faster than array_to_string with DISTINCT
        # For non-PostgreSQL, fall back to array_to_string
        use_array_optimization = (separated or is_postgresql) and is_postgresql
        
        if use_array_optimization:
            # Use unnest with optimized PostgreSQL array processing
            # Match the exact pattern from list_industries_simple for consistency
            # This is the most efficient approach: unnest first, then filter, then distinct, then paginate
            
            # Build base query to unnest keywords efficiently
            source_company = aliased(Company, name="keyword_company")
            
            # Start with unnest - this is the most efficient way to handle arrays in PostgreSQL
            # Use a subquery to unnest all keywords from companies that have them
            unnest_stmt = select(
                func.unnest(source_company.keywords).label("value")
            )
            unnest_stmt = unnest_stmt.select_from(source_company)
            unnest_stmt = unnest_stmt.where(source_company.keywords.isnot(None))
            
            # Filter by exact company name(s) if provided (apply early for better performance)
            if company:
                unnest_stmt = unnest_stmt.where(source_company.name.in_(company))
            
            # Convert to subquery for further processing
            unnested = unnest_stmt.subquery()
            value_column = unnested.c.value
            
            # Build main query from unnested values
            attr_stmt = select(value_column).select_from(unnested)
            
            # Filter out NULL and empty values efficiently
            trimmed_value = func.nullif(func.trim(value_column), "")
            attr_stmt = attr_stmt.where(value_column.isnot(None))
            attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
            
            # Apply search on unnested values (early filtering)
            if params.search:
                search_term = params.search.strip()
                if search_term:
                    attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_term}%"))
            
            # Optimize distinct queries by using subquery approach
            # When distinct=true, use a subquery to get distinct values FIRST (without ordering)
            # Then apply ordering and pagination on the smaller distinct set in the outer query
            if params.distinct:
                # Inner subquery: Get distinct values from the filtered query (no ordering, no pagination)
                distinct_subquery = attr_stmt.distinct()
                
                # Convert to subquery for outer query
                distinct_subquery_alias = distinct_subquery.subquery()
                distinct_value_column = distinct_subquery_alias.c.value
                
                # Outer query: Order and paginate on the distinct set
                attr_stmt = select(distinct_value_column).select_from(distinct_subquery_alias)
                ordering_map = {"value": distinct_value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(distinct_value_column.asc())
            else:
                # No distinct needed - apply ordering directly
                ordering_map = {"value": value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(value_column.asc())
            
            # Apply pagination LAST - this is critical for performance
            # PostgreSQL can use LIMIT to stop processing early if we have an index
            attr_stmt = attr_stmt.offset(params.offset)
            if params.limit is not None:
                attr_stmt = attr_stmt.limit(params.limit)
            
            result = await session.execute(attr_stmt)
            values = []
            for (value,) in result.fetchall():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                values.append(value)
            
            # "Retrieved %d keyword values (simple, separated)", len(values))
            return values
        else:
            # Fallback for non-PostgreSQL databases (e.g., SQLite)
            # SQLite stores arrays as JSON strings, so we need to use JSON functions
            if dialect_name == "sqlite":
                # For SQLite, fetch JSON strings and process in Python
                # This is more reliable than trying to use json_each in SQLAlchemy
                source_company = aliased(Company, name="keyword_company_sqlite")
                
                # First, fetch all companies with keywords
                base_stmt = select(source_company.keywords, source_company.name).select_from(source_company)
                base_stmt = base_stmt.where(source_company.keywords.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    base_stmt = base_stmt.where(source_company.name.in_(company))
                
                # Execute to get all keyword JSON strings
                result = await session.execute(base_stmt)
                all_keyword_strings = []
                
                for (keywords_json, company_name) in result.fetchall():
                    if keywords_json is None:
                        continue
                    
                    # Parse JSON string to get list
                    try:
                        if isinstance(keywords_json, str):
                            keywords_list = json.loads(keywords_json)
                        else:
                            keywords_list = keywords_json
                        
                        if not isinstance(keywords_list, list):
                            continue
                        
                        # Join with comma
                        keyword_string = ",".join(str(k) for k in keywords_list if k)
                        if keyword_string and keyword_string.strip():
                            all_keyword_strings.append(keyword_string)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Apply search filter in Python
                if params.search:
                    search_term = params.search.strip().lower()
                    all_keyword_strings = [
                        s for s in all_keyword_strings
                        if search_term in s.lower()
                    ]
                
                # Apply distinct in Python
                if params.distinct:
                    all_keyword_strings = list(dict.fromkeys(all_keyword_strings))  # Preserves order
                
                # Apply ordering in Python
                reverse = False
                if params.ordering and params.ordering.startswith("-"):
                    reverse = True
                    ordering_field = params.ordering[1:]
                else:
                    ordering_field = params.ordering if params.ordering else None
                
                if ordering_field == "value" or ordering_field is None:
                    all_keyword_strings.sort(reverse=reverse)
                
                # Apply pagination in Python
                start = params.offset
                end = start + params.limit if params.limit is not None else None
                paginated_values = all_keyword_strings[start:end]
                
                return paginated_values
            else:
                # For other non-PostgreSQL databases, try array_to_string (may fail)
                # This is a fallback for databases that might support it
                column_expression = func.array_to_string(Company.keywords, ",")
                
                stmt = select(column_expression).select_from(Company)
                
                # Filter out NULL keywords - use GIN index efficiently
                stmt = stmt.where(Company.keywords.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    stmt = stmt.where(Company.name.in_(company))
                
                # Filter out empty strings from array_to_string
                stmt = stmt.where(column_expression != "")
                stmt = stmt.where(func.trim(column_expression) != "")
                
                # Apply search on comma-separated string
                if params.search:
                    search_term = params.search.strip()
                    if search_term:
                        stmt = stmt.where(column_expression.ilike(f"%{search_term}%"))
                
                # Apply distinct - but this is still slow on large datasets
                # Consider using unnest even when separated=False for PostgreSQL
                if params.distinct:
                    stmt = stmt.distinct()
                
                # Apply ordering
                ordering_map = {"value": column_expression}
                stmt = apply_ordering(stmt, params.ordering, ordering_map)
                if params.distinct and not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                elif not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                
                # Apply pagination
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
            
            # "Retrieved %d keyword values (simple, not separated)", len(values))
            return values

    async def list_technologies_simple(
        self,
        session: AsyncSession,
        params: AttributeListParams,
        company: Optional[list[str]] = None,
        separated: bool = False,
    ) -> list[str]:
        """Return technology values directly from Company table.
        
        This method queries ONLY the Company table and ignores all contact filters.
        Only uses: distinct, limit, offset, ordering, search, company, separated parameters.
        
        Args:
            session: Database session
            params: Attribute list parameters (distinct, limit, offset, ordering, search)
            company: Optional list of exact company names to filter by (uses IN clause)
            separated: If True, unnest array into individual values; if False, return comma-separated strings
        
        Returns:
            List of technology values
        """
        # Listing technologies (simple)
        
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        is_postgresql = dialect_name == "postgresql"
        
        # Always use unnest for PostgreSQL - it's much faster than array_to_string with DISTINCT
        # For non-PostgreSQL, fall back to array_to_string
        use_array_optimization = (separated or is_postgresql) and is_postgresql
        
        if use_array_optimization:
            # Use unnest with optimized PostgreSQL array processing
            # Match the exact pattern from list_keywords_simple for consistency
            # This is the most efficient approach: unnest first, then filter, then distinct, then paginate
            
            # Build base query to unnest technologies efficiently
            source_company = aliased(Company, name="technology_company")
            
            # Start with unnest - this is the most efficient way to handle arrays in PostgreSQL
            # Use a subquery to unnest all technologies from companies that have them
            unnest_stmt = select(
                func.unnest(source_company.technologies).label("value")
            )
            unnest_stmt = unnest_stmt.select_from(source_company)
            unnest_stmt = unnest_stmt.where(source_company.technologies.isnot(None))
            
            # Filter by exact company name(s) if provided (apply early for better performance)
            # This reduces the dataset BEFORE unnest, which is critical for performance
            if company:
                unnest_stmt = unnest_stmt.where(source_company.name.in_(company))
            
            # Convert to subquery for further processing
            unnested = unnest_stmt.subquery()
            value_column = unnested.c.value
            
            # Build main query from unnested values
            attr_stmt = select(value_column).select_from(unnested)
            
            # Filter out NULL and empty values efficiently
            trimmed_value = func.nullif(func.trim(value_column), "")
            attr_stmt = attr_stmt.where(value_column.isnot(None))
            attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
            
            # Apply search on unnested values (early filtering)
            if params.search:
                search_term = params.search.strip()
                if search_term:
                    attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_term}%"))
            
            # Optimize distinct queries by using subquery approach
            # When distinct=true, use a subquery to get distinct values FIRST (without ordering)
            # Then apply ordering and pagination on the smaller distinct set in the outer query
            if params.distinct:
                # Inner subquery: Get distinct values from the filtered query (no ordering, no pagination)
                distinct_subquery = attr_stmt.distinct()
                
                # Convert to subquery for outer query
                distinct_subquery_alias = distinct_subquery.subquery()
                distinct_value_column = distinct_subquery_alias.c.value
                
                # Outer query: Order and paginate on the distinct set
                attr_stmt = select(distinct_value_column).select_from(distinct_subquery_alias)
                ordering_map = {"value": distinct_value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(distinct_value_column.asc())
            else:
                # No distinct needed - apply ordering directly
                ordering_map = {"value": value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(value_column.asc())
            
            # Apply pagination LAST - this is critical for performance
            # PostgreSQL can use LIMIT to stop processing early if we have an index
            attr_stmt = attr_stmt.offset(params.offset)
            if params.limit is not None:
                attr_stmt = attr_stmt.limit(params.limit)
            
            result = await session.execute(attr_stmt)
            values = []
            for (value,) in result.fetchall():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                values.append(value)
            
            # Technology values retrieved (simple, separated)
            return values
        else:
            # Fallback for non-PostgreSQL databases (e.g., SQLite)
            # SQLite stores arrays as JSON strings, so we need to use JSON functions
            if dialect_name == "sqlite":
                # For SQLite, fetch JSON strings and process in Python
                # This is more reliable than trying to use json_each in SQLAlchemy
                source_company = aliased(Company, name="technology_company_sqlite")
                
                # First, fetch all companies with technologies
                base_stmt = select(source_company.technologies, source_company.name).select_from(source_company)
                base_stmt = base_stmt.where(source_company.technologies.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    base_stmt = base_stmt.where(source_company.name.in_(company))
                
                # Execute to get all technology JSON strings
                result = await session.execute(base_stmt)
                all_technology_strings = []
                
                for (technologies_json, company_name) in result.fetchall():
                    if technologies_json is None:
                        continue
                    
                    # Parse JSON string to get list
                    try:
                        if isinstance(technologies_json, str):
                            technologies_list = json.loads(technologies_json)
                        else:
                            technologies_list = technologies_json
                        
                        if not isinstance(technologies_list, list):
                            continue
                        
                        # Join with comma
                        technology_string = ",".join(str(t) for t in technologies_list if t)
                        if technology_string and technology_string.strip():
                            all_technology_strings.append(technology_string)
                    except (json.JSONDecodeError, TypeError):
                        continue
                
                # Apply search filter in Python
                if params.search:
                    search_term = params.search.strip().lower()
                    all_technology_strings = [
                        s for s in all_technology_strings
                        if search_term in s.lower()
                    ]
                
                # Apply distinct in Python
                if params.distinct:
                    all_technology_strings = list(dict.fromkeys(all_technology_strings))  # Preserves order
                
                # Apply ordering in Python
                reverse = False
                if params.ordering and params.ordering.startswith("-"):
                    reverse = True
                    ordering_field = params.ordering[1:]
                else:
                    ordering_field = params.ordering if params.ordering else None
                
                if ordering_field == "value" or ordering_field is None:
                    all_technology_strings.sort(reverse=reverse)
                
                # Apply pagination in Python
                start = params.offset
                end = start + params.limit if params.limit is not None else None
                paginated_values = all_technology_strings[start:end]
                
                # Retrieved technology values (simple, SQLite, not separated)
                return paginated_values
            else:
                # For other non-PostgreSQL databases, try array_to_string (may fail)
                # This is a fallback for databases that might support it
                column_expression = func.array_to_string(Company.technologies, ",")
                
                stmt = select(column_expression).select_from(Company)
                
                # Filter out NULL technologies - use GIN index efficiently
                stmt = stmt.where(Company.technologies.isnot(None))
                
                # Filter by exact company name(s) if provided
                if company:
                    stmt = stmt.where(Company.name.in_(company))
                
                # Filter out empty strings from array_to_string
                stmt = stmt.where(column_expression != "")
                stmt = stmt.where(func.trim(column_expression) != "")
                
                # Apply search on comma-separated string
                if params.search:
                    search_term = params.search.strip()
                    if search_term:
                        stmt = stmt.where(column_expression.ilike(f"%{search_term}%"))
                
                # Apply distinct - but this is still slow on large datasets
                # Consider using unnest even when separated=False for PostgreSQL
                if params.distinct:
                    stmt = stmt.distinct()
                
                # Apply ordering
                ordering_map = {"value": column_expression}
                stmt = apply_ordering(stmt, params.ordering, ordering_map)
                if params.distinct and not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                elif not params.ordering:
                    stmt = stmt.order_by(column_expression.asc())
                
                # Apply pagination
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
                
                # Retrieved technology values (simple, not separated)
                return values

    async def _list_array_attribute_values(
        self,
        session: AsyncSession,
        column_factory: Callable[[Contact, Company, ContactMetadata, CompanyMetadata], Any],
        filters: ContactFilterParams,
        params: AttributeListParams,
    ) -> list[str]:
        """Optimized array attribute extraction using lateral unnesting.
        
        Performance optimizations:
        - Uses GROUP BY instead of DISTINCT for better performance on large datasets
        - Applies pagination LAST to allow PostgreSQL to stop early
        - Logs query execution time for performance monitoring
        """
        query_start_time = time.time()
        
        # Use minimal query (no JOINs) and filter using EXISTS subqueries
        stmt = self.base_query_minimal()
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        
        # Apply filters using EXISTS subqueries (no JOINs)
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms using EXISTS subqueries
        if params.search or filters.search:
            stmt = self._apply_search_terms_with_exists(
                stmt, params.search or filters.search, filters, dialect_name=dialect_name
            )

        # Get company UUIDs from filtered contacts using scalar subquery
        # Array attributes are from Company, so we need to get company UUIDs from contacts
        # Get company UUIDs from filtered contacts
        filtered_company_uuids_subq = (
            select(Contact.company_id)
            .select_from(Contact)
            .where(Contact.id.in_(select(Contact.id).select_from(stmt.subquery())))
            .where(Contact.company_id.isnot(None))
            .distinct()
        )
        
        # Execute to get company UUIDs
        company_uuids_result = await session.execute(filtered_company_uuids_subq)
        company_uuids = {row[0] for row in company_uuids_result if row[0]}
        
        if not company_uuids:
            # No companies match filters, return empty list
            # "No companies match filters, returning empty array attribute list")
            return []
        
        # Query Company table directly with filtered UUIDs (no JOIN needed)
        source_company = aliased(Company, name="array_company")
        # Get the array column from Company (column_factory expects Company for array attributes)
        array_column = column_factory(None, source_company, None, None)  # Only Company needed for array attributes

        # Use subquery to unnest arrays without lateral join
        # Create a subquery that unnests arrays for all matching companies
        unnest_subq = select(
            func.unnest(array_column).label("value"),
            source_company.uuid.label("company_uuid")
        )
        unnest_subq = unnest_subq.select_from(source_company)
        unnest_subq = unnest_subq.where(source_company.uuid.in_(company_uuids))
        unnest_subq = unnest_subq.where(array_column.isnot(None))
        unnest_subq = unnest_subq.subquery()
        
        # Main query selects from the unnested subquery
        attr_stmt = select(unnest_subq.c.value)
        value_column = unnest_subq.c.value

        trimmed_value = func.nullif(func.trim(value_column), "")
        attr_stmt = attr_stmt.where(value_column.isnot(None))
        attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
        search_term = params.search or filters.search
        if search_term:
            attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_term}%"))

        # Optimize distinct queries by using subquery approach
        # When distinct=true, use a subquery to get distinct values FIRST (without ordering)
        # Then apply ordering and pagination on the smaller distinct set in the outer query
        if params.distinct:
            # Inner subquery: Get distinct values from the filtered query (no ordering, no pagination)
            distinct_subquery = attr_stmt.distinct()
            
            # Convert to subquery for outer query
            distinct_subquery_alias = distinct_subquery.subquery()
            distinct_value_column = distinct_subquery_alias.c.value
            
            # Outer query: Order and paginate on the distinct set
            attr_stmt = select(distinct_value_column).select_from(distinct_subquery_alias)
            ordering_map = {"value": distinct_value_column}
            attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
            if params.ordering is None:
                attr_stmt = attr_stmt.order_by(distinct_value_column.asc())
        else:
            # No distinct needed - apply ordering directly
            ordering_map = {"value": value_column}
            attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
            if params.ordering is None:
                attr_stmt = attr_stmt.order_by(value_column.asc())
        
        # Apply pagination LAST - this is critical for performance
        # PostgreSQL can use LIMIT to stop processing early if we have an index
        attr_stmt = attr_stmt.offset(params.offset)
        if params.limit is not None:
            attr_stmt = attr_stmt.limit(params.limit)
        
        query_exec_start = time.time()
        result = await session.execute(attr_stmt)
        query_exec_time = time.time() - query_exec_start
        
        values = [value for (value,) in result.fetchall() if value]
        
        total_time = time.time() - query_start_time
        # Array attribute query finished with values count, query time, total time, limit, and offset
        
        return values

    async def list_departments_simple(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        params: AttributeListParams,
        separated: bool = True,
    ) -> list[str]:
        """Return department values from Contact.departments array field.
        
        This method queries Contact.departments and supports all ContactFilterParams.
        Uses unnest for PostgreSQL optimization when separated=True.
        
        Args:
            session: Database session
            filters: Contact filter parameters
            params: Attribute list parameters (distinct, limit, offset, ordering, search)
            separated: If True, unnest array into individual values; if False, return comma-separated strings
        
        Returns:
            List of department values
        """
        # Listing departments with limit, offset, ordering, search, distinct, and separated parameters
        
        bind = session.bind
        dialect_name = getattr(bind.dialect, "name", None) if bind is not None else None
        is_postgresql = dialect_name == "postgresql"
        
        # Always use unnest for PostgreSQL - it's much faster than array_to_string with DISTINCT
        use_array_optimization = (separated or is_postgresql) and is_postgresql
        
        if use_array_optimization:
            # Use unnest with optimized PostgreSQL array processing
            # Similar to list_industries_simple but for Contact.departments with contact filters
            
            # Determine which joins are needed for filters
            filter_needs_company = self._needs_company_exists_subquery(filters) or self._needs_company_exists_subquery_for_search(params.search or filters.search)
            filter_needs_contact_meta = self._needs_contact_metadata_exists_subquery(filters)
            filter_needs_company_meta = self._needs_company_metadata_exists_subquery(filters)
            
            # Create aliases
            contact_alias = aliased(Contact, name="department_contact")
            company_alias = aliased(Company, name="department_company") if filter_needs_company else None
            contact_meta_alias = aliased(ContactMetadata, name="department_contact_meta") if filter_needs_contact_meta else None
            company_meta_alias = aliased(CompanyMetadata, name="department_company_meta") if filter_needs_company_meta else None
            
            # Build base query to unnest departments efficiently
            unnest_stmt = select(
                func.unnest(contact_alias.departments).label("value"),
                contact_alias.uuid.label("contact_uuid")
            )
            unnest_stmt = unnest_stmt.select_from(contact_alias)
            unnest_stmt = unnest_stmt.where(contact_alias.departments.isnot(None))
            
            # Apply filters using EXISTS subqueries (no JOINs)
            # First, get filtered contact UUIDs
            contact_filter_stmt = select(Contact.uuid).select_from(Contact)
            contact_filter_stmt = self._apply_filters_with_exists(contact_filter_stmt, filters, dialect_name=dialect_name)
            if params.search or filters.search:
                contact_filter_stmt = self._apply_search_terms_with_exists(
                    contact_filter_stmt, params.search or filters.search, filters, dialect_name=dialect_name
                )
            
            # Filter contacts by UUIDs from filtered query
            filtered_contact_uuids_subq = contact_filter_stmt.subquery()
            unnest_stmt = unnest_stmt.where(
                contact_alias.uuid.in_(select(filtered_contact_uuids_subq.c.uuid))
            )
            
            # Convert to subquery for further processing
            unnested = unnest_stmt.subquery()
            value_column = unnested.c.value
            
            # Build main query from unnested values
            attr_stmt = select(value_column).select_from(unnested)
            
            # Filter out NULL and empty values efficiently
            trimmed_value = func.nullif(func.trim(value_column), "")
            attr_stmt = attr_stmt.where(value_column.isnot(None))
            attr_stmt = attr_stmt.where(trimmed_value.isnot(None))
            
            # Apply search on unnested values (early filtering)
            search_term = params.search or filters.search
            if search_term:
                search_stripped = search_term.strip()
                if search_stripped:
                    attr_stmt = attr_stmt.where(value_column.ilike(f"%{search_stripped}%"))
            
            # Optimize distinct queries by using subquery approach
            if params.distinct:
                distinct_subquery = attr_stmt.distinct()
                distinct_subquery_alias = distinct_subquery.subquery()
                distinct_value_column = distinct_subquery_alias.c.value
                
                attr_stmt = select(distinct_value_column).select_from(distinct_subquery_alias)
                ordering_map = {"value": distinct_value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(distinct_value_column.asc())
            else:
                ordering_map = {"value": value_column}
                attr_stmt = apply_ordering(attr_stmt, params.ordering, ordering_map)
                if params.ordering is None:
                    attr_stmt = attr_stmt.order_by(value_column.asc())
            
            # Apply pagination LAST
            attr_stmt = attr_stmt.offset(params.offset)
            if params.limit is not None:
                attr_stmt = attr_stmt.limit(params.limit)
            
            result = await session.execute(attr_stmt)
            values = []
            for (value,) in result.fetchall():
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                values.append(value)
            
            return values
        else:
            # Fallback for non-PostgreSQL databases: Use array_to_string
            # This path is less optimal but works for non-PostgreSQL
            column_expression = func.array_to_string(Contact.departments, ",")
            
            # Determine which joins are needed for filters
            filter_needs_company = self._needs_company_exists_subquery(filters) or self._needs_company_exists_subquery_for_search(params.search or filters.search)
            filter_needs_contact_meta = self._needs_contact_metadata_exists_subquery(filters)
            filter_needs_company_meta = self._needs_company_metadata_exists_subquery(filters)
            
            # Create aliases
            company_alias = aliased(Company, name="department_company") if filter_needs_company else None
            contact_meta_alias = aliased(ContactMetadata, name="department_contact_meta") if filter_needs_contact_meta else None
            company_meta_alias = aliased(CompanyMetadata, name="department_company_meta") if filter_needs_company_meta else None
            
            # Build query without JOINs - use EXISTS subqueries for filtering
            stmt = select(column_expression).select_from(Contact)
            
            # Filter out NULL departments
            stmt = stmt.where(Contact.departments.isnot(None))
            
            # Apply filters using EXISTS subqueries (no JOINs)
            stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
            
            # Apply search terms using EXISTS subqueries
            if params.search or filters.search:
                stmt = self._apply_search_terms_with_exists(
                    stmt, params.search or filters.search, filters, dialect_name=dialect_name
                )
            
            # Filter out empty strings from array_to_string
            stmt = stmt.where(column_expression != "")
            stmt = stmt.where(func.trim(column_expression) != "")
            
            # Apply search on comma-separated string
            search_term = params.search or filters.search
            if search_term:
                search_stripped = search_term.strip()
                if search_stripped:
                    stmt = stmt.where(column_expression.ilike(f"%{search_stripped}%"))
            
            # Apply distinct
            if params.distinct:
                stmt = stmt.distinct()
            
            # Apply ordering
            ordering_map = {"value": column_expression}
            stmt = apply_ordering(stmt, params.ordering, ordering_map)
            if params.distinct and not params.ordering:
                stmt = stmt.order_by(column_expression.asc())
            elif not params.ordering:
                stmt = stmt.order_by(column_expression.asc())
            
            # Apply pagination
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
            
            return values

    async def get_uuids_by_filters(
        self,
        session: AsyncSession,
        filters: ContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs that match the supplied filters (efficient UUID-only query).
        
        Uses the same separated filtering approach as list_contacts for consistency and performance.
        """
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # Getting contact UUIDs with specified limit and active filter keys

        # Always use minimal query with EXISTS subqueries for UUID query (no joins)
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        stmt = select(Contact.uuid).select_from(Contact)
        stmt = self._apply_filters_with_exists(stmt, filters, dialect_name=dialect_name)
        
        # Apply search terms using EXISTS subqueries
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, filters, dialect_name=dialect_name)
        
        stmt = stmt.where(Contact.uuid.isnot(None))
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        uuids = [uuid for (uuid,) in result.fetchall() if uuid]
        return uuids

    async def get_uuids_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        limit: Optional[int] = None,
    ) -> list[str]:
        """Return contact UUIDs for a specific company that match the supplied filters.
        
        Optimized to use EXISTS subqueries instead of joins for better performance.
        """
        from app.schemas.filters import CompanyContactFilterParams
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # Getting contact UUIDs for company with specified UUID, limit, and active filter keys

        # Use minimal query with EXISTS subqueries
        stmt = select(Contact.uuid).select_from(Contact)
        stmt = stmt.where(Contact.company_id == company_uuid)
        
        # Apply contact-only filters directly
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        dialect = (dialect_name or "").lower()
        
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name)
        # Title filtering: check for jumble_title_words first, then normalize_title_column, then standard filter
        if filters.jumble_title_words:
            # Applying jumble title filter in EXISTS query with AND logic for specified words
            stmt = self._apply_jumble_title_filter(
                stmt, Contact.title, filters.jumble_title_words,
                dialect_name=dialect_name
            )
        elif filters.normalize_title_column:
            # Applying normalized title filter in EXISTS query with title and normalize_title_column flag
            stmt = self._apply_normalized_title_filter(
                stmt, Contact.title, filters.title,
                dialect_name=dialect_name
            )
        elif filters.title:
            stmt = self._apply_multi_value_filter(stmt, Contact.title, filters.title)
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority)
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
        
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
        if filters.exclude_titles:
            # Exclude titles are normalized (words sorted alphabetically) in apollo_analysis_service
            # We need to normalize the database column before comparison
            # Applying normalized exclude_titles filter
            stmt = self._apply_normalized_title_exclusion(
                stmt, Contact.title, filters.exclude_titles,
                dialect_name=dialect_name
            )
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        
        # ContactMetadata filters using EXISTS
        contact_meta_fields = [
            filters.work_direct_phone, filters.home_phone, filters.other_phone,
            filters.city, filters.state, filters.country, filters.person_linkedin_url,
            filters.website, filters.stage, filters.facebook_url, filters.twitter_url,
        ]
        if any(field is not None for field in contact_meta_fields):
            from sqlalchemy import exists
            contact_meta_subq = select(1)
            contact_meta_subq = contact_meta_subq.select_from(ContactMetadata)
            contact_meta_subq = contact_meta_subq.where(ContactMetadata.uuid == Contact.uuid)
            
            if filters.work_direct_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.work_direct_phone, filters.work_direct_phone
                )
            if filters.home_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.home_phone, filters.home_phone
                )
            if filters.other_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.other_phone, filters.other_phone
                )
            if filters.city:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.city, filters.city
                )
            if filters.state:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.state, filters.state
                )
            if filters.country:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.country, filters.country
                )
            if filters.person_linkedin_url:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.linkedin_url, filters.person_linkedin_url
                )
            if filters.website:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.website, filters.website
                )
            if filters.stage:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.stage, filters.stage
                )
            if filters.facebook_url:
                contact_meta_subq = contact_meta_subq.where(
                    ContactMetadata.facebook_url.ilike(f"%{filters.facebook_url}%")
                )
            if filters.twitter_url:
                contact_meta_subq = contact_meta_subq.where(
                    ContactMetadata.twitter_url.ilike(f"%{filters.twitter_url}%")
                )
            
            stmt = stmt.where(exists(contact_meta_subq))
        
        # Apply search if needed
        if filters.search:
            from sqlalchemy import exists
            search_stripped = filters.search.strip()
            if search_stripped:
                pattern = f"%{search_stripped}%"
                contact_conditions = [
                    Contact.first_name.ilike(pattern),
                    Contact.last_name.ilike(pattern),
                    Contact.email.ilike(pattern),
                    Contact.title.ilike(pattern),
                    Contact.seniority.ilike(pattern),
                    Contact.text_search.ilike(pattern),
                ]
                
                # ContactMetadata search using EXISTS
                if any(field is not None for field in contact_meta_fields):
                    contact_meta_search_subq = (
                        select(1)
                        .select_from(ContactMetadata)
                        .where(ContactMetadata.uuid == Contact.uuid)
                        .where(
                            or_(
                                ContactMetadata.city.ilike(pattern),
                                ContactMetadata.state.ilike(pattern),
                                ContactMetadata.country.ilike(pattern),
                                ContactMetadata.linkedin_url.ilike(pattern),
                                ContactMetadata.twitter_url.ilike(pattern),
                            )
                        )
                    )
                    contact_conditions.append(exists(contact_meta_search_subq))
                
                if contact_conditions:
                    stmt = stmt.where(or_(*contact_conditions))
        
        # Temporal filters
        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
        
        stmt = stmt.where(Contact.uuid.isnot(None))
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        uuids = [uuid for (uuid,) in result.fetchall() if uuid]
        return uuids

    @staticmethod
    def _split_filter_values(raw_value: str) -> list[str]:
        """Normalize comma-delimited filter strings into a list of tokens."""
        return [token.strip() for token in raw_value.split(",") if token.strip()]

    @staticmethod
    def _normalize_title_in_sql(column) -> Any:
        """
        Generate a SQL expression that normalizes a title column by:
        1. Converting to lowercase
        2. Splitting into words
        3. Sorting words alphabetically
        4. Joining back together
        
        This matches the Python normalization logic in ApolloAnalysisService._normalize_title()
        
        Uses PostgreSQL's array functions with text() for reliable sorting.
        
        Args:
            column: SQLAlchemy column expression (e.g., Contact.title)
            
        Returns:
            SQLAlchemy expression representing normalized title
        """
        # Use raw SQL text for reliable PostgreSQL array sorting
        # This creates: array_to_string(ARRAY(SELECT unnest(string_to_array(lower(column), ' ')) ORDER BY 1), ' ')
        # The text() expression allows us to reference the column properly
        return text(
            "array_to_string(ARRAY(SELECT unnest(string_to_array(lower(:col), ' ')) ORDER BY 1), ' ')"
        ).bindparams(col=column)

    def _apply_normalized_title_filter(
        self,
        stmt: Select,
        column,
        raw_value: str | None,
        *,
        dialect_name: str | None = None,
        max_or_conditions: int = 50,
    ) -> Select:
        """
        Apply title filter with column normalization.
        
        Normalizes both the search values (already normalized in Python) and the database
        column before comparison. This ensures correct matching when includeSimilarTitles=false.
        
        Args:
            stmt: SQLAlchemy select statement
            column: Title column to filter (e.g., Contact.title)
            raw_value: Comma-separated normalized title values
            dialect_name: Database dialect name (e.g., 'postgresql')
            max_or_conditions: Maximum number of OR conditions before using alternative approach
            
        Returns:
            Modified select statement with normalized title filter applied
        """
        # Applying normalized title filter with raw_value and dialect
        
        if raw_value is None:
            return stmt
        
        values = ContactRepository._split_filter_values(raw_value)
        
        if not values:
            return stmt
        
        dialect = (dialect_name or "").lower()
        
        # Normalize the database column using SQL and use VALUES clause for exact matching
        # For PostgreSQL, use array functions to normalize and VALUES clause for efficient comparison
        if dialect == "postgresql":
            # Get table and column names for proper SQL reference
            table_name = column.table.name if hasattr(column, 'table') and hasattr(column.table, 'name') else 'contacts'
            column_name = column.name if hasattr(column, 'name') else 'title'
            
            # Building: Normalized title filter using VALUES clause with table name, column name, and values
            
            # Build VALUES clause with escaped normalized values
            # Escape single quotes by doubling them (PostgreSQL escaping)
            escaped_values = []
            for value in values:
                # Escape single quotes and backslashes for SQL safety
                escaped = str(value).replace("\\", "\\\\").replace("'", "''")
                escaped_values.append(f"('{escaped}')")
            
            values_clause = ", ".join(escaped_values)
            
            # Create EXISTS subquery with VALUES clause for exact matching
            # This ensures proper column correlation because the column reference
            # in the text() will be part of the outer query context
            # Use exact equality (=) instead of similarity (%) for normalized titles
            sql_template = (
                f"EXISTS ("
                f"  SELECT 1 FROM (VALUES {values_clause}) AS titles(val) "
                f"  WHERE array_to_string(ARRAY(SELECT unnest(string_to_array(lower({table_name}.{column_name}), ' ')) ORDER BY 1), ' ') = titles.val::text"
                f")"
            )
            
            # Generated: SQL template for normalized title filter using VALUES clause with table name, column name
            
            exists_sql = text(sql_template)
            
            # Applied: Normalized title filter with VALUES clause including table name, column name, and number of values
            
            # Apply the condition to the statement
            result = stmt.where(exists_sql)
            return result
        else:
            # For non-PostgreSQL, fallback to simple lowercase comparison
            # Using non-PostgreSQL fallback for normalized title filter with dialect and values
            normalized_column = func.lower(column)
            conditions = [normalized_column == value for value in values]
            
            if len(conditions) <= max_or_conditions:
                return stmt.where(or_(*conditions))
            else:
                # Split into batches if exceeds max
                batches = [values[i:i + max_or_conditions] for i in range(0, len(values), max_or_conditions)]
                batch_conditions = []
                for batch in batches:
                    batch_conds = [normalized_column == value for value in batch]
                    if batch_conds:
                        batch_conditions.append(or_(*batch_conds))
                if batch_conditions:
                    return stmt.where(or_(*batch_conditions))
                return stmt

    def _apply_normalized_title_exclusion(
        self,
        stmt: Select,
        column,
        exclude_values: list[str],
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """
        Apply title exclusion filter with column normalization.
        
        Normalizes both the exclusion values (already normalized in Python) and the database
        column before comparison. This ensures correct exclusion when personNotTitles[] is used.
        
        Args:
            stmt: SQLAlchemy select statement
            column: Title column to filter (e.g., Contact.title)
            exclude_values: List of normalized title values to exclude
            dialect_name: Database dialect name (e.g., 'postgresql')
            
        Returns:
            Modified select statement with normalized title exclusion filter applied
        """
        # Applying normalized title exclusion filter with exclude_values and dialect
        
        if not exclude_values:
            return stmt
        
        dialect = (dialect_name or "").lower()
        
        # Normalize the database column using SQL and use VALUES clause for exact matching
        # For PostgreSQL, use array functions to normalize and VALUES clause for efficient comparison
        if dialect == "postgresql":
            # Get table and column names for proper SQL reference
            table_name = column.table.name if hasattr(column, 'table') and hasattr(column.table, 'name') else 'contacts'
            column_name = column.name if hasattr(column, 'name') else 'title'
            
            # Building: Normalized title exclusion filter using VALUES clause with table name, column name, and exclude_values
            
            # Build VALUES clause with escaped normalized values
            # Escape single quotes by doubling them (PostgreSQL escaping)
            escaped_values = []
            for value in exclude_values:
                if not value:
                    continue
                # Escape single quotes and backslashes for SQL safety
                escaped = str(value).replace("\\", "\\\\").replace("'", "''")
                escaped_values.append(f"('{escaped}')")
            
            if not escaped_values:
                return stmt
            
            values_clause = ", ".join(escaped_values)
            
            # Create NOT EXISTS subquery with VALUES clause for exact exclusion
            # This ensures proper column correlation because the column reference
            # in the text() will be part of the outer query context
            # Use exact equality (=) instead of similarity (%) for normalized titles
            sql_template = (
                f"NOT EXISTS ("
                f"  SELECT 1 FROM (VALUES {values_clause}) AS titles(val) "
                f"  WHERE array_to_string(ARRAY(SELECT unnest(string_to_array(lower({table_name}.{column_name}), ' ')) ORDER BY 1), ' ') = titles.val::text"
                f")"
            )
            
            # Generated: SQL template for normalized title exclusion filter using VALUES clause with table name, column name
            
            exists_sql = text(sql_template)
            
            # Applied: Normalized title exclusion filter with VALUES clause including table name, column name, and number of values
            
            # Apply the condition to the statement (also handle NULL titles)
            result = stmt.where(
                or_(
                    column.is_(None),
                    exists_sql
                )
            )
            return result
        else:
            # For non-PostgreSQL, fallback to simple lowercase comparison
            # Using non-PostgreSQL fallback for normalized title exclusion filter with dialect and exclude_values
            normalized_column = func.lower(column)
            lowered_exclude = tuple(v.lower() for v in exclude_values if v)
            if lowered_exclude:
                return stmt.where(
                    or_(
                        column.is_(None),
                        normalized_column.notin_(lowered_exclude),
                    )
                )
            return stmt

    def _apply_jumble_title_filter(
        self,
        stmt: Select,
        column,
        words: list[str],
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """
        Apply jumble title filter requiring ALL words to be present (AND logic).
        
        When includeSimilarTitles=true, titles are split into words and ALL words
        must be present in the title for a match. This is different from OR logic
        where ANY word would match.
        
        Args:
            stmt: SQLAlchemy select statement
            column: Title column to filter (e.g., Contact.title)
            words: List of words that must ALL be present in the title
            dialect_name: Database dialect name (e.g., 'postgresql')
            
        Returns:
            Modified select statement with jumble title filter applied (AND logic)
        """
        # Applying jumble title filter with words and dialect (AND logic - all words must be present)
        
        if not words:
            return stmt
        
        # Filter out empty words
        words = [w for w in words if w and w.strip()]
        if not words:
            return stmt
        
        dialect = (dialect_name or "").lower()
        
        # For PostgreSQL, use ILIKE with AND logic (all words must be present)
        if dialect == "postgresql":
            from sqlalchemy import text
            
            # Get table and column names for proper SQL reference
            table_name = column.table.name if hasattr(column, 'table') and hasattr(column.table, 'name') else 'contacts'
            column_name = column.name if hasattr(column, 'name') else 'title'
            
            # Build conditions that require ALL words to be present
            # Each word must be found in the title (case-insensitive)
            conditions = []
            for word in words:
                # Escape single quotes and backslashes for SQL safety
                escaped_word = str(word).replace("\\", "\\\\").replace("'", "''")
                # Use ILIKE for case-insensitive substring matching
                # The word can appear anywhere in the title
                condition = f"lower({table_name}.{column_name}) LIKE lower('%{escaped_word}%')"
                conditions.append(condition)
            
            # Combine all conditions with AND
            if conditions:
                combined_condition = " AND ".join(conditions)
                sql_template = f"({combined_condition})"
            
            # Generated: SQL template for jumble title filter (AND logic) with table name, column name
            
                jumble_sql = text(sql_template)
            
            # Applied: Jumble title filter with AND logic including table name, column name, and number of words
            
            # Apply the condition to the statement
            result = stmt.where(jumble_sql)
            # Jumble title filter applied successfully
            return result
        
        # For non-PostgreSQL, use standard SQLAlchemy ILIKE with AND logic
        from sqlalchemy import and_
        conditions = [column.ilike(f"%{word}%") for word in words]
        if conditions:
            return stmt.where(and_(*conditions))
        return stmt

    @staticmethod
    def _apply_multi_value_filter(
        stmt: Select,
        column,
        raw_value: str | None,
        *,
        dialect_name: str | None = None,
        use_trigram_optimization: bool = False,
        max_or_conditions: int = 50,
    ) -> Select:
        """
        Apply substring matching supporting comma-separated values with OR semantics.
        
        Optimized for PostgreSQL with trigram indexes when many values are provided.
        Strategy selection:
        - Small lists (<10): Standard ILIKE
        - Medium lists (10-20): Trigram similarity with OR conditions
        - Large lists (>20): VALUES clause JOIN (much more efficient)
        - Very large lists (>50): Batched processing
        
        Args:
            stmt: SQLAlchemy select statement
            column: Column to filter
            raw_value: Comma-separated values or single value
            dialect_name: Database dialect name (e.g., 'postgresql')
            use_trigram_optimization: If True, use trigram similarity for title column
            max_or_conditions: Maximum number of OR conditions before using alternative approach
        """
        if raw_value is None:
            return stmt

        values = ContactRepository._split_filter_values(raw_value)
        if not values:
            return apply_ilike_filter(stmt, column, raw_value.strip(), dialect_name=dialect_name)

        if len(values) == 1:
            return apply_ilike_filter(stmt, column, values[0], dialect_name=dialect_name)

        dialect = (dialect_name or "").lower()
        num_values = len(values)
        
        # Applying multi-value filter
        
        # For PostgreSQL with many values, use optimized approaches
        if dialect == "postgresql" and num_values > 10:
            # Use trigram similarity for better index usage with many values
            if use_trigram_optimization or num_values > max_or_conditions:
                return ContactRepository._apply_trigram_similarity_filter(
                    stmt, column, values, max_or_conditions
                )
            else:
                # For 10-50 values, use optimized ILIKE with trigram index
                # PostgreSQL can use the GIN trigram index even with leading wildcards
                conditions = [column.ilike(f"%{value}%") for value in values]
                if len(conditions) <= max_or_conditions:
                    return stmt.where(or_(*conditions))
                else:
                    # Split into batches if exceeds max
                    return ContactRepository._apply_batched_filter(stmt, column, values, max_or_conditions)
        else:
            # For small lists or non-PostgreSQL, use standard ILIKE
            conditions = [column.ilike(f"%{value}%") for value in values]
            if len(conditions) <= max_or_conditions:
                return stmt.where(or_(*conditions))
            else:
                # Split into batches if exceeds max
                return ContactRepository._apply_batched_filter(stmt, column, values, max_or_conditions)

    @staticmethod
    def _apply_trigram_similarity_filter(
        stmt: Select,
        column,
        values: list[str],
        max_or_conditions: int = 50,
    ) -> Select:
        """
        Apply filter using PostgreSQL trigram operators for better index usage.
        
        Uses pg_trgm '%' operator which efficiently uses GIN trigram indexes
        for substring matching. This is more efficient than ILIKE with leading wildcards.
        For very large lists (>20), uses VALUES clause JOIN for better performance.
        For medium lists (10-20), uses OR conditions with trigram operator.
        For very large lists (>50), splits into batches.
        
        Args:
            stmt: SQLAlchemy select statement
            column: Column to filter (should have trigram index)
            values: List of search values
            max_or_conditions: Maximum conditions per batch
        """
        num_values = len(values)
        
        # For >20 values, use VALUES clause JOIN - much more efficient than many OR conditions
        if num_values > 20:
            # Optimization: Triggering VALUES clause optimization for large value sets (more than 20 values)
            return ContactRepository._apply_values_join_filter(stmt, column, values)
        
        # For <=20 values, use OR conditions with trigram operator
        if num_values <= max_or_conditions:
            # Use PostgreSQL trigram '%' operator for efficient substring matching
            # The '%' operator uses the GIN trigram index efficiently
            conditions = []
            for value in values:
                # Use trigram operator: column % value (case-insensitive)
                # This is equivalent to ILIKE '%value%' but uses trigram index better
                # We use func.lower for case-insensitive matching
                trigram_op = func.lower(column).op('%')(func.lower(func.cast(value, Text)))
                conditions.append(trigram_op)
            
            if conditions:
                return stmt.where(or_(*conditions))
        else:
            # Split into batches and combine with OR
            return ContactRepository._apply_batched_filter(
                stmt, column, values, max_or_conditions, use_similarity=True
            )
        
        return stmt

    @staticmethod
    def _apply_values_join_filter(
        stmt: Select,
        column,
        values: list[str],
    ) -> Select:
        """
        Apply filter using PostgreSQL VALUES clause with EXISTS for many values.
        
        This approach is much more efficient than many OR conditions when dealing
        with large value lists (>20). It uses a VALUES clause to create a temporary
        table and joins it using EXISTS, which PostgreSQL can optimize better.
        
        Example SQL:
        SELECT COUNT(*) FROM contacts c
        WHERE EXISTS (
            SELECT 1 FROM (VALUES ('title1'), ('title2'), ...) AS titles(val)
            WHERE lower(c.title) % lower(titles.val)
        )
        
        Args:
            stmt: SQLAlchemy select statement
            column: Column to filter (should have trigram index)
            values: List of search values (should be >20 for this method)
        """
        if not values:
            return stmt
        
        from sqlalchemy import text
        
        # Using VALUES clause optimization for many values
        
        # Build VALUES clause with escaped values
        # Escape single quotes by doubling them (PostgreSQL escaping)
        escaped_values = []
        for value in values:
            # Escape single quotes and backslashes for SQL safety
            escaped = str(value).replace("\\", "\\\\").replace("'", "''")
            escaped_values.append(f"('{escaped}')")
        
        values_clause = ", ".join(escaped_values)
        
        # Get table and column names for the SQL reference
        # Use the column's table and name directly - PostgreSQL will resolve from outer query
        table_name = column.table.name
        column_name = column.name
        
        # Create the entire EXISTS condition as raw SQL text
        # This allows proper column correlation because the column reference
        # in the text() will be part of the outer query context
        # The VALUES clause creates a derived table that PostgreSQL can optimize
        # The column reference will be resolved by PostgreSQL
        # from the outer query context, so this should work correctly
        exists_sql = text(
            f"EXISTS ("
            f"  SELECT 1 FROM (VALUES {values_clause}) AS titles(val) "
            f"  WHERE lower({table_name}.{column_name}) % lower(titles.val::text)"
            f")"
        )
        
        # Applied VALUES clause filter
        
        # Apply the condition to the statement
        return stmt.where(exists_sql)

    @staticmethod
    def _apply_batched_filter(
        stmt: Select,
        column,
        values: list[str],
        batch_size: int = 20,
        *,
        use_similarity: bool = False,
    ) -> Select:
        """
        Apply filter by splitting values into batches to avoid query planner issues.
        
        For very large value lists, splits into smaller batches and combines with OR.
        This prevents the query planner from creating inefficient execution plans.
        
        Args:
            stmt: SQLAlchemy select statement
            column: Column to filter
            values: List of search values
            batch_size: Number of values per batch
            use_similarity: If True, use trigram similarity instead of ILIKE
        """
        if not values:
            return stmt
        
        # Split into batches
        batches = [values[i:i + batch_size] for i in range(0, len(values), batch_size)]
        batch_conditions = []
        
        for batch in batches:
            if use_similarity:
                # Use PostgreSQL trigram '%' operator for this batch
                batch_conds = [
                    func.lower(column).op('%')(func.lower(func.cast(value, Text)))
                    for value in batch
                ]
            else:
                # Use ILIKE for this batch
                batch_conds = [column.ilike(f"%{value}%") for value in batch]
            
            if batch_conds:
                # Combine batch conditions with OR
                batch_conditions.append(or_(*batch_conds))
        
        if batch_conditions:
            # Combine all batches with OR
            return stmt.where(or_(*batch_conditions))
        
        return stmt

    @staticmethod
    def _apply_array_text_filter(
        stmt: Select,
        column,
        raw_value: str,
        *,
        dialect: str,
    ) -> Select:
        """
        Apply substring matching to a text-array column.
        Optimized to use array operators when possible for better GIN index usage.
        """
        normalized_values = ContactRepository._split_filter_values(raw_value)
        search_terms = normalized_values or ([raw_value] if raw_value else [])
        if not search_terms:
            return stmt

        if dialect == "postgresql":
            # Use array operators for better performance with GIN indexes
            # For substring matching, we still need array_to_string, but optimize the query
            # Try to use array overlap (&&) for exact matches first
            conditions = []
            for value in search_terms:
                # For exact array element matches, use array overlap operator
                # For substring matches, use array_to_string (still needed for ILIKE)
                # The GIN index on the array column will help with performance
                array_text = func.array_to_string(column, ",")
                conditions.append(array_text.ilike(f"%{value}%"))
            
            if conditions:
                return stmt.where(or_(*conditions))
        else:
            # Fallback for other databases
            array_text = ContactRepository._array_column_as_text(column, dialect)
            conditions = [array_text.ilike(f"%{value}%") for value in search_terms]
            if conditions:
                return stmt.where(or_(*conditions))
        
        return stmt

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
    def _extract_domain_from_url_sql(column, dialect: str):
        """
        Extract domain from URL column using SQL functions.
        
        Uses PostgreSQL regex to extract domain from URLs like:
        - https://www.example.com -> example.com
        - http://example.com/path -> example.com
        - example.com -> example.com
        """
        if dialect == "postgresql":
            # Extract domain using regex:
            # 1. Remove protocol (http://, https://, etc.)
            # 2. Extract hostname (everything before first / or end of string)
            # 3. Remove port if present
            # 4. Remove www. prefix
            # 5. Convert to lowercase
            no_protocol = func.regexp_replace(
                func.coalesce(column, ""),
                r"^https?://",
                "",
                "i"
            )
            # Extract hostname (everything before first /)
            hostname = func.split_part(no_protocol, "/", 1)
            # Remove port
            no_port = func.split_part(hostname, ":", 1)
            # Remove www. prefix and convert to lowercase
            domain = func.lower(
                func.regexp_replace(no_port, r"^www\.", "", "i")
            )
            return domain
        # For other dialects, return column as-is (fallback)
        return func.lower(cast(column, Text))

    @staticmethod
    def _apply_url_filter(
        stmt: Select,
        column,
        url_value: str | None,
    ) -> Select:
        """
        Apply URL filter using ILIKE with token matching.
        
        Args:
            stmt: SQLAlchemy select statement
            column: URL column to filter
            url_value: URL value to search for (comma-separated tokens supported)
            
        Returns:
            Modified select statement with URL filter applied
        """
        if not url_value:
            return stmt
        
        url_tokens = ContactRepository._split_filter_values(url_value) or [url_value.strip()]
        url_tokens = [token for token in url_tokens if token]
        
        if not url_tokens:
            return stmt
        
        or_conditions = [column.ilike(f"%{token}%") for token in url_tokens]
        if or_conditions:
            stmt = stmt.where(or_(*or_conditions))
        
        return stmt

    @staticmethod
    def _apply_domain_filter(
        stmt: Select,
        website_column,
        domains: list[str] | None,
        *,
        dialect: str,
    ) -> Select:
        """
        Include contacts whose website domain matches any provided domain (OR logic).
        
        Contacts with NULL website are excluded.
        """
        if not domains:
            return stmt
        normalized_domains = [
            extract_domain_from_url(d) or d.lower().strip()
            for d in domains
            if d and d.strip()
        ]
        normalized_domains = [d for d in normalized_domains if d]
        if not normalized_domains:
            return stmt
        
        # Extract domain from website URL and compare
        extracted_domain = ContactRepository._extract_domain_from_url_sql(
            website_column, dialect
        )
        # Create OR conditions for any domain match
        conditions = [
            extracted_domain == func.lower(domain)
            for domain in normalized_domains
        ]
        if conditions:
            # Include only if domain matches AND website is not NULL
            stmt = stmt.where(
                and_(
                    website_column.isnot(None),
                    or_(*conditions)
                )
            )
        return stmt

    @staticmethod
    def _apply_domain_exclusion(
        stmt: Select,
        website_column,
        domains: list[str] | None,
        *,
        dialect: str,
    ) -> Select:
        """
        Exclude contacts whose website domain matches any provided domain.
        
        Contacts with NULL website are included (not excluded).
        """
        if not domains:
            return stmt
        normalized_domains = [
            extract_domain_from_url(d) or d.lower().strip()
            for d in domains
            if d and d.strip()
        ]
        normalized_domains = [d for d in normalized_domains if d]
        if not normalized_domains:
            return stmt
        
        # Extract domain from website URL and compare
        extracted_domain = ContactRepository._extract_domain_from_url_sql(
            website_column, dialect
        )
        # Create conditions to exclude matching domains
        exclusion_conditions = [
            extracted_domain != func.lower(domain)
            for domain in normalized_domains
        ]
        if exclusion_conditions:
            # Exclude if domain matches any in the list
            # Include if website is NULL OR domain doesn't match any
            stmt = stmt.where(
                or_(
                    website_column.is_(None),
                    and_(*exclusion_conditions)
                )
            )
        return stmt

    @staticmethod
    def _array_column_as_text(column, dialect: str):
        """Return an expression suitable for ILIKE matching across dialects."""
        if dialect == "postgresql":
            return func.array_to_string(column, ",")
        return cast(column, Text)

    @staticmethod
    def _apply_array_text_filter_and(
        stmt: Select,
        column,
        raw_value: str,
        *,
        dialect: str,
    ) -> Select:
        """Apply substring matching to a text-array column with AND logic (all keywords must match)."""
        normalized_values = ContactRepository._split_filter_values(raw_value)
        search_terms = normalized_values or ([raw_value] if raw_value else [])
        if not search_terms:
            return stmt

        array_text = ContactRepository._array_column_as_text(column, dialect)
        conditions = [array_text.ilike(f"%{value}%") for value in search_terms]
        return stmt.where(and_(*conditions))

    @staticmethod
    def _apply_keyword_search_with_fields(
        stmt: Select,
        keywords: str,
        company: Company,
        search_fields: list[str] | None,
        exclude_fields: list[str] | None,
        *,
        dialect: str,
        use_and_logic: bool = False,
    ) -> Select:
        """Apply keyword search to specific fields (company.name, industries, keywords) with optional AND logic."""
        normalized_values = ContactRepository._split_filter_values(keywords)
        search_terms = normalized_values or ([keywords] if keywords else [])
        if not search_terms:
            return stmt

        # Determine which fields to search
        fields_to_search = []
        if search_fields:
            # Only search in specified fields
            search_fields_lower = [f.lower() for f in search_fields]
            if "company" in search_fields_lower:
                fields_to_search.append(("company", company.name))
            if "industries" in search_fields_lower:
                fields_to_search.append(("industries", ContactRepository._array_column_as_text(company.industries, dialect)))
            if "keywords" in search_fields_lower:
                fields_to_search.append(("keywords", ContactRepository._array_column_as_text(company.keywords, dialect)))
        else:
            # Default: search all fields
            fields_to_search = [
                ("company", company.name),
                ("industries", ContactRepository._array_column_as_text(company.industries, dialect)),
                ("keywords", ContactRepository._array_column_as_text(company.keywords, dialect)),
            ]

        # Remove excluded fields
        if exclude_fields:
            exclude_fields_lower = [f.lower() for f in exclude_fields]
            fields_to_search = [
                (name, col) for name, col in fields_to_search
                if name not in exclude_fields_lower
            ]

        if not fields_to_search:
            return stmt

        # Build conditions for each keyword term
        if use_and_logic:
            # AND logic: all keywords must match in at least one field
            field_conditions = []
            for field_name, field_column in fields_to_search:
                term_conditions = [field_column.ilike(f"%{term}%") for term in search_terms]
                field_conditions.append(and_(*term_conditions))
            # At least one field must match all terms
            return stmt.where(or_(*field_conditions))
        else:
            # OR logic: any keyword matches in any field
            conditions = []
            for field_name, field_column in fields_to_search:
                for term in search_terms:
                    conditions.append(field_column.ilike(f"%{term}%"))
            return stmt.where(or_(*conditions))

    async def get_contact_with_relations(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> Optional[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        """Fetch a contact and its related entities using separate queries."""
        contact = await self.get_by_uuid(session, contact_uuid)
        if not contact:
            return None
        
        company = await fetch_company_by_uuid(session, contact.company_id) if contact.company_id else None
        contact_meta = await fetch_contact_metadata_by_uuid(session, contact_uuid)
        company_meta = await fetch_company_metadata_by_uuid(session, company.uuid) if company else None
        
        # Contact with relations retrieved for specified contact_uuid
        return (contact, company, contact_meta, company_meta)

    async def list_contacts_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        limit: Optional[int],
        offset: int,
    ) -> Sequence[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
        """Return contacts for a specific company with associated metadata rows.
        
        Optimized to only join ContactMetadata when needed.
        """
        from app.schemas.filters import CompanyContactFilterParams
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        # Listing contacts for company with specified UUID, limit, offset, ordering, and active filter keys
        
        # Use minimal query with EXISTS subqueries (no joins)
        stmt = self.base_query_minimal()
        stmt = stmt.where(Contact.company_id == company_uuid)
        
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        
        # Apply filters using EXISTS subqueries
        # Create a simplified filter object for company contacts (only contact and contact_metadata filters apply)
        from app.schemas.filters import ContactFilterParams
        contact_filters = ContactFilterParams(
            first_name=filters.first_name,
            last_name=filters.last_name,
            title=filters.title,
            seniority=filters.seniority,
            email=filters.email,
            email_status=filters.email_status,
            mobile_phone=filters.mobile_phone,
            contact_location=filters.contact_location,
            department=filters.department,
            exclude_departments=filters.exclude_departments,
            exclude_titles=filters.exclude_titles,
            exclude_contact_locations=filters.exclude_contact_locations,
            exclude_seniorities=filters.exclude_seniorities,
            work_direct_phone=filters.work_direct_phone,
            home_phone=filters.home_phone,
            other_phone=filters.other_phone,
            city=filters.city,
            state=filters.state,
            country=filters.country,
            person_linkedin_url=filters.person_linkedin_url,
            website=filters.website,
            stage=filters.stage,
            facebook_url=filters.facebook_url,
            twitter_url=filters.twitter_url,
            search=filters.search,
            created_at_after=filters.created_at_after,
            created_at_before=filters.created_at_before,
            updated_at_after=filters.updated_at_after,
            updated_at_before=filters.updated_at_before,
        )
        
        stmt = self._apply_filters_with_exists(stmt, contact_filters, dialect_name=dialect_name)
        if filters.search:
            stmt = self._apply_search_terms_with_exists(stmt, filters.search, contact_filters, dialect_name=dialect_name)
        
        # Build ordering map using subqueries for related table columns
        ordering_map = self._build_ordering_map_with_subqueries(filters.ordering, dialect_name=dialect_name)
        stmt = apply_ordering(stmt, filters.ordering, ordering_map)
        
        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        
        result = await session.execute(stmt)
        contacts = result.scalars().all()
        
        # Extract foreign keys
        company_ids = {c.company_id for c in contacts if c.company_id}
        contact_uuids = {c.uuid for c in contacts}
        
        # Batch fetch related entities
        companies_dict = await batch_fetch_companies_by_uuids(session, company_ids)
        contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
        
        # Extract company UUIDs from fetched companies
        company_uuids = {c.uuid for c in companies_dict.values()}
        company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
        
        # Reconstruct tuples
        normalized_rows = []
        for contact in contacts:
            company = companies_dict.get(contact.company_id) if contact.company_id else None
            contact_meta = contact_meta_dict.get(contact.uuid)
            company_meta = company_meta_dict.get(company.uuid) if company else None
            normalized_rows.append((contact, company, contact_meta, company_meta))
        
        return normalized_rows

    async def count_contacts_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
    ) -> int:
        """Count contacts for a specific company that match the supplied filters.
        
        Optimized to use EXISTS subqueries instead of joins.
        """
        from app.schemas.filters import CompanyContactFilterParams
        
        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())
        
        # Use minimal query with EXISTS subqueries
        stmt = select(func.count(Contact.id)).select_from(Contact)
        stmt = stmt.where(Contact.company_id == company_uuid)
        
        # Apply contact-only filters directly
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        dialect = (dialect_name or "").lower()
        
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name, dialect_name=dialect_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name, dialect_name=dialect_name)
        # Use trigram optimization for title column
        stmt = self._apply_multi_value_filter(
            stmt, Contact.title, filters.title, 
            dialect_name=dialect_name, 
            use_trigram_optimization=True
        )
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority, dialect_name=dialect_name)
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
        
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
        if filters.exclude_titles:
            # Exclude titles are normalized (words sorted alphabetically) in apollo_analysis_service
            # We need to normalize the database column before comparison
            # Applying normalized exclude_titles filter
            stmt = self._apply_normalized_title_exclusion(
                stmt, Contact.title, filters.exclude_titles,
                dialect_name=dialect_name
            )
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        
        # ContactMetadata filters using EXISTS
        contact_meta_fields = [
            filters.work_direct_phone, filters.home_phone, filters.other_phone,
            filters.city, filters.state, filters.country, filters.person_linkedin_url,
            filters.website, filters.stage, filters.facebook_url, filters.twitter_url,
        ]
        if any(field is not None for field in contact_meta_fields):
            from sqlalchemy import exists
            contact_meta_subq = select(1)
            contact_meta_subq = contact_meta_subq.select_from(ContactMetadata)
            contact_meta_subq = contact_meta_subq.where(ContactMetadata.uuid == Contact.uuid)
            
            if filters.work_direct_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.work_direct_phone, filters.work_direct_phone
                )
            if filters.home_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.home_phone, filters.home_phone
                )
            if filters.other_phone:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.other_phone, filters.other_phone
                )
            if filters.city:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.city, filters.city
                )
            if filters.state:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.state, filters.state
                )
            if filters.country:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.country, filters.country
                )
            if filters.person_linkedin_url:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.linkedin_url, filters.person_linkedin_url
                )
            if filters.website:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.website, filters.website
                )
            if filters.stage:
                contact_meta_subq = self._apply_multi_value_filter(
                    contact_meta_subq, ContactMetadata.stage, filters.stage
                )
            if filters.facebook_url:
                contact_meta_subq = contact_meta_subq.where(
                    ContactMetadata.facebook_url.ilike(f"%{filters.facebook_url}%")
                )
            if filters.twitter_url:
                contact_meta_subq = contact_meta_subq.where(
                    ContactMetadata.twitter_url.ilike(f"%{filters.twitter_url}%")
                )
            
            stmt = stmt.where(exists(contact_meta_subq))
        
        # Apply search if needed
        if filters.search:
            from sqlalchemy import exists
            search_stripped = filters.search.strip()
            if search_stripped:
                pattern = f"%{search_stripped}%"
                contact_conditions = [
                    Contact.first_name.ilike(pattern),
                    Contact.last_name.ilike(pattern),
                    Contact.email.ilike(pattern),
                    Contact.title.ilike(pattern),
                    Contact.seniority.ilike(pattern),
                    Contact.text_search.ilike(pattern),
                ]
                
                # ContactMetadata search using EXISTS
                if any(field is not None for field in contact_meta_fields):
                    contact_meta_search_subq = (
                        select(1)
                        .select_from(ContactMetadata)
                        .where(ContactMetadata.uuid == Contact.uuid)
                        .where(
                            or_(
                                ContactMetadata.city.ilike(pattern),
                                ContactMetadata.state.ilike(pattern),
                                ContactMetadata.country.ilike(pattern),
                                ContactMetadata.linkedin_url.ilike(pattern),
                                ContactMetadata.twitter_url.ilike(pattern),
                            )
                        )
                    )
                    contact_conditions.append(exists(contact_meta_search_subq))
                
                if contact_conditions:
                    stmt = stmt.where(or_(*contact_conditions))
        
        # Temporal filters
        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
        
        result = await session.execute(stmt)
        count = result.scalar() or 0
        return count

    def _convert_company_contact_filters_to_contact_filters(
        self,
        filters: CompanyContactFilterParams,
    ) -> ContactFilterParams:
        """Convert CompanyContactFilterParams to ContactFilterParams."""
        from app.schemas.filters import ContactFilterParams
        return ContactFilterParams(
            first_name=filters.first_name,
            last_name=filters.last_name,
            title=filters.title,
            seniority=filters.seniority,
            email=filters.email,
            email_status=filters.email_status,
            mobile_phone=filters.mobile_phone,
            contact_location=filters.contact_location,
            department=filters.department,
            exclude_departments=filters.exclude_departments,
            exclude_titles=filters.exclude_titles,
            exclude_contact_locations=filters.exclude_contact_locations,
            exclude_seniorities=filters.exclude_seniorities,
            work_direct_phone=filters.work_direct_phone,
            home_phone=filters.home_phone,
            other_phone=filters.other_phone,
            city=filters.city,
            state=filters.state,
            country=filters.country,
            person_linkedin_url=filters.person_linkedin_url,
            website=filters.website,
            stage=filters.stage,
            facebook_url=filters.facebook_url,
            twitter_url=filters.twitter_url,
            search=filters.search,
            created_at_after=filters.created_at_after,
            created_at_before=filters.created_at_before,
            updated_at_after=filters.updated_at_after,
            updated_at_before=filters.updated_at_before,
        )

    async def _build_department_attribute_query_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        filters: CompanyContactFilterParams,
        params: AttributeListParams,
    ) -> Select:
        """Build query for department array attribute by company."""
        # Get filtered contact UUIDs using EXISTS subqueries
        contact_filter_stmt = select(Contact.uuid)
        contact_filter_stmt = contact_filter_stmt.select_from(Contact)
        contact_filter_stmt = contact_filter_stmt.where(Contact.company_id == company_uuid)
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        
        # Convert CompanyContactFilterParams to ContactFilterParams for filtering
        contact_filters = self._convert_company_contact_filters_to_contact_filters(filters)
        
        contact_filter_stmt = self._apply_filters_with_exists(contact_filter_stmt, contact_filters, dialect_name=dialect_name)
        if filters.search:
            contact_filter_stmt = self._apply_search_terms_with_exists(
                contact_filter_stmt, filters.search, contact_filters, dialect_name=dialect_name
            )
        
        # Get filtered contact UUIDs
        filtered_contact_uuids_subq = contact_filter_stmt.subquery()
        
        # Use unnest on filtered contacts only
        unnest_subquery = (
            select(func.unnest(Contact.departments).label("value"))
            .select_from(Contact)
            .where(Contact.uuid.in_(select(filtered_contact_uuids_subq.c.uuid)))
            .where(Contact.departments.isnot(None))
        )
        
        stmt = (
            select(unnest_subquery.c.value)
            .where(unnest_subquery.c.value.isnot(None))
            .where(unnest_subquery.c.value != "")
        )
        
        # Extract value column for reuse
        value_column = unnest_subquery.c.value
        
        if params.search:
            stmt = stmt.where(value_column.ilike(f"%{params.search}%"))
        
        if params.distinct:
            stmt = stmt.distinct()
        
        # Apply ordering
        if params.ordering:
            if params.ordering.startswith("-"):
                stmt = stmt.order_by(value_column.desc())
            else:
                stmt = stmt.order_by(value_column.asc())
        else:
            stmt = stmt.order_by(value_column.asc())
        
        if params.limit:
            stmt = stmt.limit(params.limit)
        if params.offset:
            stmt = stmt.offset(params.offset)
        
        return stmt

    async def _build_scalar_attribute_query_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        attribute: str,
        filters: CompanyContactFilterParams,
        params: AttributeListParams,
    ) -> Select:
        """Build query for scalar attribute by company."""
        from sqlalchemy import select as sql_select
        
        # Map attribute names to columns
        column_map = {
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "seniority": Contact.seniority,
            "email_status": Contact.email_status,
        }
        
        column = column_map.get(attribute)
        
        # Convert column to scalar subquery if it's from ContactMetadata
        if attribute in ("city", "state", "country"):
            if attribute == "city":
                column = (
                    sql_select(ContactMetadata.city)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery()
                )
            elif attribute == "state":
                column = (
                    sql_select(ContactMetadata.state)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery()
                )
            elif attribute == "country":
                column = (
                    sql_select(ContactMetadata.country)
                    .where(ContactMetadata.uuid == Contact.uuid)
                    .scalar_subquery()
                )
        
        # Build query without JOINs
        stmt = select(column)
        stmt = stmt.select_from(Contact)
        stmt = stmt.where(Contact.company_id == company_uuid)
        
        # Apply filters using EXISTS subqueries
        dialect_name = getattr(session.bind.dialect, "name", None) if session.bind else None
        contact_filters = self._convert_company_contact_filters_to_contact_filters(filters)
        
        stmt = self._apply_filters_with_exists(stmt, contact_filters, dialect_name=dialect_name)
        if filters.search:
            stmt = self._apply_search_terms_with_exists(
                stmt, filters.search, contact_filters, dialect_name=dialect_name
            )
        
        stmt = stmt.where(column.isnot(None))
        stmt = stmt.where(column != "")
        
        if params.search:
            stmt = stmt.where(column.ilike(f"%{params.search}%"))
        
        if params.distinct:
            stmt = stmt.distinct()
        
        # Apply ordering
        if params.ordering:
            if params.ordering.startswith("-"):
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())
        else:
            stmt = stmt.order_by(column.asc())
        
        if params.limit:
            stmt = stmt.limit(params.limit)
        if params.offset:
            stmt = stmt.offset(params.offset)
        
        return stmt

    async def list_attribute_values_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
        attribute: str,
        filters: CompanyContactFilterParams,
        params: AttributeListParams,
    ) -> Sequence[str]:
        """Return distinct attribute values for contacts within a specific company."""
        # Map attribute names to columns
        column_map = {
            "first_name": Contact.first_name,
            "last_name": Contact.last_name,
            "title": Contact.title,
            "seniority": Contact.seniority,
            "email_status": Contact.email_status,
            "department": Contact.departments,  # Array field
            "city": None,  # Will use scalar subquery
            "state": None,  # Will use scalar subquery
            "country": None,  # Will use scalar subquery
        }
        
        if attribute not in column_map:
            return []
        
        # Handle array fields specially
        if attribute == "department":
            stmt = await self._build_department_attribute_query_by_company(
                session, company_uuid, filters, params
            )
        else:
            stmt = await self._build_scalar_attribute_query_by_company(
                session, company_uuid, attribute, filters, params
            )
        
        result = await session.execute(stmt)
        values = [row[0] for row in result.fetchall() if row[0]]
        return values

    def _apply_company_contact_filters(
        self,
        stmt: Select,
        filters: CompanyContactFilterParams,
        company: Company,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply CompanyContactFilterParams to the given SQLAlchemy statement."""
        from app.schemas.filters import CompanyContactFilterParams
        
        # Applying company contact filters with sorted filter keys
        
        # Contact identity fields
        dialect = (dialect_name or "").lower()
        stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name, dialect_name=dialect_name)
        stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name, dialect_name=dialect_name)
        # Use trigram optimization for title column
        stmt = self._apply_multi_value_filter(
            stmt, Contact.title, filters.title, 
            dialect_name=dialect_name, 
            use_trigram_optimization=True
        )
        stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority, dialect_name=dialect_name)
        stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
        stmt = apply_ilike_filter(stmt, Contact.status, filters.status)
        stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
        stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
        
        # Department filter (array field)
        if filters.department:
            dialect = (dialect_name or "").lower()
            if dialect == "postgresql":
                stmt = stmt.where(
                    func.array_to_string(Contact.departments, ",").ilike(f"%{filters.department}%")
                )
            else:
                stmt = stmt.where(
                    cast(Contact.departments, Text).ilike(f"%{filters.department}%")
                )
        
        # Contact metadata fields
        if contact_meta is not None:
            stmt = self._apply_multi_value_filter(stmt, contact_meta.work_direct_phone, filters.work_direct_phone)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.home_phone, filters.home_phone)
            stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.other_phone, filters.other_phone)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.city, filters.city)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.state, filters.state)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.country, filters.country)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.linkedin_url, filters.person_linkedin_url)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.website, filters.website)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.facebook_url, filters.facebook_url)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.twitter_url, filters.twitter_url)
            stmt = self._apply_multi_value_filter(stmt, contact_meta.stage, filters.stage)
        
        # Exclusion filters
        if filters.exclude_titles:
            # Exclude titles are normalized (words sorted alphabetically) in apollo_analysis_service
            # We need to normalize the database column before comparison
            # Applying normalized exclude_titles filter
            stmt = self._apply_normalized_title_exclusion(
                stmt, Contact.title, filters.exclude_titles,
                dialect_name=dialect_name
            )
        
        if filters.exclude_contact_locations:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
        
        if filters.exclude_seniorities:
            stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
        
        if filters.exclude_departments:
            dialect = (dialect_name or "").lower()
            stmt = self._apply_array_text_exclusion(
                stmt,
                Contact.departments,
                filters.exclude_departments,
                dialect,
            )
        
        # Temporal filters
        if filters.created_at_after is not None:
            stmt = stmt.where(Contact.created_at >= filters.created_at_after)
        if filters.created_at_before is not None:
            stmt = stmt.where(Contact.created_at <= filters.created_at_before)
        if filters.updated_at_after is not None:
            stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
        if filters.updated_at_before is not None:
            stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
        
        return stmt

    def _apply_company_contact_search(
        self,
        stmt: Select,
        search: Optional[str],
        company: Company,
        company_meta: CompanyMetadata | None = None,
        contact_meta: ContactMetadata | None = None,
        *,
        dialect_name: str | None = None,
    ) -> Select:
        """Apply case-insensitive search across contact text columns for company contacts."""
            # "Applying company contact search: search_present=%s", bool(search))
        
        if not search:
            return stmt
        
        dialect = (dialect_name or "").lower()
        columns: list[Any] = [
            Contact.first_name,
            Contact.last_name,
            Contact.email,
            Contact.title,
            Contact.seniority,
            Contact.text_search,
        ]
        
        if contact_meta is not None:
            columns.extend([
                contact_meta.city,
                contact_meta.state,
                contact_meta.country,
                contact_meta.linkedin_url,
                contact_meta.website,
                contact_meta.facebook_url,
                contact_meta.twitter_url,
            ])
        
        stmt = apply_search(stmt, search, columns)
        return stmt

