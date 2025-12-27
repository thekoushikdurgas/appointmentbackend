"""Service for converting filter parameters to VQL (Vivek Query Language) format."""

import logging
from typing import Any, Dict, List, Optional

from app.schemas.filters import CompanyFilterParams, ContactFilterParams
from app.schemas.vql import (
    VQLKeywordMatch,
    VQLOrderBy,
    VQLQuery,
    VQLRangeQuery,
    VQLTextMatch,
    VQLWhere,
)

logger = logging.getLogger(__name__)


class VQLConverter:
    """Converts filter parameters to VQL query format."""

    # Field mappings from backend filters to VQL field names
    CONTACT_TEXT_FIELDS = {
        "first_name": "first_name",
        "last_name": "last_name",
        "title": "title",
        "city": "city",
        "state": "state",
        "country": "country",
        "person_linkedin_url": "linkedin_url",
        "contact_location": "city",  # Map to city for now, can be expanded
    }

    CONTACT_KEYWORD_FIELDS = {
        "email": "email",
        "email_status": "email_status",
        "seniority": "seniority",
        "department": "departments",
        "departments": "departments",
        "company_id": "company_id",
    }

    # Denormalized company fields in contact index
    COMPANY_DENORMALIZED_FIELDS = {
        "company": "company_name",
        "include_company_name": "company_name",
        "company_name_for_emails": "company_name",  # Approximate mapping
        "company_location": "company_address",
        "company_address": "company_address",
        "company_city": "company_city",
        "company_state": "company_state",
        "company_country": "company_country",
        "company_linkedin_url": "company_linkedin_url",
        "employees_count": "company_employees_count",
        "employees_min": "company_employees_count",
        "employees_max": "company_employees_count",
        "annual_revenue": "company_annual_revenue",
        "annual_revenue_min": "company_annual_revenue",
        "annual_revenue_max": "company_annual_revenue",
        "total_funding": "company_total_funding",
        "total_funding_min": "company_total_funding",
        "total_funding_max": "company_total_funding",
        "technologies": "company_technologies",
        "keywords": "company_keywords",
        "industries": "company_industries",
    }

    COMPANY_TEXT_FIELDS = {
        "name": "name",
        "address": "address",
        "city": "city",
        "state": "state",
        "country": "country",
        "linkedin_url": "linkedin_url",
        "website": "website",
        "normalized_domain": "normalized_domain",
    }

    COMPANY_KEYWORD_FIELDS = {
        "industries": "industries",
        "keywords": "keywords",
        "technologies": "technologies",
    }

    def convert_contact_filters_to_vql(
        self,
        filters: ContactFilterParams,
        limit: Optional[int] = None,
        offset: int = 0,
        page: Optional[int] = None,
    ) -> VQLQuery:
        """
        Convert ContactFilterParams to VQL query.

        Args:
            filters: Contact filter parameters
            limit: Results per page
            offset: Offset for pagination
            page: Page number (1-indexed)

        Returns:
            VQL query object
        """
        where = self._build_contact_where(filters)
        order_by = self._build_order_by(filters.ordering) if filters.ordering else None

        # Calculate page and limit
        vql_page = page or filters.page or 1
        vql_limit = limit or filters.page_size or 25

        # Handle cursor-based pagination
        search_after = None
        if filters.cursor:
            # For now, cursor is handled as offset in backend
            # VQL will use search_after for proper cursor pagination
            pass

        return VQLQuery(
            where=where,
            order_by=order_by,
            page=vql_page,
            limit=min(vql_limit, 100),  # VQL max limit is 100
            search_after=search_after,
        )

    def convert_company_filters_to_vql(
        self,
        filters: CompanyFilterParams,
        limit: Optional[int] = None,
        offset: int = 0,
        page: Optional[int] = None,
    ) -> VQLQuery:
        """
        Convert CompanyFilterParams to VQL query.

        Args:
            filters: Company filter parameters
            limit: Results per page
            offset: Offset for pagination
            page: Page number (1-indexed)

        Returns:
            VQL query object
        """
        where = self._build_company_where(filters)
        order_by = self._build_order_by(filters.ordering) if filters.ordering else None

        # Calculate page and limit
        vql_page = page or filters.page or 1
        vql_limit = limit or filters.page_size or 25

        return VQLQuery(
            where=where,
            order_by=order_by,
            page=vql_page,
            limit=min(vql_limit, 100),  # VQL max limit is 100
        )

    def _build_contact_where(self, filters: ContactFilterParams) -> Optional[VQLWhere]:
        """Build VQL where clause for contact filters."""
        text_matches_must: List[VQLTextMatch] = []
        text_matches_must_not: List[VQLTextMatch] = []
        keyword_must: Dict[str, Any] = {}
        keyword_must_not: Dict[str, Any] = {}
        range_must: Dict[str, Dict[str, Any]] = {}

        filter_dict = filters.model_dump(exclude_none=True)

        # Process text matches
        for field, vql_field in self.CONTACT_TEXT_FIELDS.items():
            if field in filter_dict:
                value = filter_dict[field]
                if value:
                    text_matches_must.append(
                        VQLTextMatch(
                            text_value=str(value),
                            filter_key=vql_field,
                            search_type="shuffle",
                            fuzzy=True,
                        )
                    )

        # Process denormalized company text fields
        for field, vql_field in self.COMPANY_DENORMALIZED_FIELDS.items():
            if field in filter_dict and vql_field.startswith("company_"):
                value = filter_dict[field]
                if isinstance(value, str) and value:
                    text_matches_must.append(
                        VQLTextMatch(
                            text_value=value,
                            filter_key=vql_field,
                            search_type="shuffle",
                            fuzzy=True,
                        )
                    )

        # Process keyword matches
        for field, vql_field in self.CONTACT_KEYWORD_FIELDS.items():
            if field in filter_dict:
                value = filter_dict[field]
                if value:
                    if isinstance(value, list):
                        keyword_must[vql_field] = value
                    else:
                        keyword_must[vql_field] = str(value)

        # Process denormalized company keyword fields
        company_keyword_fields = {
            "technologies": "company_technologies",
            "keywords": "company_keywords",
            "industries": "company_industries",
        }
        for field, vql_field in company_keyword_fields.items():
            if field in filter_dict:
                value = filter_dict[field]
                if value:
                    if isinstance(value, list):
                        keyword_must[vql_field] = value
                    elif isinstance(value, str):
                        # Split comma-separated values
                        keyword_must[vql_field] = [v.strip() for v in value.split(",")]

        # Process email_status
        if filters.email_status:
            keyword_must["email_status"] = filters.email_status

        # Process seniority
        if filters.seniority:
            keyword_must["seniority"] = filters.seniority

        # Process departments
        if filters.department:
            if isinstance(filters.department, list):
                keyword_must["departments"] = filters.department
            else:
                keyword_must["departments"] = [filters.department]

        # Process range queries for denormalized company fields
        if filters.employees_min is not None or filters.employees_max is not None:
            range_must["company_employees_count"] = {}
            if filters.employees_min is not None:
                range_must["company_employees_count"]["gte"] = filters.employees_min
            if filters.employees_max is not None:
                range_must["company_employees_count"]["lte"] = filters.employees_max

        if filters.annual_revenue_min is not None or filters.annual_revenue_max is not None:
            range_must["company_annual_revenue"] = {}
            if filters.annual_revenue_min is not None:
                range_must["company_annual_revenue"]["gte"] = filters.annual_revenue_min
            if filters.annual_revenue_max is not None:
                range_must["company_annual_revenue"]["lte"] = filters.annual_revenue_max

        if filters.total_funding_min is not None or filters.total_funding_max is not None:
            range_must["company_total_funding"] = {}
            if filters.total_funding_min is not None:
                range_must["company_total_funding"]["gte"] = filters.total_funding_min
            if filters.total_funding_max is not None:
                range_must["company_total_funding"]["lte"] = filters.total_funding_max

        # Process exclude filters
        if filters.exclude_titles:
            for title in filters.exclude_titles:
                text_matches_must_not.append(
                    VQLTextMatch(
                        text_value=title,
                        filter_key="title",
                        search_type="shuffle",
                        fuzzy=True,
                    )
                )

        if filters.exclude_seniorities:
            keyword_must_not["seniority"] = filters.exclude_seniorities

        if filters.exclude_departments:
            keyword_must_not["departments"] = filters.exclude_departments

        if filters.exclude_company_ids:
            keyword_must_not["company_id"] = filters.exclude_company_ids

        if filters.exclude_industries:
            keyword_must_not["company_industries"] = filters.exclude_industries

        if filters.exclude_technologies:
            keyword_must_not["company_technologies"] = filters.exclude_technologies

        if filters.exclude_keywords:
            keyword_must_not["company_keywords"] = filters.exclude_keywords

        # Build where clause
        where_dict: Dict[str, Any] = {}

        if text_matches_must or text_matches_must_not:
            where_dict["text_matches"] = {}
            if text_matches_must:
                where_dict["text_matches"]["must"] = [
                    tm.model_dump(exclude_none=True) for tm in text_matches_must
                ]
            if text_matches_must_not:
                where_dict["text_matches"]["must_not"] = [
                    tm.model_dump(exclude_none=True) for tm in text_matches_must_not
                ]

        if keyword_must or keyword_must_not:
            where_dict["keyword_match"] = {}
            if keyword_must:
                where_dict["keyword_match"]["must"] = keyword_must
            if keyword_must_not:
                where_dict["keyword_match"]["must_not"] = keyword_must_not

        if range_must:
            where_dict["range_query"] = {"must": range_must}

        if not where_dict:
            return None

        return VQLWhere(**where_dict)

    def _build_company_where(self, filters: CompanyFilterParams) -> Optional[VQLWhere]:
        """Build VQL where clause for company filters."""
        text_matches_must: List[VQLTextMatch] = []
        text_matches_must_not: List[VQLTextMatch] = []
        keyword_must: Dict[str, Any] = {}
        keyword_must_not: Dict[str, Any] = {}
        range_must: Dict[str, Dict[str, Any]] = {}

        filter_dict = filters.model_dump(exclude_none=True)

        # Process text matches
        for field, vql_field in self.COMPANY_TEXT_FIELDS.items():
            if field in filter_dict:
                value = filter_dict[field]
                if value:
                    text_matches_must.append(
                        VQLTextMatch(
                            text_value=str(value),
                            filter_key=vql_field,
                            search_type="shuffle",
                            fuzzy=True,
                        )
                    )

        # Process keyword matches
        for field, vql_field in self.COMPANY_KEYWORD_FIELDS.items():
            if field in filter_dict:
                value = filter_dict[field]
                if value:
                    if isinstance(value, list):
                        keyword_must[vql_field] = value
                    elif isinstance(value, str):
                        # Split comma-separated values
                        keyword_must[vql_field] = [v.strip() for v in value.split(",")]

        # Process range queries
        if filters.employees_min is not None or filters.employees_max is not None:
            range_must["employees_count"] = {}
            if filters.employees_min is not None:
                range_must["employees_count"]["gte"] = filters.employees_min
            if filters.employees_max is not None:
                range_must["employees_count"]["lte"] = filters.employees_max

        if filters.annual_revenue_min is not None or filters.annual_revenue_max is not None:
            range_must["annual_revenue"] = {}
            if filters.annual_revenue_min is not None:
                range_must["annual_revenue"]["gte"] = filters.annual_revenue_min
            if filters.annual_revenue_max is not None:
                range_must["annual_revenue"]["lte"] = filters.annual_revenue_max

        if filters.total_funding_min is not None or filters.total_funding_max is not None:
            range_must["total_funding"] = {}
            if filters.total_funding_min is not None:
                range_must["total_funding"]["gte"] = filters.total_funding_min
            if filters.total_funding_max is not None:
                range_must["total_funding"]["lte"] = filters.total_funding_max

        # Build where clause
        where_dict: Dict[str, Any] = {}

        if text_matches_must or text_matches_must_not:
            where_dict["text_matches"] = {}
            if text_matches_must:
                where_dict["text_matches"]["must"] = [
                    tm.model_dump(exclude_none=True) for tm in text_matches_must
                ]
            if text_matches_must_not:
                where_dict["text_matches"]["must_not"] = [
                    tm.model_dump(exclude_none=True) for tm in text_matches_must_not
                ]

        if keyword_must or keyword_must_not:
            where_dict["keyword_match"] = {}
            if keyword_must:
                where_dict["keyword_match"]["must"] = keyword_must
            if keyword_must_not:
                where_dict["keyword_match"]["must_not"] = keyword_must_not

        if range_must:
            where_dict["range_query"] = {"must": range_must}

        if not where_dict:
            return None

        return VQLWhere(**where_dict)

    def _build_order_by(self, ordering: str) -> List[VQLOrderBy]:
        """
        Convert ordering string to VQL order_by list.

        Args:
            ordering: Ordering string (e.g., "created_at:desc,email:asc")

        Returns:
            List of VQLOrderBy objects
        """
        order_by_list: List[VQLOrderBy] = []

        if not ordering:
            return order_by_list

        # Split by comma and parse each ordering clause
        for order_clause in ordering.split(","):
            order_clause = order_clause.strip()
            if ":" in order_clause:
                field, direction = order_clause.split(":", 1)
                field = field.strip()
                direction = direction.strip().lower()
                if direction not in ("asc", "desc"):
                    direction = "asc"
            else:
                field = order_clause.strip()
                direction = "asc"

            if field:
                order_by_list.append(
                    VQLOrderBy(order_by=field, order_direction=direction)
                )

        return order_by_list

