"""Utilities for building pagination and cursor navigation links.

This module provides optimized pagination utilities for both offset-based
and cursor-based pagination with performance optimizations.

Best practices:
- Use cursor-based pagination for deep pagination (>1000 offset)
- Use offset-based pagination for first few pages
- Optimize queries with proper indexes on ordering columns
- Set reasonable default page sizes (50-100 items)
- Enforce maximum page size limits
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.config import get_settings
from app.schemas.common import CursorPage
from app.utils.cursor import decode_offset_cursor
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def build_pagination_link(base_url: str, *, limit: int, offset: int) -> str:
    """Return a URL with updated limit/offset query parameters."""
    # Parse the base URL to extract components
    url = urlparse(base_url)
    # Parse existing query parameters and update with new limit/offset
    query = dict(parse_qsl(url.query))
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    result = urlunparse(new_url)
    return result


def build_cursor_link(base_url: str, cursor: str) -> str:
    """Return a URL that encodes the supplied cursor token and removes offset pagination."""
    # Parse base URL and update query parameters with cursor, removing offset/limit
    url = urlparse(base_url)
    query = dict(parse_qsl(url.query))
    query["cursor"] = cursor
    query.pop("offset", None)
    query.pop("limit", None)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    result = urlunparse(new_url)
    return result


def build_paginated_attribute_list(
    request_url: str,
    params: Any,  # AttributeListParams (original params with original limit)
    values: list[str],
    fetch_limit: Optional[int] = None,  # The actual limit used for fetching (may be limit+1)
) -> CursorPage[str]:
    """
    Build paginated attribute list with limit+1 pattern, deduplication, and edge case handling.
    
    This helper consolidates the complex pagination logic used in address list methods.
    It handles:
    - limit+1 pattern for accurate pagination detection
    - Edge cases for post-SQL filtering
    - Deduplication when distinct=True
    - Pagination link building
    
    Args:
        request_url: Base request URL for building pagination links
        params: AttributeListParams instance with limit, offset, distinct (original params)
        values: List of values returned from repository (may be limit+1 length if fetch_limit was used)
        fetch_limit: The actual limit used when fetching (None = use params.limit)
        
    Returns:
        CursorPage[str] with paginated results and links
        
    Example:
        # When using limit+1 pattern:
        modified_params = params.model_copy(update={"limit": params.limit + 1})
        values = await repository.list_attribute_values(..., modified_params)
        page = build_paginated_attribute_list(
            request_url="/api/contacts/attributes/addresses",
            params=params,  # original params
            values=values,
            fetch_limit=params.limit + 1  # actual fetch limit
        )
    """
    # Use limit+1 pattern: if we requested limit+1, check if we got exactly that many
    # This indicates there are more results
    raw_count = len(values)
    actual_fetch_limit = fetch_limit if fetch_limit is not None else params.limit
    has_more_results = params.limit is not None and raw_count == actual_fetch_limit
    
    # Edge case: Post-SQL filtering (NULL/empty string removal) can reduce count
    # If we requested limit+1 but got close to limit items (limit-2 to limit),
    # conservatively assume there may be more results
    if params.limit is not None and not has_more_results:
        if raw_count >= params.limit - 2 and raw_count <= params.limit:
            has_more_results = True
    
    # Apply deduplication if needed (before truncating to limit)
    distinct_requested = params.distinct
    if distinct_requested:
        seen = set()
        unique_values = []
        for value in values:
            if value is None:
                continue
            normalized = value.lower() if isinstance(value, str) else str(value)
            if normalized not in seen:
                seen.add(normalized)
                unique_values.append(value)
        values = unique_values
        deduplicated_count = len(values)
        
        # Edge case: When distinct=True, Python-level deduplication may further reduce count
        # If after deduplication we still have close to 'limit' items, conservatively assume more may exist
        if params.limit is not None and not has_more_results:
            if deduplicated_count >= params.limit - 2 and deduplicated_count <= params.limit:
                has_more_results = True
    
    # Return only the first 'limit' rows to the client
    if params.limit is not None and len(values) > params.limit:
        values = values[:params.limit]
    
    # Build pagination links
    next_link = None
    if has_more_results:
        next_offset = params.offset + params.limit
        next_link = build_pagination_link(request_url, limit=params.limit, offset=next_offset)
    
    previous_link = None
    if params.offset > 0:
        prev_offset = max(params.offset - params.limit, 0) if params.limit is not None else 0
        previous_link = build_pagination_link(request_url, limit=params.limit or 25, offset=prev_offset)
    
    return CursorPage(next=next_link, previous=previous_link, results=values)


def build_simple_list_pagination_links(
    request_url: str,
    limit: Optional[int],
    offset: int,
    results_count: int,
    default_limit: int = 25,
) -> tuple[Optional[str], Optional[str]]:
    """
    Build pagination links for simple list endpoints.
    
    This helper consolidates the common pagination pattern used across
    list_*_simple methods in services. It determines if there are more
    results based on whether the results count equals the limit.
    
    Args:
        request_url: Base request URL for building pagination links
        limit: Requested limit (None = unlimited)
        offset: Current offset
        results_count: Number of results returned
        default_limit: Default limit to use when limit is None (for previous link)
        
    Returns:
        Tuple of (next_link, previous_link), both can be None
        
    Example:
        next_link, previous_link = build_simple_list_pagination_links(
            request_url="/api/contacts/attributes/industries",
            limit=50,
            offset=0,
            results_count=50
        )
    """
    next_link = None
    if limit is not None and results_count == limit:
        # If we got exactly 'limit' results, there might be more
        next_offset = offset + limit
        next_link = build_pagination_link(request_url, limit=limit, offset=next_offset)
    
    previous_link = None
    if offset > 0:
        # If we're not at the start, there's a previous page
        prev_offset = max(offset - (limit or default_limit), 0)
        previous_link = build_pagination_link(
            request_url, limit=limit or default_limit, offset=prev_offset
        )
    
    return next_link, previous_link


# Enhanced pagination helpers

def normalize_page_size(
    requested: Optional[int],
    default: Optional[int] = None,
    max_size: Optional[int] = None,
) -> Optional[int]:
    """
    Normalize and validate page size with defaults and limits.
    
    Args:
        requested: Requested page size (None = unlimited or use default)
        default: Default page size if requested is None (uses settings if None)
        max_size: Maximum allowed page size (uses settings if None)
        
    Returns:
        Normalized page size (None if unlimited)
        
    Example:
        # With defaults from settings
        page_size = normalize_page_size(requested=150)  # Capped at MAX_PAGE_SIZE
        
        # With custom defaults
        page_size = normalize_page_size(requested=None, default=50, max_size=200)
    """
    if default is None:
        default = settings.DEFAULT_PAGE_SIZE
    
    if max_size is None:
        max_size = settings.MAX_PAGE_SIZE
    
    if requested is None:
        return default
    
    if requested <= 0:
        # Invalid page size requested, using default
        return default
    
    if max_size is not None and requested > max_size:
        # Page size exceeds maximum, capping to max_size
        return max_size
    
    return requested


def should_use_cursor_pagination(offset: int, threshold: int = 1000) -> bool:
    """
    Determine if cursor-based pagination should be used instead of offset.
    
    Offset-based pagination performance degrades with large offsets (O(n) scan).
    Cursor-based pagination maintains consistent performance.
    
    Args:
        offset: Current offset value
        threshold: Offset threshold for switching to cursor (default: 1000)
        
    Returns:
        True if cursor pagination is recommended
        
    Example:
        if should_use_cursor_pagination(offset=1500):
            # Use cursor-based pagination
            cursor = encode_keyset_cursor(last_id)
        else:
            # Use offset-based pagination
            query = query.offset(offset).limit(limit)
    """
    return offset >= threshold


def optimize_pagination_params(
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    default_limit: Optional[int] = None,
    max_limit: Optional[int] = None,
) -> dict[str, any]:
    """
    Optimize pagination parameters with validation and recommendations.
    
    Args:
        offset: Offset value (None = 0)
        limit: Page size (None = use default)
        cursor: Cursor token (takes precedence over offset if provided)
        default_limit: Default page size
        max_limit: Maximum page size
        
    Returns:
        Dictionary with optimized pagination parameters:
        - limit: Normalized page size
        - offset: Resolved offset (0 if None)
        - use_cursor: Whether to use cursor-based pagination
        - cursor: Cursor token if provided
        - recommendation: Performance recommendation
        
    Example:
        params = optimize_pagination_params(
            offset=1500,
            limit=100,
            default_limit=50,
            max_limit=1000
        )
        # Returns: {
        #     "limit": 100,
        #     "offset": 1500,
        #     "use_cursor": True,
        #     "cursor": None,
        #     "recommendation": "Use cursor-based pagination for better performance"
        # }
    """
    resolved_offset = offset or 0
    normalized_limit = normalize_page_size(limit, default_limit, max_limit)
    
    # Decode cursor if provided
    resolved_cursor = cursor
    if cursor:
        try:
            resolved_offset = decode_offset_cursor(cursor)
        except Exception as exc:
            resolved_cursor = None
    
    # Determine if cursor pagination is recommended
    use_cursor = should_use_cursor_pagination(resolved_offset) or bool(resolved_cursor)
    
    recommendation = None
    if resolved_offset >= 1000 and not resolved_cursor:
        recommendation = "Consider using cursor-based pagination for better performance with large offsets"
    elif normalized_limit and normalized_limit > 500:
        recommendation = "Large page size may impact performance. Consider using smaller pages with cursor pagination."
    
    return {
        "limit": normalized_limit,
        "offset": resolved_offset,
        "use_cursor": use_cursor,
        "cursor": resolved_cursor,
        "recommendation": recommendation,
    }


def calculate_total_pages(total_items: int, page_size: int) -> int:
    """
    Calculate total number of pages.
    
    Args:
        total_items: Total number of items
        page_size: Items per page
        
    Returns:
        Total number of pages (at least 1)
    """
    if page_size <= 0:
        return 1
    return max(1, (total_items + page_size - 1) // page_size)


def calculate_page_from_offset(offset: int, page_size: int) -> int:
    """
    Calculate page number from offset.
    
    Args:
        offset: Current offset
        page_size: Items per page
        
    Returns:
        Page number (1-indexed)
    """
    if page_size <= 0:
        return 1
    return (offset // page_size) + 1


def calculate_offset_from_page(page: int, page_size: int) -> int:
    """
    Calculate offset from page number.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        
    Returns:
        Offset value
    """
    if page < 1:
        page = 1
    if page_size <= 0:
        page_size = settings.DEFAULT_PAGE_SIZE or 100
    return (page - 1) * page_size


# Query optimization helpers for pagination

def apply_pagination_to_query(
    query,
    offset: int = 0,
    limit: Optional[int] = None,
    use_index_hint: bool = True,
):
    """
    Apply pagination to a SQLAlchemy query with optimizations.
    
    Args:
        query: SQLAlchemy Select query
        offset: Offset value
        limit: Limit value (None = no limit)
        use_index_hint: Whether to optimize for index usage (default: True)
        
    Returns:
        Query with pagination applied
        
    Example:
        query = select(Contact)
        paginated_query = apply_pagination_to_query(
            query,
            offset=100,
            limit=50
        )
    """
    # Apply offset
    if offset > 0:
        query = query.offset(offset)
    
    # Apply limit
    if limit is not None and limit > 0:
        query = query.limit(limit)
    
    # Performance hint: For large offsets, ensure ordering is indexed
    # Large offsets (>1000) may benefit from cursor-based pagination for better performance
    
    return query


def get_pagination_metadata(
    total_items: Optional[int],
    page_size: int,
    current_offset: int = 0,
) -> dict[str, any]:
    """
    Generate pagination metadata for API responses.
    
    Args:
        total_items: Total number of items (None if unknown)
        page_size: Current page size
        current_offset: Current offset
        
    Returns:
        Dictionary with pagination metadata
        
    Example:
        metadata = get_pagination_metadata(
            total_items=1000,
            page_size=50,
            current_offset=100
        )
        # Returns: {
        #     "total_items": 1000,
        #     "page_size": 50,
        #     "current_page": 3,
        #     "total_pages": 20,
        #     "has_next": True,
        #     "has_previous": True
        # }
    """
    current_page = calculate_page_from_offset(current_offset, page_size)
    
    result = {
        "page_size": page_size,
        "current_page": current_page,
        "current_offset": current_offset,
    }
    
    if total_items is not None:
        total_pages = calculate_total_pages(total_items, page_size)
        result.update(
            {
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": current_page < total_pages,
                "has_previous": current_page > 1,
            }
        )
    else:
        # Unknown total - can't determine has_next/has_previous
        result.update(
            {
                "total_items": None,
                "total_pages": None,
                "has_next": None,
                "has_previous": current_page > 1,
            }
        )
    
    return result

