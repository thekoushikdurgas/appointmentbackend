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
        logger.info("Analyzing Apollo URL: url_length=%d", len(url))

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

            logger.info(
                "URL analysis complete: total_params=%d categories=%d",
                statistics.total_parameters,
                statistics.categories_used,
            )

            return response

        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error analyzing Apollo URL: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while analyzing the URL",
            ) from exc

