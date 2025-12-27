"""Aggregate API routers for version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    billing,
    health,
    root,
    usage,
    users,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(billing.router)
api_router.include_router(usage.router)
api_router.include_router(health.router)

