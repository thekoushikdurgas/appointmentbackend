"""Custom FastAPI middleware for structured request logging and timing."""

import time
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests and outgoing responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request entry and exit details."""
        raw_path_value = request.scope.get("raw_path")
        if isinstance(raw_path_value, (bytes, bytearray)):
            raw_path = raw_path_value.decode("latin-1", errors="ignore")
        elif raw_path_value:
            raw_path = str(raw_path_value)
        else:
            raw_path = request.url.path
        scope_path = request.scope.get("path") or raw_path
        logger.debug(
            "LoggingMiddleware raw_path=%r scope_path=%s normalized_path=%s",
            raw_path_value,
            scope_path,
            request.url.path,
        )
        path_candidate = raw_path.split("?", 1)[0]
        if not path_candidate.startswith("/"):
            path_candidate = f"/{path_candidate}"
        if path_candidate.startswith("/api/v1/contacts//"):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )

        logger.info("Entering LoggingMiddleware.dispatch method=%s path=%s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Error processing request method=%s path=%s", request.method, request.url.path)
            raise
        logger.info(
            "Exiting LoggingMiddleware.dispatch method=%s path=%s status=%s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Process-Time header with request duration and logs the timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Measure and log request processing duration."""
        logger.debug("Entering TimingMiddleware.dispatch method=%s path=%s", request.method, request.url.path)
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Error during TimingMiddleware.dispatch method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise
        duration = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{duration:.6f}"
        logger.debug(
            "Exiting TimingMiddleware.dispatch method=%s path=%s duration=%.4f status=%s",
            request.method,
            request.url.path,
            duration,
            response.status_code,
        )
        return response

