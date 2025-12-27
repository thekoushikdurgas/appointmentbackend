"""Aggregate API routers for version 3 endpoints."""

from fastapi import APIRouter

from app.api.v3.endpoints import (
    activities,
    companies,
    contacts,
    email,
    exports,
    linkedin,
    s3,
    sales_navigator,
    upload,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
api_router = APIRouter()
api_router.include_router(companies.router)
api_router.include_router(contacts.router)
api_router.include_router(email.router)
api_router.include_router(exports.router, prefix="/exports")
api_router.include_router(linkedin.router)
api_router.include_router(activities.router)
api_router.include_router(s3.router)
api_router.include_router(sales_navigator.router)
api_router.include_router(upload.router)

