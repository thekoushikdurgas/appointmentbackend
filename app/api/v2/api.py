"""Aggregate API routers for version 2 endpoints."""

from fastapi import APIRouter

from app.api.v2.endpoints import ai_chats, apollo, auth, billing, email, exports, gemini, linkedin, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(ai_chats.router)
api_router.include_router(apollo.router)
api_router.include_router(exports.router, prefix="/exports")
api_router.include_router(linkedin.router)
api_router.include_router(email.router)
api_router.include_router(billing.router)
api_router.include_router(gemini.router)

