"""FastAPI application entry point and middleware configuration."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1.api import api_router
from app.api.v2.api import api_router as api_router_v2
from app.api.v3.api import api_router as api_router_v3
from app.api.v4.api import api_router as api_router_v4
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    CORSFriendlyTrustedHostMiddleware,
    LoggingMiddleware,
    RequestIdMiddleware,
    TimingMiddleware,
)
from app.utils.query_cache import QueryCache, get_query_cache, set_query_cache, warm_cache_batch
from app.utils.background_tasks import initialize_task_limiting, wait_for_active_tasks
from app.utils.cache_helpers import get_lru_cache_stats, clear_all_lru_caches
from app.utils.parallel_processing import get_thread_pool
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles


settings = get_settings()
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
        logger.debug("Cache warming skipped: caching is disabled")
        return
    
    if not settings.ENABLE_CACHE_WARMING:
        logger.debug("Cache warming skipped: ENABLE_CACHE_WARMING is False")
        return
    
    warming_queries = settings.CACHE_WARMING_QUERIES
    if not warming_queries:
        logger.debug("Cache warming skipped: no queries configured")
        return
    
    logger.info("Starting cache warming: queries=%d", len(warming_queries))
    warmed_count = 0
    failed_count = 0
    
    for query_key in warming_queries:
        try:
            # Query keys are in format "prefix:arg1:arg2" or just "prefix"
            # For now, we support simple prefix-based warming
            # More complex warming would require actual query execution
            parts = query_key.split(":")
            prefix = parts[0]
            
            # For now, we just ensure the cache is ready
            # Actual warming would require executing the queries
            # This is a placeholder for future implementation
            logger.debug("Cache warming query: %s", query_key)
            warmed_count += 1
        except Exception as exc:
            logger.warning("Failed to warm cache for query %s: %s", query_key, exc)
            failed_count += 1
    
    logger.info(
        "Cache warming completed: warmed=%d failed=%d total=%d",
        warmed_count,
        failed_count,
        len(warming_queries),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Configures logging, prepares directories, initializes query cache,
    and sets up background task management.
    """
    logger.debug("Entering lifespan startup")
    setup_logging()
    # Only create local directories if not using S3
    if not settings.S3_BUCKET_NAME:
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.UPLOAD_DIR, "avatars").mkdir(parents=True, exist_ok=True)
    
    # Initialize query cache (Redis or in-memory)
    use_redis = settings.ENABLE_REDIS_CACHE and settings.REDIS_URL is not None
    query_cache = QueryCache(
        enabled=settings.ENABLE_QUERY_CACHING,
        use_redis=use_redis,
        redis_url=settings.REDIS_URL,
    )
    set_query_cache(query_cache)
    if settings.ENABLE_QUERY_CACHING:
        if use_redis:
            logger.info("Query cache initialized and enabled (Redis backend)")
        else:
            logger.info("Query cache initialized and enabled (in-memory)")
    else:
        logger.info("Query cache initialized (disabled)")
    
    # Initialize background task rate limiting
    initialize_task_limiting()
    
    # Initialize parallel processing thread pool
    if settings.ENABLE_PARALLEL_PROCESSING:
        try:
            get_thread_pool()  # Initialize thread pool
            logger.info("Parallel processing thread pool initialized")
        except Exception as exc:
            logger.warning("Failed to initialize thread pool (non-critical): %s", exc, exc_info=True)
    
    # Warm cache if enabled
    if settings.ENABLE_CACHE_WARMING and settings.ENABLE_QUERY_CACHING:
        try:
            await warm_cache(query_cache)
        except Exception as exc:
            logger.warning("Cache warming failed (non-critical): %s", exc, exc_info=True)
    
    logger.info("Application startup complete: project=%s version=%s", settings.PROJECT_NAME, settings.VERSION)
    yield
    
    # Cleanup - graceful shutdown
    logger.info("Application shutdown initiated: project=%s", settings.PROJECT_NAME)
    
    # Wait for active background tasks to complete
    tasks_completed = await wait_for_active_tasks()
    if tasks_completed:
        logger.info("All background tasks completed during shutdown")
    else:
        logger.warning("Some background tasks did not complete during shutdown timeout")
    
    # Cleanup thread pool
    try:
        from app.utils.parallel_processing import _thread_pool
        if _thread_pool:
            _thread_pool.shutdown(wait=True)
            logger.info("Thread pool shutdown complete")
    except Exception as exc:
        logger.warning("Error shutting down thread pool: %s", exc)
    
    # Log cache statistics
    try:
        cache_stats = get_lru_cache_stats()
        if cache_stats:
            logger.info("LRU cache statistics: %s", cache_stats)
    except Exception as exc:
        logger.debug("Could not get cache stats: %s", exc)
    
    logger.debug("Exiting lifespan cleanup")


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
    logger.info("Response compression enabled (min_size=%d bytes)", settings.COMPRESSION_MIN_SIZE)

# HTTP Cache middleware (optional - can be added per-endpoint using decorators)
# Note: HTTP cache headers are added per-endpoint using @cache_response decorator
# from app.utils.http_cache import cache_response
if settings.ENABLE_HTTP_CACHE:
    logger.info("HTTP cache headers enabled (use @cache_response decorator on endpoints)")

# Add custom middleware first (these process requests last, responses first)
app.add_middleware(LoggingMiddleware)
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


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Translate application exceptions into JSON responses."""
    logger.warning(
        "Handling AppException path=%s status=%s code=%s",
        request.url.path,
        exc.status_code,
        exc.error_code,
    )
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )
    logger.debug(
        "AppException response built path=%s status=%s",
        request.url.path,
        exc.status_code,
    )
    return response


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
    
    logger.debug(
        "Handling OPTIONS preflight request: path=%s origin=%s allowed_origins=%s",
        full_path,
        origin,
        allowed_origins,
    )
    
    # Validate origin against allowed origins
    if origin and origin in allowed_origins:
        allow_origin = origin
        logger.debug("Origin allowed: %s", origin)
    elif not origin:
        # No origin header (same-origin request or non-browser client)
        # Use first allowed origin as fallback, or "*" if none configured
        allow_origin = str(allowed_origins[0]) if allowed_origins else "*"
        logger.debug("No origin header, using fallback origin: %s", allow_origin)
    else:
        # Origin not in allowed list - reject the preflight
        logger.warning("Origin not allowed: %s (allowed: %s)", origin, allowed_origins)
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
    logger.debug("Entering health_check")
    payload = {"status": "healthy", "environment": settings.ENVIRONMENT}
    logger.info("Health check response: status=%s environment=%s", payload["status"], payload["environment"])
    logger.debug("Exiting health_check payload=%s", payload)
    return payload


@app.get("/health/db", tags=["Health"])
async def database_health_check():
    """Database connection pool health check endpoint."""
    from app.db.session import check_pool_health
    
    logger.debug("Entering database_health_check")
    health = check_pool_health()
    logger.info(
        "Database health check: status=%s message=%s",
        health.get("status"),
        health.get("message"),
    )
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

