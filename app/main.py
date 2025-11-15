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
    TimingMiddleware,
)
from fastapi.staticfiles import StaticFiles


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Configures logging, prepares directories, and will later initialize external resources.
    """
    logger.debug("Entering lifespan startup")
    setup_logging()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR, "avatars").mkdir(parents=True, exist_ok=True)
    # logger.info("Application startup complete: project=%s version=%s", settings.PROJECT_NAME, settings.VERSION)
    yield
    # logger.info("Application shutdown initiated: project=%s", settings.PROJECT_NAME)
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

# Add custom middleware first (these process requests last, responses first)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TimingMiddleware)

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
    allow_origins=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:3000","http://127.0.0.1:8000","http://54.87.173.234","http://54.87.173.234:8000"],
    # allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["*"],
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
        allow_origin = "*"
        logger.debug("No origin header, allowing all origins")
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
    # logger.info("Health check response: status=%s environment=%s", payload["status"], payload["environment"])
    logger.debug("Exiting health_check payload=%s", payload)
    return payload


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router_v2, prefix=settings.API_V2_PREFIX)

# Mount static files for media (avatars)
app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/favicon.ico", status_code=204, include_in_schema=False)
async def favicon() -> Response:
    """Return an empty favicon response to silence browser requests."""
    return Response(status_code=204)


@app.get("/admin/", include_in_schema=False)
async def admin_placeholder() -> JSONResponse:
    """Present a placeholder admin endpoint to satisfy integration probes."""
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden"})

