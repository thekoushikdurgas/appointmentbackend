"""Query result caching utilities for frequently accessed queries.

This module provides in-memory caching for query results to improve performance
for frequently accessed data. The cache is used by:
- Contacts and companies services for list queries

Usage:
    from app.utils.query_cache import get_query_cache
    
    cache = get_query_cache()
    result = await cache.get("prefix", *args, **kwargs)
    if result is None:
        result = await expensive_query()
        await cache.set("prefix", result, *args, **kwargs)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from cachetools import TTLCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    TTLCache = None  # type: ignore

from app.core.config import get_settings

settings = get_settings()

# Try to import redis - optional dependency
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None


class RedisQueryCache:
    """Redis-backed query result cache for distributed caching."""
    
    def __init__(self, redis_url: str, enabled: bool = True):
        """
        Initialize Redis query cache.
        
        Args:
            redis_url: Redis connection URL
            enabled: Whether caching is enabled
        """
        self.enabled = enabled and settings.ENABLE_REDIS_CACHE
        self.default_ttl = settings.QUERY_CACHE_TTL
        self.redis_url = redis_url
        self._redis_client: Optional[Any] = None
        self._lock = asyncio.Lock()
        
    async def _get_client(self):
        """Get or create Redis client."""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis is not available. Install redis package: pip install redis")
        
        if self._redis_client is None:
            try:
                self._redis_client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis_client.ping()
            except Exception as exc:
                self._redis_client = None
                raise
        
        return self._redis_client
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from query parameters."""
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else [],
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"query_cache:{prefix}:{key_hash}"
    
    async def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """Get cached query result from Redis."""
        if not self.enabled:
            return None
        
        try:
            client = await self._get_client()
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            value = await client.get(cache_key)
            
            if value is None:
                return None
            
            # Deserialize JSON value
            result = json.loads(value)
            return result
        except Exception as exc:
            return None
    
    async def set(
        self,
        prefix: str,
        value: Any,
        ttl: Optional[int] = None,
        *args,
        **kwargs,
    ) -> bool:
        """Cache query result in Redis."""
        if not self.enabled:
            return False
        
        try:
            client = await self._get_client()
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            ttl = ttl or self.default_ttl
            
            # Serialize value to JSON
            value_json = json.dumps(value, default=str)
            await client.setex(cache_key, ttl, value_json)
            return True
        except Exception as exc:
            return False
    
    async def delete(self, prefix: str, *args, **kwargs) -> bool:
        """Delete cached query result from Redis."""
        if not self.enabled:
            return False
        
        try:
            client = await self._get_client()
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            deleted = await client.delete(cache_key)
            return deleted > 0
        except Exception as exc:
            return False
    
    async def clear_prefix(self, prefix: str) -> int:
        """Clear all cache entries with a given prefix."""
        if not self.enabled:
            return 0
        
        try:
            client = await self._get_client()
            pattern = f"query_cache:{prefix}:*"
            deleted = 0
            
            async for key in client.scan_iter(match=pattern):
                await client.delete(key)
                deleted += 1
            return deleted
        except Exception as exc:
            return 0
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        if not self.enabled:
            return 0
        
        try:
            client = await self._get_client()
            # Convert to Redis pattern format
            redis_pattern = pattern.replace("*", "*")
            deleted = 0
            
            async for key in client.scan_iter(match=redis_pattern):
                await client.delete(key)
                deleted += 1
            return deleted
        except Exception as exc:
            return 0
    
    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics from Redis."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            client = await self._get_client()
            info = await client.info("stats")
            keyspace = await client.info("keyspace")
            
            return {
                "enabled": True,
                "backend": "redis",
                "default_ttl": self.default_ttl,
                "redis_info": {
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                },
                "keyspace": keyspace,
            }
        except Exception as exc:
            return {"enabled": True, "backend": "redis", "error": str(exc)}
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


class QueryCache:
    """
    In-memory query result cache for frequently accessed queries.
    
    Uses cachetools.TTLCache for efficient TTL-based caching with automatic expiration
    and LRU eviction when maxsize is reached. Falls back to Redis if configured.
    
    Best practices:
    - Use for read-only, frequently accessed data
    - Set appropriate maxsize to prevent memory issues
    - Use Redis backend for multi-worker deployments
    - Invalidate cache on data mutations
    """

    def __init__(self, enabled: bool = True, use_redis: bool = False, redis_url: Optional[str] = None):
        """
        Initialize query cache.
        
        Args:
            enabled: Whether caching is enabled. If False, caching is disabled.
            use_redis: Whether to use Redis backend (if available and configured)
            redis_url: Redis connection URL (required if use_redis=True)
        """
        self.enabled = enabled and settings.ENABLE_QUERY_CACHING
        self.default_ttl = settings.QUERY_CACHE_TTL
        
        # Use Redis if enabled and available
        if use_redis and redis_url and settings.ENABLE_REDIS_CACHE:
            if REDIS_AVAILABLE:
                self._redis_cache = RedisQueryCache(redis_url, enabled=enabled)
                self._in_memory_cache: Optional[Any] = None
                self._use_redis = True
            else:
                self._redis_cache = None
                self._use_redis = False
                self._init_in_memory_cache()
        else:
            # Use in-memory cache
            self._redis_cache = None
            self._use_redis = False
            self._init_in_memory_cache()
        
        self._lock = asyncio.Lock()
    
    def _init_in_memory_cache(self) -> None:
        """Initialize in-memory cache using cachetools.TTLCache."""
        if not CACHETOOLS_AVAILABLE:
            self._cache: Optional[Any] = None
            self.enabled = False
            return
        
        maxsize = settings.CACHE_MAX_SIZE
        # TTLCache requires maxsize > 0, default_ttl is used per-entry
        # We'll use a default TTL that applies to all entries unless overridden
        self._cache = TTLCache(maxsize=maxsize, ttl=self.default_ttl)

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from query parameters.
        
        Args:
            prefix: Cache key prefix
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Cache key string
        """
        # Create a deterministic key from parameters
        key_data = {
            "prefix": prefix,
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else [],
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"query_cache:{prefix}:{key_hash}"


    async def get(self, prefix: str, *args, **kwargs) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            prefix: Cache key prefix
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
            
        Returns:
            Cached result or None if not found
        """
        if not self.enabled:
            return None

        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.get(prefix, *args, **kwargs)

        # Fallback to in-memory cache
        if self._cache is None:
            return None
        
        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            # TTLCache is thread-safe for reads, but we use lock for consistency
            async with self._lock:
                value = self._cache.get(cache_key)
                
                if value is None:
                    return None
                return value
            
        except Exception as exc:
            return None

    async def set(
        self,
        prefix: str,
        value: Any,
        ttl: Optional[int] = None,
        *args,
        **kwargs,
    ) -> bool:
        """
        Cache query result.
        
        Args:
            prefix: Cache key prefix
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (defaults to QUERY_CACHE_TTL)
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled:
            return False

        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.set(prefix, value, ttl, *args, **kwargs)

        # Fallback to in-memory cache
        if self._cache is None:
            return False
        
        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            ttl = ttl or self.default_ttl
            
            # TTLCache automatically handles TTL and LRU eviction
            # If we need a different TTL, we'd need to create a new cache entry
            # For simplicity, we use the default TTL from cache initialization
            # If custom TTL is needed, we could use a wrapper or separate cache per TTL
            async with self._lock:
                # TTLCache handles expiration and LRU eviction automatically
                self._cache[cache_key] = value
            return True
        except Exception as exc:
            return False

    async def delete(self, prefix: str, *args, **kwargs) -> bool:
        """
        Delete cached query result.
        
        Args:
            prefix: Cache key prefix
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enabled:
            return False

        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.delete(prefix, *args, **kwargs)

        # Fallback to in-memory cache
        if self._cache is None:
            return False
        
        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            async with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    return True
                return False
        except Exception as exc:
            return False

    async def clear_prefix(self, prefix: str) -> int:
        """
        Clear all cache entries with a given prefix.
        
        Args:
            prefix: Prefix to clear
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.clear_prefix(prefix)

        # Fallback to in-memory cache
        if self._cache is None:
            return 0
        
        try:
            pattern_prefix = f"query_cache:{prefix}:"
            deleted = 0
            
            async with self._lock:
                keys_to_delete = [
                    key for key in list(self._cache.keys()) if key.startswith(pattern_prefix)
                ]
                for key in keys_to_delete:
                    try:
                        del self._cache[key]
                        deleted += 1
                    except KeyError:
                        # Key may have expired between list and delete
                        pass
            return deleted
        except Exception as exc:
            return 0

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Cache key pattern (e.g., "query_cache:contacts:*")
                    Supports simple wildcard matching with *
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.invalidate_pattern(pattern)

        # Fallback to in-memory cache
        if self._cache is None:
            return 0
        
        try:
            # Convert Redis-style pattern to simple matching
            # Replace * with .* for regex, but we'll use simple string matching
            pattern_prefix = pattern.replace("*", "")
            deleted = 0
            
            async with self._lock:
                keys_to_delete = [
                    key for key in list(self._cache.keys()) if pattern_prefix in key
                ]
                for key in keys_to_delete:
                    try:
                        del self._cache[key]
                        deleted += 1
                    except KeyError:
                        # Key may have expired between list and delete
                        pass
            return deleted
        except Exception as exc:
            return 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled:
            return {"enabled": False}
        
        # Use Redis if available
        if self._use_redis and self._redis_cache:
            return await self._redis_cache.get_cache_stats()
        
        # Fallback to in-memory cache stats
        if self._cache is None:
            return {"enabled": False, "backend": "in-memory", "error": "cachetools not available"}
        
        # TTLCache automatically handles expiration, so all entries are valid
        return {
            "enabled": True,
            "backend": "in-memory (cachetools.TTLCache)",
            "default_ttl": self.default_ttl,
            "total_entries": len(self._cache),
            "valid_entries": len(self._cache),  # TTLCache only contains valid entries
            "max_entries": settings.CACHE_MAX_SIZE,
            "currsize": len(self._cache),
            "maxsize": settings.CACHE_MAX_SIZE,
        }


# Global cache instance (will be initialized during app startup)
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    global _query_cache
    if _query_cache is None:
        # Initialize with caching enabled if ENABLE_QUERY_CACHING is True
        # Use Redis if enabled and URL is provided
        use_redis = settings.ENABLE_REDIS_CACHE and settings.REDIS_URL is not None
        _query_cache = QueryCache(
            enabled=settings.ENABLE_QUERY_CACHING,
            use_redis=use_redis,
            redis_url=settings.REDIS_URL,
        )
    return _query_cache


def set_query_cache(cache: QueryCache) -> None:
    """Set the global query cache instance."""
    global _query_cache
    _query_cache = cache


# Cache invalidation utilities and patterns

async def _invalidate_operation(
    cache: QueryCache,
    prefix: str,
    operation: str,
    invalidate_list: bool = True,
    *args,
    **kwargs,
) -> int:
    """
    Internal helper for cache invalidation operations.
    
    Consolidates the common pattern used by create/update/delete operations.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix to invalidate
        operation: Operation type ("create", "update", "delete")
        invalidate_list: Whether to also invalidate list cache
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
    
    Returns:
        Number of entries invalidated
    """
    count = 0
    
    # Invalidate specific entry if args/kwargs provided
    if args or kwargs:
        deleted = await cache.delete(prefix, *args, **kwargs)
        if deleted:
            count += 1
    
    # Invalidate list cache if requested
    if invalidate_list:
        pattern = f"query_cache:{prefix}:*"
        pattern_count = await cache.invalidate_pattern(pattern)
        count += pattern_count
    
    return count


async def cache_aside(
    cache: QueryCache,
    prefix: str,
    fetch_func: Callable[..., Awaitable[Any]],
    ttl: Optional[int] = None,
    *args,
    **kwargs,
) -> Any:
    """
    Cache-aside pattern helper.
    
    Implements the cache-aside pattern: check cache first, if miss then
    fetch from source and cache the result.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix
        fetch_func: Async function to fetch data if cache miss
        ttl: Optional TTL override (uses default if None)
        *args: Positional arguments for key generation and fetch_func
        **kwargs: Keyword arguments for key generation and fetch_func
        
    Returns:
        Cached or freshly fetched value
        
    Example:
        async def get_user(user_id: int):
            return await cache_aside(
                cache,
                "user",
                fetch_user_from_db,
                user_id=user_id
            )
    """
    # Try cache first
    cached = await cache.get(prefix, *args, **kwargs)
    if cached is not None:
        return cached
    
    # Cache miss: fetch from source
    value = await fetch_func(*args, **kwargs)
    
    # Cache the result
    await cache.set(prefix, value, ttl=ttl, *args, **kwargs)
    
    return value


async def invalidate_pattern_safe(
    cache: QueryCache,
    pattern: str,
) -> int:
    """
    Safely invalidate cache entries matching a pattern.
    
    Wrapper around cache.invalidate_pattern with better error handling
    and logging for common invalidation scenarios.
    
    Args:
        cache: QueryCache instance
        pattern: Cache key pattern (e.g., "query_cache:contacts:*")
        
    Returns:
        Number of entries invalidated
        
    Example:
        # Invalidate all contact-related cache entries
        await invalidate_pattern_safe(cache, "query_cache:contacts:*")
    """
    try:
        count = await cache.invalidate_pattern(pattern)
        return count
    except Exception as exc:
        return 0


def create_invalidation_decorator(cache: QueryCache, prefix: str):
    """
    Create a decorator that automatically invalidates cache after function execution.
    
    Useful for update/delete operations that should invalidate related cache entries.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix to invalidate
        
    Returns:
        Decorator function
        
    Example:
        invalidate_user_cache = create_invalidation_decorator(cache, "user")
        
        @invalidate_user_cache(user_id=kwargs.get("user_id"))
        async def update_user(user_id: int, data: dict):
            return await db.update_user(user_id, data)
    """
    def decorator(*args, **kwargs):
        async def wrapper(func):
            result = await func(*args, **kwargs)
            # Extract key arguments from function call
            await invalidate_on_update(cache, prefix, *args, **kwargs)
            return result
        return wrapper
    return decorator


# Enhanced invalidation patterns

class CacheInvalidationEvent:
    """Event for cache invalidation with metadata."""
    
    def __init__(
        self,
        prefix: str,
        pattern: Optional[str] = None,
        reason: str = "manual",
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.prefix = prefix
        self.pattern = pattern
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = time.time()


# Event-driven invalidation registry
_invalidation_handlers: dict[str, list[Callable[[CacheInvalidationEvent], Awaitable[None]]]] = {}


def register_invalidation_handler(
    prefix: str,
    handler: Callable[[CacheInvalidationEvent], Awaitable[None]],
) -> None:
    """
    Register a handler for cache invalidation events.
    
    Useful for implementing complex invalidation logic, logging, or notifications.
    
    Args:
        prefix: Cache prefix to listen for
        handler: Async function that handles invalidation events
        
    Example:
        async def log_invalidation(event: CacheInvalidationEvent):
            pass  # Handle invalidation event
        
        register_invalidation_handler("user", log_invalidation)
    """
    if prefix not in _invalidation_handlers:
        _invalidation_handlers[prefix] = []
    _invalidation_handlers[prefix].append(handler)


async def invalidate_with_event(
    cache: QueryCache,
    prefix: str,
    pattern: Optional[str] = None,
    reason: str = "manual",
    metadata: Optional[dict[str, Any]] = None,
    *args,
    **kwargs,
) -> int:
    """
    Invalidate cache entries and trigger registered event handlers.
    
    This provides event-driven cache invalidation with extensibility for
    logging, notifications, or complex invalidation logic.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix to invalidate
        pattern: Optional pattern for pattern-based invalidation
        reason: Reason for invalidation (for logging/auditing)
        metadata: Optional metadata to pass to handlers
        *args: Positional arguments for key generation (if pattern is None)
        **kwargs: Keyword arguments for key generation (if pattern is None)
        
    Returns:
        Number of entries invalidated
        
    Example:
        # Invalidate specific entry with event
        await invalidate_with_event(
            cache,
            "user",
            reason="user_updated",
            metadata={"user_id": 123},
            user_id=123
        )
        
        # Invalidate pattern with event
        await invalidate_with_event(
            cache,
            "contacts",
            pattern="query_cache:contacts:*",
            reason="bulk_update"
        )
    """
    # Create invalidation event
    event = CacheInvalidationEvent(
        prefix=prefix,
        pattern=pattern,
        reason=reason,
        metadata=metadata or {},
    )
    
    # Perform invalidation
    if pattern:
        count = await cache.invalidate_pattern(pattern)
    else:
        deleted = await cache.delete(prefix, *args, **kwargs)
        count = 1 if deleted else 0
    
    # Trigger registered handlers
    handlers = _invalidation_handlers.get(prefix, [])
    for handler in handlers:
        try:
            await handler(event)
        except Exception as exc:
            pass  # Handler error is non-critical
    
    return count


async def invalidate_on_create(
    cache: QueryCache,
    prefix: str,
    *args,
    **kwargs,
) -> None:
    """
    Invalidate cache after a create operation.
    
    Typically invalidates list/collection caches since a new item was added.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix (usually collection name)
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
    
    Example:
        # After creating a contact, invalidate contact list cache
        await create_contact(session, data)
        await invalidate_on_create(cache, "contacts")
    """
    await _invalidate_operation(cache, prefix, "create", invalidate_list=True, *args, **kwargs)


async def invalidate_on_update(
    cache: QueryCache,
    prefix: str,
    *args,
    **kwargs,
) -> bool:
    """
    Invalidate cache entry after an update operation.
    
    This is a helper for event-driven cache invalidation pattern.
    Call this after updating data to ensure cache consistency.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix to invalidate
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
        
    Returns:
        True if invalidation was successful
        
    Example:
        # After updating a user
        await update_user_in_db(user_id, data)
        await invalidate_on_update(cache, "user", user_id=user_id)
    """
    count = await _invalidate_operation(cache, prefix, "update", invalidate_list=True, *args, **kwargs)
    return count > 0


async def invalidate_on_delete(
    cache: QueryCache,
    prefix: str,
    *args,
    **kwargs,
) -> None:
    """
    Invalidate cache after a delete operation.
    
    Invalidates both the specific item cache and collection caches.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
    
    Example:
        # After deleting a contact
        await delete_contact(session, contact_id)
        await invalidate_on_delete(cache, "contacts")
    """
    await _invalidate_operation(cache, prefix, "delete", invalidate_list=True, *args, **kwargs)


# Cache warming utilities

async def warm_cache_entry(
    cache: QueryCache,
    prefix: str,
    fetch_func: Callable[..., Awaitable[Any]],
    ttl: Optional[int] = None,
    *args,
    **kwargs,
) -> Any:
    """
    Warm a cache entry by fetching and caching data.
    
    Useful for pre-populating cache during startup or after invalidation.
    
    Args:
        cache: QueryCache instance
        prefix: Cache key prefix
        fetch_func: Async function to fetch data
        ttl: Optional TTL override
        *args: Positional arguments for key generation and fetch_func
        **kwargs: Keyword arguments for key generation and fetch_func
        
    Returns:
        Cached value
        
    Example:
        # Warm cache on startup
        await warm_cache_entry(
            cache,
            "popular_contacts",
            fetch_popular_contacts,
            limit=100
        )
    """
    value = await fetch_func(*args, **kwargs)
    await cache.set(prefix, value, ttl=ttl, *args, **kwargs)
    return value


async def warm_cache_batch(
    cache: QueryCache,
    warming_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Warm multiple cache entries in batch.
    
    Args:
        cache: QueryCache instance
        warming_tasks: List of dicts with keys: prefix, fetch_func, ttl (optional), args, kwargs
        
    Returns:
        Dictionary with warming results (successful, failed counts)
        
    Example:
        tasks = [
            {
                "prefix": "popular_contacts",
                "fetch_func": fetch_popular_contacts,
                "kwargs": {"limit": 100}
            },
            {
                "prefix": "active_companies",
                "fetch_func": fetch_active_companies,
                "ttl": 600
            }
        ]
        results = await warm_cache_batch(cache, tasks)
    """
    successful = 0
    failed = 0
    errors = []
    
    for task in warming_tasks:
        try:
            prefix = task["prefix"]
            fetch_func = task["fetch_func"]
            ttl = task.get("ttl")
            args = task.get("args", [])
            kwargs = task.get("kwargs", {})
            
            await warm_cache_entry(cache, prefix, fetch_func, ttl, *args, **kwargs)
            successful += 1
        except Exception as exc:
            failed += 1
            errors.append({"prefix": task.get("prefix", "unknown"), "error": str(exc)})
    
    result = {
        "successful": successful,
        "failed": failed,
        "total": len(warming_tasks),
        "errors": errors,
    }
    
    return result
