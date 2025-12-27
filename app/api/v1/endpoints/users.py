"""User profile API endpoints."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_super_admin
from app.core.constants import VALID_ROLES
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.repositories.user import UserProfileRepository, UserRepository
from app.repositories.user_scraping import UserScrapingRepository
from app.schemas.filters import UserFilterParams
from app.schemas.user import (
    AvatarUploadResponse,
    NotificationPreferences,
    ProfileResponse,
    ProfileUpdate,
    UpdateUserCreditsRequest,
    UpdateUserRoleRequest,
    UserHistoryListResponse,
    UserListItem,
    UserListResponse,
    UserStatsResponse,
)
from app.schemas.user_scraping import UserScrapingListResponse, UserScrapingResponse
from app.services.user_service import UserService, get_full_avatar_url
from app.utils.logger import get_logger, log_error
from app.utils.validation import is_valid_uuid

router = APIRouter(prefix="/users", tags=["Users"])
service = UserService()
logger = get_logger(__name__)


async def resolve_user_filters(request: Request) -> UserFilterParams:
    """Build user filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return UserFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/profile/", response_model=ProfileResponse)
async def get_profile(
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Get the profile information for the currently authenticated user.
    
    If a profile doesn't exist, it will be automatically created with default values.
    """
    # Get profile for authenticated user
    try:
        profile = await service.get_user_profile(session, current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to retrieve profile
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        ) from exc


@router.put("/profile/", response_model=ProfileResponse)
async def update_profile(
    update_data: ProfileUpdate,
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Update the profile information for the currently authenticated user.
    
    All fields are optional - only provided fields will be updated (partial update).
    The notifications field is merged with existing preferences, not replaced.
    """
    try:
        profile = await service.update_user_profile(session, current_user.uuid, update_data)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to update profile
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        ) from exc


@router.post("/profile/avatar/", response_model=AvatarUploadResponse)
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AvatarUploadResponse:
    """
    Upload an avatar image file for the currently authenticated user.
    
    The image will be stored in the media directory and the user's avatar_url will be updated automatically.
    
    File Requirements:
    - File Types: JPEG, PNG, GIF, or WebP
    - Maximum Size: 5MB
    - Validation: Both file extension and file content (magic bytes) are validated
    """
    # Validate Content-Type - must be multipart/form-data for file uploads
    # Reject JSON requests immediately
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"avatar": ["File upload requires multipart/form-data content type, not application/json"]}
        )
    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"avatar": ["File upload requires multipart/form-data content type"]}
        )
    
    # Validate that avatar file is provided and has a filename
    # FastAPI may create an empty UploadFile object when JSON is sent, so check both existence and filename
    if avatar is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"avatar": ["File is required"]}
        )
    
    # Check if filename exists and is not empty (catches empty UploadFile objects from JSON requests)
    if not avatar.filename or avatar.filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"avatar": ["File is required. Please upload a valid image file."]}
        )
    
    request_start_time = time.time()
    logger.info(
        "Avatar upload endpoint called",
        extra={
            "context": {
                "user_uuid": current_user.uuid,
                "has_avatar": avatar is not None,
                "content_type": avatar.content_type if avatar else None,
                "filename": avatar.filename if avatar else None,
                "file_size": getattr(avatar, 'size', None),
            },
            "request_id": request.headers.get("X-Request-Id"),
        }
    )
    try:
        avatar_url, profile = await service.upload_avatar(session, current_user.uuid, avatar)
        # Logging is handled in the service layer with appropriate levels
        
        request_duration_ms = (time.time() - request_start_time) * 1000
        logger.info(
            "Avatar upload endpoint completed successfully",
            extra={
                "context": {
                    "user_uuid": current_user.uuid,
                    "avatar_url": avatar_url,
                },
                "performance": {
                    "duration_ms": request_duration_ms,
                },
                "request_id": request.headers.get("X-Request-Id"),
            }
        )
        
        response = AvatarUploadResponse(
            avatar_url=avatar_url,
            profile=profile,
            message="Avatar uploaded successfully"
        )
        return response
    except HTTPException as http_exc:
        request_duration_ms = (time.time() - request_start_time) * 1000
        logger.warning(
            "Avatar upload endpoint failed with HTTP exception",
            extra={
                "context": {
                    "user_uuid": current_user.uuid,
                    "status_code": http_exc.status_code,
                    "detail": str(http_exc.detail),
                },
                "performance": {
                    "duration_ms": request_duration_ms,
                },
                "request_id": request.headers.get("X-Request-Id"),
            }
        )
        raise
    except Exception as exc:
        request_duration_ms = (time.time() - request_start_time) * 1000
        # Failed to upload avatar
        log_error(
            "Avatar upload endpoint failed with unexpected error",
            exc,
            "app.api.v1.endpoints.users",
            context={
                "user_uuid": current_user.uuid,
                "filename": avatar.filename if avatar else None,
                "request_duration_ms": request_duration_ms,
            },
            request_id=request.headers.get("X-Request-Id"),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(exc)}"
        ) from exc


@router.post("/promote-to-admin/", response_model=ProfileResponse)
async def promote_to_admin(
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Promote the currently authenticated user to admin role.
    
    This endpoint allows authenticated users to change their role to "Admin".
    The operation is logged for audit purposes.
    """
    try:
        profile = await service.promote_user_to_admin(session, current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to promote user to admin
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user to admin"
        ) from exc


@router.post("/promote-to-super-admin/", response_model=ProfileResponse)
async def promote_to_super_admin(
    user_id: str = Query(..., description="User ID to promote to super admin"),
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Promote a user to super admin role (Super Admin only).
    
    This endpoint allows super admins to promote any user to "SuperAdmin" role.
    The operation is logged for audit purposes.
    
    Requires:
    - Super Admin role for the requesting user
    - user_id query parameter specifying the target user
    """
    try:
        profile = await service.promote_user_to_super_admin(session, user_id)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to promote user to super admin
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user to super admin"
        ) from exc


# Super Admin Endpoints
@router.get("/", response_model=UserListResponse)
async def list_all_users(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    List all users (Super Admin only).
    
    Returns paginated list of all users with their profiles.
    """
    # List all users (Super Admin only)
    try:
        user_repo = UserRepository()
        profile_repo = UserProfileRepository()
        
        users, total = await user_repo.list_all_users(session, limit=limit, offset=offset)
        
        # Get profiles for all users
        user_list = []
        for user in users:
            profile = await profile_repo.get_by_user_id(session, user.uuid)
            user_list.append(UserListItem(
                uuid=user.uuid,
                email=user.email,
                name=user.name,
                role=profile.role if profile else None,
                credits=profile.credits if profile else 0,
                subscription_plan=profile.subscription_plan if profile else None,
                subscription_period=getattr(profile, 'subscription_period', None) if profile else None,
                subscription_status=profile.subscription_status if profile else None,
                is_active=user.is_active,
                created_at=user.created_at,
                last_sign_in_at=user.last_sign_in_at,
            ))
        
        return UserListResponse(users=user_list, total=total)
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to list users
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        ) from exc


@router.put("/{user_id}/role/", response_model=ProfileResponse)
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Update a user's role (Super Admin only).
    
    Valid roles: SuperAdmin, Admin, FreeUser, ProUser
    """
    # Update user role (Super Admin only)
    
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request.role}. Valid roles: {', '.join(VALID_ROLES)}"
        )
    
    try:
        profile_repo = UserProfileRepository()
        user_repo = UserRepository()
        
        user = await user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = await profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        await profile_repo.update_profile(session, profile, role=request.role)
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        
        return ProfileResponse(
            uuid=user.uuid,
            name=user.name,
            email=user.email,
            role=profile.role,
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to update user role
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        ) from exc


@router.put("/{user_id}/credits/", response_model=ProfileResponse)
async def update_user_credits(
    user_id: str,
    request: UpdateUserCreditsRequest,
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Update a user's credits (Super Admin only).
    """
    try:
        profile_repo = UserProfileRepository()
        user_repo = UserRepository()
        
        user = await user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = await profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        await profile_repo.update_profile(session, profile, credits=request.credits)
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        
        return ProfileResponse(
            uuid=user.uuid,
            name=user.name,
            email=user.email,
            role=profile.role,
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to update user credits
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user credits"
        ) from exc


@router.delete("/{user_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a user (Super Admin only).
    
    This will cascade delete the user's profile and all related data.
    """
    # Delete user (Super Admin only)
    if user_id == current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        user_repo = UserRepository()
        user = await user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await user_repo.delete_user(session, user)
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to delete user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        ) from exc


@router.get("/stats/", response_model=UserStatsResponse)
async def get_user_stats(
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserStatsResponse:
    """
    Get user statistics (Admin/Super Admin only).
    
    Returns aggregated statistics about users.
    """
    # Get user statistics (Admin/Super Admin only)
    try:
        # Check if user is admin or super admin
        profile_repo = UserProfileRepository()
        admin_profile = await profile_repo.get_by_user_id(session, current_user.uuid)
        if not admin_profile or admin_profile.role not in ["Admin", "SuperAdmin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or Super Admin role required"
            )
        
        # Get total users
        total_stmt = select(func.count(User.id))
        total_result = await session.execute(total_stmt)
        total_users = total_result.scalar_one()
        
        # Get active users
        active_stmt = select(func.count(User.id)).where(User.is_active == True)
        active_result = await session.execute(active_stmt)
        active_users = active_result.scalar_one()
        
        # Get users by role
        role_stmt = (
            select(UserProfile.role, func.count(UserProfile.id))
            .group_by(UserProfile.role)
        )
        role_result = await session.execute(role_stmt)
        users_by_role = {row[0] or "None": row[1] for row in role_result.all()}
        
        # Get users by plan
        plan_stmt = (
            select(UserProfile.subscription_plan, func.count(UserProfile.id))
            .group_by(UserProfile.subscription_plan)
        )
        plan_result = await session.execute(plan_stmt)
        users_by_plan = {row[0] or "free": row[1] for row in plan_result.all()}
        
        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            users_by_role=users_by_role,
            users_by_plan=users_by_plan,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to get user statistics
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        ) from exc


@router.get("/history/", response_model=UserHistoryListResponse)
async def get_user_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID (must be valid UUID format)"),
    event_type: Optional[str] = Query(None, description="Filter by event type (registration or login)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> UserHistoryListResponse:
    """
    Get user history records (Super Admin only).
    
    Returns paginated list of user registration and login events with IP geolocation data.
    Supports filtering by user_id (UUID format) and event_type.
    """
    # Get user history records (Super Admin only)
    # Validate user_id is a valid UUID format if provided
    if user_id is not None and not is_valid_uuid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a valid UUID format"
        )
    
    try:
        result = await service.get_user_history(
            session,
            user_id=user_id,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
        return UserHistoryListResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to retrieve user history
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user history"
        ) from exc


@router.get("/sales-navigator/list", response_model=UserScrapingListResponse)
async def list_user_scraping(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserScrapingListResponse:
    """
    List Sales Navigator scraping records for the authenticated user.
    
    Returns paginated list of scraping metadata records ordered by timestamp (newest first).
    Only returns records for the currently authenticated user.
    """
    # List Sales Navigator scraping records for authenticated user
    try:
        scraping_repo = UserScrapingRepository()
        scraping_records, total = await scraping_repo.list_by_user(
            session,
            user_id=current_user.uuid,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        items = [
            UserScrapingResponse(
                id=record.id,
                user_id=record.user_id,
                timestamp=record.timestamp,
                version=record.version,
                source=record.source,
                search_context=record.search_context,
                pagination=record.pagination,
                user_info=record.user_info,
                application_info=record.application_info,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            for record in scraping_records
        ]
        
        return UserScrapingListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to retrieve user scraping records
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user scraping records"
        ) from exc

