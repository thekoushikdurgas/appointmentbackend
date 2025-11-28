"""Query result caching utilities for frequently accessed queries.

This module provides in-memory caching for query results to improve performance
for frequently accessed data. The cache is used by:
- Apollo analysis service (apollo_analysis_service.py)
- Apollo API endpoints (api/v2/endpoints/apollo.py)
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
from collections import OrderedDict
from typing import Any, Optional, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

settings = get_settings()


class CacheEntry:
    """Represents a cache entry with value and expiration timestamp."""

    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() > self.expires_at


class QueryCache:
    """In-memory query result cache for frequently accessed queries."""

    def __init__(self, enabled: bool = True):
        """
        Initialize query cache.
        
        Args:
            enabled: Whether caching is enabled. If False, caching is disabled.
        """
        self.enabled = enabled and settings.ENABLE_QUERY_CACHING
        self.default_ttl = settings.QUERY_CACHE_TTL
        self.logger = get_logger(__name__)
        # Use OrderedDict for LRU-like behavior and thread-safe access
        self._cache: dict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        # Cleanup expired entries periodically
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes

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

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.debug("Cleaned up %d expired cache entries", len(expired_keys))
            
            self._last_cleanup = current_time

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
            # Periodic cleanup
            await self._cleanup_expired()
            
            cache_key = self._generate_cache_key(prefix, *args, **kwargs)
            
            async with self._lock:
                entry = self._cache.get(cache_key)
                
                if entry is None:
                    self.logger.debug("Cache miss for key=%s", cache_key)
                    return None
                
                if entry.is_expired():
                    # Remove expired entry
                    del self._cache[cache_key]
                    self.logger.debug("Cache entry expired for key=%s", cache_key)
                    return None
                
                # Move to end (LRU behavior)
                self._cache.move_to_end(cache_key)
                self.logger.debug("Cache hit for key=%s", cache_key)
                return entry.value
                
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
            expires_at = time.time() + ttl
            
            async with self._lock:
                # Store entry (move to end if exists for LRU)
                self._cache[cache_key] = CacheEntry(value=value, expires_at=expires_at)
                self._cache.move_to_end(cache_key)
                
                # Limit cache size to prevent memory issues (keep last 1000 entries)
                if len(self._cache) > 1000:
                    # Remove oldest entry
                    self._cache.popitem(last=False)
            
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
            
            async with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self.logger.debug("Deleted cache key=%s", cache_key)
                    return True
                return False
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
            pattern_prefix = f"query_cache:{prefix}:"
            deleted = 0
            
            async with self._lock:
                keys_to_delete = [
                    key for key in self._cache.keys() if key.startswith(pattern_prefix)
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                    deleted += 1
            
            if deleted > 0:
                self.logger.debug("Cleared %d cache entries with prefix=%s", deleted, prefix)
            return deleted
        except Exception as exc:
            self.logger.warning("Error clearing cache prefix: %s", exc)
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

        try:
            # Convert Redis-style pattern to simple matching
            # Replace * with .* for regex, but we'll use simple string matching
            pattern_prefix = pattern.replace("*", "")
            deleted = 0
            
            async with self._lock:
                keys_to_delete = [
                    key for key in self._cache.keys() if pattern_prefix in key
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                    deleted += 1
            
            if deleted > 0:
                self.logger.debug("Invalidated %d cache entries matching pattern=%s", deleted, pattern)
            return deleted
        except Exception as exc:
            self.logger.warning("Error invalidating cache pattern: %s", exc)
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled:
            return {"enabled": False}
        
        # Count non-expired entries
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self._cache.values() if not entry.is_expired()
        )
        
        return {
            "enabled": True,
            "default_ttl": self.default_ttl,
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "max_entries": 1000,
        }


# Global cache instance (will be initialized during app startup)
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get the global query cache instance."""
    global _query_cache
    if _query_cache is None:
        # Initialize with caching enabled if ENABLE_QUERY_CACHING is True
        _query_cache = QueryCache(enabled=settings.ENABLE_QUERY_CACHING)
    return _query_cache


def set_query_cache(cache: QueryCache) -> None:
    """Set the global query cache instance."""
    global _query_cache
    _query_cache = cache

