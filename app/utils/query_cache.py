"""Query result caching utilities for frequently accessed queries."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

settings = get_settings()


class QueryCache:
    """Redis-based query result cache for frequently accessed queries."""

    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize query cache.
        
        Args:
            redis_client: Optional Redis client instance. If None, caching is disabled.
        """
        self.redis_client = redis_client
        self.default_ttl = settings.QUERY_CACHE_TTL
        self.logger = get_logger(__name__)
        self.enabled = redis_client is not None

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

        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            cached = await self.redis_client.get(cache_key)
            if cached:
                self.logger.debug("Cache hit for key=%s", cache_key)
                return json.loads(cached)
            self.logger.debug("Cache miss for key=%s", cache_key)
            return None
        except Exception as exc:
            self.logger.warning("Error reading from cache: %s", exc)
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

        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(cache_key, ttl, serialized)
            self.logger.debug("Cached result for key=%s ttl=%d", cache_key, ttl)
            return True
        except Exception as exc:
            self.logger.warning("Error writing to cache: %s", exc)
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

        try:
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            await self.redis_client.delete(cache_key)
            self.logger.debug("Deleted cache key=%s", cache_key)
            return True
        except Exception as exc:
            self.logger.warning("Error deleting from cache: %s", exc)
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

        try:
            pattern = f"query_cache:{prefix}:*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.logger.debug("Cleared %d cache entries with prefix=%s", deleted, prefix)
                return deleted
            return 0
        except Exception as exc:
            self.logger.warning("Error clearing cache prefix: %s", exc)
            return 0


# Global cache instance (will be initialized with Redis client if available)
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    global _query_cache
    if _query_cache is None:
        # Initialize with None (caching disabled) if Redis not available
        # In production, this should be initialized with a Redis client
        _query_cache = QueryCache()
    return _query_cache


def set_query_cache(cache: QueryCache) -> None:
    """Set the global query cache instance."""
    global _query_cache
    _query_cache = cache

