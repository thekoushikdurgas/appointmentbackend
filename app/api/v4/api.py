"""Aggregate API routers for version 4 endpoints."""

from fastapi import APIRouter

from app.api.v4.endpoints import (
    admin_dashboard_pages,
    admin_marketing,
    dashboard_pages,
    marketing,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
api_router = APIRouter()
api_router.include_router(marketing.router)
api_router.include_router(dashboard_pages.router)
api_router.include_router(admin_marketing.router)
api_router.include_router(admin_dashboard_pages.router)

