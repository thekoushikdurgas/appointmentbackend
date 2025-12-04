"""Aggregate API routers for version 3 endpoints."""

from fastapi import APIRouter

from app.api.v3.endpoints import (
    analysis,
    cleanup,
    data_pipeline,
    email_pattern,
    s3,
    validation,
)

api_router = APIRouter()
api_router.include_router(s3.router)
api_router.include_router(cleanup.router)
api_router.include_router(email_pattern.router)
api_router.include_router(analysis.router)
api_router.include_router(validation.router)
api_router.include_router(data_pipeline.router)

