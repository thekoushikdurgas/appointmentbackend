"""Service layer for Apollo.io URL analysis."""

from collections import defaultdict
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from fastapi import HTTPException, status

from app.core.logging import get_logger
from app.schemas.apollo import (
    AnalysisStatistics,
    ApolloUrlAnalysisResponse,
    ParameterCategory,
    ParameterDetail,
    UrlStructure,
)
from app.utils.industry_mapping import get_industry_names_from_ids

logger = get_logger(__name__)


class ApolloAnalysisService:
    """Business logic for Apollo.io URL analysis."""

    # Parameter categories mapping
    PARAM_CATEGORIES: Dict[str, List[str]] = {
        "Pagination": ["page"],
        "Sorting": ["sortByField", "sortAscending"],
        "Person Filters": [
            "personTitles[]",
            "personNotTitles[]",
            "personLocations[]",
            "personNotLocations[]",
            "personSeniorities[]",
            "personDepartmentOrSubdepartments[]",
        ],
        "Organization Filters": [
            "organizationNumEmployeesRanges[]",
            "organizationLocations[]",
            "organizationNotLocations[]",
            "organizationIndustryTagIds[]",
            "organizationNotIndustryTagIds[]",
            "organizationJobLocations[]",
            "organizationNumJobsRange[min]",
            "organizationJobPostedAtRange[min]",
            "revenueRange[min]",
            "revenueRange[max]",
            "organizationTradingStatus[]",
        ],
        "Email Filters": [
            "contactEmailStatusV2[]",
            "contactEmailExcludeCatchAll",
        ],
        "Keyword Filters": [
            "qOrganizationKeywordTags[]",
            "qNotOrganizationKeywordTags[]",
            "qAndedOrganizationKeywordTags[]",
            "includedOrganizationKeywordFields[]",
            "excludedOrganizationKeywordFields[]",
            "includedAndedOrganizationKeywordFields[]",
        ],
        "Search Lists": [
            "qOrganizationSearchListId",
            "qNotOrganizationSearchListId",
            "qPersonPersonaIds[]",
        ],
        "Technology": ["currentlyUsingAnyOfTechnologyUids[]"],
        "Market Segments": ["marketSegments[]"],
        "Intent": ["intentStrengths[]"],
        "Lookalike": ["lookalikeOrganizationIds[]"],
        "Prospecting": ["prospectedByCurrentTeam[]"],
        "Other": [
            "uniqueUrlId",
            "tour",
            "includeSimilarTitles",
            "existFields[]",
            "notOrganizationIds[]",
            "organizationIds[]",
            "qKeywords",
        ],
    }

    # Parameter descriptions mapping
    PARAM_DESCRIPTIONS: Dict[str, str] = {
        "page": "Page number for pagination",
        "sortByField": "Field to sort results by",
        "sortAscending": "Sort direction (true/false)",
        "personTitles[]": "Job titles to include",
        "personNotTitles[]": "Job titles to exclude",
        "personLocations[]": "Person locations to include",
        "personNotLocations[]": "Person locations to exclude",
        "personSeniorities[]": "Seniority levels to include",
        "personDepartmentOrSubdepartments[]": "Departments to include",
        "organizationNumEmployeesRanges[]": "Company size ranges",
        "organizationLocations[]": "Organization locations to include",
        "organizationNotLocations[]": "Organization locations to exclude",
        "organizationIndustryTagIds[]": "Industry tag IDs to include",
        "organizationNotIndustryTagIds[]": "Industry tag IDs to exclude",
        "organizationJobLocations[]": "Job posting locations",
        "organizationNumJobsRange[min]": "Minimum number of job postings",
        "organizationJobPostedAtRange[min]": "Job posting date range",
        "revenueRange[min]": "Minimum revenue",
        "revenueRange[max]": "Maximum revenue",
        "organizationTradingStatus[]": "Company trading status",
        "contactEmailStatusV2[]": "Email verification status",
        "contactEmailExcludeCatchAll": "Exclude catch-all emails",
        "qOrganizationKeywordTags[]": "Organization keywords to include",
        "qNotOrganizationKeywordTags[]": "Organization keywords to exclude",
        "qAndedOrganizationKeywordTags[]": "Organization keywords to include (ALL must match)",
        "includedOrganizationKeywordFields[]": "Fields to search for keywords",
        "excludedOrganizationKeywordFields[]": "Fields to exclude from keyword search",
        "includedAndedOrganizationKeywordFields[]": "Fields to search for ANDed keywords",
        "qOrganizationSearchListId": "Saved organization list ID",
        "qNotOrganizationSearchListId": "Excluded organization list ID",
        "qPersonPersonaIds[]": "Person persona IDs",
        "currentlyUsingAnyOfTechnologyUids[]": "Technology stack filters",
        "marketSegments[]": "Market segment filters",
        "intentStrengths[]": "Buying intent levels",
        "lookalikeOrganizationIds[]": "Similar organization IDs",
        "prospectedByCurrentTeam[]": "Prospecting status",
        "uniqueUrlId": "Unique identifier for saved searches",
        "tour": "Tour mode flag",
        "includeSimilarTitles": "Include similar titles",
        "existFields[]": "Required fields",
        "notOrganizationIds[]": "Excluded organization IDs",
        "organizationIds[]": "Organization IDs to include",
        "qKeywords": "Keyword search in profiles or organizations",
    }

    def __init__(self) -> None:
        """Initialize the service."""
        logger.debug("Entering ApolloAnalysisService.__init__")

    def analyze_url(self, url: str) -> ApolloUrlAnalysisResponse:
        """
        Analyze an Apollo.io URL and return structured analysis.

        Args:
            url: The Apollo.io URL to analyze

        Returns:
            ApolloUrlAnalysisResponse with categorized parameters and analysis

        Raises:
            HTTPException: If URL is invalid or not an Apollo.io URL
        """
        # logger.info("Analyzing Apollo URL: url_length=%d", len(url))

        # Validate URL
        if not url or not isinstance(url, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL is required and must be a string",
            )

        # Check if it's an Apollo.io URL
        if "apollo.io" not in url.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL must be from apollo.io domain",
            )

        try:
            # Parse URL structure
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Extract hash part (Apollo uses hash-based routing)
            hash_path: Optional[str] = None
            query_string: Optional[str] = None
            params: Dict[str, List[str]] = {}

            if "#" in url:
                hash_part = url.split("#", 1)[1]
                if "?" in hash_part:
                    path_part, query_part = hash_part.split("?", 1)
                    hash_path = path_part
                    query_string = query_part
                    # Parse query parameters
                    parsed_params = parse_qs(query_part, keep_blank_values=True)
                    # Decode URL-encoded values
                    for key, values in parsed_params.items():
                        params[key] = [unquote(v) for v in values]
                else:
                    hash_path = hash_part
            else:
                # Try parsing as regular query string
                if parsed_url.query:
                    query_string = parsed_url.query
                    parsed_params = parse_qs(parsed_url.query, keep_blank_values=True)
                    for key, values in parsed_params.items():
                        params[key] = [unquote(v) for v in values]

            # Build URL structure
            url_structure = UrlStructure(
                base_url=base_url,
                hash_path=hash_path,
                query_string=query_string,
                has_query_params=len(params) > 0,
            )

            # Categorize parameters
            categorized_params: Dict[str, Dict[str, ParameterDetail]] = defaultdict(dict)
            total_parameter_values = 0

            for param_name, param_values in params.items():
                total_parameter_values += len(param_values)

                # Find which category this parameter belongs to
                category_name = "Other"
                for cat_name, param_list in self.PARAM_CATEGORIES.items():
                    if param_name in param_list:
                        category_name = cat_name
                        break

                # Get description
                description = self.PARAM_DESCRIPTIONS.get(
                    param_name, "Filter parameter"
                )

                # Create parameter detail
                param_detail = ParameterDetail(
                    name=param_name,
                    values=param_values,
                    description=description,
                    category=category_name,
                )

                categorized_params[category_name][param_name] = param_detail

            # Build categories list
            categories_list: List[ParameterCategory] = []
            for category_name in sorted(self.PARAM_CATEGORIES.keys()):
                if category_name in categorized_params:
                    params_in_category = list(categorized_params[category_name].values())
                    categories_list.append(
                        ParameterCategory(
                            name=category_name,
                            parameters=params_in_category,
                            total_parameters=len(params_in_category),
                        )
                    )

            # Add any uncategorized parameters to "Other"
            if "Other" not in [cat.name for cat in categories_list]:
                other_params = categorized_params.get("Other", {})
                if other_params:
                    categories_list.append(
                        ParameterCategory(
                            name="Other",
                            parameters=list(other_params.values()),
                            total_parameters=len(other_params),
                        )
                    )

            # Build statistics
            statistics = AnalysisStatistics(
                total_parameters=len(params),
                total_parameter_values=total_parameter_values,
                categories_used=len(categories_list),
                categories=[cat.name for cat in categories_list],
            )

            # Build response
            response = ApolloUrlAnalysisResponse(
                url=url,
                url_structure=url_structure,
                categories=categories_list,
                statistics=statistics,
                raw_parameters=params,
            )

            # logger.info(
            #     "URL analysis complete: total_params=%d categories=%d",
            #     statistics.total_parameters,
            #     statistics.categories_used,
            # )

            return response

        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error analyzing Apollo URL: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while analyzing the URL",
            ) from exc

    @staticmethod
    def _normalize_title(title: str) -> str:
        """
        Normalize a job title by sorting words alphabetically.
        
        This allows matching titles regardless of word order:
        - "Project Manager" → "manager project"
        - "Manager Project" → "manager project"
        
        Args:
            title: Original job title
            
        Returns:
            Normalized title with words sorted alphabetically (lowercase)
        """
        # Convert to lowercase and split into words
        words = title.lower().split()
        # Sort words alphabetically
        words.sort()
        # Join back together
        return " ".join(words)

    def map_to_contact_filters(
        self, raw_parameters: dict[str, list[str]], include_unmapped: bool = False
    ) -> tuple[dict[str, any], dict[str, tuple[list[str], str]]] | dict[str, any]:
        """
        Map Apollo.io URL parameters to ContactFilterParams.

        Args:
            raw_parameters: Dictionary of parameter names to lists of values from Apollo URL
            include_unmapped: If True, returns tuple of (filters, unmapped_params)

        Returns:
            If include_unmapped is False: Dictionary that can be used to construct ContactFilterParams
            If include_unmapped is True: Tuple of (filters dict, unmapped params dict)
                unmapped params dict format: {param_name: (values, reason)}

        Note:
            - Multiple values are combined with OR logic (comma-separated for text filters)
            - Exclusion filters are passed as lists
            - ID-based parameters are skipped (no mapping available)
        """
        # logger.info("Mapping Apollo parameters to contact filters: params=%d", len(raw_parameters))

        contact_filters = {}
        mapped_params = set()
        unmapped_params = {}

        # Pagination: page → page
        if "page" in raw_parameters:
            try:
                contact_filters["page"] = int(raw_parameters["page"][0])
                mapped_params.add("page")
            except (ValueError, IndexError):
                pass

        # Sorting: sortByField + sortAscending → ordering
        if "sortByField" in raw_parameters:
            sort_field = raw_parameters["sortByField"][0]
            sort_ascending = raw_parameters.get("sortAscending", ["true"])[0].lower()

            # Apollo uses [none] to indicate no sorting - skip setting ordering in that case
            if sort_field and sort_field.lower() not in ["[none]", "none", ""]:
                # Map Apollo field names to contacts ordering fields
                field_map = {
                    "contact_name": "first_name",
                    "title": "title",
                    "company": "company",
                    "employees": "employees",
                    "revenue": "annual_revenue",
                    "funding": "total_funding",
                    "location": "city",
                    "recommendations_score": "created_at",  # Default fallback
                }

                mapped_field = field_map.get(sort_field, sort_field)
                # Prepend '-' for descending (when sortAscending is false)
                if sort_ascending == "false":
                    contact_filters["ordering"] = f"-{mapped_field}"
                else:
                    contact_filters["ordering"] = mapped_field
            
            # Always mark sortByField as mapped, even if it's [none]
            mapped_params.add("sortByField")
            if "sortAscending" in raw_parameters:
                mapped_params.add("sortAscending")

        # Person Filters - personTitles[] → title (combine with comma)
        if "personTitles[]" in raw_parameters:
            titles = raw_parameters["personTitles[]"]
            if titles:
                # Check if includeSimilarTitles is true
                include_similar = raw_parameters.get("includeSimilarTitles", ["false"])[0].lower() == "true"
                
                if include_similar:
                    # Use exact titles (case will be handled by case-insensitive DB query)
                    contact_filters["title"] = ",".join(titles)
                    logger.debug("Using exact titles (includeSimilarTitles=true): %s", titles)
                else:
                    # Normalize titles by sorting words alphabetically
                    normalized_titles = [self._normalize_title(t) for t in titles]
                    contact_filters["title"] = ",".join(normalized_titles)
                    logger.debug(
                        "Normalized titles (includeSimilarTitles=false): %s → %s",
                        titles,
                        normalized_titles,
                    )
                
                mapped_params.add("personTitles[]")

        # Person Filters - personNotTitles[] → exclude_titles (list)
        if "personNotTitles[]" in raw_parameters:
            exclude_titles = raw_parameters["personNotTitles[]"]
            if exclude_titles:
                # Check if includeSimilarTitles is true
                include_similar = raw_parameters.get("includeSimilarTitles", ["false"])[0].lower() == "true"
                
                if include_similar:
                    # Use exact titles (case will be handled by case-insensitive DB query)
                    contact_filters["exclude_titles"] = exclude_titles
                    logger.debug("Using exact exclude titles (includeSimilarTitles=true): %s", exclude_titles)
                else:
                    # Normalize titles by sorting words alphabetically
                    normalized_not_titles = [self._normalize_title(t) for t in exclude_titles]
                    contact_filters["exclude_titles"] = normalized_not_titles
                    logger.debug(
                        "Normalized exclude titles (includeSimilarTitles=false): %s → %s",
                        exclude_titles,
                        normalized_not_titles,
                    )
                
                mapped_params.add("personNotTitles[]")

        # Mark includeSimilarTitles as mapped if it influenced title processing
        if "includeSimilarTitles" in raw_parameters:
            if "personTitles[]" in mapped_params or "personNotTitles[]" in mapped_params:
                # Mark as mapped if it influenced title processing
                mapped_params.add("includeSimilarTitles")

        # Person Filters - personSeniorities[] → seniority (combine with comma)
        if "personSeniorities[]" in raw_parameters:
            seniorities = raw_parameters["personSeniorities[]"]
            if seniorities:
                contact_filters["seniority"] = ",".join(seniorities)
                mapped_params.add("personSeniorities[]")

        # Person Filters - personDepartmentOrSubdepartments[] → department (combine with comma)
        if "personDepartmentOrSubdepartments[]" in raw_parameters:
            departments = raw_parameters["personDepartmentOrSubdepartments[]"]
            if departments:
                contact_filters["department"] = ",".join(departments)
                mapped_params.add("personDepartmentOrSubdepartments[]")

        # Person Filters - personLocations[] → contact_location (combine with comma)
        if "personLocations[]" in raw_parameters:
            locations = raw_parameters["personLocations[]"]
            if locations:
                contact_filters["contact_location"] = ",".join(locations)
                mapped_params.add("personLocations[]")

        # Person Filters - personNotLocations[] → exclude_contact_locations (list)
        if "personNotLocations[]" in raw_parameters:
            exclude_locations = raw_parameters["personNotLocations[]"]
            if exclude_locations:
                contact_filters["exclude_contact_locations"] = exclude_locations
                mapped_params.add("personNotLocations[]")

        # Organization Filters - organizationNumEmployeesRanges[] → employees_min/max
        if "organizationNumEmployeesRanges[]" in raw_parameters:
            ranges = raw_parameters["organizationNumEmployeesRanges[]"]
            all_mins = []
            all_maxs = []

            for range_str in ranges:
                # Parse ranges like "11,50" or "1,10"
                parts = range_str.split(",")
                if len(parts) == 2:
                    try:
                        min_val = int(parts[0].strip())
                        max_val = int(parts[1].strip())
                        all_mins.append(min_val)
                        all_maxs.append(max_val)
                    except ValueError:
                        logger.warning("Invalid employee range format: %s", range_str)

            if all_mins:
                contact_filters["employees_min"] = min(all_mins)
            if all_maxs:
                contact_filters["employees_max"] = max(all_maxs)
            
            if all_mins or all_maxs:
                mapped_params.add("organizationNumEmployeesRanges[]")

        # Organization Filters - organizationLocations[] → company_location (combine with comma)
        if "organizationLocations[]" in raw_parameters:
            locations = raw_parameters["organizationLocations[]"]
            if locations:
                contact_filters["company_location"] = ",".join(locations)
                mapped_params.add("organizationLocations[]")

        # Organization Filters - organizationNotLocations[] → exclude_company_locations (list)
        if "organizationNotLocations[]" in raw_parameters:
            exclude_locations = raw_parameters["organizationNotLocations[]"]
            if exclude_locations:
                contact_filters["exclude_company_locations"] = exclude_locations
                mapped_params.add("organizationNotLocations[]")

        # Organization Filters - revenueRange[min] → annual_revenue_min
        if "revenueRange[min]" in raw_parameters:
            try:
                contact_filters["annual_revenue_min"] = int(raw_parameters["revenueRange[min]"][0])
                mapped_params.add("revenueRange[min]")
            except (ValueError, IndexError):
                pass

        # Organization Filters - revenueRange[max] → annual_revenue_max
        if "revenueRange[max]" in raw_parameters:
            try:
                contact_filters["annual_revenue_max"] = int(raw_parameters["revenueRange[max]"][0])
                mapped_params.add("revenueRange[max]")
            except (ValueError, IndexError):
                pass

        # Email Filters - contactEmailStatusV2[] → email_status (combine with comma)
        if "contactEmailStatusV2[]" in raw_parameters:
            statuses = raw_parameters["contactEmailStatusV2[]"]
            if statuses:
                contact_filters["email_status"] = ",".join(statuses)
                mapped_params.add("contactEmailStatusV2[]")

        # Keywords - qOrganizationKeywordTags[] → keywords (combine with comma)
        if "qOrganizationKeywordTags[]" in raw_parameters:
            keywords = raw_parameters["qOrganizationKeywordTags[]"]
            if keywords:
                contact_filters["keywords"] = ",".join(keywords)
                mapped_params.add("qOrganizationKeywordTags[]")

        # Keywords - qNotOrganizationKeywordTags[] → exclude_keywords (list)
        if "qNotOrganizationKeywordTags[]" in raw_parameters:
            exclude_keywords = raw_parameters["qNotOrganizationKeywordTags[]"]
            if exclude_keywords:
                contact_filters["exclude_keywords"] = exclude_keywords
                mapped_params.add("qNotOrganizationKeywordTags[]")

        # Keywords - qAndedOrganizationKeywordTags[] → keywords_and (AND logic, combine with comma)
        if "qAndedOrganizationKeywordTags[]" in raw_parameters:
            keywords = raw_parameters["qAndedOrganizationKeywordTags[]"]
            if keywords:
                contact_filters["keywords_and"] = ",".join(keywords)
                mapped_params.add("qAndedOrganizationKeywordTags[]")

        # Keywords - includedOrganizationKeywordFields[] → keyword_search_fields (list of field names)
        if "includedOrganizationKeywordFields[]" in raw_parameters:
            fields = raw_parameters["includedOrganizationKeywordFields[]"]
            if fields:
                # Normalize field names: map Apollo field names to our field names
                normalized_fields = []
                for field in fields:
                    field_lower = field.lower()
                    if field_lower in ["company", "companyname", "name"]:
                        normalized_fields.append("company")
                    elif field_lower in ["industry", "industries"]:
                        normalized_fields.append("industries")
                    elif field_lower in ["keyword", "keywords"]:
                        normalized_fields.append("keywords")
                if normalized_fields:
                    contact_filters["keyword_search_fields"] = normalized_fields
                    mapped_params.add("includedOrganizationKeywordFields[]")

        # Keywords - excludedOrganizationKeywordFields[] → keyword_exclude_fields (list of field names)
        if "excludedOrganizationKeywordFields[]" in raw_parameters:
            fields = raw_parameters["excludedOrganizationKeywordFields[]"]
            if fields:
                # Normalize field names: map Apollo field names to our field names
                normalized_fields = []
                for field in fields:
                    field_lower = field.lower()
                    if field_lower in ["company", "companyname", "name"]:
                        normalized_fields.append("company")
                    elif field_lower in ["industry", "industries"]:
                        normalized_fields.append("industries")
                    elif field_lower in ["keyword", "keywords"]:
                        normalized_fields.append("keywords")
                if normalized_fields:
                    contact_filters["keyword_exclude_fields"] = normalized_fields
                    mapped_params.add("excludedOrganizationKeywordFields[]")

        # Keywords - includedAndedOrganizationKeywordFields[] → keywords_and + keyword_search_fields (combine both)
        if "includedAndedOrganizationKeywordFields[]" in raw_parameters:
            fields = raw_parameters["includedAndedOrganizationKeywordFields[]"]
            if fields:
                # Normalize field names: map Apollo field names to our field names
                normalized_fields = []
                for field in fields:
                    field_lower = field.lower()
                    if field_lower in ["company", "companyname", "name"]:
                        normalized_fields.append("company")
                    elif field_lower in ["industry", "industries"]:
                        normalized_fields.append("industries")
                    elif field_lower in ["keyword", "keywords"]:
                        normalized_fields.append("keywords")
                if normalized_fields:
                    # For AND logic with field control, we need to use keywords_and
                    # But we also need the keywords themselves - this parameter only provides fields
                    # So we'll set keyword_search_fields, and the actual keywords should come from qAndedOrganizationKeywordTags[]
                    contact_filters["keyword_search_fields"] = normalized_fields
                    mapped_params.add("includedAndedOrganizationKeywordFields[]")
                    # If qAndedOrganizationKeywordTags[] was also provided, keywords_and should already be set
                    # If not, we still mark this as mapped but keywords_and might be empty

        # Technology - currentlyUsingAnyOfTechnologyUids[] → technologies_uids (comma-join UIDs)
        if "currentlyUsingAnyOfTechnologyUids[]" in raw_parameters:
            uids = raw_parameters["currentlyUsingAnyOfTechnologyUids[]"]
            if uids:
                # Pass UIDs as comma-separated string for substring matching
                contact_filters["technologies_uids"] = ",".join(uids)
                mapped_params.add("currentlyUsingAnyOfTechnologyUids[]")

        # Industry - organizationIndustryTagIds[] → industries (convert tag IDs to industry names)
        if "organizationIndustryTagIds[]" in raw_parameters:
            tag_ids = raw_parameters["organizationIndustryTagIds[]"]
            if tag_ids:
                logger.debug(
                    "Mapping organizationIndustryTagIds[] to industries: tag_ids=%s",
                    tag_ids,
                )
                industry_names = get_industry_names_from_ids(tag_ids)
                if industry_names:
                    contact_filters["industries"] = ",".join(industry_names)
                    # logger.info(
                    #     "Mapped organizationIndustryTagIds[] to industries filter: %s",
                    #     contact_filters["industries"],
                    # )
                    mapped_params.add("organizationIndustryTagIds[]")
                else:
                    logger.warning(
                        "No valid industry names found for organizationIndustryTagIds[]: %s",
                        tag_ids,
                    )

        # Industry - organizationNotIndustryTagIds[] → exclude_industries (convert tag IDs to industry names)
        if "organizationNotIndustryTagIds[]" in raw_parameters:
            tag_ids = raw_parameters["organizationNotIndustryTagIds[]"]
            if tag_ids:
                logger.debug(
                    "Mapping organizationNotIndustryTagIds[] to exclude_industries: tag_ids=%s",
                    tag_ids,
                )
                industry_names = get_industry_names_from_ids(tag_ids)
                if industry_names:
                    contact_filters["exclude_industries"] = industry_names
                    # logger.info(
                    #     "Mapped organizationNotIndustryTagIds[] to exclude_industries filter: %s",
                    #     industry_names,
                    # )
                    mapped_params.add("organizationNotIndustryTagIds[]")
                else:
                    logger.warning(
                        "No valid industry names found for organizationNotIndustryTagIds[]: %s",
                        tag_ids,
                    )

        # Search - qKeywords → search
        if "qKeywords" in raw_parameters:
            search_term = raw_parameters["qKeywords"][0]
            if search_term:
                contact_filters["search"] = search_term
                mapped_params.add("qKeywords")

        # Build unmapped parameters dictionary with reasons
        for param_name, param_values in raw_parameters.items():
            if param_name not in mapped_params:
                # Categorize the reason for not mapping
                if param_name in ["qOrganizationSearchListId", "qNotOrganizationSearchListId", 
                                    "qPersonPersonaIds[]"]:
                    reason = "Apollo-specific feature (search lists, personas)"
                elif param_name in ["marketSegments[]", "intentStrengths[]", "lookalikeOrganizationIds[]"]:
                    reason = "Apollo-specific feature (market segments, intent, lookalike)"
                elif param_name in ["prospectedByCurrentTeam[]"]:
                    reason = "Apollo-specific feature (prospecting status)"
                elif param_name in ["organizationJobLocations[]", "organizationNumJobsRange[min]", 
                                    "organizationJobPostedAtRange[min]", "organizationTradingStatus[]"]:
                    reason = "Unmapped filter (job postings, trading status)"
                elif param_name in ["contactEmailExcludeCatchAll"]:
                    reason = "Unmapped filter (email catch-all exclusion)"
                elif param_name in ["uniqueUrlId", "tour", "includeSimilarTitles", "existFields[]",
                                    "notOrganizationIds[]", "organizationIds[]"]:
                    reason = "UI flag or advanced filter (not applicable)"
                else:
                    reason = "Unknown parameter (no mapping defined)"
                
                unmapped_params[param_name] = (param_values, reason)

        # logger.info(
        #     "Mapped Apollo parameters: input_params=%d mapped_params=%d unmapped_params=%d",
        #     len(raw_parameters),
        #     len(contact_filters),
        #     len(unmapped_params),
        # )

        if include_unmapped:
            return contact_filters, unmapped_params
        return contact_filters

