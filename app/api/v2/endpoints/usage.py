"""Usage tracking API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.usage_service import UsageService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/usage", tags=["Usage"])


class ResetUsageRequest(BaseModel):
    """Request to reset feature usage."""

    feature: str


class ResetUsageResponse(BaseModel):
    """Response for usage reset."""

    feature: str
    used: int
    limit: int
    success: bool


@router.post("/reset", response_model=ResetUsageResponse)
async def reset_usage(
    request: ResetUsageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResetUsageResponse:
    """
    Reset usage counter for a specific feature.
    
    Args:
        request: ResetUsageRequest with feature name
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        ResetUsageResponse with updated usage stats
    """
    try:
        service = UsageService()
        result = await service.reset_usage(
            session=session,
            user_id=str(current_user.uuid),
            feature=request.feature,
        )
        return ResetUsageResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset usage: {str(exc)}"
        ) from exc

