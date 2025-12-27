"""Cache service utilities for common cache invalidation patterns.

This module provides reusable cache invalidation helpers to eliminate
code duplication across services. It encapsulates the common pattern of
checking if caching is enabled, getting the cache instance, and safely
invalidating cache entries with proper error handling.

Used by:
- contacts_service.py
- companies_service.py
- Other services that need cache invalidation
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.utils.logger import get_logger
from app.utils.query_cache import get_query_cache

settings = get_settings()
logger = get_logger(__name__)


async def invalidate_list_cache(prefix: str) -> None:
    """
    Invalidate all list cache entries for a given prefix.
    
    This is the common pattern used after create/update/delete operations
    to ensure list queries return fresh data.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
    
    Example:
        # After creating a contact
        await invalidate_list_cache("contacts")
    """
    if not settings.ENABLE_QUERY_CACHING:
        return
    
    cache = get_query_cache()
    pattern = f"query_cache:{prefix}:list:*"
    
    try:
        count = await cache.invalidate_pattern(pattern)
    except Exception:
        # Cache invalidation failed for prefix (non-critical error)
        pass


async def invalidate_entity_cache(
    prefix: str,
    entity_id: str,
) -> None:
    """
    Invalidate cache entries for a specific entity.
    
    Args:
        prefix: Cache prefix (e.g., "contact", "company")
        entity_id: Entity identifier (UUID or ID)
    
    Example:
        # After updating a contact
        await invalidate_entity_cache("contact", contact_uuid)
    """
    if not settings.ENABLE_QUERY_CACHING:
        return
    
    cache = get_query_cache()
    
    try:
        deleted = await cache.delete(prefix, entity_id=entity_id)
    except Exception:
        # Cache invalidation failed for entity (non-critical error)
        pass


async def invalidate_pattern(
    pattern: str,
) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Cache key pattern (e.g., "query_cache:contacts:*")
    
    Returns:
        Number of cache entries invalidated
    
    Example:
        # Custom pattern invalidation
        count = await invalidate_pattern("query_cache:contacts:search:*")
    """
    if not settings.ENABLE_QUERY_CACHING:
        return 0
    
    cache = get_query_cache()
    
    try:
        count = await cache.invalidate_pattern(pattern)
        return count
    except Exception:
        # Cache invalidation failed for pattern (non-critical error)
        return 0


@asynccontextmanager
async def cache_invalidation_context(
    prefix: str,
    operation: str = "update",
):
    """
    Context manager for automatic cache invalidation.
    
    Automatically invalidates list cache after the context exits successfully.
    Useful for wrapping create/update/delete operations.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        operation: Operation type ("create", "update", "delete") - kept for documentation
    
    Example:
        async with cache_invalidation_context("contacts", "create"):
            contact = await self.repository.create_contact(session, data)
            await session.commit()
            # Cache is automatically invalidated on successful exit
    """
    try:
        yield
        # Invalidate cache after successful operation
        await invalidate_list_cache(prefix)
        # Cache invalidated after operation for prefix
    except Exception:
        # Re-raise the exception, cache invalidation happens on success only
        # Operation failed, skipping cache invalidation
        raise


async def invalidate_on_create(
    prefix: str,
) -> None:
    """
    Invalidate cache after a create operation.
    
    Convenience wrapper for invalidate_list_cache.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
    """
    await invalidate_list_cache(prefix)


async def invalidate_on_update(
    prefix: str,
) -> None:
    """
    Invalidate cache after an update operation.
    
    Convenience wrapper for invalidate_list_cache.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
    """
    await invalidate_list_cache(prefix)


async def invalidate_on_delete(
    prefix: str,
) -> None:
    """
    Invalidate cache after a delete operation.
    
    Convenience wrapper for invalidate_list_cache.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
    """
    await invalidate_list_cache(prefix)

