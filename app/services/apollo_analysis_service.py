"""Service layer for Apollo.io URL analysis."""

from collections import defaultdict
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse
import hashlib

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.apollo import (
    AnalysisStatistics,
    ApolloUrlAnalysisResponse,
    ParameterCategory,
    ParameterDetail,
    UrlStructure,
)
from app.utils.apollo_patterns import ApolloPatternDetector
from app.utils.industry_mapping import get_industry_names_from_ids
from app.utils.query_cache import get_query_cache

logger = get_logger(__name__)
settings = get_settings()


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
        self.cache = get_query_cache()
        # Cache TTL for URL analysis: 1 hour (3600 seconds)
        self.analysis_cache_ttl = 3600
        # Cache for normalized titles (in-memory LRU cache)
        self._title_normalization_cache: dict[str, str] = {}
        # Common titles that don't need normalization (exact matches)
        self._common_titles = {
            "ceo", "cfo", "cto", "cmo", "founder", "owner", "president", "vp", "director",
            "manager", "senior", "head", "lead", "chief", "executive", "partner"
        }

    def _normalize_url_for_cache(self, url: str) -> str:
        """
        Normalize URL for cache key generation.
        
        Normalizes URLs to handle encoding differences and ensure consistent cache keys.
        
        Args:
            url: Raw Apollo URL
            
        Returns:
            Normalized URL string
        """
        try:
            # Parse and reconstruct URL to normalize encoding
            parsed = urlparse(url)
            # Normalize by decoding and re-encoding
            normalized = url
            # Sort query parameters if present for consistent cache keys
            if "#" in url:
                hash_part = url.split("#", 1)[1]
                if "?" in hash_part:
                    path_part, query_part = hash_part.split("?", 1)
                    # Parse and sort parameters
                    params = parse_qs(query_part, keep_blank_values=True)
                    # Reconstruct with sorted keys
                    sorted_params = sorted(params.items())
                    if sorted_params:
                        query_string = "&".join(
                            f"{k}={','.join(sorted(v))}" if len(v) > 1 else f"{k}={v[0]}"
                            for k, v in sorted_params
                        )
                        normalized = f"{parsed.scheme}://{parsed.netloc}#{path_part}?{query_string}"
            return normalized
        except Exception:
            # If normalization fails, use original URL
            return url

    def _generate_cache_key(self, url: str) -> str:
        """
        Generate cache key for Apollo URL analysis.
        
        Args:
            url: Apollo URL
            
        Returns:
            Cache key string
        """
        normalized = self._normalize_url_for_cache(url)
        # Create hash for consistent key length
        url_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"apollo:url_analysis:{url_hash}"

    async def analyze_url(self, url: str) -> ApolloUrlAnalysisResponse:
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

        # Try to get from cache
        if self.cache.enabled:
            try:
                cached_result = await self.cache.get("apollo_url_analysis", url=url)
                if cached_result:
                    logger.debug("Cache hit for Apollo URL analysis: url_length=%d", len(url))
                    # Reconstruct response from cached data
                    return ApolloUrlAnalysisResponse(**cached_result)
            except Exception as exc:
                logger.warning("Error reading from cache, proceeding with analysis: %s", exc)

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

            # Cache the result
            if self.cache.enabled:
                try:
                    # Convert response to dict for caching
                    cache_data = response.model_dump(mode='json')
                    await self.cache.set(
                        "apollo_url_analysis",
                        cache_data,
                        ttl=self.analysis_cache_ttl,
                        url=url
                    )
                    logger.debug("Cached Apollo URL analysis result: url_length=%d", len(url))
                except Exception as exc:
                    logger.warning("Error caching URL analysis result: %s", exc)

            return response

        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error analyzing Apollo URL: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while analyzing the URL",
            ) from exc

    def _normalize_title(self, title: str) -> str:
        """
        Normalize a job title by sorting words alphabetically.
        
        This allows matching titles regardless of word order:
        - "Project Manager" → "manager project"
        - "Manager Project" → "manager project"
        
        Uses in-memory cache for performance.
        
        Args:
            title: Original job title
            
        Returns:
            Normalized title with words sorted alphabetically (lowercase)
        """
        # Check cache first
        title_lower = title.lower().strip()
        if title_lower in self._title_normalization_cache:
            return self._title_normalization_cache[title_lower]
        
        # Quick check for common single-word titles
        if title_lower in self._common_titles:
            normalized = title_lower
        else:
            # Convert to lowercase and split into words
            words = title_lower.split()
            # Sort words alphabetically
            words.sort()
            # Join back together
            normalized = " ".join(words)
        
        # Cache the result (limit cache size to prevent memory issues)
        if len(self._title_normalization_cache) < 10000:
            self._title_normalization_cache[title_lower] = normalized
        
        return normalized

    def _jumble_title(self, title: str) -> list[str]:
        """
        Split a job title into individual words for jumble mapping.
        
        When includeSimilarTitles=true, personTitles[] uses jumble mapping:
        - "Project Manager" → ["project", "manager"]
        - This allows searching for each word separately
        
        Args:
            title: Original job title
            
        Returns:
            List of individual words (lowercase, stripped)
        """
        # Convert to lowercase, strip, and split into words
        words = title.lower().strip().split()
        # Filter out empty strings and return
        return [word for word in words if word]

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
        # Log mapping operation (single log per call to avoid duplicates)
        logger.info("Mapping Apollo parameters to contact filters: params=%d", len(raw_parameters))

        # Detect common patterns for optimization hints
        detected_patterns = ApolloPatternDetector.detect_patterns(raw_parameters)
        if detected_patterns:
            logger.debug("Detected Apollo patterns: %s", ", ".join(sorted(detected_patterns)))

        contact_filters = {}
        mapped_params = set()
        unmapped_params = {}

        # Batch process: Pagination and Sorting (simple mappings)
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
                    "person_name.raw": "first_name",  # Person name sorting
                    "title": "title",
                    "company": "company",
                    "sanitized_organization_name_unanalyzed": "company",  # Organization name sorting
                    "employees": "employees",
                    "revenue": "annual_revenue",
                    "funding": "total_funding",
                    "location": "city",
                    "organization_linkedin_industry_tag_ids": "industry",  # Industry tag sorting
                    "recommendations_score": "created_at",  # Default fallback
                }

                mapped_field = field_map.get(sort_field)
                if mapped_field is None:
                    # Unknown Apollo sort field - log warning and use default
                    logger.warning(
                        "Unknown Apollo sortByField: %s, falling back to created_at",
                        sort_field
                    )
                    mapped_field = "created_at"
                
                # Prepend '-' for descending (when sortAscending is false)
                if sort_ascending == "false":
                    contact_filters["ordering"] = f"-{mapped_field}"
                else:
                    contact_filters["ordering"] = mapped_field
            
            # Always mark sortByField as mapped, even if it's [none]
            mapped_params.add("sortByField")
            if "sortAscending" in raw_parameters:
                mapped_params.add("sortAscending")

        # Batch process: Person Filters (titles, locations, seniorities, departments)
        include_similar = raw_parameters.get("includeSimilarTitles", ["false"])[0].lower() == "true"
        
        # Process personTitles[]: dependent on includeSimilarTitles
        # - includeSimilarTitles=false: use exact mapping (normalize)
        # - includeSimilarTitles=true: use jumble mapping (split into words)
        if "personTitles[]" in raw_parameters:
            titles = raw_parameters["personTitles[]"]
            if titles:
                if include_similar:
                    # Jumble mapping: split each title into individual words
                    jumbled_words = []
                    for title in titles:
                        words = self._jumble_title(title)
                        jumbled_words.extend(words)
                    # Remove duplicates while preserving order
                    unique_words = []
                    seen = set()
                    for word in jumbled_words:
                        if word not in seen:
                            unique_words.append(word)
                            seen.add(word)
                    contact_filters["title"] = ",".join(unique_words)
                    logger.debug("Using jumble mapping (includeSimilarTitles=true): %s → %s", titles, unique_words)
                else:
                    # Exact mapping: normalize titles (sort words alphabetically)
                    normalized_titles = [self._normalize_title(t) for t in titles]
                    contact_filters["title"] = ",".join(normalized_titles)
                    logger.debug("Using exact mapping (includeSimilarTitles=false): %s → %s", titles[:3], normalized_titles[:3])
                mapped_params.add("personTitles[]")

        # Process personNotTitles[]: NOT dependent on includeSimilarTitles
        # Always use exact mapping (normalize), regardless of includeSimilarTitles flag
        if "personNotTitles[]" in raw_parameters:
            exclude_titles = raw_parameters["personNotTitles[]"]
            if exclude_titles:
                # Always normalize exclude titles (exact mapping)
                normalized_not_titles = [self._normalize_title(t) for t in exclude_titles]
                contact_filters["exclude_titles"] = normalized_not_titles
                logger.debug("Using exact mapping for exclude titles (always normalized): %s → %s", exclude_titles[:3], normalized_not_titles[:3])
                mapped_params.add("personNotTitles[]")

        if "includeSimilarTitles" in raw_parameters:
            if "personTitles[]" in mapped_params or "personNotTitles[]" in mapped_params:
                mapped_params.add("includeSimilarTitles")

        # Batch process other person filters (simple comma joins)
        person_filters = {
            "personSeniorities[]": "seniority",
            "personDepartmentOrSubdepartments[]": "department",
            "personLocations[]": "contact_location",
        }
        for apollo_param, filter_key in person_filters.items():
            if apollo_param in raw_parameters:
                values = raw_parameters[apollo_param]
                if values:
                    contact_filters[filter_key] = ",".join(values)
                    mapped_params.add(apollo_param)

        if "personNotLocations[]" in raw_parameters:
            exclude_locations = raw_parameters["personNotLocations[]"]
            if exclude_locations:
                contact_filters["exclude_contact_locations"] = exclude_locations
                mapped_params.add("personNotLocations[]")

        # Batch process: Organization Filters (employees, locations, revenue)
        # Process employee ranges
        if "organizationNumEmployeesRanges[]" in raw_parameters:
            ranges = raw_parameters["organizationNumEmployeesRanges[]"]
            all_mins = []
            all_maxs = []
            # Batch parse all ranges
            for range_str in ranges:
                parts = range_str.split(",")
                if len(parts) == 2:
                    try:
                        all_mins.append(int(parts[0].strip()))
                        all_maxs.append(int(parts[1].strip()))
                    except ValueError:
                        logger.warning("Invalid employee range format: %s", range_str)
            if all_mins:
                contact_filters["employees_min"] = min(all_mins)
            if all_maxs:
                contact_filters["employees_max"] = max(all_maxs)
            if all_mins or all_maxs:
                mapped_params.add("organizationNumEmployeesRanges[]")

        # Batch process organization locations
        if "organizationLocations[]" in raw_parameters:
            locations = raw_parameters["organizationLocations[]"]
            if locations:
                contact_filters["company_location"] = ",".join(locations)
                mapped_params.add("organizationLocations[]")

        if "organizationNotLocations[]" in raw_parameters:
            exclude_locations = raw_parameters["organizationNotLocations[]"]
            if exclude_locations:
                contact_filters["exclude_company_locations"] = exclude_locations
                mapped_params.add("organizationNotLocations[]")

        # Batch process revenue ranges
        revenue_filters = {
            "revenueRange[min]": "annual_revenue_min",
            "revenueRange[max]": "annual_revenue_max",
        }
        for apollo_param, filter_key in revenue_filters.items():
            if apollo_param in raw_parameters:
                try:
                    contact_filters[filter_key] = int(raw_parameters[apollo_param][0])
                    mapped_params.add(apollo_param)
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

        # Batch process: Industry filters (convert tag IDs to industry names)
        # Process both include and exclude industry filters together
        industry_tag_params = [
            ("organizationIndustryTagIds[]", "industries", True),  # (param, filter_key, is_comma_separated)
            ("organizationNotIndustryTagIds[]", "exclude_industries", False),
        ]
        for apollo_param, filter_key, is_comma_separated in industry_tag_params:
            if apollo_param in raw_parameters:
                tag_ids = raw_parameters[apollo_param]
                if tag_ids:
                    # Industry tag lookup is already cached at module level in industry_mapping
                    industry_names = get_industry_names_from_ids(tag_ids)
                    if industry_names:
                        if is_comma_separated:
                            contact_filters[filter_key] = ",".join(industry_names)
                        else:
                            contact_filters[filter_key] = industry_names
                        mapped_params.add(apollo_param)
                    else:
                        logger.warning("No valid industry names found for %s: %s", apollo_param, tag_ids[:3])

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

        logger.info(
            "Mapped Apollo parameters: input_params=%d mapped_params=%d unmapped_params=%d",
            len(raw_parameters),
            len(contact_filters),
            len(unmapped_params),
        )

        if include_unmapped:
            return contact_filters, unmapped_params
        return contact_filters

