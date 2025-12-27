"""Middleware for monitoring VQL query metrics."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VQLMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to track VQL query success/failure rates and performance."""

    def __init__(self, app):
        """Initialize the monitoring middleware."""
        super().__init__(app)
        self.vql_queries = 0
        self.vql_successes = 0
        self.vql_failures = 0
        self.vql_total_time = 0.0
        self.db_fallbacks = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track VQL metrics."""
        start_time = time.time()
        
        # Check if this is a VQL-enabled endpoint (including migration endpoints)
        is_vql_endpoint = (
            request.url.path.startswith("/api/v1/contacts") or
            request.url.path.startswith("/api/v1/companies") or
            request.url.path.startswith("/api/v2/linkedin")
        )
        
        response = await call_next(request)
        
        # Track metrics if VQL endpoint
        if is_vql_endpoint:
            duration = time.time() - start_time
            
            # Check response headers for VQL usage
            vql_used = response.headers.get("X-VQL-Used", "false") == "true"
            vql_fallback = response.headers.get("X-VQL-Fallback", "false") == "true"
            
            if vql_used:
                self.vql_queries += 1
                self.vql_successes += 1
                self.vql_total_time += duration
                logger.debug(
                    "VQL query successful",
                    extra={
                        "context": {
                            "path": request.url.path,
                            "method": request.method,
                        },
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
            elif vql_fallback:
                self.vql_queries += 1
                self.vql_failures += 1
                self.db_fallbacks += 1
                self.vql_total_time += duration
                logger.warning(
                    "VQL query failed, using database fallback",
                    extra={
                        "context": {
                            "path": request.url.path,
                            "method": request.method,
                            "status_code": response.status_code,
                        },
                        "performance": {"duration_ms": duration * 1000}
                    }
                )
        
        return response

    def get_stats(self) -> dict:
        """Get current VQL statistics."""
        avg_time = (
            self.vql_total_time / self.vql_queries
            if self.vql_queries > 0
            else 0.0
        )
        success_rate = (
            (self.vql_successes / self.vql_queries * 100)
            if self.vql_queries > 0
            else 0.0
        )
        
        return {
            "total_queries": self.vql_queries,
            "successes": self.vql_successes,
            "failures": self.vql_failures,
            "fallbacks": self.db_fallbacks,
            "average_time": avg_time,
            "success_rate": success_rate,
        }

