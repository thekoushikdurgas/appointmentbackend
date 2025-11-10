"""FastAPI application entry point and middleware configuration."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware  # type: ignore[import-not-found]

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.middleware import LoggingMiddleware, TimingMiddleware


settings = get_settings()
logger = get_logger(__name__)

_DEPLOYMENT_HOST = "54.221.83.239"
_PROXY_TRUSTED_IPS: tuple[str, ...] = ("127.0.0.1", _DEPLOYMENT_HOST)


def _compute_trusted_hosts() -> set[str]:
    """Build the trusted host list including the deployment reverse proxy host."""
    configured_hosts = {host.strip() for host in settings.TRUSTED_HOSTS if host.strip()}
    if settings.ENVIRONMENT == "production":
        configured_hosts.add(_DEPLOYMENT_HOST)
    configured_hosts.discard("*")
    return configured_hosts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Configures logging, prepares directories, and will later initialize external resources.
    """
    logger.debug("Entering lifespan startup")
    setup_logging()
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(
        "Runtime configuration: environment=%s version=%s trusted_hosts=%s proxy_trusted_ips=%s cors_origins=%s",
        settings.ENVIRONMENT,
        settings.VERSION,
        sorted(trusted_hosts) if trusted_hosts else ["*"],
        _PROXY_TRUSTED_IPS,
        [str(origin) for origin in settings.ALLOWED_ORIGINS],
    )
    logger.info("Application startup complete: project=%s version=%s", settings.PROJECT_NAME, settings.VERSION)
    yield
    logger.info("Application shutdown initiated: project=%s", settings.PROJECT_NAME)
    logger.debug("Exiting lifespan cleanup")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    lifespan=lifespan,
    servers=[
        {"url": "https://54.221.83.239", "description": "Production (NGINX reverse proxy)"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ],
)

app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=list(_PROXY_TRUSTED_IPS),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

trusted_hosts = _compute_trusted_hosts()
if trusted_hosts and (settings.ENVIRONMENT == "production" or settings.TRUSTED_HOSTS != ["*"]):
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=sorted(trusted_hosts),
    )

app.add_middleware(LoggingMiddleware)
app.add_middleware(TimingMiddleware)


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


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint used during scaffolding."""
    logger.debug("Entering health_check")
    payload = {"status": "healthy", "environment": settings.ENVIRONMENT}
    payload.update(
        {
            "version": settings.VERSION,
            "trusted_hosts": sorted(trusted_hosts) if trusted_hosts else ["*"],
            "proxy_trusted_ips": list(_PROXY_TRUSTED_IPS),
        }
    )
    logger.info("Health check response: status=%s environment=%s", payload["status"], payload["environment"])
    logger.debug("Exiting health_check payload=%s", payload)
    return payload


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/favicon.ico", status_code=204, include_in_schema=False)
async def favicon() -> Response:
    """Return an empty favicon response to silence browser requests."""
    return Response(status_code=204)


@app.get("/admin/", include_in_schema=False)
async def admin_placeholder() -> JSONResponse:
    """Present a placeholder admin endpoint to satisfy integration probes."""
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden"})

