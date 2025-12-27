"""Aggregate API routers for version 2 endpoints."""

from fastapi import APIRouter

from app.api.v2.endpoints import (
    ai_chat_websocket,
    ai_chats,
    analytics,
    gemini,
    usage,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
api_router = APIRouter()
api_router.include_router(ai_chats.router)
api_router.include_router(ai_chat_websocket.router)  # WebSocket endpoints
api_router.include_router(analytics.router)
api_router.include_router(gemini.router)
api_router.include_router(usage.router)

