"""FastAPI application entry point and middleware configuration."""

import json
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1.api import api_router
from app.api.v2.api import api_router as api_router_v2
from app.api.v3.api import api_router as api_router_v3
from app.api.v4.api import api_router as api_router_v4
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging
from app.core.middleware import (
    CORSFriendlyTrustedHostMiddleware,
    PathValidationMiddleware,
    RequestIdMiddleware,
    TimingMiddleware,
)
from app.middleware.performance_monitor import PerformanceMonitorMiddleware
from app.db.session import check_pool_health
from app.utils.background_tasks import initialize_task_limiting, wait_for_active_tasks
from app.utils.cache_helpers import get_lru_cache_stats
from app.utils.logger import get_logger, log_error, log_api_error, get_validation_suggestion
from app.utils.parallel_processing import _thread_pool, get_thread_pool
from app.utils.query_cache import QueryCache, set_query_cache

settings = get_settings()

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


async def warm_cache(cache: QueryCache) -> None:
    """
    Warm the cache by pre-loading frequently accessed data.
    
    This function pre-populates the cache with data that is likely to be
    accessed soon after application startup, reducing cold-start latency.
    
    Best practices:
    - Only warm cache for truly frequently accessed, read-only data
    - Keep warming queries simple and fast
    - Use cache warming sparingly - it adds startup time
    - Consider using Redis for distributed cache warming
    
    Args:
        cache: QueryCache instance to warm
    """
    if not cache.enabled:
        # Cache warming skipped: caching is disabled
        return
    
    if not settings.ENABLE_CACHE_WARMING:
        # Cache warming skipped: ENABLE_CACHE_WARMING is False
        return
    
    warming_queries = settings.CACHE_WARMING_QUERIES
    if not warming_queries:
        # Cache warming skipped: no queries configured
        return
    
    # Process cache warming queries
    # Query keys are in format "prefix:arg1:arg2" or just "prefix"
    # For now, we support simple prefix-based warming
    # More complex warming would require actual query execution
    warmed_count = 0
    failed_count = 0
    
    for query_key in warming_queries:
        try:
            # Parse query key to extract prefix
            parts = query_key.split(":")
            prefix = parts[0]
            
            # For now, we just ensure the cache is ready
            # Actual warming would require executing the queries
            # This is a placeholder for future implementation
            warmed_count += 1
        except Exception as exc:
            # Failed to warm cache for query (non-critical error)
            failed_count += 1
            logger.debug(
                "Failed to warm cache for query",
                exc_info=True,
                extra={
                    "context": {
                        "query_key": query_key,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                }
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Prepares directories, initializes query cache,
    and sets up background task management.
    """
    logger.info("Application starting up")
    
    # Only create local directories if not using S3
    if not settings.S3_BUCKET_NAME:
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.UPLOAD_DIR, "avatars").mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created upload directories: {settings.UPLOAD_DIR}")
    
    # Initialize query cache (Redis or in-memory)
    use_redis = settings.ENABLE_REDIS_CACHE and settings.REDIS_URL is not None
    query_cache = QueryCache(
        enabled=settings.ENABLE_QUERY_CACHING,
        use_redis=use_redis,
        redis_url=settings.REDIS_URL,
    )
    set_query_cache(query_cache)
    logger.info(
        "Query cache initialized",
        extra={"context": {"enabled": settings.ENABLE_QUERY_CACHING, "use_redis": use_redis}}
    )
    
    # Initialize background task rate limiting
    initialize_task_limiting()
    logger.debug("Background task rate limiting initialized")
    
    # Initialize parallel processing thread pool
    if settings.ENABLE_PARALLEL_PROCESSING:
        try:
            get_thread_pool()  # Initialize thread pool
            logger.debug("Thread pool initialized")
        except Exception as exc:
            log_error("Failed to initialize thread pool", exc, "app.main")
    
    # Warm cache if enabled
    if settings.ENABLE_CACHE_WARMING and settings.ENABLE_QUERY_CACHING:
        try:
            await warm_cache(query_cache)
            logger.debug("Cache warming completed")
        except Exception as exc:
            log_error("Cache warming failed", exc, "app.main")
    
    # Log security configuration
    if settings.TRUSTED_HOSTS:
        logger.info(
            "Trusted hosts configured",
            extra={"context": {"trusted_hosts": settings.TRUSTED_HOSTS, "count": len(settings.TRUSTED_HOSTS)}}
        )
    else:
        logger.warning("No trusted hosts configured - all hosts will be accepted")
    
    logger.info("Application startup complete")
    
    # Application startup complete
    yield
    
    # Cleanup - graceful shutdown
    logger.info("Application shutting down")
    
    # Wait for active background tasks to complete
    tasks_completed = await wait_for_active_tasks()
    logger.info(
        "Background tasks completed",
        extra={"context": {"tasks_completed": tasks_completed}}
    )
    
    # Cleanup thread pool
    try:
        if _thread_pool:
            _thread_pool.shutdown(wait=True)
            logger.debug("Thread pool shutdown complete")
    except Exception as exc:
        log_error("Error shutting down thread pool", exc, "app.main")
    
    # Get cache statistics (for potential future use)
    try:
        cache_stats = get_lru_cache_stats()
        logger.debug("Cache statistics retrieved", extra={"context": cache_stats})
    except Exception as exc:
        log_error("Could not get cache stats", exc, "app.main")
    
    logger.info("Application shutdown complete")


docs_url = (
    settings.DOCS_URL
    if settings.DOCS_URL and (settings.DEBUG or settings.ENVIRONMENT != "production")
    else None
)
redoc_url = (
    settings.REDOC_URL
    if settings.REDOC_URL and (settings.DEBUG or settings.ENVIRONMENT != "production")
    else None
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    root_path=settings.ROOT_PATH or "",
    lifespan=lifespan,
)

# Add response compression middleware if enabled
# This should be early in the stack to compress responses
if settings.ENABLE_RESPONSE_COMPRESSION:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.COMPRESSION_MIN_SIZE,
    )

# Add custom middleware first (these process requests last, responses first)
app.add_middleware(PathValidationMiddleware)
app.add_middleware(PerformanceMonitorMiddleware, window_size=1000, log_interval=100)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIdMiddleware)

# Add security middleware
# Use CORS-friendly wrapper that allows OPTIONS requests to bypass host validation
if settings.USE_PROXY_HEADERS:
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=set(settings.TRUSTED_HOSTS) if settings.TRUSTED_HOSTS else None,
    )

if settings.TRUSTED_HOSTS:
    # Use custom middleware that allows OPTIONS requests for CORS preflight
    app.add_middleware(
        CORSFriendlyTrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )

# Add CORS middleware LAST so it processes requests FIRST (outermost layer)
# This ensures CORS headers are added even if other middleware might reject the request
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed logging."""
    request_id = request.headers.get("X-Request-Id")
    
    # Extract validation error details
    errors = exc.errors()
    failed_fields = []
    error_details = []
    sanitized_errors = []
    
    for error in errors:
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        error_msg = error.get("msg", "Validation error")
        input_value = error.get("input")
        
        failed_fields.append(field_path)
        suggestion = get_validation_suggestion(error_type, field_path)
        error_detail = {
            "field": field_path,
            "type": error_type,
            "message": error_msg,
            "input": str(input_value)[:100] if input_value is not None else None,  # Truncate long values
        }
        if suggestion:
            error_detail["suggestion"] = suggestion
        error_details.append(error_detail)
        
        # Create sanitized error for JSON response
        # Fix: Handle non-serializable objects in error dict
        suggestion = get_validation_suggestion(error_type, field_path)
        sanitized_error = {
            "type": error_type,
            "loc": error.get("loc", []),
            "msg": error_msg,
        }
        if suggestion:
            sanitized_error["suggestion"] = suggestion
        
        # Safely handle input value
        if input_value is not None:
            try:
                # Try to serialize to check if it's JSON serializable
                json.dumps(input_value)
                sanitized_error["input"] = input_value
            except (TypeError, ValueError):
                # Convert non-serializable objects to string
                sanitized_error["input"] = str(input_value)[:100]
        else:
            sanitized_error["input"] = None
        
        # Safely handle ctx field - may contain ValueError or other non-serializable objects
        ctx = error.get("ctx")
        if ctx:
            sanitized_ctx = {}
            for key, value in ctx.items():
                try:
                    # Try to serialize to check if it's JSON serializable
                    json.dumps(value)
                    sanitized_ctx[key] = value
                except (TypeError, ValueError):
                    # Convert non-serializable objects (like ValueError) to string
                    sanitized_ctx[key] = str(value)
            sanitized_error["ctx"] = sanitized_ctx
        
        # Add url if present
        if "url" in error:
            sanitized_error["url"] = error["url"]
        
        sanitized_errors.append(sanitized_error)
    
    # Extract client information for logging
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    
    # Try to read request body for logging (sanitized, truncated)
    request_body = None
    try:
        # Read body for 4xx errors to help debug client issues
        body = await request.body()
        if body:
            body_str = body.decode("utf-8", errors="replace")[:500]  # Truncate to 500 chars
            # Sanitize sensitive data - remove potential password/token fields
            sanitized_body = re.sub(
                r'"(?:password|token|secret|api[_-]?key|access[_-]?token)"\s*:\s*"[^"]*"',
                '"***REDACTED***": "***REDACTED***"',
                body_str,
                flags=re.IGNORECASE
            )
            request_body = sanitized_body
    except Exception:
        # Ignore errors reading body (non-critical for logging)
        pass
    
    # Log validation error with enhanced context
    logger.warning(
        f"Request validation failed: {len(errors)} error(s)",
        extra={
            "context": {
                "path": request.url.path,
                "method": request.method,
                "failed_fields": failed_fields,
                "error_count": len(errors),
                "error_details": error_details,
                "query_params": str(request.query_params)[:200] if request.query_params else None,
                "client_host": client_host,
                "user_agent": user_agent[:200] if user_agent else None,
                "referer": referer[:200] if referer else None,
                "request_body": request_body,  # Already sanitized and truncated
            },
            "request_id": request_id,
        }
    )
    
    # Return validation error response with sanitized errors
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": sanitized_errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with comprehensive logging."""
    request_id = request.headers.get("X-Request-Id")
    user_id = None
    
    # Extract user_id if available
    try:
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.uuid)
    except Exception:
        pass
    
    # Extract client information
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    
    # Try to read request body for 4xx/5xx errors (sanitized, truncated)
    request_body = None
    if exc.status_code >= 400:
        try:
            body = await request.body()
            if body:
                body_str = body.decode("utf-8", errors="replace")[:500]  # Truncate to 500 chars
                # Sanitize sensitive data
                sanitized_body = re.sub(
                    r'"(?:password|token|secret|api[_-]?key|access[_-]?token)"\s*:\s*"[^"]*"',
                    '"***REDACTED***": "***REDACTED***"',
                    body_str,
                    flags=re.IGNORECASE
                )
                request_body = sanitized_body
        except Exception:
            # Ignore errors reading body (non-critical for logging)
            pass
    
    log_api_error(
        endpoint=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        error_type="HTTPException",
        error_message=exc.detail,
        user_id=user_id,
        request_id=request_id,
        context={
            "query_params": str(request.query_params)[:200] if request.query_params else None,
            "client_host": client_host,
            "user_agent": user_agent[:200] if user_agent else None,
            "referer": referer[:200] if referer else None,
            "request_body": request_body,  # Already sanitized and truncated
        },
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Translate application exceptions into JSON responses."""
    request_id = request.headers.get("X-Request-Id")
    user_id = None
    
    # Extract user_id if available
    try:
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.uuid)
    except Exception:
        pass
    
    # Extract client information
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    
    # Try to read request body for 4xx/5xx errors (sanitized, truncated)
    request_body = None
    if exc.status_code >= 400:
        try:
            body = await request.body()
            if body:
                body_str = body.decode("utf-8", errors="replace")[:500]
                import re
                sanitized_body = re.sub(
                    r'"(?:password|token|secret|api[_-]?key|access[_-]?token)"\s*:\s*"[^"]*"',
                    '"***REDACTED***": "***REDACTED***"',
                    body_str,
                    flags=re.IGNORECASE
                )
                request_body = sanitized_body
        except Exception:
            pass
    
    log_api_error(
        endpoint=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        error_type=exc.error_code,
        error_message=exc.detail,
        user_id=user_id,
        request_id=request_id,
        context={
            "error_code": exc.error_code,
            "client_host": client_host,
            "user_agent": user_agent[:200] if user_agent else None,
            "referer": referer[:200] if referer else None,
            "request_body": request_body,
            "query_params": str(request.query_params)[:200] if request.query_params else None,
        },
    )
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler that logs all unhandled exceptions."""
    request_id = request.headers.get("X-Request-Id")
    user_id = None
    
    # Extract user_id if available
    try:
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.uuid)
    except Exception:
        pass
    
    # Extract client information
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    
    # Try to read request body for logging (sanitized, truncated)
    request_body = None
    try:
        body = await request.body()
        if body:
            body_str = body.decode("utf-8", errors="replace")[:500]
            import re
            sanitized_body = re.sub(
                r'"(?:password|token|secret|api[_-]?key|access[_-]?token)"\s*:\s*"[^"]*"',
                '"***REDACTED***": "***REDACTED***"',
                body_str,
                flags=re.IGNORECASE
            )
            request_body = sanitized_body
    except Exception:
        # Ignore errors reading body (non-critical for logging)
        pass
    
    # Log full error details with enhanced context
    log_error(
        f"Unhandled exception: {type(exc).__name__}",
        exc,
        "app.main",
        context={
            "path": request.url.path,
            "method": request.method,
            "query_params": str(request.query_params)[:200] if request.query_params else None,
            "client_host": client_host,
            "user_agent": user_agent[:200] if user_agent else None,
            "referer": referer[:200] if referer else None,
            "request_body": request_body,  # Already sanitized and truncated
            "user_id": user_id,
            "error_type": type(exc).__name__,
        },
        request_id=request_id,
    )
    
    # Return generic error response (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """
    Handle CORS preflight OPTIONS requests.
    
    This ensures that preflight requests receive proper CORS headers
    even if other middleware might interfere. The CORSMiddleware should
    handle this automatically, but this provides a fallback.
    """
    origin = request.headers.get("origin")
    allowed_origins = [str(o) for o in settings.ALLOWED_ORIGINS]
    
    # Validate origin against allowed origins
    if origin and origin in allowed_origins:
        allow_origin = origin
    elif not origin:
        # No origin header (same-origin request or non-browser client)
        # Use first allowed origin as fallback, or "*" if none configured
        allow_origin = str(allowed_origins[0]) if allowed_origins else "*"
    else:
        # Origin not in allowed list - reject the preflight
        return Response(
            status_code=403,
            headers={
                "Access-Control-Allow-Origin": "null",
            },
        )
    
    # Get requested method and headers from preflight request
    requested_method = request.headers.get("access-control-request-method", "*")
    requested_headers = request.headers.get("access-control-request-headers", "*")
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": requested_headers if requested_headers != "*" else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        },
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint used during scaffolding."""
    payload = {"status": "healthy", "environment": settings.ENVIRONMENT}
    return payload


@app.get("/health/db", tags=["Health"])
async def database_health_check():
    """Database connection pool health check endpoint."""
    health = check_pool_health()
    return health


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router_v2, prefix=settings.API_V2_PREFIX)
app.include_router(api_router_v3, prefix=settings.API_V3_PREFIX)
app.include_router(api_router_v4, prefix=settings.API_V4_PREFIX)

# Mount static files for media (avatars) only if not using S3
if not settings.S3_BUCKET_NAME:
    app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/favicon.ico", status_code=204, include_in_schema=False)
async def favicon() -> Response:
    """Return an empty favicon response to silence browser requests."""
    return Response(status_code=204)


@app.get("/admin/", include_in_schema=False)
async def admin_placeholder() -> JSONResponse:
    """Present a placeholder admin endpoint to satisfy integration probes."""
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden"})


# Catch-all GET handler to log unmatched routes and handle root
@app.get("/{full_path:path}")
async def catch_all_get_handler(request: Request, full_path: str):
    """Catch-all GET handler to log unmatched routes."""
    # Check if this is actually the root path
    if full_path == "" or full_path == "/" or (not full_path and request.url.path == "/"):
        # Return a simple root response
        settings = get_settings()
        return JSONResponse(content={
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": settings.DOCS_URL or "/docs",
        })
    # For other unmatched paths, let FastAPI return 404 naturally
    raise HTTPException(status_code=404, detail="Not Found")

