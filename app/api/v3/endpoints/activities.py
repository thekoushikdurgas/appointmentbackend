"""User activities API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import ActivityActionType, ActivityServiceType, ActivityStatus, User
from app.repositories.user import UserActivityRepository
from app.schemas.user import ActivityStatsResponse, UserActivityItem, UserActivityListResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/activities", tags=["Activities"])
activity_repo = UserActivityRepository()


@router.get("/", response_model=UserActivityListResponse)
async def list_activities(
    service_type: Optional[str] = Query(None, description="Filter by service type: linkedin or email"),
    action_type: Optional[str] = Query(None, description="Filter by action type: search or export"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: success, failed, or partial"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserActivityListResponse:
    """
    Get the current user's activity history.
    
    Returns a paginated list of activities with optional filtering by:
    - service_type: linkedin or email
    - action_type: search or export
    - status: success, failed, or partial
    - start_date: Filter activities from this date onwards
    - end_date: Filter activities up to this date
    
    Results are ordered by created_at descending (most recent first).
    """
    try:
        # Parse enum filters
        service_type_enum = None
        if service_type:
            try:
                service_type_enum = ActivityServiceType(service_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid service_type: {service_type}. Must be 'linkedin' or 'email'",
                )
        
        action_type_enum = None
        if action_type:
            try:
                action_type_enum = ActivityActionType(action_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action_type: {action_type}. Must be 'search' or 'export'",
                )
        
        status_enum = None
        if status_filter:
            try:
                status_enum = ActivityStatus(status_filter.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Must be 'success', 'failed', or 'partial'",
                )
        
        # Get activities
        activities, total = await activity_repo.list_activities(
            session=session,
            user_id=current_user.uuid,
            service_type=service_type_enum,
            action_type=action_type_enum,
            status=status_enum,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        
        # Convert to response items
        items = [
            UserActivityItem(
                id=activity.id,
                user_id=activity.user_id,
                service_type=activity.service_type,
                action_type=activity.action_type,
                status=activity.status,
                request_params=activity.request_params,
                result_count=activity.result_count,
                result_summary=activity.result_summary,
                error_message=activity.error_message,
                ip_address=activity.ip_address,
                user_agent=activity.user_agent,
                created_at=activity.created_at,
            )
            for activity in activities
        ]
        
        return UserActivityListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activities",
        ) from exc


@router.get("/stats/", response_model=ActivityStatsResponse)
async def get_activity_stats(
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActivityStatsResponse:
    """
    Get activity statistics for the current user.
    
    Returns counts by:
    - service_type (linkedin, email)
    - action_type (search, export)
    - status (success, failed, partial)
    - recent_activities (last 24 hours)
    
    Optionally filtered by date range.
    """
    try:
        stats = await activity_repo.get_activity_stats(
            session=session,
            user_id=current_user.uuid,
            start_date=start_date,
            end_date=end_date,
        )
        
        return ActivityStatsResponse(**stats)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity statistics",
        ) from exc

