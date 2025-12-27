"""Root endpoints that expose API metadata."""

from fastapi import APIRouter, Depends, Request

from app.core.config import get_settings
from app.schemas.filters import RootFilterParams
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


async def resolve_root_filters(request: Request) -> RootFilterParams:
    """Build root filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return RootFilterParams.model_validate(data)
    except Exception:
        # Root filters are minimal, return empty params on validation error
        return RootFilterParams()


@router.get("/")
async def root(
    filters: RootFilterParams = Depends(resolve_root_filters),
) -> dict[str, str]:
    """Return a lightweight descriptor for the API."""
    logger.debug(
        "Root endpoint handler called",
        extra={"context": {"filters": str(filters)}}
    )
    settings = get_settings()
    payload = {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": settings.DOCS_URL or "/docs",
    }
    logger.debug(
        "Root endpoint returning payload",
        extra={"context": {"payload": payload}}
    )
    return payload


@router.get("/health/")
async def health(
    filters: RootFilterParams = Depends(resolve_root_filters),
) -> dict[str, str]:
    """Return a lightweight health payload for the versioned API."""
    settings = get_settings()
    payload = {"status": "healthy", "environment": settings.ENVIRONMENT}
    return payload
