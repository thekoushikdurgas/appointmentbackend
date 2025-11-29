"""Service layer for user authentication and profile management."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import DEFAULT_ROLE, FREE_USER, INITIAL_FREE_CREDITS
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserHistory, UserHistoryEventType, UserProfile
from app.repositories.token_blacklist import TokenBlacklistRepository
from app.repositories.user import UserHistoryRepository, UserProfileRepository, UserRepository
from app.services.s3_service import S3Service
from app.utils.validation import is_valid_uuid
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
        history_repository: Optional[UserHistoryRepository] = None,
        blacklist_repository: Optional[TokenBlacklistRepository] = None,
        s3_service: Optional[S3Service] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        logger.debug("Entering UserService.__init__")
        self.user_repo = user_repository or UserRepository()
        self.profile_repo = profile_repository or UserProfileRepository()
        self.history_repo = history_repository or UserHistoryRepository()
        self.blacklist_repo = blacklist_repository or TokenBlacklistRepository()
        self.s3_service = s3_service or S3Service()
        logger.debug("Exiting UserService.__init__")

    async def get_user_history(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Get user history records with optional filtering and pagination.
        
        Args:
            session: Database session
            user_id: Optional user ID to filter by (must be valid UUID format if provided)
            event_type: Optional event type filter ('registration' or 'login')
            limit: Maximum number of records to return
            offset: Number of records to skip
        
        Returns:
            Dictionary with history records and pagination info
            
        Raises:
            HTTPException: If user_id is provided but not a valid UUID format
        """
        # Validate user_id is a valid UUID format if provided
        if user_id is not None and not is_valid_uuid(user_id):
            logger.warning("Invalid user_id format provided: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id must be a valid UUID format"
            )
        
        logger.debug("Getting user history: user_id=%s event_type=%s limit=%d offset=%d", user_id, event_type, limit, offset)
        
        # Convert event_type string to enum if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = UserHistoryEventType(event_type)
            except ValueError:
                logger.warning("Invalid event_type: %s", event_type)
                event_type_enum = None
        
        history_records, total = await self.history_repo.list_history(
            session,
            user_id=user_id,
            event_type=event_type_enum,
            limit=limit,
            offset=offset,
        )
        
        # Format response
        history_items = []
        for record in history_records:
            # Get user email for display
            user = await self.user_repo.get_by_uuid(session, record.user_id) if record.user_id else None
            
            history_items.append({
                "id": record.id,
                "user_id": record.user_id,
                "user_email": user.email if user else None,
                "user_name": user.name if user else None,
                "event_type": record.event_type,
                "ip": record.ip,
                "continent": record.continent,
                "continent_code": record.continent_code,
                "country": record.country,
                "country_code": record.country_code,
                "region": record.region,
                "region_name": record.region_name,
                "city": record.city,
                "district": record.district,
                "zip": record.zip,
                "lat": float(record.lat) if record.lat else None,
                "lon": float(record.lon) if record.lon else None,
                "timezone": record.timezone,
                "currency": record.currency,
                "isp": record.isp,
                "org": record.org,
                "asname": record.asname,
                "reverse": record.reverse,
                "device": record.device,
                "proxy": record.proxy,
                "hosting": record.hosting,
                "created_at": record.created_at,
            })
        
        return {
            "items": history_items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

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
        
        # Create default profile with FREE_USER role and 50 initial credits
        await self.profile_repo.create_profile(
            session,
            user_id=user.uuid,
            notifications={"weeklyReports": True, "newLeadAlerts": True},
            role=DEFAULT_ROLE,
            credits=INITIAL_FREE_CREDITS,
            subscription_plan="free",
            subscription_status="active",
        )
        
        # Generate tokens
        token_data = {"sub": user.uuid}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Create user history record if geolocation data is available
        if register_data.geolocation:
            try:
                geolocation = register_data.geolocation
                await self.history_repo.create_history(
                    session,
                    user_id=user.uuid,
                    event_type=UserHistoryEventType.REGISTRATION,
                    ip=geolocation.ip,
                    continent=geolocation.continent,
                    continent_code=geolocation.continent_code,
                    country=geolocation.country,
                    country_code=geolocation.country_code,
                    region=geolocation.region,
                    region_name=geolocation.region_name,
                    city=geolocation.city,
                    district=geolocation.district,
                    zip=geolocation.zip,
                    lat=geolocation.lat,
                    lon=geolocation.lon,
                    timezone=geolocation.timezone,
                    currency=geolocation.currency,
                    isp=geolocation.isp,
                    org=geolocation.org,
                    asname=geolocation.asname,
                    reverse=geolocation.reverse,
                    device=geolocation.device,
                    proxy=geolocation.proxy,
                    hosting=geolocation.hosting,
                )
                logger.debug("User history created for registration: user_uuid=%s", user.uuid)
            except Exception as exc:
                # Log error but don't fail registration
                event_type_info = f"enum={UserHistoryEventType.REGISTRATION.name} value={UserHistoryEventType.REGISTRATION.value}"
                logger.warning(
                    "Failed to create user history for registration: user_uuid=%s event_type=%s error=%s",
                    user.uuid,
                    event_type_info,
                    exc,
                )
        
        logger.info("User registered successfully: uuid=%s email=%s", user.uuid, user.email)
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
            # API spec shows this can be either format, using dict format for consistency
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
        token_data = {"sub": user.uuid}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Store user.uuid before try block to avoid lazy loading issues if session is rolled back
        user_uuid = user.uuid
        user_email = user.email
        
        # Create user history record if geolocation data is available
        # Use a savepoint to isolate history creation from main transaction
        if login_data.geolocation:
            try:
                geolocation = login_data.geolocation
                # Create a savepoint to isolate history creation
                # If it fails, we rollback only the savepoint, not the entire transaction
                async with session.begin_nested():
                    await self.history_repo.create_history(
                        session,
                        user_id=user_uuid,
                        event_type=UserHistoryEventType.LOGIN,
                        ip=geolocation.ip,
                        continent=geolocation.continent,
                        continent_code=geolocation.continent_code,
                        country=geolocation.country,
                        country_code=geolocation.country_code,
                        region=geolocation.region,
                        region_name=geolocation.region_name,
                        city=geolocation.city,
                        district=geolocation.district,
                        zip=geolocation.zip,
                        lat=geolocation.lat,
                        lon=geolocation.lon,
                        timezone=geolocation.timezone,
                        currency=geolocation.currency,
                        isp=geolocation.isp,
                        org=geolocation.org,
                        asname=geolocation.asname,
                        reverse=geolocation.reverse,
                        device=geolocation.device,
                        proxy=geolocation.proxy,
                        hosting=geolocation.hosting,
                    )
                logger.debug("User history created for login: user_uuid=%s", user_uuid)
            except Exception as exc:
                # Log error but don't fail login - history creation is non-critical
                # The savepoint rollback ensures main transaction (user update) is preserved
                event_type_info = f"enum={UserHistoryEventType.LOGIN.name} value={UserHistoryEventType.LOGIN.value}"
                logger.warning(
                    "Failed to create user history for login: user_uuid=%s event_type=%s error=%s",
                    user_uuid,
                    event_type_info,
                    exc,
                )
        
        logger.info("User authenticated successfully: uuid=%s email=%s", user_uuid, user_email)
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
        
        # Check if token is blacklisted
        is_blacklisted = await self.blacklist_repo.is_token_blacklisted(session, refresh_token)
        if is_blacklisted:
            logger.warning("Token refresh failed: token is blacklisted")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
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
        token_data = {"sub": user.uuid}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        logger.info("Access token refreshed successfully: user_uuid=%s", user_id)
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
                role=DEFAULT_ROLE,
                credits=INITIAL_FREE_CREDITS,
                subscription_plan="free",
                subscription_status="active",
            )
        
        # Build response
        notifications = profile.notifications or {}
        return ProfileResponse(
            uuid=user.uuid,
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
                role=DEFAULT_ROLE,
                credits=INITIAL_FREE_CREDITS,
                subscription_plan="free",
                subscription_status="active",
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
            uuid=user.uuid,
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
        
        # Read first chunk for validation (magic bytes check)
        chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
        first_chunk = await file.read(min(chunk_size, 12))  # Read up to 12 bytes for magic bytes
        await file.seek(0)  # Reset file pointer
        
        # Validate file size (5MB max) - check content-length header if available
        max_size = 5 * 1024 * 1024  # 5MB
        # Note: For chunked uploads, we'll validate size during upload
        
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
            if first_chunk.startswith(signature):
                if ext == ".webp" and b"WEBP" in first_chunk[:12]:
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
                # Upload to S3 using chunked upload
                s3_key = f"{self.s3_service.avatars_prefix}{filename}"
                
                # For S3, we need to read the file in chunks and upload
                # Reset file pointer to beginning
                await file.seek(0)
                chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
                file_chunks = []
                total_size = 0
                
                while chunk := await file.read(chunk_size):
                    file_chunks.append(chunk)
                    total_size += len(chunk)
                    # Check size limit
                    if total_size > max_size:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"avatar": ["Image file too large. Maximum size is 5.0MB"]}
                        )
                
                # Combine chunks for S3 upload (S3 service expects full content)
                file_content = b"".join(file_chunks)
                
                await self.s3_service.upload_file(
                    file_content=file_content,
                    s3_key=s3_key,
                    content_type=file.content_type or "image/jpeg",
                )
                logger.debug("Avatar uploaded to S3: key=%s size=%d", s3_key, total_size)
                
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
            # Fallback to local storage - use chunked async upload
            avatars_dir = Path(settings.UPLOAD_DIR) / "avatars"
            avatars_dir.mkdir(parents=True, exist_ok=True)
            file_path = avatars_dir / filename
            
            try:
                # Reset file pointer to beginning
                await file.seek(0)
                chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
                total_size = 0
                
                async with aiofiles.open(file_path, "wb") as async_file:
                    while chunk := await file.read(chunk_size):
                        await async_file.write(chunk)
                        total_size += len(chunk)
                        # Check size limit during upload
                        if total_size > max_size:
                            await async_file.close()
                            file_path.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"avatar": ["Image file too large. Maximum size is 5.0MB"]}
                            )
                
                logger.debug("Avatar saved locally: path=%s size=%d", file_path, total_size)
            except HTTPException:
                raise
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
            id=user.uuid,
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
        
        if not user.is_active:
            logger.warning("Promotion failed: user account is disabled: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
        # Get or create profile
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.debug("Profile not found, creating default profile: user_id=%s", user_id)
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role=DEFAULT_ROLE,
                credits=INITIAL_FREE_CREDITS,
                subscription_plan="free",
                subscription_status="active",
            )
        
        # Update role to Admin
        from app.core.constants import ADMIN
        await self.profile_repo.update_profile(session, profile, role=ADMIN)
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        logger.info("User promoted to admin successfully: user_uuid=%s email=%s", user_id, user.email)
        return ProfileResponse(
            id=user.uuid,
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

    async def promote_user_to_super_admin(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> ProfileResponse:
        """
        Promote a user to super admin role.
        
        Updates the user's profile role to "SuperAdmin". If the profile doesn't exist, it will be created.
        
        Returns: Updated ProfileResponse with role="SuperAdmin"
        """
        logger.info("Promoting user to super admin: user_id=%s", user_id)
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            logger.warning("Promotion failed: user not found: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            logger.warning("Promotion failed: user account is disabled: %s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
        # Get or create profile
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.debug("Profile not found, creating default profile: user_id=%s", user_id)
            profile = await self.profile_repo.create_profile(
                session,
                user_id=user_id,
                notifications={"weeklyReports": True, "newLeadAlerts": True},
                role=DEFAULT_ROLE,
                credits=INITIAL_FREE_CREDITS,
                subscription_plan="free",
                subscription_status="active",
            )
        
        # Update role to SuperAdmin
        from app.core.constants import SUPER_ADMIN
        await self.profile_repo.update_profile(session, profile, role=SUPER_ADMIN)
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        logger.info("User promoted to super admin successfully: user_uuid=%s email=%s", user_id, user.email)
        return ProfileResponse(
            id=user.uuid,
            name=user.name,
            email=user.email,
            role=profile.role or "SuperAdmin",
            avatar_url=get_full_avatar_url(profile.avatar_url),
            is_active=user.is_active,
            job_title=profile.job_title,
            bio=profile.bio,
            timezone=profile.timezone,
            notifications=NotificationPreferences(**notifications) if notifications else None,
            created_at=user.created_at,
            updated_at=profile.updated_at or user.updated_at,
        )

