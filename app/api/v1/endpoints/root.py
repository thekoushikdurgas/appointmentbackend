"""Root endpoints that expose API metadata."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call


router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
@log_function_call(logger=logger, log_result=True)
async def root() -> dict[str, str]:
    """Return a lightweight descriptor for the API."""
    settings = get_settings()
    logger.info("Root endpoint requested: project=%s version=%s", settings.PROJECT_NAME, settings.VERSION)
    payload = {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": settings.DOCS_URL or "/docs",
    }
    logger.debug("Root endpoint payload prepared: docs=%s", payload["docs"])
    return payload

