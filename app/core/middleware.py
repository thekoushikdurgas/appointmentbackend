"""Custom FastAPI middleware for structured request logging and timing."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests and outgoing responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request entry and exit details."""
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

