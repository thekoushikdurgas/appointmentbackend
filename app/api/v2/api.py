"""Aggregate API routers for version 2 endpoints."""

from fastapi import APIRouter

from app.api.v2.endpoints import ai_chats, apollo, apollo_websocket, auth, exports, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(ai_chats.router)
api_router.include_router(apollo.router)
api_router.include_router(apollo_websocket.router)
api_router.include_router(exports.router, prefix="/exports")

