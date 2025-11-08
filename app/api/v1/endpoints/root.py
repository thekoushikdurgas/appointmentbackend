from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": settings.DOCS_URL or "/docs",
    }

