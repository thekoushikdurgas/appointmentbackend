"""Service layer for user authentication and profile management."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserProfile
from app.repositories.user import UserProfileRepository, UserRepository
from app.services.s3_service import S3Service
from app.schemas.user import (
    NotificationPreferences,
    ProfileResponse,
    ProfileUpdate,
    UserLogin,
    UserRegister,
)

settings = get_settings()
logger = get_logger(__name__)


def get_full_avatar_url(avatar_url: Optional[str]) -> Optional[str]:
    """
    Convert a relative avatar URL to a full URL.
    
    If avatar_url is already a full URL (starts with http:// or https://), return it as-is.
    If avatar_url is an S3 key, generate appropriate URL (presigned or public).
    If avatar_url is a relative path, prepend BASE_URL.
    If avatar_url is None, return None.
    """
    if not avatar_url:
        return None
    
    # If already a full URL, return as-is
    if avatar_url.startswith("http://") or avatar_url.startswith("https://"):
        return avatar_url
    
    # Check if it's an S3 key
    s3_service = S3Service()
    if s3_service.is_s3_key(avatar_url):
        if settings.S3_USE_PRESIGNED_URLS and settings.S3_BUCKET_NAME:
            # For S3 keys, we'll return the key as-is and let the service generate URLs when needed
            # Or generate a public URL if bucket is public
            try:
                return s3_service.get_public_url(avatar_url)
            except Exception:
                # If public URL generation fails, return as-is (will be handled by service)
                return avatar_url
        else:
            return s3_service.get_public_url(avatar_url)
    
    # Remove leading slash if present (BASE_URL should handle it)
    path = avatar_url.lstrip("/")
    base_url = settings.BASE_URL.rstrip("/")
    
    return f"{base_url}/{path}"


class UserService:
    """Business logic for user authentication and profile management."""

    def __init__(
        self,
        user_repository: Optional[UserRepository] = None,
        profile_repository: Optional[UserProfileRepository] = None,
        s3_service: Optional[S3Service] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        logger.debug("Entering UserService.__init__")
        self.user_repo = user_repository or UserRepository()
        self.profile_repo = profile_repository or UserProfileRepository()
        self.s3_service = s3_service or S3Service()
        logger.debug("Exiting UserService.__init__")

    async def register_user(
        self,
        session: AsyncSession,
        register_data: UserRegister,
    ) -> tuple[User, str, str]:
        """
        Register a new user and create their profile.
        
        Returns: (user, access_token, refresh_token)
        """
        logger.debug("Registering user: email=%s", register_data.email)
        
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(session, register_data.email)
        if existing_user:
            logger.warning("Registration failed: email already exists: %s", register_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"email": ["Email already exists"]}
            )
        
        # Validate password
        if len(register_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"password": ["This password is too short. It must contain at least 8 characters."]}
            )
        
        # Hash password and create user
        hashed_password = get_password_hash(register_data.password)
        user = await self.user_repo.create_user(
            session,
            email=register_data.email,
            hashed_password=hashed_password,
            name=register_data.name,
        )
        
        # Create default profile
        await self.profile_repo.create_profile(
            session,
            user_id=user.id,
            notifications={"weeklyReports": True, "newLeadAlerts": True},
            role="Member",
        )
        
        # Generate tokens
        token_data = {"sub": user.id}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        logger.info("User registered successfully: id=%s email=%s", user.id, user.email)
        return user, access_token, refresh_token

    async def authenticate_user(
        self,
        session: AsyncSession,
        login_data: UserLogin,
    ) -> tuple[User, str, str]:
        """
        Authenticate a user with email and password.
        
        Returns: (user, access_token, refresh_token)
        """
        logger.debug("Authenticating user: email=%s", login_data.email)
        
        user = await self.user_repo.get_by_email(session, login_data.email)
        if not user:
            logger.warning("Authentication failed: user not found: %s", login_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            logger.warning("Authentication failed: user disabled: %s", login_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning("Authentication failed: invalid password: %s", login_data.email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or password"
            )
        
        # Update last sign in
        user.last_sign_in_at = datetime.now(timezone.utc)
        await session.flush()
        
        # Generate tokens
        token_data = {"sub": user.id}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        logger.info("User authenticated successfully: id=%s email=%s", user.id, user.email)
        return user, access_token, refresh_token

    async def refresh_access_token(
        self,
        session: AsyncSession,
        refresh_token: str,
    ) -> tuple[str, str]:
        """
        Refresh an access token using a refresh token.
        
        Returns: (new_access_token, new_refresh_token)
        """
        logger.debug("Refreshing access token")
        
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning("Token refresh failed: invalid refresh token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token refresh failed: missing user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user or not user.is_active:
            logger.warning("Token refresh failed: user not found or inactive: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
        # Generate new tokens (token rotation)
        token_data = {"sub": user.id}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        logger.info("Access token refreshed successfully: user_id=%s", user_id)
        return new_access_token, new_refresh_token

    async def get_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> ProfileResponse:
        """Get user profile, creating one if it doesn't exist."""
        logger.debug("Getting user profile: user_id=%s", user_id)
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            logger.warning("Profile get failed: user not found: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            # Auto-create profile if it doesn't exist
            logger.debug("Profile not found, creating default profile: user_id=%s", user_id)
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role="Member",
            )
        
        # Build response
        notifications = profile.notifications or {}
        return ProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=profile.role or "Member",
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )

    async def update_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        update_data: ProfileUpdate,
    ) -> ProfileResponse:
        """Update user profile."""
        logger.debug("Updating user profile: user_id=%s", user_id)
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            logger.warning("Profile update failed: user not found: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user name if provided
        if update_data.name is not None:
            await self.user_repo.update_user(session, user, name=update_data.name)
        
        # Get or create profile
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role="Member",
            )
        
        # Prepare update data
        update_dict = update_data.model_dump(exclude_none=True)
        
        # Handle notifications merge
        if "notifications" in update_dict and update_dict["notifications"]:
            current_notifications = profile.notifications or {}
            new_notifications = update_dict["notifications"]
            if isinstance(new_notifications, dict):
                current_notifications.update(new_notifications)
                update_dict["notifications"] = current_notifications
        
        # Update profile
        await self.profile_repo.update_profile(session, profile, **update_dict)
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        return ProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=profile.role or "Member",
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )

    async def upload_avatar(
        self,
        session: AsyncSession,
        user_id: str,
        file: UploadFile,
    ) -> tuple[str, ProfileResponse]:
        """
        Upload and save user avatar.
        
        Returns: (avatar_url, profile_response)
        """
        logger.debug("Uploading avatar: user_id=%s filename=%s", user_id, file.filename)
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["This field is required."]}
            )
        
        # Validate file extension
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp"]}
            )
        
        # Read file content for validation
        file_content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Validate file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["Image file too large. Maximum size is 5.0MB"]}
            )
        
        # Validate magic bytes (file signature)
        valid_signatures = {
            b"\xff\xd8\xff": ".jpg",  # JPEG
            b"\x89\x50\x4e\x47": ".png",  # PNG
            b"GIF87a": ".gif",  # GIF87a
            b"GIF89a": ".gif",  # GIF89a
            b"RIFF": ".webp",  # WebP (starts with RIFF, but need more checks)
        }
        
        is_valid = False
        for signature, ext in valid_signatures.items():
            if file_content.startswith(signature):
                if ext == ".webp" and b"WEBP" in file_content[:12]:
                    is_valid = True
                    break
                elif ext != ".webp":
                    is_valid = True
                    break
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["File does not appear to be a valid image file"]}
            )
        
        # Get user and profile
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role="Member",
            )
        
        # Delete old avatar if it exists
        if profile.avatar_url:
            try:
                # Check if it's an S3 key
                if self.s3_service.is_s3_key(profile.avatar_url):
                    # Extract S3 key from URL if it's a full URL
                    s3_key = profile.avatar_url
                    if s3_key.startswith("https://"):
                        # Extract key from full S3 URL
                        parts = s3_key.split(".s3.")
                        if len(parts) > 1:
                            s3_key = parts[1].split("/", 1)[1] if "/" in parts[1] else s3_key
                    await self.s3_service.delete_file(s3_key)
                    logger.debug("Deleted old avatar from S3: %s", s3_key)
                elif not profile.avatar_url.startswith("http"):
                    # Local file - delete if exists
                    old_avatar_path = Path(settings.UPLOAD_DIR) / "avatars" / Path(profile.avatar_url).name
                    if old_avatar_path.exists():
                        try:
                            old_avatar_path.unlink()
                            logger.debug("Deleted old avatar: %s", old_avatar_path)
                        except Exception as exc:
                            logger.warning("Failed to delete old avatar: %s", exc)
            except Exception as exc:
                logger.warning("Failed to delete old avatar: %s", exc)
        
        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        filename = f"{user_id}_{timestamp}{file_ext}"
        
        # Upload to S3 if configured, otherwise save locally
        if settings.S3_BUCKET_NAME:
            try:
                # Upload to S3
                s3_key = f"{self.s3_service.avatars_prefix}{filename}"
                await self.s3_service.upload_file(
                    file_content=file_content,
                    s3_key=s3_key,
                    content_type=file.content_type or "image/jpeg",
                )
                logger.debug("Avatar uploaded to S3: key=%s", s3_key)
                
                # Store S3 key in database
                avatar_url = s3_key
                
                # Generate full URL for response
                if settings.S3_USE_PRESIGNED_URLS:
                    full_avatar_url = await self.s3_service.generate_presigned_url(s3_key)
                else:
                    full_avatar_url = self.s3_service.get_public_url(s3_key)
                    
            except Exception as exc:
                logger.exception("Failed to upload avatar to S3: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error uploading file to S3: {str(exc)}"
                )
        else:
            # Fallback to local storage
            avatars_dir = Path(settings.UPLOAD_DIR) / "avatars"
            avatars_dir.mkdir(parents=True, exist_ok=True)
            file_path = avatars_dir / filename
            
            try:
                with file_path.open("wb") as buffer:
                    buffer.write(file_content)
            except Exception as exc:
                logger.exception("Failed to save avatar file: %s", file_path)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error saving file: {str(exc)}"
                )
            
            # Store relative path in database
            avatar_url = f"/media/avatars/{filename}"
            full_avatar_url = get_full_avatar_url(avatar_url)
        
        # Update profile with avatar URL
        await self.profile_repo.update_profile(session, profile, avatar_url=avatar_url)
        await session.refresh(profile)
        await session.refresh(user)
        notifications = profile.notifications or {}
        profile_response = ProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=profile.role or "Member",
            avatar_url=full_avatar_url,
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )
        
        logger.info("Avatar uploaded successfully: user_id=%s filename=%s", user_id, filename)
        return full_avatar_url, profile_response

    async def promote_user_to_admin(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> ProfileResponse:
        """
        Promote a user to admin role.
        
        Updates the user's profile role to "Admin". If the profile doesn't exist, it will be created.
        
        Returns: Updated ProfileResponse with role="Admin"
        """
        logger.info("Promoting user to admin: user_id=%s", user_id)
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            logger.warning("Promotion failed: user not found: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get or create profile
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.debug("Profile not found, creating default profile: user_id=%s", user_id)
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role="Member",
            )
        
        # Update role to Admin
        await self.profile_repo.update_profile(session, profile, role="Admin")
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        logger.info("User promoted to admin successfully: user_id=%s email=%s", user_id, user.email)
        return ProfileResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=profile.role or "Admin",
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )

