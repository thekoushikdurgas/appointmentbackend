"""HTTP cache header utilities for FastAPI responses.

This module provides utilities for adding HTTP cache headers (ETag, Cache-Control)
to FastAPI responses, enabling client-side caching and reducing server load.

Best practices:
- Use ETag for content-based caching
- Use Cache-Control for time-based caching
- Support 304 Not Modified responses
- Set appropriate cache directives based on data sensitivity
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_etag(data: Any) -> str:
    """
    Generate an ETag from response data.
    
    Args:
        data: Response data (will be JSON serialized)
        
    Returns:
        ETag string (weak ETag with "W/" prefix)
    """
    try:
        # Serialize data to JSON for hashing
        if isinstance(data, (str, bytes)):
            content = data if isinstance(data, bytes) else data.encode()
        else:
            content = json.dumps(data, sort_keys=True, default=str).encode()
        
        # Generate MD5 hash
        etag_hash = hashlib.md5(content).hexdigest()
        # Use weak ETag (W/) for better cache hit rates with minor variations
        return f'W/"{etag_hash}"'
    except Exception as exc:
        logger.warning("Failed to generate ETag: %s", exc)
        # Fallback: use timestamp-based ETag
        return f'W/"{hash(str(datetime.now().timestamp()))}"'


def add_cache_headers(
    response: Response,
    max_age: int = 300,
    public: bool = True,
    must_revalidate: bool = False,
    etag: Optional[str] = None,
    last_modified: Optional[datetime] = None,
) -> Response:
    """
    Add HTTP cache headers to a response.
    
    Args:
        response: FastAPI Response object
        max_age: Maximum age in seconds (default: 5 minutes)
        public: If True, cache can be stored by any cache (default: True)
               If False, only private caches (browser) can store
        must_revalidate: If True, cache must revalidate with server before using stale data
        etag: Optional ETag value (will be generated from response body if not provided)
        last_modified: Optional Last-Modified timestamp
        
    Returns:
        Response with cache headers added
    """
    # Build Cache-Control header
    cache_control_parts = []
    
    if public:
        cache_control_parts.append("public")
    else:
        cache_control_parts.append("private")
    
    cache_control_parts.append(f"max-age={max_age}")
    
    if must_revalidate:
        cache_control_parts.append("must-revalidate")
    
    response.headers["Cache-Control"] = ", ".join(cache_control_parts)
    
    # Add ETag if provided
    if etag:
        response.headers["ETag"] = etag
    
    # Add Last-Modified if provided
    if last_modified:
        # Format according to HTTP spec (RFC 7231)
        response.headers["Last-Modified"] = last_modified.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    
    logger.debug(
        "Added cache headers: max_age=%d public=%s must_revalidate=%s etag=%s",
        max_age,
        public,
        must_revalidate,
        bool(etag),
    )
    
    return response


def check_cache_headers(request: Request, etag: Optional[str] = None) -> Optional[Response]:
    """
    Check if request has valid cache headers and return 304 Not Modified if appropriate.
    
    Args:
        request: FastAPI Request object
        etag: Current ETag value for the resource
        
    Returns:
        304 Response if cache is valid, None otherwise
    """
    if not etag:
        return None
    
    # Check If-None-Match header
    if_none_match = request.headers.get("If-None-Match")
    if if_none_match:
        # Handle weak ETags (W/") and multiple ETags
        request_etags = [e.strip().strip('"') for e in if_none_match.split(",")]
        current_etag = etag.strip().strip('W/').strip('"')
        
        # Check if any requested ETag matches current ETag
        for req_etag in request_etags:
            req_etag_clean = req_etag.strip().strip('W/').strip('"')
            if req_etag_clean == current_etag:
                logger.debug("Cache hit (304 Not Modified): etag=%s", etag)
                return Response(status_code=304, headers={"ETag": etag})
    
    # Check If-Modified-Since header
    if_modified_since = request.headers.get("If-Modified-Since")
    if if_modified_since:
        try:
            # Parse If-Modified-Since header
            modified_since = datetime.strptime(
                if_modified_since, "%a, %d %b %Y %H:%M:%S GMT"
            )
            # For now, we don't have last_modified, so skip this check
            # In real implementation, compare with resource's last_modified
        except (ValueError, TypeError):
            pass
    
    return None


def create_cached_response(
    data: Any,
    request: Request,
    max_age: int = 300,
    public: bool = True,
    must_revalidate: bool = False,
    last_modified: Optional[datetime] = None,
) -> Response:
    """
    Create a response with cache headers, checking for 304 Not Modified.
    
    This is a convenience function that:
    1. Generates ETag from data
    2. Checks if client has valid cache (returns 304 if so)
    3. Otherwise returns JSON response with cache headers
    
    Args:
        data: Response data
        request: FastAPI Request object
        max_age: Maximum age in seconds
        public: Whether cache is public
        must_revalidate: Whether cache must revalidate
        last_modified: Optional last modified timestamp
        
    Returns:
        Response (304 Not Modified or 200 OK with data)
    """
    # Generate ETag from data
    etag = generate_etag(data)
    
    # Check if client has valid cache
    not_modified_response = check_cache_headers(request, etag)
    if not_modified_response:
        return not_modified_response
    
    # Create JSON response
    response = JSONResponse(content=data)
    
    # Add cache headers
    add_cache_headers(
        response,
        max_age=max_age,
        public=public,
        must_revalidate=must_revalidate,
        etag=etag,
        last_modified=last_modified,
    )
    
    return response


def add_no_cache_headers(response: Response) -> Response:
    """
    Add headers to prevent caching (for sensitive/dynamic data).
    
    Args:
        response: FastAPI Response object
        
    Returns:
        Response with no-cache headers
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def add_cache_headers_for_static(
    response: Response,
    max_age: int = 31536000,  # 1 year for truly static content
) -> Response:
    """
    Add cache headers for static content (long-term caching).
    
    Args:
        response: FastAPI Response object
        max_age: Maximum age in seconds (default: 1 year)
        
    Returns:
        Response with static cache headers
    """
    return add_cache_headers(
        response,
        max_age=max_age,
        public=True,
        must_revalidate=False,
    )


def add_cache_headers_for_api(
    response: Response,
    max_age: int = 300,  # 5 minutes for API responses
    must_revalidate: bool = True,
) -> Response:
    """
    Add cache headers for API responses (short-term caching with revalidation).
    
    Args:
        response: FastAPI Response object
        max_age: Maximum age in seconds (default: 5 minutes)
        must_revalidate: Whether cache must revalidate (default: True)
        
    Returns:
        Response with API cache headers
    """
    return add_cache_headers(
        response,
        max_age=max_age,
        public=True,
        must_revalidate=must_revalidate,
    )


# Decorator for adding cache headers to endpoints

def cache_response(
    max_age: int = 300,
    public: bool = True,
    must_revalidate: bool = False,
):
    """
    Decorator to add cache headers to endpoint responses.
    
    Usage:
        @app.get("/data")
        @cache_response(max_age=600, must_revalidate=True)
        async def get_data():
            return {"data": "value"}
    
    Args:
        max_age: Maximum age in seconds
        public: Whether cache is public
        must_revalidate: Whether cache must revalidate
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")
            
            # Call original function
            result = await func(*args, **kwargs) if hasattr(func, "__call__") else func(*args, **kwargs)
            
            # If result is already a Response, add headers to it
            if isinstance(result, Response):
                add_cache_headers(
                    result,
                    max_age=max_age,
                    public=public,
                    must_revalidate=must_revalidate,
                )
                return result
            
            # If result is data, create cached response
            if request:
                return create_cached_response(
                    result,
                    request,
                    max_age=max_age,
                    public=public,
                    must_revalidate=must_revalidate,
                )
            
            # Fallback: create JSON response with cache headers
            response = JSONResponse(content=result)
            add_cache_headers(
                response,
                max_age=max_age,
                public=public,
                must_revalidate=must_revalidate,
            )
            return response
        
        return wrapper
    return decorator

