"""Custom FastAPI middleware for structured request logging and timing."""

import json
import time
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.utils.logger import get_logger, log_api_request, log_performance_issue

settings = get_settings()
logger = get_logger(__name__)


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
            logger.warning(
                "Invalid host header rejected",
                extra={
                    "context": {
                        "host": host,
                        "allowed_hosts": list(self.allowed_hosts),
                        "path": request.url.path,
                        "method": request.method,
                    }
                }
            )
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
            logger.warning(
                "Invalid path pattern rejected",
                extra={
                    "context": {
                        "path": path_candidate,
                        "method": request.method,
                    }
                }
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

        response = await call_next(request)
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Process-Time header with request duration and logs request/response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Measure request processing duration and add to response headers."""
        start_time = time.perf_counter()
        
        # Extract request context
        request_id = request.headers.get("X-Request-Id")
        method = request.method
        path = request.url.path
        
        # Get user ID from request state if available (set by auth middleware)
        user_id = getattr(request.state, "user_id", None) if hasattr(request.state, "user_id") else None
        
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.headers["X-Process-Time"] = f"{duration_ms/1000:.6f}"
            
            # Log API request
            log_api_request(
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
            )
            
            # Log performance issues for slow endpoints
            if duration_ms > 1000.0:  # 1 second threshold
                log_performance_issue(
                    endpoint=path,
                    method=method,
                    duration_ms=duration_ms,
                    status_code=response.status_code,
                    user_id=user_id,
                    request_id=request_id,
                )
            
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path}",
                exc_info=True,
                extra={
                    "context": {
                        "method": method,
                        "path": path,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                    "request_id": request_id,
                    "user_id": user_id,
                    "performance": {"duration_ms": duration_ms},
                }
            )
            raise


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Echoes X-Request-Id header from request to response if provided."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Echo X-Request-Id header in response if present in request."""
        request_id = request.headers.get("X-Request-Id")
        response = await call_next(request)
        if request_id:
            response.headers["X-Request-Id"] = request_id
        return response
