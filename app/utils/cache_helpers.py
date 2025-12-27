"""Cache helper utilities for immutable data using functools.lru_cache.

This module provides utilities for caching immutable, read-only data using
Python's built-in functools.lru_cache decorator. This is ideal for:
- Application settings and configuration
- ML model loading
- Static reference data
- Read-only database lookups that rarely change

Best practices:
- Use @lru_cache() for truly immutable data
- Use cachetools.TTLCache for data with expiration needs
- Use Redis for distributed caching across workers
- Clear cache on process restart (automatic with lru_cache)
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache, wraps
from typing import Any, Callable, Optional, TypeVar

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def lru_cache_with_key(
    maxsize: int = 128,
    typed: bool = False,
    key_func: Optional[Callable[..., str]] = None,
):
    """
    Create an LRU cache decorator with custom key generation.
    
    This is useful when you need to cache based on a subset of arguments
    or need custom key generation logic.
    
    Args:
        maxsize: Maximum number of entries in cache (None = unlimited)
        typed: If True, arguments of different types are cached separately
        key_func: Optional function to generate cache key from arguments
        
    Returns:
        Decorator function
        
    Example:
        @lru_cache_with_key(maxsize=100, key_func=lambda user_id, **kwargs: str(user_id))
        def get_user_settings(user_id: int, include_private: bool = False):
            # Only cache based on user_id, ignore include_private
            return fetch_user_settings(user_id, include_private)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if key_func is None:
            # Use standard lru_cache if no custom key function
            cached_func = lru_cache(maxsize=maxsize, typed=typed)(func)
        else:
            # Create wrapper with custom key generation
            cache: dict[str, T] = {}
            
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                cache_key = key_func(*args, **kwargs)
                if cache_key in cache:
                    return cache[cache_key]
                
                # Cache miss - call function
                result = func(*args, **kwargs)
                
                # Manage cache size (simple LRU by removing oldest if needed)
                if maxsize is not None and len(cache) >= maxsize:
                    # Remove first item (simple FIFO, not true LRU)
                    oldest_key = next(iter(cache))
                    del cache[oldest_key]
                
                cache[cache_key] = result
                return result
            
            # Add cache management methods
            wrapper.cache_info = lambda: {
                "hits": 0,  # Simplified - not tracking hits/misses
                "misses": 0,
                "maxsize": maxsize,
                "currsize": len(cache),
            }
            wrapper.cache_clear = lambda: cache.clear()
            
            return wrapper
        
        return cached_func
    
    return decorator


def hash_args(*args, **kwargs) -> str:
    """
    Generate a deterministic hash from function arguments.
    
    Useful for creating cache keys from complex arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        MD5 hash string of serialized arguments
    """
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items()) if kwargs else [],
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


# Example cached functions for immutable data

@lru_cache(maxsize=1)
def get_app_config_cached() -> dict[str, Any]:
    """
    Example: Cache application configuration.
    
    This is called once per process and cached for the lifetime of the process.
    Perfect use case for @lru_cache() since config rarely changes.
    """
    settings = get_settings()
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }


@lru_cache(maxsize=100)
def get_reference_data_cached(data_type: str) -> dict[str, Any]:
    """
    Example: Cache reference data lookups.
    
    Use this pattern for static reference data that doesn't change often.
    The cache persists for the process lifetime.
    """
    # This would typically fetch from database or file
    # For now, return empty dict as placeholder
    return {}


def clear_all_lru_caches() -> dict[str, int]:
    """
    Clear all lru_cache decorated functions.
    
    Returns:
        Dictionary mapping function names to cache sizes cleared
    """
    cleared = {}
    
    # Clear example caches
    if hasattr(get_app_config_cached, "cache_clear"):
        info = get_app_config_cached.cache_info()
        get_app_config_cached.cache_clear()
        cleared["get_app_config_cached"] = info.currsize if hasattr(info, "currsize") else 0
    
    if hasattr(get_reference_data_cached, "cache_clear"):
        info = get_reference_data_cached.cache_info()
        get_reference_data_cached.cache_clear()
        cleared["get_reference_data_cached"] = info.currsize if hasattr(info, "currsize") else 0
    
    return cleared


def get_lru_cache_stats() -> dict[str, Any]:
    """
    Get statistics for all lru_cache decorated functions.
    
    Returns:
        Dictionary with cache statistics
    """
    stats = {}
    
    # Get stats for example caches
    if hasattr(get_app_config_cached, "cache_info"):
        info = get_app_config_cached.cache_info()
        stats["get_app_config_cached"] = {
            "hits": info.hits if hasattr(info, "hits") else 0,
            "misses": info.misses if hasattr(info, "misses") else 0,
            "maxsize": info.maxsize if hasattr(info, "maxsize") else 1,
            "currsize": info.currsize if hasattr(info, "currsize") else 0,
        }
    
    if hasattr(get_reference_data_cached, "cache_info"):
        info = get_reference_data_cached.cache_info()
        stats["get_reference_data_cached"] = {
            "hits": info.hits if hasattr(info, "hits") else 0,
            "misses": info.misses if hasattr(info, "misses") else 0,
            "maxsize": info.maxsize if hasattr(info, "maxsize") else 100,
            "currsize": info.currsize if hasattr(info, "currsize") else 0,
        }
    
    return stats


# Decision guide for choosing caching strategy

CACHING_STRATEGY_GUIDE = """
When to use each caching strategy:

1. functools.lru_cache (@lru_cache):
   ✅ Use for:
   - Truly immutable, read-only data
   - Application settings and configuration
   - ML model loading (once per process)
   - Static reference data
   - Data that persists for process lifetime
   - Single-worker deployments
   
   ❌ Don't use for:
   - Data that needs TTL/expiration
   - Data that changes during runtime
   - Multi-worker deployments (each worker has separate cache)
   - Large datasets (>1GB per worker)
   - Data requiring distributed access

2. cachetools.TTLCache:
   ✅ Use for:
   - Data with time-based expiration needs
   - Frequently changing data with acceptable staleness
   - Single-worker deployments
   - Moderate cache sizes (<1GB per worker)
   
   ❌ Don't use for:
   - Multi-worker deployments (cache inconsistency)
   - Very large datasets
   - Data requiring guaranteed freshness

3. Redis (distributed cache):
   ✅ Use for:
   - Multi-worker/multi-server deployments
   - Shared mutable state across processes
   - Large cache sizes (>1GB)
   - Cache persistence requirements
   - Horizontal scaling scenarios
   - When cache consistency is critical
   
   ❌ Don't use for:
   - Single-worker deployments (overhead)
   - Very small datasets (network overhead)
   - Sub-millisecond latency requirements (network latency)

4. HTTP Cache Headers (ETag, Cache-Control):
   ✅ Use for:
   - Client-side caching
   - Reducing server load for static/semi-static data
   - API responses that don't change frequently
   - Reducing bandwidth usage
   
   ❌ Don't use for:
   - Highly dynamic data
   - Data requiring real-time updates
   - Sensitive data (unless carefully configured)
"""

