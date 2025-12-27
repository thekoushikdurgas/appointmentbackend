"""Helper class for detecting when EXISTS subqueries are needed in repository queries.

This module provides a reusable pattern for determining which tables need
EXISTS subqueries based on filter parameters. This eliminates code duplication
in repository classes that use conditional JOINs via EXISTS subqueries.

Used by:
- ContactRepository (for contact queries with company/metadata filters)
- CompanyRepository (potentially for similar patterns)
"""

from __future__ import annotations

from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExistsSubqueryDetector:
    """
    Helper class for detecting when EXISTS subqueries are needed.
    
    This class encapsulates the pattern of checking if any fields in a list
    are not None, which indicates that an EXISTS subquery is needed for
    that table.
    
    Example:
        detector = ExistsSubqueryDetector()
        if detector.needs_subquery(filters, [filters.company, filters.employees_count]):
            # Add Company EXISTS subquery
    """

    @staticmethod
    def needs_subquery(filters: Any, field_list: list[Any]) -> bool:
        """
        Check if any field in the list is not None.
        
        Args:
            filters: Filter object (for accessing fields)
            field_list: List of filter fields to check
        
        Returns:
            True if any field is not None, False otherwise
        """
        return any(field is not None for field in field_list)

    @staticmethod
    def needs_subquery_for_search(search: Optional[str]) -> bool:
        """
        Check if search term requires EXISTS subquery.
        
        Search terms typically require checking multiple tables, so they
        often need EXISTS subqueries.
        
        Args:
            search: Search term string
        
        Returns:
            True if search is not None and not empty, False otherwise
        """
        return search is not None and bool(search.strip())


class ContactFilterSubqueryDetector(ExistsSubqueryDetector):
    """
    Specialized detector for ContactFilterParams.
    
    Provides convenience methods for common contact filter patterns.
    """

    @staticmethod
    def needs_company_subquery(filters: Any) -> bool:
        """
        Check if Company table EXISTS subquery is needed.
        
        Args:
            filters: ContactFilterParams instance
        
        Returns:
            True if any company-related filter is set
        """
        company_fields = [
            filters.company,
            filters.include_company_name,
            filters.company_location,
            filters.employees_count,
            filters.employees_min,
            filters.employees_max,
            filters.annual_revenue,
            filters.annual_revenue_min,
            filters.annual_revenue_max,
            filters.total_funding,
            filters.total_funding_min,
            filters.total_funding_max,
            filters.technologies,
            filters.technologies_uids,
            filters.keywords,
            filters.keywords_and,
            filters.industries,
            filters.exclude_company_locations,
            filters.exclude_company_name,
            filters.exclude_technologies,
            filters.exclude_keywords,
            filters.exclude_industries,
            filters.company_address,
        ]
        return ExistsSubqueryDetector.needs_subquery(filters, company_fields)

    @staticmethod
    def needs_contact_metadata_subquery(filters: Any) -> bool:
        """
        Check if ContactMetadata table EXISTS subquery is needed.
        
        Args:
            filters: ContactFilterParams instance
        
        Returns:
            True if any contact metadata filter is set
        """
        contact_meta_fields = [
            filters.work_direct_phone,
            filters.home_phone,
            filters.other_phone,
            filters.city,
            filters.state,
            filters.country,
            filters.person_linkedin_url,
            filters.website,
            filters.stage,
            filters.facebook_url,
            filters.twitter_url,
        ]
        return ExistsSubqueryDetector.needs_subquery(filters, contact_meta_fields)

    @staticmethod
    def needs_company_metadata_subquery(filters: Any) -> bool:
        """
        Check if CompanyMetadata table EXISTS subquery is needed.
        
        Args:
            filters: ContactFilterParams instance
        
        Returns:
            True if any company metadata filter is set
        """
        company_meta_fields = [
            filters.include_domain_list,
            filters.exclude_domain_list,
            filters.company_name_for_emails,
            filters.corporate_phone,
            filters.company_phone,
            filters.company_city,
            filters.company_state,
            filters.company_country,
            filters.company_linkedin_url,
            filters.latest_funding_amount_min,
            filters.latest_funding_amount_max,
            filters.facebook_url,
            filters.twitter_url,
        ]
        return ExistsSubqueryDetector.needs_subquery(filters, company_meta_fields)

