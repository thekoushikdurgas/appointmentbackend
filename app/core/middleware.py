"""Custom FastAPI middleware for structured request logging and timing."""

import time
from typing import Callable

from fastapi import Request, Response, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()


class CORSFriendlyTrustedHostMiddleware(BaseHTTPMiddleware):
    """
    TrustedHostMiddleware that allows OPTIONS requests to pass through.
    
    This ensures CORS preflight requests are not blocked by host validation,
    allowing CORS middleware to properly handle them.
    """

    def __init__(self, app, allowed_hosts):
        """Initialize the middleware with allowed hosts."""
        super().__init__(app)
        self.allowed_hosts = set(allowed_hosts) if allowed_hosts else None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch request, bypassing host validation for OPTIONS and WebSocket upgrade requests.
        
        OPTIONS requests (CORS preflight) are allowed through without host validation
        so that CORS middleware can add proper headers.
        WebSocket upgrade requests are also allowed through to enable WebSocket connections.
        """
        # Allow OPTIONS requests to bypass host validation for CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Allow WebSocket upgrade requests to bypass host validation
        upgrade_header = request.headers.get("upgrade", "").lower()
        if upgrade_header == "websocket":
            return await call_next(request)
        
        # For non-OPTIONS requests, apply host validation
        if self.allowed_hosts is None:
            return await call_next(request)
        
        # Get the host from the request
        host = request.headers.get("host", "").split(":")[0]
        
        # Check if host is in allowed hosts
        if host not in self.allowed_hosts:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid host header: {host}"},
            )
        
        return await call_next(request)


class PathValidationMiddleware(BaseHTTPMiddleware):
    """Validates request paths and handles special cases."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request path and handle special cases."""
        raw_path_value = request.scope.get("raw_path")
        if isinstance(raw_path_value, (bytes, bytearray)):
            raw_path = raw_path_value.decode("latin-1", errors="ignore")
        elif raw_path_value:
            raw_path = str(raw_path_value)
        else:
            raw_path = request.url.path
        scope_path = request.scope.get("path") or raw_path
        path_candidate = raw_path.split("?", 1)[0]
        if not path_candidate.startswith("/"):
            path_candidate = f"/{path_candidate}"
        if path_candidate.startswith("/api/v1/contacts//"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

        response = await call_next(request)
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Process-Time header with request duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Measure request processing duration and add to response headers."""
        start_time = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{duration:.6f}"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Echoes X-Request-Id header from request to response if provided."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Echo X-Request-Id header in response if present in request."""
        request_id = request.headers.get("X-Request-Id")
        response = await call_next(request)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response
