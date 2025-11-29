"""FastAPI application entry point and middleware configuration."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1.api import api_router
from app.api.v2.api import api_router as api_router_v2
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    CORSFriendlyTrustedHostMiddleware,
    LoggingMiddleware,
    RequestIdMiddleware,
    TimingMiddleware,
)
from app.utils.query_cache import QueryCache, set_query_cache
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Configures logging, prepares directories, and initializes query cache.
    """
    logger.debug("Entering lifespan startup")
    setup_logging()
    # Only create local directories if not using S3
    if not settings.S3_BUCKET_NAME:
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.UPLOAD_DIR, "avatars").mkdir(parents=True, exist_ok=True)
    
    # Initialize in-memory query cache
    query_cache = QueryCache(enabled=settings.ENABLE_QUERY_CACHING)
    set_query_cache(query_cache)
    if settings.ENABLE_QUERY_CACHING:
        logger.info("Query cache initialized and enabled (in-memory)")
    else:
        logger.info("Query cache initialized (disabled)")
    
    logger.info("Application startup complete: project=%s version=%s", settings.PROJECT_NAME, settings.VERSION)
    yield
    
    # Cleanup
    logger.info("Application shutdown initiated: project=%s", settings.PROJECT_NAME)
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


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router_v2, prefix=settings.API_V2_PREFIX)

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

