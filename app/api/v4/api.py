"""Aggregate API routers for version 4 endpoints."""

from fastapi import APIRouter

from app.api.v4.endpoints import sales_navigator

api_router = APIRouter()
api_router.include_router(sales_navigator.router)

