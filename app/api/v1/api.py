"""Aggregate API routers for version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import bulk, companies, contacts, imports, root

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(contacts.router)
api_router.include_router(companies.router)
api_router.include_router(imports.router)
api_router.include_router(bulk.router)

