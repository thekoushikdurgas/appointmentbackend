"""FastAPI application entry point and middleware configuration."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.middleware import LoggingMiddleware, TimingMiddleware


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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],
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
    logger.info("Health check response: status=%s environment=%s", payload["status"], payload["environment"])
    logger.debug("Exiting health_check payload=%s", payload)
    return payload


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

