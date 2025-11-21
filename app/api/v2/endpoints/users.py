"""User profile API endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.filters import UserFilterParams
from app.schemas.user import AvatarUploadResponse, ProfileResponse, ProfileUpdate
from app.services.user_service import UserService

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
    logger.debug("Get profile request: user_id=%s", current_user.id)
    
    try:
        profile = await service.get_user_profile(session, current_user.id)
        logger.debug("Profile retrieved: user_id=%s", current_user.id)
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
    logger.info("Update profile request: user_id=%s fields=%s", current_user.id, list(update_data.model_dump(exclude_none=True).keys()))
    
    try:
        profile = await service.update_user_profile(session, current_user.id, update_data)
        logger.info("Profile updated: user_id=%s", current_user.id)
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
    logger.info("Avatar upload request: user_id=%s filename=%s", current_user.id, avatar.filename)
    
    try:
        avatar_url, profile = await service.upload_avatar(session, current_user.id, avatar)
        
        response = AvatarUploadResponse(
            avatar_url=avatar_url,
            profile=profile,
            message="Avatar uploaded successfully"
        )
        logger.info("Avatar uploaded: user_id=%s filename=%s", current_user.id, avatar.filename)
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
    logger.info("Promote to admin request: user_id=%s", current_user.id)
    
    try:
        profile = await service.promote_user_to_admin(session, current_user.id)
        logger.info("User promoted to admin: user_id=%s", current_user.id)
        return profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Promote to admin failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote user to admin"
        ) from exc
