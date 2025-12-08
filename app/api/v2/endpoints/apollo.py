"""Apollo.io URL Analysis API endpoints."""

import asyncio
import hashlib
import json
import time
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, resolve_pagination_params
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.apollo import (
    ApolloContactsSearchResponse,
    ApolloUrlAnalysisRequest,
    ApolloUrlAnalysisResponse,
    ApolloUrlAnalysisWithCountResponse,
    MappingSummary,
    ParameterCategory,
    ParameterCategoryWithCount,
    ParameterDetail,
    ParameterDetailWithCount,
    ParameterValueWithCount,
    UnmappedCategory,
    UnmappedParameter,
)
from app.schemas.common import CountResponse, CursorPage, UuidListResponse
from app.schemas.contacts import ContactListItem, ContactSimpleItem
from app.schemas.filters import ApolloFilterParams, ContactFilterParams
from app.services.apollo_analysis_service import ApolloAnalysisService
from app.services.contacts_service import ContactsService
from app.utils.cursor import decode_offset_cursor
from app.utils.industry_mapping import get_industry_names_from_ids
from app.utils.normalization import normalize_list_param
from app.utils.query_cache import get_query_cache

router = APIRouter(prefix="/apollo", tags=["Apollo"])
settings = get_settings()
service = ApolloAnalysisService()
contacts_service = ContactsService()
query_cache = get_query_cache()
# Cache TTL for Apollo query results: 5 minutes (300 seconds)
APOLLO_QUERY_CACHE_TTL = 300


def _convert_industry_tagids_to_names(param_name: str, tag_ids: list[str]) -> list[str]:
    """
    Convert industry Tag IDs to industry names for display in API responses.
    
    Args:
        param_name: The parameter name (e.g., 'organizationIndustryTagIds[]')
        tag_ids: List of Tag IDs or other values
        
    Returns:
        List of industry names if param is industry-related, otherwise original values
    """
    # Only convert for industry-related parameters
    if param_name in ("organizationIndustryTagIds[]", "organizationNotIndustryTagIds[]"):
        industry_names = get_industry_names_from_ids(tag_ids)
        if industry_names:
            return industry_names
    return tag_ids


async def _batch_execute_tasks(
    tasks: list,
    max_concurrent: int = 20,
) -> list:
    """
    Execute async tasks in parallel batches to avoid overwhelming the database.
    
    Args:
        tasks: List of async tasks (coroutines) to execute
        max_concurrent: Maximum number of concurrent tasks per batch
        
    Returns:
        List of results in the same order as tasks
    """
    if not tasks:
        return []
    
    results = []
    for i in range(0, len(tasks), max_concurrent):
        batch = tasks[i:i + max_concurrent]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        # Convert exceptions to 0 (for count queries, exceptions should return 0)
        processed_results = [
            0 if isinstance(r, Exception) else r for r in batch_results
        ]
        results.extend(processed_results)
    
    return results


def _get_filter_signature(filters: ApolloFilterParams) -> str:
    """
    Generate a deterministic signature for filter parameters for deduplication.
    
    Args:
        filters: ApolloFilterParams instance
        
    Returns:
        MD5 hash string representing the filter combination
    """
    # Convert filters to dict, excluding None and unset values
    filter_dict = filters.model_dump(exclude_none=True, exclude_unset=True)
    
    # Sort keys and values for deterministic hashing
    # Handle nested structures (lists, dicts) by converting to sorted tuples
    def normalize_value(v):
        if isinstance(v, list):
            return tuple(sorted(str(item) for item in v))
        if isinstance(v, dict):
            return tuple(sorted((str(k), normalize_value(v)) for k, v in v.items()))
        return str(v)
    
    normalized_dict = {
        str(k): normalize_value(v) for k, v in sorted(filter_dict.items())
    }
    
    # Create deterministic JSON string
    key_string = json.dumps(normalized_dict, sort_keys=True, default=str)
    
    # Hash with MD5
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return key_hash


def _generate_count_cache_key(filters: ApolloFilterParams) -> str:
    """
    Generate a cache key for contact count queries.
    
    Uses the same logic as _get_filter_signature for consistency.
    
    Args:
        filters: ApolloFilterParams instance
        
    Returns:
        Cache key string for use with query_cache
    """
    return _get_filter_signature(filters)


def _handle_employee_range(
    filter_dict: dict, param_value: str
) -> tuple[dict, bool]:
    """Handle organizationNumEmployeesRanges[] parameter.
    
    Args:
        filter_dict: Filter dictionary to modify
        param_value: Range value in format "min,max"
        
    Returns:
        Tuple of (filter_dict, success) where success indicates if parsing succeeded
    """
    parts = param_value.split(",")
    if len(parts) != 2:
        return filter_dict, False
    
    try:
        min_val = int(parts[0].strip())
        max_val = int(parts[1].strip())
        filter_dict.pop("employees_min", None)
        filter_dict.pop("employees_max", None)
        filter_dict["employees_min"] = min_val
        filter_dict["employees_max"] = max_val
        return filter_dict, True
    except ValueError:
        return filter_dict, False


def _handle_revenue_range(
    filter_dict: dict, param_name: str, param_value: str
) -> tuple[dict, bool]:
    """Handle revenueRange[min] or revenueRange[max] parameter.
    
    Args:
        filter_dict: Filter dictionary to modify
        param_name: Parameter name ("revenueRange[min]" or "revenueRange[max]")
        param_value: Revenue value as string
        
    Returns:
        Tuple of (filter_dict, success) where success indicates if parsing succeeded
    """
    try:
        value_int = int(param_value)
        filter_dict.pop("annual_revenue_min", None)
        filter_dict.pop("annual_revenue_max", None)
        if param_name == "revenueRange[min]":
            filter_dict["annual_revenue_min"] = value_int
        else:
            filter_dict["annual_revenue_max"] = value_int
        return filter_dict, True
    except ValueError:
        return filter_dict, False


def _handle_simple_parameter(
    filter_dict: dict, param_name: str, param_value: str
) -> Optional[str]:
    """Handle simple parameter mappings that can be directly modified.
    
    Args:
        filter_dict: Filter dictionary to modify
        param_name: Apollo parameter name
        param_value: Parameter value
        
    Returns:
        Filter key if mapping exists, None otherwise
    """
    simple_param_mappings = {
        "personSeniorities[]": "seniority",
        "personDepartmentOrSubdepartments[]": "department",
        "personLocations[]": "contact_location",
        "organizationLocations[]": "company_location",
        "contactEmailStatusV2[]": "email_status",
        "qOrganizationKeywordTags[]": "keywords",
        "qKeywords": "search",
    }
    
    filter_key = simple_param_mappings.get(param_name)
    if filter_key:
        filter_dict[filter_key] = param_value
    return filter_key


def _handle_complex_parameter(
    all_apollo_params: dict[str, list[str]],
    param_name: str,
    param_value: str,
    apollo_service: ApolloAnalysisService,
) -> tuple[dict, dict]:
    """Handle complex parameters that require remapping.
    
    Args:
        all_apollo_params: All Apollo parameters
        param_name: Parameter name to modify
        param_value: Single parameter value
        apollo_service: Apollo service for remapping
        
    Returns:
        Tuple of (filter_dict, unmapped_dict)
    """
    # Build raw params with only this value
    raw_params = {}
    for key, values in all_apollo_params.items():
        if key not in ("page", "sortByField", "sortAscending"):
            if key == param_name:
                raw_params[key] = [param_value]
            else:
                raw_params[key] = values
    
    # Remap with single value (for complex parameters)
    return apollo_service.map_to_contact_filters(raw_params, include_unmapped=True)


def _separate_count_results(all_results: list, task_metadata: list) -> tuple[list[int], list[int]]:
    """Separate results into parameter and value counts using metadata.
    
    Returns:
        Tuple of (param_counts, value_counts)
    """
    param_counts = []
    value_counts = []
    for i, metadata in enumerate(task_metadata):
        if metadata["type"] == "param":
            param_counts.append(all_results[i])
        else:
            value_counts.append(all_results[i])
    return param_counts, value_counts


def _build_count_tasks(
    categories,
    all_apollo_params: dict[str, list[str]],
    service: ApolloAnalysisService,
    session: AsyncSession,
    base_filter_dict: dict,
    base_unmapped_dict: dict,
) -> dict:
    """
    Build count tasks for all parameters and values.
    
    Returns:
        Dictionary with tasks, metadata, param_info_list, and original_query_count
    """
    all_count_tasks = []
    task_metadata = []
    param_info_list = []
    original_query_count = 0
    skipped_param_queries = 0
    skipped_exclusion_value_queries = 0
    
    exclusion_params = {
        "personNotLocations[]",
        "organizationNotLocations[]",
        "organizationNotIndustryTagIds[]",
        "personNotTitles[]",
        "qNotOrganizationKeywordTags[]",
    }
    
    param_task_index = 0
    value_task_index = 0
    
    for category in categories:
        for param in category.parameters:
            if param.name in ("page", "sortByField", "sortAscending"):
                continue
            
            converted_values = _convert_industry_tagids_to_names(param.name, param.values)
            is_single_value = len(param.values) == 1
            is_exclusion_param = param.name in exclusion_params
            skip_param_query = is_single_value
            param_task_index_for_info = None
            
            if not skip_param_query:
                param_task = _count_contacts_for_parameter(
                    session, param.name, param.values, all_apollo_params, service,
                    base_filter_dict=base_filter_dict,
                    base_unmapped_dict=base_unmapped_dict,
                )
                all_count_tasks.append(param_task)
                task_metadata.append({
                    "type": "param",
                    "param_index": param_task_index,
                    "value_index": None,
                })
                param_task_index_for_info = param_task_index
                param_task_index += 1
                original_query_count += 1
            else:
                skipped_param_queries += 1
                original_query_count += 1
            
            skip_value_queries = is_exclusion_param and not skip_param_query
            if skip_value_queries:
                skipped_exclusion_value_queries += len(param.values)
                original_query_count += len(param.values)
            
            value_tasks_for_param = []
            value_metadata = []
            for original_value in param.values:
                converted_single = _convert_industry_tagids_to_names(param.name, [original_value])
                display_value = converted_single[0] if converted_single else original_value
                
                if skip_value_queries:
                    value_metadata.append(display_value)
                    continue
                
                value_task = _count_contacts_for_value(
                    session, param.name, original_value, all_apollo_params, service,
                    base_filter_dict=base_filter_dict,
                    base_unmapped_dict=base_unmapped_dict,
                )
                all_count_tasks.append(value_task)
                task_metadata.append({
                    "type": "value",
                    "param_index": param_task_index_for_info if param_task_index_for_info is not None else (param_task_index - 1),
                    "value_index": value_task_index,
                })
                value_tasks_for_param.append(value_task)
                value_metadata.append(display_value)
                value_task_index += 1
                original_query_count += 1
            
            param_info_list.append({
                "category": category,
                "param": param,
                "converted_values": converted_values,
                "value_metadata": value_metadata,
                "value_task_count": len(value_tasks_for_param),
                "param_task_index": param_task_index_for_info,
                "value_task_start_index": value_task_index - len(value_tasks_for_param) if value_tasks_for_param else None,
                "skip_param_query": skip_param_query,
                "skip_value_queries": skip_value_queries,
                "is_exclusion_param": is_exclusion_param,
            })
    
    return {
        "tasks": all_count_tasks,
        "metadata": task_metadata,
        "param_info_list": param_info_list,
        "original_query_count": original_query_count,
    }


def _build_filter_from_base(
    base_filter_dict: dict,
    base_unmapped_dict: dict,
    param_name: str,
    param_value: Optional[str] = None,
    param_values: Optional[list[str]] = None,
    all_apollo_params: Optional[dict[str, list[str]]] = None,
    apollo_service: Optional[ApolloAnalysisService] = None,
) -> tuple[dict, dict]:
    """
    Build filter dictionary from base filters by modifying for specific parameter/value.
    
    This function reuses pre-computed base filters and only modifies the specific
    parameter being counted, avoiding redundant filter mapping operations.
    
    Args:
        base_filter_dict: Pre-computed base filter dictionary (all parameters)
        base_unmapped_dict: Pre-computed unmapped parameters dictionary
        param_name: Apollo parameter name to modify
        param_value: Single parameter value (for value counts)
        param_values: List of parameter values (for parameter counts, uses all values)
        all_apollo_params: All Apollo parameters (for special cases)
        apollo_service: Apollo service (for special cases that need remapping)
        
    Returns:
        Tuple of (filter_dict, unmapped_dict) ready for ContactFilterParams validation
    """
    # Early return if parameter is unmapped
    if param_name in base_unmapped_dict:
        return {}, base_unmapped_dict
    
    # Start with a copy of base filters
    filter_dict = dict(base_filter_dict)
    
    # Exclusion parameters use base filters as-is
    exclusion_params = {
        "personNotLocations[]",
        "organizationNotLocations[]",
        "organizationNotIndustryTagIds[]",
        "personNotTitles[]",
        "qNotOrganizationKeywordTags[]",
    }
    if param_name in exclusion_params:
        return filter_dict, base_unmapped_dict
    
    # Handle employee range parameter
    if param_name == "organizationNumEmployeesRanges[]" and param_value:
        filter_dict, success = _handle_employee_range(filter_dict, param_value)
        return (filter_dict, base_unmapped_dict) if success else ({}, base_unmapped_dict)
    
    # Handle revenue range parameters
    if param_name in ("revenueRange[min]", "revenueRange[max]") and param_value:
        filter_dict, success = _handle_revenue_range(filter_dict, param_name, param_value)
        return (filter_dict, base_unmapped_dict) if success else ({}, base_unmapped_dict)
    
    # Handle inclusion parameters with value counts
    if param_value is not None:
        # Try simple parameter mapping first
        filter_key = _handle_simple_parameter(filter_dict, param_name, param_value)
        if filter_key:
            return filter_dict, base_unmapped_dict
        
        # Handle complex parameters that need remapping
        if all_apollo_params and apollo_service:
            return _handle_complex_parameter(
                all_apollo_params, param_name, param_value, apollo_service
            )
    
    # For parameter counts (all values), use base filters as-is
    return filter_dict, base_unmapped_dict


def _assemble_count_results(
    categories,
    param_info_list: list,
    param_counts: list[int],
    value_counts: list[int],
) -> list:
    """
    Assemble count results into categorized response structure.
    
    Returns:
        List of ParameterCategoryWithCount objects
    """
    converted_categories = []
    value_count_index = 0
    param_count_index = 0
    
    # Group param_info_list by category
    category_params = {}
    for param_info in param_info_list:
        category_name = param_info["category"].name
        if category_name not in category_params:
            category_params[category_name] = {
                "category": param_info["category"],
                "params": [],
            }
        category_params[category_name]["params"].append(param_info)
    
    # Build categories with counts
    for category in categories:
        converted_params = []
        
        # Handle pagination/sorting parameters first
        for param in category.parameters:
            if param.name in ("page", "sortByField", "sortAscending"):
                converted_values = _convert_industry_tagids_to_names(param.name, param.values)
                value_counts_list = [
                    ParameterValueWithCount(value=val, count=0)
                    for val in converted_values
                ]
                converted_params.append(
                    ParameterDetailWithCount(
                        name=param.name,
                        values=value_counts_list,
                        description=param.description,
                        category=param.category,
                        count=0,
                    )
                )
        
        # Process parameters with counts
        if category.name in category_params:
            for param_info in category_params[category.name]["params"]:
                param = param_info["param"]
                skip_param_query = param_info.get("skip_param_query", False)
                skip_value_queries = param_info.get("skip_value_queries", False)
                
                # Get parameter count
                if skip_param_query:
                    if param_info.get("value_task_start_index") is not None:
                        param_count = value_counts[param_info["value_task_start_index"]]
                    else:
                        param_count = value_counts[value_count_index] if value_count_index < len(value_counts) else 0
                else:
                    if param_info.get("param_task_index") is not None and param_info["param_task_index"] < len(param_counts):
                        param_count = param_counts[param_info["param_task_index"]]
                    else:
                        param_count = param_counts[param_count_index] if param_count_index < len(param_counts) else 0
                        param_count_index += 1
                
                # Get value counts for this parameter
                value_counts_for_param, updated_index = _get_value_counts_for_param(
                    param_info, param_count, skip_value_queries, skip_param_query, value_counts, value_count_index
                )
                value_count_index = updated_index
                
                if skip_param_query and param_info.get("value_task_start_index") is not None:
                    value_count_index = param_info["value_task_start_index"] + 1
                
                converted_params.append(
                    ParameterDetailWithCount(
                        name=param.name,
                        values=value_counts_for_param,
                        description=param.description,
                        category=param.category,
                        count=param_count,
                    )
                )
        
        category_max_count = max(
            [p.count for p in converted_params] + [0]
        ) if converted_params else 0
        
        converted_categories.append(
            ParameterCategoryWithCount(
                name=category.name,
                parameters=converted_params,
                total_parameters=category.total_parameters,
                count=category_max_count,
            )
        )
    
    return converted_categories


def _get_value_counts_for_param(
    param_info: dict,
    param_count: int,
    skip_value_queries: bool,
    skip_param_query: bool,
    value_counts: list[int],
    value_count_index: int,
) -> tuple[list, int]:
    """Get value counts for a parameter, handling various optimization cases.
    
    Returns:
        Tuple of (value_counts_list, updated_value_count_index)
    """
    value_counts_for_param = []
    current_index = value_count_index
    
    if skip_value_queries or skip_param_query:
        # For exclusion params or single-value params, reuse parameter count
        for display_value in param_info["value_metadata"]:
            value_counts_for_param.append(
                ParameterValueWithCount(value=display_value, count=param_count)
            )
    else:
        # Normal case: get value counts from value_counts
        start_idx = param_info.get("value_task_start_index")
        if start_idx is not None:
            for i, display_value in enumerate(param_info["value_metadata"]):
                if start_idx + i < len(value_counts):
                    value_count = value_counts[start_idx + i]
                else:
                    value_count = value_counts[current_index] if current_index < len(value_counts) else 0
                    current_index += 1
                value_counts_for_param.append(
                    ParameterValueWithCount(value=display_value, count=value_count)
                )
        else:
            # Fallback: use sequential indexing
            for display_value in param_info["value_metadata"]:
                value_count = value_counts[current_index] if current_index < len(value_counts) else 0
                current_index += 1
                value_counts_for_param.append(
                    ParameterValueWithCount(value=display_value, count=value_count)
                )
    
    return value_counts_for_param, current_index


async def _count_contacts_for_parameter(
    session: AsyncSession,
    param_name: str,
    param_values: list[str],
    all_apollo_params: dict[str, list[str]],
    apollo_service: ApolloAnalysisService,
    base_filter_dict: Optional[dict] = None,
    base_unmapped_dict: Optional[dict] = None,
) -> int:
    """
    Count contacts matching a specific Apollo parameter with all its values,
    within the context of all other filters from the Apollo URL.
    
    Args:
        session: Database session
        param_name: Apollo parameter name (e.g., "personTitles[]")
        param_values: List of parameter values
        all_apollo_params: All parameters from the Apollo URL (for contextual filtering)
        apollo_service: Apollo analysis service for mapping
        base_filter_dict: Optional pre-computed base filter dictionary (for optimization)
        base_unmapped_dict: Optional pre-computed unmapped parameters dictionary
        
    Returns:
        Count of contacts matching this parameter within the context of all other filters, or 0 if parameter cannot be mapped
    """
    if param_name in ("page", "sortByField", "sortAscending"):
        return 0
    
    try:
        filter_dict, unmapped_dict = _get_filter_dict(
            base_filter_dict,
            base_unmapped_dict,
            param_name,
            param_values=param_values,
            all_apollo_params=all_apollo_params,
            apollo_service=apollo_service,
        )
        
        if param_name in unmapped_dict or not filter_dict:
            return 0
        
        return await _execute_count_query(session, filter_dict)
        
    except Exception:
        return 0


def _get_filter_dict(
    base_filter_dict: Optional[dict],
    base_unmapped_dict: Optional[dict],
    param_name: str,
    all_apollo_params: dict[str, list[str]],
    apollo_service: ApolloAnalysisService,
    param_value: Optional[str] = None,
    param_values: Optional[list[str]] = None,
) -> tuple[dict, dict]:
    """
    Get filter dictionary using pre-computed base filters or compute from scratch.
    
    Returns:
        Tuple of (filter_dict, unmapped_dict)
    """
    if base_filter_dict is not None and base_unmapped_dict is not None:
        return _build_filter_from_base(
            base_filter_dict,
            base_unmapped_dict,
            param_name,
            param_value=param_value,
            param_values=param_values,
            all_apollo_params=all_apollo_params,
            apollo_service=apollo_service,
        )
    
    raw_params = {
        k: v for k, v in all_apollo_params.items()
        if k not in ("page", "sortByField", "sortAscending")
    }
    return apollo_service.map_to_contact_filters(raw_params, include_unmapped=True)


async def _execute_count_query(session: AsyncSession, filter_dict: dict) -> int:
    """
    Execute count query with caching support.
    
    Returns:
        Count of contacts matching the filters
    """
    try:
        filters = ApolloFilterParams.model_validate(filter_dict)
    except ValidationError:
        return 0
    
    cache_key = _generate_count_cache_key(filters)
    cached_count = await query_cache.get("apollo_count", cache_key)
    if cached_count is not None:
        return int(cached_count)
    
    count_response = await contacts_service.count_contacts(session, filters)
    count = count_response.count
    
    await query_cache.set(
        "apollo_count",
        count,
        ttl=APOLLO_QUERY_CACHE_TTL,
        cache_key=cache_key,
    )
    
    return count


async def _count_contacts_for_value(
    session: AsyncSession,
    param_name: str,
    single_value: str,
    all_apollo_params: dict[str, list[str]],
    apollo_service: ApolloAnalysisService,
    base_filter_dict: Optional[dict] = None,
    base_unmapped_dict: Optional[dict] = None,
) -> int:
    """
    Count contacts matching a specific Apollo parameter with a single value,
    within the context of all other filters from the Apollo URL.
    
    For exclusion filters (personNotLocations[], organizationNotIndustryTagIds[], etc.),
    this counts contacts that match all other filters (including other exclusions) 
    and are excluded by this specific value.
    
    Handles special cases like employee ranges, revenue ranges, etc.
    
    Args:
        session: Database session
        param_name: Apollo parameter name (e.g., "personTitles[]")
        single_value: Single parameter value
        all_apollo_params: All parameters from the Apollo URL (for contextual filtering)
        apollo_service: Apollo analysis service for mapping
        base_filter_dict: Optional pre-computed base filter dictionary (for optimization)
        base_unmapped_dict: Optional pre-computed unmapped parameters dictionary
        
    Returns:
        Count of contacts matching this parameter value within the context of all other filters, or 0 if cannot be mapped
    """
    if param_name in ("page", "sortByField", "sortAscending"):
        return 0
    
    try:
        filter_dict, unmapped_dict = _get_filter_dict(
            base_filter_dict,
            base_unmapped_dict,
            param_name,
            param_value=single_value,
            all_apollo_params=all_apollo_params,
            apollo_service=apollo_service,
        )
        
        if param_name in unmapped_dict or not filter_dict:
            return 0
        
        return await _execute_count_query(session, filter_dict)
        
    except Exception:
        return 0


def _resolve_pagination(
    filters: ApolloFilterParams,
    limit: Optional[int],
) -> Optional[int]:
    """Choose the most appropriate page size within configured bounds."""
    return resolve_pagination_params(filters, limit, cap_explicit_limit=False)


@router.post("/analyze", response_model=ApolloUrlAnalysisResponse)
async def analyze_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloUrlAnalysisResponse:
    """
    Analyze an Apollo.io URL and return structured parameter breakdown.

    This endpoint parses Apollo.io search URLs (typically from the People Search page)
    and extracts all query parameters, categorizing them into logical groups such as:
    - Pagination (page numbers)
    - Sorting (sort field and direction)
    - Person Filters (titles, locations, seniorities, departments)
    - Organization Filters (employee ranges, locations, industries, revenue)
    - Email Filters (verification status, catch-all exclusion)
    - Keyword Filters (organization keywords, search fields)
    - And more...

    The analysis includes:
    - URL structure breakdown (base URL, hash path, query string)
    - Categorized parameters with descriptions
    - Parameter values (URL-decoded)
    - Statistics about the search criteria

    Args:
        request_data: Request containing the Apollo.io URL to analyze
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        ApolloUrlAnalysisResponse with complete URL analysis

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or analysis fails
    """
    try:
        result = await service.analyze_url(request_data.url)
        
        # Convert Tag IDs to industry names in the response for better readability
        converted_categories = []
        converted_raw_parameters = {}
        
        for category in result.categories:
            converted_params = []
            for param in category.parameters:
                # Convert Tag IDs to industry names if applicable
                converted_values = _convert_industry_tagids_to_names(param.name, param.values)
                converted_params.append(
                    ParameterDetail(
                        name=param.name,
                        values=converted_values,
                        description=param.description,
                        category=param.category,
                    )
                )
            converted_categories.append(
                ParameterCategory(
                    name=category.name,
                    parameters=converted_params,
                    total_parameters=category.total_parameters,
                )
            )
        
        # Also convert in raw_parameters
        for param_name, param_values in result.raw_parameters.items():
            converted_raw_parameters[param_name] = _convert_industry_tagids_to_names(
                param_name, param_values
            )
        
        # Build new response with converted values
        converted_result = ApolloUrlAnalysisResponse(
            url=result.url,
            url_structure=result.url_structure,
            categories=converted_categories,
            statistics=result.statistics,
            raw_parameters=converted_raw_parameters,
        )
        
        return converted_result
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the URL",
        ) from exc


@router.post("/analyze/count", response_model=ApolloUrlAnalysisWithCountResponse)
async def analyze_apollo_url_with_counts(
    request_data: ApolloUrlAnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloUrlAnalysisWithCountResponse:
    """
    Analyze an Apollo.io URL and return structured parameter breakdown with contact counts.
    
    This endpoint extends `/apollo/analyze` by adding contact counts for each parameter
    and each value within parameters. This helps users understand the impact of each
    filter on their contact database.
    
    The response includes:
    - URL structure breakdown (base URL, hash path, query string)
    - Categorized parameters with descriptions
    - Parameter values (URL-decoded)
    - Statistics about the search criteria
    - Contact counts for each parameter (all values combined)
    - Contact counts for each individual value
    
    Args:
        request_data: Request containing the Apollo.io URL to analyze
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)
    
    Returns:
        ApolloUrlAnalysisWithCountResponse with complete URL analysis and counts
    
    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or analysis fails
    """
    try:
        # Step 1: Analyze the Apollo URL to extract parameters (same as /analyze)
        result = await service.analyze_url(request_data.url)
        
        # Step 2: Prepare all Apollo parameters for contextual counting
        # Exclude pagination and sorting parameters from filter context (they don't filter contacts)
        all_apollo_params = dict(result.raw_parameters)
        
        # Step 2.5: Pre-compute base filter mapping (cached for reuse)
        # This avoids calling map_to_contact_filters 100+ times with similar parameters
        base_raw_params = {
            k: v for k, v in all_apollo_params.items()
            if k not in ("page", "sortByField", "sortAscending")
        }
        base_filter_dict, base_unmapped_dict = service.map_to_contact_filters(
            base_raw_params, include_unmapped=True
        )
        
        # Step 3: Collect all count tasks first, then execute in parallel
        task_data = _build_count_tasks(
            result.categories,
            all_apollo_params,
            service,
            session,
            base_filter_dict,
            base_unmapped_dict,
        )
        all_count_tasks = task_data["tasks"]
        task_metadata = task_data["metadata"]
        param_info_list = task_data["param_info_list"]
        original_query_count = task_data["original_query_count"]
        
        # Execute all count tasks in parallel batches with higher concurrency
        max_concurrent = settings.APOLLO_COUNT_MAX_CONCURRENT
        
        start_time = time.time()
        
        # Execute all tasks in single batch
        all_results = await _batch_execute_tasks(all_count_tasks, max_concurrent=max_concurrent)
        
        execution_time = time.time() - start_time
        actual_query_count = len(all_count_tasks)
        reduced_query_count = original_query_count - actual_query_count
        reduction_percentage = (reduced_query_count / original_query_count * 100) if original_query_count > 0 else 0
        
        # Separate results into parameter and value counts using metadata
        param_counts = []
        value_counts = []
        for i, metadata in enumerate(task_metadata):
            if metadata["type"] == "param":
                param_counts.append(all_results[i])
            else:
                value_counts.append(all_results[i])
        
        # Step 4: Assemble results using the collected metadata
        converted_categories = _assemble_count_results(
            result.categories,
            param_info_list,
            param_counts,
            value_counts,
        )
        
        # Also convert in raw_parameters
        converted_raw_parameters = {}
        for param_name, param_values in result.raw_parameters.items():
            converted_raw_parameters[param_name] = _convert_industry_tagids_to_names(
                param_name, param_values
            )
        
        # Build response with converted values and counts
        converted_result = ApolloUrlAnalysisWithCountResponse(
            url=result.url,
            url_structure=result.url_structure,
            categories=converted_categories,
            statistics=result.statistics,
            raw_parameters=converted_raw_parameters,
        )
        
        return converted_result
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the URL with counts",
        ) from exc


@router.post("/contacts", response_model=ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]])
async def search_contacts_from_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    request: Request,
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    cursor: Optional[str] = Query(None),
    view: Optional[str] = Query(None),
    include_company_name: Optional[str] = Query(None, description="Include contacts whose company name matches (case-insensitive substring)"),
    exclude_company_name: Optional[list[str]] = Query(None, description="Exclude contacts whose company name matches any provided value (case-insensitive)"),
    include_domain_list: Optional[list[str]] = Query(None, description="Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    exclude_domain_list: Optional[list[str]] = Query(None, description="Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]]:
    """
    Search contacts using Apollo.io URL parameters.

    This endpoint converts an Apollo.io People Search URL into contact filter
    parameters and returns matching contacts from the database. It provides a
    seamless way to replicate Apollo.io searches in your own contact database.

    **Parameter Mappings:**
    - `page` → `page`
    - `sortByField` + `sortAscending` → `ordering` (with `-` prefix for descending)
    - `personTitles[]` → `title` (comma-separated for OR logic)
    - `personNotTitles[]` → `exclude_titles`
    - `personSeniorities[]` → `seniority` (comma-separated)
    - `personDepartmentOrSubdepartments[]` → `department` (comma-separated)
    - `personLocations[]` → `contact_location` (comma-separated)
    - `personNotLocations[]` → `exclude_contact_locations`
    - `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`
    - `organizationLocations[]` → `company_location` (comma-separated)
    - `organizationNotLocations[]` → `exclude_company_locations`
    - `revenueRange[min/max]` → `annual_revenue_min`, `annual_revenue_max`
    - `contactEmailStatusV2[]` → `email_status` (comma-separated)
    - `qOrganizationKeywordTags[]` → `keywords` (comma-separated)
    - `qNotOrganizationKeywordTags[]` → `exclude_keywords`
    - `qKeywords` → `search`

    **Skipped Parameters:**
    - ID-based filters (industry tags, technology UIDs) - no mapping available
    - Apollo-specific features (search lists, personas, intent, lookalike)
    - Unmapped filters (job postings, trading status, market segments)

    Args:
        request_data: Request containing the Apollo.io URL to convert
        request: FastAPI request object for URL construction
        limit: Maximum number of results per page. If not provided, returns all matching contacts (no pagination limit).
        offset: Starting offset for results
        cursor: Opaque cursor token for pagination
        view: When "simple", returns ContactSimpleItem, otherwise ContactListItem
        include_company_name: Include contacts whose company name matches (case-insensitive substring)
        exclude_company_name: Exclude contacts whose company name matches any provided value (case-insensitive)
        include_domain_list: Include contacts whose company website domain matches any provided domain (case-insensitive)
        exclude_domain_list: Exclude contacts whose company website domain matches any provided domain (case-insensitive)
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        CursorPage containing ContactListItem or ContactSimpleItem results

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or query fails
    """
    try:
        # Step 1: Analyze the Apollo URL to extract parameters
        analysis = await service.analyze_url(request_data.url)

        # Step 2: Map Apollo parameters to contact filter parameters (with unmapped tracking)
        filter_dict, unmapped_dict = service.map_to_contact_filters(analysis.raw_parameters, include_unmapped=True)
        
        # Check for conflicting parameters
        if "personTitles[]" in analysis.raw_parameters and "personNotTitles[]" in analysis.raw_parameters:
            person_titles = analysis.raw_parameters["personTitles[]"]
            person_not_titles = analysis.raw_parameters["personNotTitles[]"]
            # Check if any titles appear in both lists
            normalized_person_titles = {service._normalize_title(t) for t in person_titles}
            normalized_person_not_titles = {service._normalize_title(t) for t in person_not_titles}
            conflicting = normalized_person_titles & normalized_person_not_titles

        # Step 2.5: Apply company name and domain filters from query parameters
        if include_company_name is not None:
            filter_dict["include_company_name"] = include_company_name
        if exclude_company_name is not None:
            filter_dict["exclude_company_name"] = exclude_company_name
        # Normalize domain lists to handle comma-separated values
        normalized_include_domains = normalize_list_param(include_domain_list)
        if normalized_include_domains is not None:
            filter_dict["include_domain_list"] = normalized_include_domains
        normalized_exclude_domains = normalize_list_param(exclude_domain_list)
        if normalized_exclude_domains is not None:
            filter_dict["exclude_domain_list"] = normalized_exclude_domains

        # Step 3: Validate and construct ApolloFilterParams
        try:
            filters = ApolloFilterParams.model_validate(filter_dict)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
            ) from exc

        # Step 4: Determine pagination settings
        # Use helper function to resolve pagination with proper priority
        page_limit = _resolve_pagination(filters, limit)

        use_cursor = False
        resolved_offset = 0 if offset is None else offset
        cursor_token = cursor or filters.cursor
        
        if cursor_token:
            try:
                resolved_offset = decode_offset_cursor(cursor_token)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc
            use_cursor = True
        elif offset is None and filters.page is not None and page_limit is not None:
            # Only use filters.page if no explicit offset was provided (offset is None)
            # This prevents the Apollo URL's page parameter from overriding explicit pagination
            resolved_offset = (filters.page - 1) * page_limit

        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())

        # Step 4.5: Try to get from cache (if enabled and not using cursor)
        cache_key_data = {
            "url": request_data.url,
            "limit": page_limit,
            "offset": resolved_offset,
            "view": view,
            "include_company_name": include_company_name,
            "exclude_company_name": exclude_company_name,
            "include_domain_list": normalized_include_domains,
            "exclude_domain_list": normalized_exclude_domains,
        }
        
        cached_result = None
        if query_cache.enabled and not use_cursor and page_limit is not None and page_limit <= 1000:
            # Only cache for reasonable page sizes to avoid memory issues
            try:
                cached_result = await query_cache.get("apollo_query_result", **cache_key_data)
                if cached_result:
                    # Reconstruct response from cached data
                    return ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]](**cached_result)
            except Exception as exc:
                pass

        # Step 5: Query contacts based on view parameter
        # Pass None directly for unlimited queries (service handles it properly)
        if (view or "").strip().lower() == "simple":
            page = await contacts_service.list_contacts_simple(
                session,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=str(request.url),
                use_cursor=use_cursor,
            )
        else:
            page = await contacts_service.list_contacts(
                session,
                filters,
                limit=page_limit,
                offset=resolved_offset,
                request_url=str(request.url),
                use_cursor=use_cursor,
            )

        # Step 6: Build unmapped categories structure from analysis
        unmapped_categories = []
        category_unmapped_map = {}  # Map category name to list of unmapped parameters
        
        # Group unmapped parameters by category
        for param_name, (param_values, reason) in unmapped_dict.items():
            # Find the category for this parameter from the analysis
            param_category = "Other"
            for category in analysis.categories:
                for param in category.parameters:
                    if param.name == param_name:
                        param_category = category.name
                        break
            
            if param_category not in category_unmapped_map:
                category_unmapped_map[param_category] = []
            
            # Convert Tag IDs to industry names for better readability
            converted_values = _convert_industry_tagids_to_names(param_name, param_values)
            
            category_unmapped_map[param_category].append(
                UnmappedParameter(
                    name=param_name,
                    values=converted_values,
                    category=param_category,
                    reason=reason
                )
            )
        
        # Build UnmappedCategory objects
        for category_name, params in category_unmapped_map.items():
            unmapped_categories.append(
                UnmappedCategory(
                    name=category_name,
                    parameters=params,
                    total_parameters=len(params)
                )
            )
        
        # Step 7: Build mapping summary
        mapped_param_names = sorted(
            [p for p in analysis.raw_parameters.keys() if p not in unmapped_dict]
        )
        unmapped_param_names = sorted(unmapped_dict.keys())
        
        mapping_summary = MappingSummary(
            total_apollo_parameters=len(analysis.raw_parameters),
            mapped_parameters=len(mapped_param_names),
            unmapped_parameters=len(unmapped_param_names),
            mapped_parameter_names=mapped_param_names,
            unmapped_parameter_names=unmapped_param_names
        )
        
        # Step 8: Build final response with mapping metadata
        response = ApolloContactsSearchResponse[Union[ContactListItem, ContactSimpleItem]](
            next=page.next,
            previous=page.previous,
            results=page.results,
            apollo_url=request_data.url,
            mapping_summary=mapping_summary,
            unmapped_categories=unmapped_categories
        )

        # Cache the result (if enabled and not using cursor)
        if query_cache.enabled and not use_cursor and page_limit is not None and page_limit <= 1000:
            try:
                cache_data = response.model_dump(mode='json')
                await query_cache.set(
                    "apollo_query_result",
                    cache_data,
                    ttl=APOLLO_QUERY_CACHE_TTL,
                    **cache_key_data
                )
            except Exception as exc:
                pass

        return response

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching contacts",
        ) from exc


@router.post("/contacts/count", response_model=CountResponse)
async def count_contacts_from_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    include_company_name: Optional[str] = Query(None, description="Include contacts whose company name matches (case-insensitive substring)"),
    exclude_company_name: Optional[list[str]] = Query(None, description="Exclude contacts whose company name matches any provided value (case-insensitive)"),
    include_domain_list: Optional[list[str]] = Query(None, description="Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    exclude_domain_list: Optional[list[str]] = Query(None, description="Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CountResponse:
    """
    Count contacts matching Apollo.io URL parameters.

    This endpoint converts an Apollo.io People Search URL into contact filter
    parameters and returns the total count of matching contacts from the database.

    **Parameter Mappings:**
    Same as `/api/v2/apollo/contacts` endpoint - all Apollo URL parameters are
    mapped to contact filters using the same logic.

    **Query Parameters:**
    - `include_company_name`: Include contacts whose company name matches (case-insensitive substring)
    - `exclude_company_name`: Exclude contacts whose company name matches any provided value (case-insensitive)
    - `include_domain_list`: Include contacts whose company website domain matches any provided domain (case-insensitive)
    - `exclude_domain_list`: Exclude contacts whose company website domain matches any provided domain (case-insensitive)

    Args:
        request_data: Request containing the Apollo.io URL to convert
        include_company_name: Optional company name inclusion filter
        exclude_company_name: Optional list of company names to exclude
        include_domain_list: Optional list of domains to include
        exclude_domain_list: Optional list of domains to exclude
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        CountResponse with total count of matching contacts

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or query fails
    """
    try:
        # Step 1: Analyze the Apollo URL to extract parameters
        analysis = await service.analyze_url(request_data.url)

        # Step 2: Map Apollo parameters to contact filter parameters
        filter_dict, unmapped_dict = service.map_to_contact_filters(analysis.raw_parameters, include_unmapped=True)

        # Step 2.5: Apply company name and domain filters from query parameters
        if include_company_name is not None:
            filter_dict["include_company_name"] = include_company_name
        if exclude_company_name is not None:
            filter_dict["exclude_company_name"] = exclude_company_name
        # Normalize domain lists to handle comma-separated values
        normalized_include_domains = normalize_list_param(include_domain_list)
        if normalized_include_domains is not None:
            filter_dict["include_domain_list"] = normalized_include_domains
        normalized_exclude_domains = normalize_list_param(exclude_domain_list)
        if normalized_exclude_domains is not None:
            filter_dict["exclude_domain_list"] = normalized_exclude_domains

        # Step 3: Validate and construct ApolloFilterParams
        try:
            filters = ApolloFilterParams.model_validate(filter_dict)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
            ) from exc

        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())

        # Step 3.5: Try to get from cache (if enabled)
        cache_key_data = {
            "url": request_data.url,
            "include_company_name": include_company_name,
            "exclude_company_name": exclude_company_name,
            "include_domain_list": normalized_include_domains,
            "exclude_domain_list": normalized_exclude_domains,
        }
        
        cached_result = None
        if query_cache.enabled:
            try:
                cached_result = await query_cache.get("apollo_count_result", **cache_key_data)
                if cached_result:
                    # Reconstruct response from cached data
                    return CountResponse(**cached_result)
            except Exception as exc:
                pass

        # Step 4: Count contacts
        count_response = await contacts_service.count_contacts(session, filters)

        # Step 4.5: Cache the result (if enabled)
        if query_cache.enabled:
            try:
                cache_data = count_response.model_dump(mode='json')
                await query_cache.set(
                    "apollo_count_result",
                    cache_data,
                    ttl=APOLLO_QUERY_CACHE_TTL,
                    **cache_key_data
                )
            except Exception as exc:
                pass

        return count_response

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while counting contacts",
        ) from exc


@router.post("/contacts/count/uuids", response_model=UuidListResponse)
async def get_contact_uuids_from_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    offset: int = Query(0, ge=0, description="Number of UUIDs to skip before returning results"),
    limit: Optional[int] = Query(None, ge=1, description="Limit the number of UUIDs returned. If not provided, returns all matching UUIDs."),
    include_company_name: Optional[str] = Query(None, description="Include contacts whose company name matches (case-insensitive substring)"),
    exclude_company_name: Optional[list[str]] = Query(None, description="Exclude contacts whose company name matches any provided value (case-insensitive)"),
    include_domain_list: Optional[list[str]] = Query(None, description="Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    exclude_domain_list: Optional[list[str]] = Query(None, description="Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website."),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UuidListResponse:
    """
    Get contact UUIDs matching Apollo.io URL parameters.

    This endpoint converts an Apollo.io People Search URL into contact filter
    parameters and returns the UUIDs of matching contacts from the database.

    **Parameter Mappings:**
    Same as `/api/v2/apollo/contacts` endpoint - all Apollo URL parameters are
    mapped to contact filters using the same logic.

    **Query Parameters:**
    - `offset`: Number of UUIDs to skip before returning results (default: 0)
    - `limit`: Limit the number of UUIDs returned. If not provided, returns all matching UUIDs.
    - `include_company_name`: Include contacts whose company name matches (case-insensitive substring)
    - `exclude_company_name`: Exclude contacts whose company name matches any provided value (case-insensitive)
    - `include_domain_list`: Include contacts whose company website domain matches any provided domain (case-insensitive)
    - `exclude_domain_list`: Exclude contacts whose company website domain matches any provided domain (case-insensitive)

        Args:
        request_data: Request containing the Apollo.io URL to convert
        offset: Number of UUIDs to skip before returning results (default: 0)
        limit: Optional limit on number of UUIDs to return
        include_company_name: Optional company name inclusion filter
        exclude_company_name: Optional list of company names to exclude
        include_domain_list: Optional list of domains to include
        exclude_domain_list: Optional list of domains to exclude
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        UuidListResponse with count and list of contact UUIDs

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or query fails
    """
    try:
        # Step 1: Analyze the Apollo URL to extract parameters
        analysis = await service.analyze_url(request_data.url)

        # Step 2: Map Apollo parameters to contact filter parameters
        filter_dict, unmapped_dict = service.map_to_contact_filters(analysis.raw_parameters, include_unmapped=True)

        # Step 2.5: Apply company name and domain filters from query parameters
        if include_company_name is not None:
            filter_dict["include_company_name"] = include_company_name
        if exclude_company_name is not None:
            filter_dict["exclude_company_name"] = exclude_company_name
        # Normalize domain lists to handle comma-separated values
        normalized_include_domains = normalize_list_param(include_domain_list)
        if normalized_include_domains is not None:
            filter_dict["include_domain_list"] = normalized_include_domains
        normalized_exclude_domains = normalize_list_param(exclude_domain_list)
        if normalized_exclude_domains is not None:
            filter_dict["exclude_domain_list"] = normalized_exclude_domains

        # Step 3: Validate and construct ApolloFilterParams
        try:
            filters = ApolloFilterParams.model_validate(filter_dict)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filter parameters: {exc.errors()[0].get('msg', 'Validation error')}",
            ) from exc

        active_filter_keys = sorted(filters.model_dump(exclude_none=True).keys())

        # Step 4: Get contact UUIDs
        uuids = await contacts_service.get_uuids_by_filters(session, filters, limit)

        return UuidListResponse(count=len(uuids), uuids=uuids)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while getting contact UUIDs",
        ) from exc

