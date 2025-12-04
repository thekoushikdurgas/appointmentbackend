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
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.query_cache import get_query_cache

logger = get_logger(__name__)
settings = get_settings()


async def invalidate_list_cache(prefix: str, logger_instance: Optional[object] = None) -> None:
    """
    Invalidate all list cache entries for a given prefix.
    
    This is the common pattern used after create/update/delete operations
    to ensure list queries return fresh data.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    
    Example:
        # After creating a contact
        await invalidate_list_cache("contacts", self.logger)
    """
    if not settings.ENABLE_QUERY_CACHING:
        return
    
    log = logger_instance or logger
    cache = get_query_cache()
    pattern = f"query_cache:{prefix}:list:*"
    
    try:
        count = await cache.invalidate_pattern(pattern)
        if count > 0:
            log.debug("Invalidated %d cache entries for prefix=%s", count, prefix)
    except Exception as exc:
        log.warning("Failed to invalidate %s list cache: %s", prefix, exc)


async def invalidate_entity_cache(
    prefix: str,
    entity_id: str,
    logger_instance: Optional[object] = None
) -> None:
    """
    Invalidate cache entries for a specific entity.
    
    Args:
        prefix: Cache prefix (e.g., "contact", "company")
        entity_id: Entity identifier (UUID or ID)
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    
    Example:
        # After updating a contact
        await invalidate_entity_cache("contact", contact_uuid, self.logger)
    """
    if not settings.ENABLE_QUERY_CACHING:
        return
    
    log = logger_instance or logger
    cache = get_query_cache()
    
    try:
        # Invalidate specific entity cache
        deleted = await cache.delete(prefix, entity_id=entity_id)
        if deleted:
            log.debug("Invalidated cache for %s entity_id=%s", prefix, entity_id)
    except Exception as exc:
        log.warning("Failed to invalidate %s entity cache (id=%s): %s", prefix, entity_id, exc)


async def invalidate_pattern(
    pattern: str,
    logger_instance: Optional[object] = None
) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Cache key pattern (e.g., "query_cache:contacts:*")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    
    Returns:
        Number of cache entries invalidated
    
    Example:
        # Custom pattern invalidation
        count = await invalidate_pattern("query_cache:contacts:search:*", self.logger)
    """
    if not settings.ENABLE_QUERY_CACHING:
        return 0
    
    log = logger_instance or logger
    cache = get_query_cache()
    
    try:
        count = await cache.invalidate_pattern(pattern)
        if count > 0:
            log.debug("Invalidated %d cache entries matching pattern=%s", count, pattern)
        return count
    except Exception as exc:
        log.warning("Failed to invalidate cache pattern %s: %s", pattern, exc)
        return 0


@asynccontextmanager
async def cache_invalidation_context(
    prefix: str,
    operation: str = "update",
    logger_instance: Optional[object] = None
):
    """
    Context manager for automatic cache invalidation.
    
    Automatically invalidates list cache after the context exits successfully.
    Useful for wrapping create/update/delete operations.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        operation: Operation type for logging ("create", "update", "delete")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    
    Example:
        async with cache_invalidation_context("contacts", "create", self.logger):
            contact = await self.repository.create_contact(session, data)
            await session.commit()
            # Cache is automatically invalidated on successful exit
    """
    log = logger_instance or logger
    try:
        yield
        # Invalidate cache after successful operation
        await invalidate_list_cache(prefix, log)
        log.debug("Cache invalidated after %s operation for prefix=%s", operation, prefix)
    except Exception as exc:
        # Re-raise the exception, cache invalidation happens on success only
        log.debug("Operation failed, skipping cache invalidation: %s", exc)
        raise


async def invalidate_on_create(
    prefix: str,
    logger_instance: Optional[object] = None
) -> None:
    """
    Invalidate cache after a create operation.
    
    Convenience wrapper for invalidate_list_cache with create-specific logging.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    """
    await invalidate_list_cache(prefix, logger_instance)


async def invalidate_on_update(
    prefix: str,
    logger_instance: Optional[object] = None
) -> None:
    """
    Invalidate cache after an update operation.
    
    Convenience wrapper for invalidate_list_cache with update-specific logging.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    """
    await invalidate_list_cache(prefix, logger_instance)


async def invalidate_on_delete(
    prefix: str,
    logger_instance: Optional[object] = None
) -> None:
    """
    Invalidate cache after a delete operation.
    
    Convenience wrapper for invalidate_list_cache with delete-specific logging.
    
    Args:
        prefix: Cache prefix (e.g., "contacts", "companies")
        logger_instance: Optional logger instance to use for warnings.
                        If None, uses module logger.
    """
    await invalidate_list_cache(prefix, logger_instance)

