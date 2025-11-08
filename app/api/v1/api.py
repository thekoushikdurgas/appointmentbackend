from fastapi import APIRouter

from app.api.v1.endpoints import contacts, imports, root

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(contacts.router)
api_router.include_router(imports.router)

