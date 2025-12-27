"""Feature usage tracking API endpoints."""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.usage import (
    TrackUsageRequest,
    TrackUsageResponse,
)
from app.services.usage_service import UsageService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/usage", tags=["Usage"])
service = UsageService()


@router.get("/current/")
async def get_current_usage(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Dict[str, int]]:
    """
    Get current feature usage for the authenticated user.
    
    Returns usage counts and limits for all features.
    Matches frontend expectation: Record<Feature, { used: number; limit: number }>
    """
    try:
        usage_data = await service.get_current_usage(session, current_user.uuid)
        # Return as dict directly to match frontend format
        return usage_data
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature usage"
        ) from exc


@router.post("/track/", response_model=TrackUsageResponse, status_code=status.HTTP_200_OK)
async def track_usage(
    request: TrackUsageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TrackUsageResponse:
    """
    Track feature usage for the authenticated user.
    
    Increments the usage count for the specified feature by the given amount.
    """
    try:
        result = await service.track_usage(
            session,
            current_user.uuid,
            request.feature,
            request.amount
        )
        return TrackUsageResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track feature usage"
        ) from exc

