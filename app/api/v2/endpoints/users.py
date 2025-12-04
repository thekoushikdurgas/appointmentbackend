"""User profile API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_super_admin
from app.core.constants import VALID_ROLES
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserProfileRepository, UserRepository
from app.repositories.user_scraping import UserScrapingRepository
from app.schemas.filters import UserFilterParams
from app.schemas.user import (
    AvatarUploadResponse,
    ProfileResponse,
    ProfileUpdate,
    UpdateUserCreditsRequest,
    UpdateUserRoleRequest,
    UserHistoryListResponse,
    UserListResponse,
    UserListItem,
    UserStatsResponse,
)
from app.schemas.user_scraping import UserScrapingListResponse, UserScrapingResponse
from app.services.user_service import UserService
from app.utils.validation import is_valid_uuid

router = APIRouter(prefix="/users", tags=["Users"])
logger = get_logger(__name__)
service = UserService()


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
@log_function_call(logger=logger, log_result=True)
async def get_profile(
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """
    Get the profile information for the currently authenticated user.
    
    If a profile doesn't exist, it will be automatically created with default values.
    """
    logger.debug("Get profile request: user_uuid=%s", current_user.uuid)
    
    try:
        profile = await service.get_user_profile(session, current_user.uuid)
        logger.debug("Profile retrieved: user_uuid=%s", current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Get profile failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        ) from exc


@router.put("/profile/", response_model=ProfileResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Update profile request: user_uuid=%s fields=%s", current_user.uuid, list(update_data.model_dump(exclude_none=True).keys()))
    
    try:
        profile = await service.update_user_profile(session, current_user.uuid, update_data)
        logger.info("Profile updated: user_uuid=%s", current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Update profile failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        ) from exc


@router.post("/profile/avatar/", response_model=AvatarUploadResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def upload_avatar(
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
    logger.info("Avatar upload request: user_uuid=%s filename=%s", current_user.uuid, avatar.filename)
    
    try:
        avatar_url, profile = await service.upload_avatar(session, current_user.uuid, avatar)
        
        response = AvatarUploadResponse(
            avatar_url=avatar_url,
            profile=profile,
            message="Avatar uploaded successfully"
        )
        logger.info("Avatar uploaded: user_uuid=%s filename=%s", current_user.uuid, avatar.filename)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Avatar upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(exc)}"
        ) from exc


@router.post("/promote-to-admin/", response_model=ProfileResponse)
@log_function_call(logger=logger, log_result=True)
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
    logger.info("Promote to admin request: user_uuid=%s", current_user.uuid)
    
    try:
        profile = await service.promote_user_to_admin(session, current_user.uuid)
        logger.info("User promoted to admin: user_uuid=%s", current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Promote to admin failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user to admin"
        ) from exc


@router.post("/promote-to-super-admin/", response_model=ProfileResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Promote to super admin request: target_user_uuid=%s admin_id=%s", user_id, current_user.uuid)
    
    try:
        profile = await service.promote_user_to_super_admin(session, user_id)
        logger.info("User promoted to super admin: user_uuid=%s promoted_by=%s", user_id, current_user.uuid)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Promote to super admin failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user to super admin"
        ) from exc


# Super Admin Endpoints
@router.get("/", response_model=UserListResponse)
@log_function_call(logger=logger, log_result=True)
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
    logger.info("List all users request: user_uuid=%s limit=%d offset=%d", current_user.uuid, limit, offset)
    
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
        
        logger.info("Listed users: returned=%d total=%d", len(user_list), total)
        return UserListResponse(users=user_list, total=total)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("List all users failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        ) from exc


@router.put("/{user_id}/role/", response_model=ProfileResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Update user role request: user_uuid=%s new_role=%s admin_id=%s", 
               user_id, request.role, current_user.uuid)
    
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
        from app.services.user_service import get_full_avatar_url
        from app.schemas.user import NotificationPreferences
        notifications = profile.notifications or {}
        
        logger.info("User role updated: user_uuid=%s new_role=%s", user_id, request.role)
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
        logger.exception("Update user role failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        ) from exc


@router.put("/{user_id}/credits/", response_model=ProfileResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Update user credits request: user_uuid=%s new_credits=%d admin_id=%s", 
               user_id, request.credits, current_user.uuid)
    
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
        from app.services.user_service import get_full_avatar_url
        from app.schemas.user import NotificationPreferences
        notifications = profile.notifications or {}
        
        logger.info("User credits updated: user_uuid=%s new_credits=%d", user_id, request.credits)
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
        logger.exception("Update user credits failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user credits"
        ) from exc


@router.delete("/{user_id}/", status_code=status.HTTP_204_NO_CONTENT)
@log_function_call(logger=logger, log_result=True)
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
    logger.info("Delete user request: user_uuid=%s admin_id=%s", user_id, current_user.uuid)
    
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
        await session.commit()
        
        logger.info("User deleted: user_uuid=%s", user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Delete user failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        ) from exc


@router.get("/stats/", response_model=UserStatsResponse)
@log_function_call(logger=logger, log_result=True)
async def get_user_stats(
    filters: UserFilterParams = Depends(resolve_user_filters),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserStatsResponse:
    """
    Get user statistics (Admin/Super Admin only).
    
    Returns aggregated statistics about users.
    """
    logger.info("Get user stats request: user_uuid=%s", current_user.uuid)
    
    try:
        from sqlalchemy import func
        from app.models.user import User, UserProfile
        
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
        
        logger.info("User stats retrieved: total=%d active=%d", total_users, active_users)
        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            users_by_role=users_by_role,
            users_by_plan=users_by_plan,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Get user stats failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        ) from exc


@router.get("/history/", response_model=UserHistoryListResponse)
@log_function_call(logger=logger, log_result=True)
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
    logger.info("Get user history request: user_uuid=%s event_type=%s limit=%d offset=%d admin_id=%s",
               user_id, event_type, limit, offset, current_user.uuid)
    
    # Validate user_id is a valid UUID format if provided
    if user_id is not None and not is_valid_uuid(user_id):
        logger.warning("Invalid user_id format provided: %s", user_id)
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
        logger.info("User history retrieved: total=%d returned=%d", result["total"], len(result["items"]))
        return UserHistoryListResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Get user history failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user history"
        ) from exc


@router.get("/sales-navigator/list", response_model=UserScrapingListResponse)
@log_function_call(logger=logger, log_result=True)
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
    logger.info("List user scraping request: user_uuid=%s limit=%d offset=%d", 
               current_user.uuid, limit, offset)
    
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
        
        logger.info("Listed user scraping records: returned=%d total=%d", len(items), total)
        return UserScrapingListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("List user scraping failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user scraping records"
        ) from exc
