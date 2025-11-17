"""Aggregate API routers for version 1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import companies, companies_websocket, contacts, contacts_websocket, imports, root

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(contacts.router)
api_router.include_router(contacts_websocket.router)
api_router.include_router(companies.router)
api_router.include_router(companies_websocket.router)
api_router.include_router(imports.router)

