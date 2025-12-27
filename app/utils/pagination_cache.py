"""Pagination and caching utilities for list operations.

This module provides reusable helpers for common pagination and caching patterns
used in list operations across services. It eliminates duplication between
list_contacts and list_companies methods.

Used by:
- contacts_service.py (list_contacts)
- companies_service.py (list_companies)
- Other services with similar list operations
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar

from app.core.config import get_settings
from app.schemas.common import CursorPage
from app.utils.cursor import encode_offset_cursor
from app.utils.logger import get_logger
from app.utils.pagination import build_cursor_link, build_pagination_link
from app.utils.query_cache import get_query_cache

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")


async def get_cached_list_result(
    cache_prefix: str,
    filters: Any,
    limit: Optional[int],
    offset: int,
    use_cursor: bool,
) -> Optional[dict[str, Any]]:
    """
    Check cache for a list query result.
    
    Args:
        cache_prefix: Cache prefix (e.g., "contacts", "companies")
        filters: Filter parameters (will be converted to dict)
        limit: Query limit
        offset: Query offset
        use_cursor: Whether cursor pagination is used
    
    Returns:
        Cached result dict if found, None otherwise
    """
    if not settings.ENABLE_QUERY_CACHING or limit is None or limit > 1000:
        return None
    
    # Checking cache for list query
    cache = get_query_cache()
    cache_key_args = {
        "filters": filters.model_dump(exclude_none=True) if hasattr(filters, "model_dump") else filters,
        "limit": limit,
        "offset": offset,
        "use_cursor": use_cursor,
    }
    
    try:
        cached_result = await cache.get(f"{cache_prefix}:list", **cache_key_args)
        if cached_result:
            # Cache hit for list query
            return cached_result
    except Exception as exc:
        # Error checking cache for list query
        pass
    
    return None


async def cache_list_result(
    cache_prefix: str,
    page: CursorPage[Any],
    filters: Any,
    limit: Optional[int],
    offset: int,
    use_cursor: bool,
) -> None:
    """
    Cache a list query result.
    
    Args:
        cache_prefix: Cache prefix (e.g., "contacts", "companies")
        page: CursorPage result to cache
        filters: Filter parameters (will be converted to dict)
        limit: Query limit
        offset: Query offset
        use_cursor: Whether cursor pagination is used
    """
    if not settings.ENABLE_QUERY_CACHING or limit is None or limit > 1000:
        return
    
    # Caching list query result
    cache = get_query_cache()
    cache_key_args = {
        "filters": filters.model_dump(exclude_none=True) if hasattr(filters, "model_dump") else filters,
        "limit": limit,
        "offset": offset,
        "use_cursor": use_cursor,
    }
    
    try:
        await cache.set(f"{cache_prefix}:list", page.model_dump(), **cache_key_args)
    except Exception as exc:
        # Failed to cache list result
        pass


def build_pagination_links(
    request_url: str,
    limit: Optional[int],
    offset: int,
    results_count: int,
    use_cursor: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    """
    Build next and previous pagination links.
    
    Args:
        request_url: Base request URL
        limit: Query limit
        offset: Query offset
        results_count: Number of results returned
        use_cursor: Whether to use cursor pagination
    
    Returns:
        Tuple of (next_link, previous_link)
    """
    next_link = None
    # Only show next link if we have a limit and returned exactly that many results
    if limit is not None and results_count == limit:
        if use_cursor:
            next_cursor = encode_offset_cursor(offset + limit)
            next_link = build_cursor_link(request_url, next_cursor)
        else:
            next_link = build_pagination_link(
                request_url,
                limit=limit,
                offset=offset + limit,
            )
    
    previous_link = None
    if offset > 0:
        if use_cursor:
            prev_offset = max(offset - (limit or 0), 0)
            prev_cursor = encode_offset_cursor(prev_offset)
            previous_link = build_cursor_link(request_url, prev_cursor)
        else:
            prev_offset = max(offset - (limit or 0), 0)
            previous_link = build_pagination_link(request_url, limit=limit, offset=prev_offset)
    
    return next_link, previous_link


def build_list_meta(
    filters: Any,
    use_cursor: bool,
    results_count: int,
    limit: Optional[int],
    using_replica: bool = False,
) -> dict[str, Any]:
    """
    Build metadata for list operation results.
    
    Args:
        filters: Filter parameters
        use_cursor: Whether cursor pagination is used
        results_count: Number of results returned
        limit: Query limit
        using_replica: Whether using replica database
    
    Returns:
        Metadata dictionary
    """
    active_filter_keys = (
        sorted(filters.model_dump(exclude_none=True).keys())
        if hasattr(filters, "model_dump")
        else []
    )
    
    return {
        "strategy": "cursor" if use_cursor else "limit-offset",
        "count_mode": "estimated" if not active_filter_keys else "actual",
        "filters_applied": len(active_filter_keys) > 0,
        "ordering": getattr(filters, "ordering", None) or "-created_at",
        "returned_records": results_count,
        "page_size": limit,
        "page_size_cap": settings.MAX_PAGE_SIZE,
        "using_replica": using_replica,
    }


async def execute_list_query(
    cache_prefix: str,
    filters: Any,
    limit: Optional[int],
    offset: int,
    request_url: str,
    use_cursor: bool,
    fetch_func: Callable[[], Any],
    hydrate_func: Callable[[Any], T],
    using_replica: bool = False,
) -> CursorPage[T]:
    """
    Execute a list query with caching and pagination.
    
    This is a high-level helper that combines cache checking, query execution,
    pagination building, and result caching.
    
    Args:
        cache_prefix: Cache prefix (e.g., "contacts", "companies")
        filters: Filter parameters
        limit: Query limit
        offset: Query offset
        request_url: Base request URL for pagination links
        use_cursor: Whether to use cursor pagination
        fetch_func: Async function that fetches the data (returns list of entities)
        hydrate_func: Function that hydrates a single entity (entity -> T)
        using_replica: Whether using replica database
    
    Returns:
        CursorPage with results, pagination links, and metadata
    """
    # Executing list query
    
    # Check cache
    cached_result = await get_cached_list_result(
        cache_prefix, filters, limit, offset, use_cursor
    )
    if cached_result:
        return CursorPage(**cached_result)
    
    # Execute query
    entities = await fetch_func()
    results = [hydrate_func(entity) for entity in entities]
    
    # Build pagination links
    next_link, previous_link = build_pagination_links(
        request_url, limit, offset, len(results), use_cursor
    )
    
    # Build metadata
    meta = build_list_meta(filters, use_cursor, len(results), limit, using_replica)
    
    # Create page
    page = CursorPage(
        next=next_link,
        previous=previous_link,
        results=results,
        meta=meta,
    )
    
    # Cache result
    await cache_list_result(cache_prefix, page, filters, limit, offset, use_cursor)
    
    return page

