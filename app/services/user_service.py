"""Service layer for user authentication and profile management."""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import ADMIN, DEFAULT_ROLE, INITIAL_FREE_CREDITS, SUPER_ADMIN
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
from app.schemas.user import (
    NotificationPreferences,
    ProfileResponse,
    ProfileUpdate,
    UserLogin,
    UserRegister,
)
from app.services.s3_service import S3Service
from app.utils.logger import get_logger, log_error, log_api_error
from app.utils.query_cache import get_query_cache
from app.utils.validation import is_valid_uuid

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
        self.user_repo = user_repository or UserRepository()
        self.profile_repo = profile_repository or UserProfileRepository()
        self.history_repo = history_repository or UserHistoryRepository()
        self.blacklist_repo = blacklist_repository or TokenBlacklistRepository()
        self.s3_service = s3_service or S3Service()

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id must be a valid UUID format"
            )
        
        # Convert event_type string to enum if provided
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = UserHistoryEventType(event_type)
            except ValueError:
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
        start_time = time.time()
        logger.debug(
            "Starting user registration",
            extra={
                "context": {
                    "email": register_data.email,
                    "name": register_data.name,
                }
            }
        )
        
        # Check if user already exists (should be fast with email index and cache)
        email_check_start = time.time()
        existing_user = await self.user_repo.get_by_email_cached(session, register_data.email)
        email_check_duration = (time.time() - email_check_start) * 1000
        if existing_user:
            logger.warning(
                "Registration failed: email already exists",
                extra={
                    "context": {
                        "email": register_data.email,
                        "email_check_duration_ms": email_check_duration,
                    }
                }
            )
            # Email already exists - registration failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"email": ["Email already exists"]}
            )
        
        # Validate password
        if len(register_data.password) < 8:
            logger.warning(
                "Registration failed: password too short",
                extra={
                    "context": {
                        "email": register_data.email,
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"password": ["This password is too short. It must contain at least 8 characters."]}
            )
        
        # Hash password and create user
        user_create_start = time.time()
        try:
            hashed_password = get_password_hash(register_data.password)
        except Exception as exc:
            password_hash_duration = (time.time() - user_create_start) * 1000
            log_error(
                "Registration failed: password hashing error",
                exc,
                "app.services.user_service",
                context={
                    "email": register_data.email,
                    "password_hash_duration_ms": password_hash_duration,
                    "failure_point": "password_hashing"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing password. Please try again."
            ) from exc
        
        try:
            user = await self.user_repo.create_user(
                session,
                email=register_data.email,
                hashed_password=hashed_password,
                name=register_data.name,
            )
        except Exception as exc:
            user_create_duration = (time.time() - user_create_start) * 1000
            log_error(
                "Registration failed: user creation error",
                exc,
                "app.services.user_service",
                context={
                    "email": register_data.email,
                    "name": register_data.name,
                    "user_create_duration_ms": user_create_duration,
                    "failure_point": "user_creation"
                }
            )
            # Re-raise HTTPException if that's what was raised
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user account. Please try again."
            ) from exc
        
        user_create_duration = (time.time() - user_create_start) * 1000
        
        # Batch: Create profile + history in parallel (if geolocation available)
        batch_start = time.time()
        profile_task = self.profile_repo.create_profile(
            session,
            user_id=user.uuid,
            notifications={"weeklyReports": True, "newLeadAlerts": True},
            role=DEFAULT_ROLE,
            credits=INITIAL_FREE_CREDITS,
            subscription_plan="free",
            subscription_status="active",
        )
        
        # Create history task if geolocation data is available
        history_task = None
        if register_data.geolocation:
            try:
                geolocation = register_data.geolocation
                history_task = self.history_repo.create_history(
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
            except Exception as exc:
                # History creation setup failed but registration continues (non-critical)
                log_error(
                    "Failed to setup user history during registration",
                    exc,
                    "app.services.user_service",
                    context={
                        "user_uuid": user.uuid,
                    }
                )
                history_task = None
        
        # Execute profile creation first (required) - sequential to avoid session flush conflicts
        try:
            await profile_task
        except Exception as exc:
            profile_create_duration = (time.time() - batch_start) * 1000
            log_error(
                "Registration failed: profile creation error",
                exc,
                "app.services.user_service",
                context={
                    "user_uuid": user.uuid,
                    "email": register_data.email,
                    "profile_create_duration_ms": profile_create_duration,
                    "failure_point": "profile_creation"
                }
            )
            # Re-raise HTTPException if that's what was raised
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user profile. Please try again."
            ) from exc
        
        profile_create_duration = (time.time() - batch_start) * 1000
        
        # Execute history creation second (optional) - sequential to avoid session flush conflicts
        history_create_duration = 0.0
        if history_task:
            history_start = time.time()
            await history_task
            history_create_duration = (time.time() - history_start) * 1000
        
        # Generate tokens
        token_start = time.time()
        try:
            token_data = {"sub": user.uuid}
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
        except Exception as exc:
            token_duration = (time.time() - token_start) * 1000
            log_error(
                "Registration failed: token generation error",
                exc,
                "app.services.user_service",
                context={
                    "user_uuid": user.uuid,
                    "email": register_data.email,
                    "token_generation_duration_ms": token_duration,
                    "failure_point": "token_generation"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating authentication tokens. Please try again."
            ) from exc
        
        token_duration = (time.time() - token_start) * 1000
        
        duration_ms = (time.time() - start_time) * 1000
        # Only log as INFO if slow, otherwise DEBUG
        if duration_ms > 1000:
            logger.info(
                "User registration completed (slow)",
                extra={
                    "context": {
                        "user_uuid": user.uuid,
                        "email": user.email,
                    },
                    "performance": {
                        "total_duration_ms": duration_ms,
                        "email_check_ms": email_check_duration,
                        "user_create_ms": user_create_duration,
                        "profile_create_ms": profile_create_duration,
                        "history_create_ms": history_create_duration,
                        "token_generation_ms": token_duration,
                    }
                }
            )
        else:
            logger.debug(
                "User registration completed",
                extra={
                    "context": {
                        "user_uuid": user.uuid,
                        "email": user.email,
                    },
                    "performance": {
                        "total_duration_ms": duration_ms,
                    }
                }
            )
        
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
        start_time = time.time()
        logger.debug(
            "Starting user authentication",
            extra={
                "context": {
                    "email": login_data.email,
                }
            }
        )
        
        user = await self.user_repo.get_by_email_cached(session, login_data.email)
        if not user:
            log_api_error(
                endpoint="/api/v1/auth/login/",
                method="POST",
                status_code=400,
                error_type="AuthenticationError",
                error_message="User not found",
                context={"email": login_data.email, "reason": "user_not_found"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            logger.warning(
                "Authentication failed: user account disabled",
                extra={
                    "context": {
                        "user_uuid": user.uuid,
                        "email": user.email,
                    }
                }
            )
            # User account is disabled - authentication failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
        if not verify_password(login_data.password, user.hashed_password):
            log_api_error(
                endpoint="/api/v1/auth/login/",
                method="POST",
                status_code=400,
                error_type="AuthenticationError",
                error_message="Invalid password",
                user_id=str(user.uuid),
                context={"email": user.email, "reason": "invalid_password"}
            )
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
                logger.debug(
                    "User history created for login",
                    extra={
                        "context": {
                            "user_uuid": user_uuid,
                            "country": geolocation.country if geolocation else None,
                        }
                    }
                )
            except Exception as exc:
                # History creation failed but login continues (non-critical)
                # The savepoint rollback ensures main transaction (user update) is preserved
                log_error(
                    "Failed to create user history during login",
                    exc,
                    "app.services.user_service",
                    context={
                        "user_uuid": user_uuid,
                    }
                )
        
        duration_ms = (time.time() - start_time) * 1000
        # Only log as INFO if slow, otherwise DEBUG
        if duration_ms > 1000:
            logger.info(
                "User authentication completed (slow)",
                extra={
                    "context": {
                        "user_uuid": user_uuid,
                        "email": user_email,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
        else:
            logger.debug(
                "User authentication completed",
                extra={
                    "context": {
                        "user_uuid": user_uuid,
                        "email": user_email,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
        
        # User authenticated successfully
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
        # Check if token is blacklisted
        is_blacklisted = await self.blacklist_repo.is_token_blacklisted(session, refresh_token)
        if is_blacklisted:
            # Token is blacklisted - refresh failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            # Missing user ID in token - refresh failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user or not user.is_active:
            # User not found or inactive - refresh failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is invalid or expired"
            )
        
        # Generate new tokens (token rotation)
        token_data = {"sub": user.uuid}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        # Access token refreshed successfully
        return new_access_token, new_refresh_token

    async def get_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> ProfileResponse:
        """Get user profile, creating one if it doesn't exist."""
        cache = get_query_cache()
        cache_key = f"user_profile:{user_id}"
        
        # Try cache first
        if cache.enabled:
            cached = await cache.get("user_profile", user_id=user_id)
            if cached is not None:
                # Convert dict back to ProfileResponse if needed
                if isinstance(cached, dict):
                    return ProfileResponse(**cached)
                return cached
        
        user = await self.user_repo.get_by_uuid_cached(session, user_id)
        if not user:
            # User not found - profile get failed
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            # Auto-create profile if it doesn't exist
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
        profile_response = ProfileResponse(
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
        
        # Cache the result (convert to dict for caching)
        if cache.enabled:
            await cache.set("user_profile", profile_response.dict(), ttl=300, user_id=user_id)
        
        return profile_response

    async def update_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        update_data: ProfileUpdate,
    ) -> ProfileResponse:
        """Update user profile."""
        user = await self.user_repo.get_by_uuid_cached(session, user_id)
        if not user:
            # User not found - profile update failed
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
        profile_response = ProfileResponse(
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
        
        # Invalidate and update cache
        cache = get_query_cache()
        if cache.enabled:
            await cache.delete("user_profile", user_id=user_id)
            await cache.set("user_profile", profile_response.dict(), ttl=300, user_id=user_id)
        
        return profile_response

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
        start_time = time.time()
        operation_start = time.time()
        
        logger.info(
            "Avatar upload started",
            extra={
                "context": {
                    "user_id": user_id,
                    "filename": file.filename if file else None,
                    "content_type": file.content_type if file else None,
                }
            }
        )
        
        # Validate file
        validation_start = time.time()
        if not file.filename:
            logger.warning(
                "Avatar upload failed: missing filename",
                extra={
                    "context": {
                        "user_id": user_id,
                        "error": "filename_required"
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["This field is required."]}
            )
        
        # Validate file extension
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            logger.warning(
                "Avatar upload failed: invalid file extension",
                extra={
                    "context": {
                        "user_id": user_id,
                        "filename": file.filename,
                        "file_ext": file_ext,
                        "allowed_extensions": list(allowed_extensions),
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp"]}
            )
        
        # Read first chunk for validation (magic bytes check) with timeout
        chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
        try:
            first_chunk = await asyncio.wait_for(
                file.read(min(chunk_size, 12)),
                timeout=5.0  # 5 second timeout for reading magic bytes
            )
            await asyncio.wait_for(file.seek(0), timeout=1.0)  # Reset file pointer with timeout
        except asyncio.TimeoutError:
            validation_duration = (time.time() - validation_start) * 1000
            logger.error(
                "Avatar upload failed: file read timeout during validation",
                extra={
                    "context": {
                        "user_id": user_id,
                        "filename": file.filename,
                        "validation_duration_ms": validation_duration,
                        "error": "file_read_timeout"
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail={"avatar": ["File read operation timed out. Please try again."]}
            )
        except Exception as exc:
            validation_duration = (time.time() - validation_start) * 1000
            log_error(
                "Avatar upload failed: file read error during validation",
                exc,
                "app.services.user_service",
                context={
                    "user_id": user_id,
                    "filename": file.filename,
                    "validation_duration_ms": validation_duration,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"avatar": [f"Error reading file: {str(exc)}"]}
            ) from exc
        
        # Validate file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        
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
        
        validation_duration = (time.time() - validation_start) * 1000
        if not is_valid:
            logger.warning(
                "Avatar upload failed: invalid file signature (magic bytes)",
                extra={
                    "context": {
                        "user_id": user_id,
                        "filename": file.filename,
                        "file_ext": file_ext,
                        "validation_duration_ms": validation_duration,
                        "first_bytes": first_chunk.hex()[:24] if len(first_chunk) > 0 else None,
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"avatar": ["File does not appear to be a valid image file"]}
            )
        
        logger.debug(
            "Avatar file validation passed",
            extra={
                "context": {
                    "user_id": user_id,
                    "filename": file.filename,
                    "file_ext": file_ext,
                    "validation_duration_ms": validation_duration,
                }
            }
        )
        
        # Optimize: Get user and profile in parallel or with single query if possible
        # Get user and profile - these queries should be fast with indexes
        db_start = time.time()
        user = await self.user_repo.get_by_uuid_cached(session, user_id)
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
        db_duration = (time.time() - db_start) * 1000
        if db_duration > 100:  # Log if DB queries take >100ms
            logger.debug(
                "Avatar upload: slow DB queries",
                extra={
                    "context": {
                        "user_id": user_id,
                        "db_duration_ms": db_duration,
                    }
                }
            )
        
        # Store old avatar URL for background cleanup (non-blocking)
        old_avatar_url = profile.avatar_url if profile else None
        old_avatar_cleanup_duration = 0  # Will be 0 since it's now background
        
        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        filename = f"{user_id}_{timestamp}{file_ext}"
        
        # Upload to S3 if configured, otherwise save locally
        s3_upload_start = time.time()
        s3_total_duration = 0.0
        if settings.S3_BUCKET_NAME:
            s3_key = f"{self.s3_service.avatars_prefix}{filename}"
            logger.debug(
                "Avatar upload: starting S3 upload",
                extra={
                    "context": {
                        "user_id": user_id,
                        "s3_key": s3_key,
                        "filename": filename,
                    }
                }
            )
            try:
                # Upload to S3 using chunked upload
                # Reset file pointer to beginning with timeout
                try:
                    await asyncio.wait_for(file.seek(0), timeout=1.0)
                except asyncio.TimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail={"avatar": ["File seek operation timed out"]}
                    )
                
                chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
                file_chunks = []
                total_size = 0
                
                read_start = time.time()
                try:
                    # Read file in chunks with timeout protection (30 seconds total)
                    read_timeout = 30.0
                    chunk_read_start = time.time()
                    while True:
                        chunk = await asyncio.wait_for(
                            file.read(chunk_size),
                            timeout=read_timeout
                        )
                        if not chunk:
                            break
                        file_chunks.append(chunk)
                        total_size += len(chunk)
                        # Check size limit
                        if total_size > max_size:
                            logger.warning(
                                "Avatar upload failed: file too large",
                                extra={
                                    "context": {
                                        "user_id": user_id,
                                        "total_size": total_size,
                                        "max_size": max_size,
                                        "filename": file.filename,
                                    }
                                }
                            )
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail={"avatar": ["Image file too large. Maximum size is 5.0MB"]}
                            )
                        # Update timeout for next chunk (remaining time)
                        elapsed = time.time() - chunk_read_start
                        read_timeout = max(1.0, 30.0 - elapsed)
                except asyncio.TimeoutError:
                    read_duration = (time.time() - read_start) * 1000
                    logger.error(
                        "Avatar upload failed: file read timeout",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "total_size": total_size,
                                "read_duration_ms": read_duration,
                                "filename": file.filename,
                                "error": "file_read_timeout"
                            }
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail={"avatar": ["File read operation timed out. Please try again."]}
                    )
                read_duration = (time.time() - read_start) * 1000
                
                logger.debug(
                    "Avatar file read completed",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "total_size": total_size,
                            "read_duration_ms": read_duration,
                            "chunks_count": len(file_chunks),
                        }
                    }
                )
                
                # Combine chunks for S3 upload (S3 service expects full content)
                file_content = b"".join(file_chunks)
                
                upload_start = time.time()
                try:
                    # S3 upload with timeout (20 seconds)
                    await asyncio.wait_for(
                        self.s3_service.upload_file(
                            file_content=file_content,
                            s3_key=s3_key,
                            content_type=file.content_type or "image/jpeg",
                        ),
                        timeout=20.0
                    )
                except asyncio.TimeoutError:
                    upload_duration = (time.time() - upload_start) * 1000
                    logger.error(
                        "Avatar upload failed: S3 upload timeout",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "s3_key": s3_key,
                                "file_size": total_size,
                                "upload_duration_ms": upload_duration,
                                "error": "s3_upload_timeout"
                            }
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail={"avatar": ["S3 upload timed out. Please try again."]}
                    )
                upload_duration = (time.time() - upload_start) * 1000
                
                logger.debug(
                    "Avatar S3 upload completed",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "s3_key": s3_key,
                            "upload_duration_ms": upload_duration,
                        }
                    }
                )
                
                # Store S3 key in database
                avatar_url = s3_key
                
                # Generate full URL for response with timeout
                url_start = time.time()
                try:
                    if settings.S3_USE_PRESIGNED_URLS:
                        full_avatar_url = await asyncio.wait_for(
                            self.s3_service.generate_presigned_url(s3_key),
                            timeout=5.0
                        )
                    else:
                        full_avatar_url = self.s3_service.get_public_url(s3_key)
                except asyncio.TimeoutError:
                    url_duration = (time.time() - url_start) * 1000
                    logger.warning(
                        "Avatar upload: presigned URL generation timeout (non-critical)",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "s3_key": s3_key,
                                "url_duration_ms": url_duration,
                            }
                        }
                    )
                    # Fallback to public URL if presigned URL generation times out
                    full_avatar_url = self.s3_service.get_public_url(s3_key)
                url_duration = (time.time() - url_start) * 1000
                
                s3_total_duration = (time.time() - s3_upload_start) * 1000
                logger.info(
                    "Avatar S3 upload operations completed",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "s3_key": s3_key,
                            "file_size": total_size,
                        },
                        "performance": {
                            "read_duration_ms": read_duration,
                            "upload_duration_ms": upload_duration,
                            "url_duration_ms": url_duration,
                            "total_s3_duration_ms": s3_total_duration,
                        }
                    }
                )
                    
            except HTTPException:
                raise
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                log_error(
                    "Avatar upload failed: S3 upload error",
                    exc,
                    "app.services.user_service",
                    context={
                        "user_id": user_id,
                        "s3_key": s3_key if 's3_key' in locals() else None,
                        "duration_ms": duration_ms,
                        "filename": file.filename,
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error uploading file to S3: {str(exc)}"
                ) from exc
        else:
            # Fallback to local storage - use chunked async upload
            local_storage_start = time.time()
            logger.debug(
                "Avatar upload: starting local storage upload",
                extra={
                    "context": {
                        "user_id": user_id,
                        "filename": filename,
                        "upload_dir": settings.UPLOAD_DIR,
                    }
                }
            )
            avatars_dir = Path(settings.UPLOAD_DIR) / "avatars"
            avatars_dir.mkdir(parents=True, exist_ok=True)
            file_path = avatars_dir / filename
            
            try:
                # Reset file pointer to beginning with timeout
                try:
                    await asyncio.wait_for(file.seek(0), timeout=1.0)
                except asyncio.TimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail={"avatar": ["File seek operation timed out"]}
                    )
                
                chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
                total_size = 0
                
                write_start = time.time()
                try:
                    async with aiofiles.open(file_path, "wb") as async_file:
                        # Read and write with timeout protection (30 seconds total)
                        write_timeout = 30.0
                        chunk_write_start = time.time()
                        while True:
                            try:
                                chunk = await asyncio.wait_for(
                                    file.read(chunk_size),
                                    timeout=write_timeout
                                )
                            except asyncio.TimeoutError:
                                write_duration = (time.time() - write_start) * 1000
                                await async_file.close()
                                file_path.unlink(missing_ok=True)
                                logger.error(
                                    "Avatar upload failed: file read timeout during local storage",
                                    extra={
                                        "context": {
                                            "user_id": user_id,
                                            "total_size": total_size,
                                            "write_duration_ms": write_duration,
                                            "filename": file.filename,
                                            "file_path": str(file_path),
                                            "error": "file_read_timeout"
                                        }
                                    }
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                                    detail={"avatar": ["File read operation timed out. Please try again."]}
                                )
                            
                            if not chunk:
                                break
                            
                            try:
                                await asyncio.wait_for(
                                    async_file.write(chunk),
                                    timeout=5.0  # 5 second timeout for each write
                                )
                            except asyncio.TimeoutError:
                                write_duration = (time.time() - write_start) * 1000
                                await async_file.close()
                                file_path.unlink(missing_ok=True)
                                logger.error(
                                    "Avatar upload failed: file write timeout during local storage",
                                    extra={
                                        "context": {
                                            "user_id": user_id,
                                            "total_size": total_size,
                                            "write_duration_ms": write_duration,
                                            "filename": file.filename,
                                            "file_path": str(file_path),
                                            "error": "file_write_timeout"
                                        }
                                    }
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                                    detail={"avatar": ["File write operation timed out. Please try again."]}
                                )
                            
                            total_size += len(chunk)
                            # Check size limit during upload
                            if total_size > max_size:
                                await async_file.close()
                                file_path.unlink(missing_ok=True)
                                logger.warning(
                                    "Avatar upload failed: file too large",
                                    extra={
                                        "context": {
                                            "user_id": user_id,
                                            "total_size": total_size,
                                            "max_size": max_size,
                                            "filename": file.filename,
                                        }
                                    }
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail={"avatar": ["Image file too large. Maximum size is 5.0MB"]}
                                )
                            
                            # Update timeout for next chunk (remaining time)
                            elapsed = time.time() - chunk_write_start
                            write_timeout = max(1.0, 30.0 - elapsed)
                except HTTPException:
                    raise
                except asyncio.TimeoutError:
                    write_duration = (time.time() - write_start) * 1000
                    file_path.unlink(missing_ok=True)
                    logger.error(
                        "Avatar upload failed: local storage operation timeout",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "write_duration_ms": write_duration,
                                "filename": file.filename,
                                "file_path": str(file_path),
                                "error": "local_storage_timeout"
                            }
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail={"avatar": ["File storage operation timed out. Please try again."]}
                    )
                
                write_duration = (time.time() - write_start) * 1000
                s3_total_duration = (time.time() - local_storage_start) * 1000
                
                logger.info(
                    "Avatar saved to local storage",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "file_path": str(file_path),
                            "file_size": total_size,
                        },
                        "performance": {
                            "write_duration_ms": write_duration,
                            "total_storage_duration_ms": s3_total_duration,
                        }
                    }
                )
            except HTTPException:
                raise
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                log_error(
                    "Avatar upload failed: local storage error",
                    exc,
                    "app.services.user_service",
                    context={
                        "user_id": user_id,
                        "file_path": str(file_path),
                        "duration_ms": duration_ms,
                        "filename": file.filename,
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error saving file: {str(exc)}"
                ) from exc
            
            # Store relative path in database
            avatar_url = f"/media/avatars/{filename}"
            full_avatar_url = get_full_avatar_url(avatar_url)
        
        # Update profile with avatar URL FIRST (don't wait for old avatar cleanup)
        update_start = time.time()
        try:
            await asyncio.wait_for(
                self.profile_repo.update_profile(session, profile, avatar_url=avatar_url),
                timeout=5.0  # 5 second timeout for profile update
            )
            await asyncio.wait_for(session.refresh(profile), timeout=2.0)
            await asyncio.wait_for(session.refresh(user), timeout=2.0)
        except asyncio.TimeoutError:
            update_duration = (time.time() - update_start) * 1000
            logger.error(
                "Avatar upload failed: profile update timeout",
                extra={
                    "context": {
                        "user_id": user_id,
                        "avatar_url": avatar_url,
                        "update_duration_ms": update_duration,
                        "error": "profile_update_timeout"
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail={"avatar": ["Profile update timed out. Please try again."]}
            )
        update_duration = (time.time() - update_start) * 1000
        
        logger.debug(
            "Avatar profile update completed",
            extra={
                "context": {
                    "user_id": user_id,
                    "avatar_url": avatar_url,
                    "update_duration_ms": update_duration,
                }
            }
        )
        
        # Delete old avatar in BACKGROUND (non-blocking)
        if old_avatar_url:
            asyncio.create_task(self._cleanup_old_avatar(old_avatar_url, user_id))
        
        notifications = profile.notifications or {}
        profile_response = ProfileResponse(
            uuid=user.uuid,
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
        
        # Log performance metrics
        total_duration = (time.time() - start_time) * 1000
        logger.info(
            "Avatar uploaded successfully",
            extra={
                "context": {
                    "user_id": user_id,
                    "avatar_url": full_avatar_url,
                    "filename": filename,
                    "storage_type": "S3" if settings.S3_BUCKET_NAME else "local",
                },
                "performance": {
                    "total_duration_ms": total_duration,
                    "db_duration_ms": db_duration,
                    "old_avatar_cleanup_ms": old_avatar_cleanup_duration,
                    "s3_upload_ms": s3_total_duration if settings.S3_BUCKET_NAME else 0,
                    "update_duration_ms": update_duration,
                }
            }
        )
        
        return full_avatar_url, profile_response
    
    async def _cleanup_old_avatar(self, avatar_url: str, user_id: str) -> None:
        """
        Background task to clean up old avatar file.
        
        This runs asynchronously and doesn't block the main request.
        """
        try:
            # Check if it's an S3 key
            if self.s3_service.is_s3_key(avatar_url):
                # Extract S3 key from URL if it's a full URL
                s3_key = avatar_url
                if s3_key.startswith("https://"):
                    # Extract key from full S3 URL
                    parts = s3_key.split(".s3.")
                    if len(parts) > 1:
                        s3_key = parts[1].split("/", 1)[1] if "/" in parts[1] else s3_key
                await self.s3_service.delete_file(s3_key)
                logger.debug(
                    "Old avatar deleted from S3 (background)",
                    extra={"context": {"user_id": user_id, "s3_key": s3_key}}
                )
            elif not avatar_url.startswith("http"):
                # Local file - delete if exists
                old_avatar_path = Path(settings.UPLOAD_DIR) / "avatars" / Path(avatar_url).name
                if old_avatar_path.exists():
                    old_avatar_path.unlink()
                    logger.debug(
                        "Old avatar deleted from local storage (background)",
                        extra={"context": {"user_id": user_id, "path": str(old_avatar_path)}}
                    )
        except Exception as exc:
            logger.warning(
                "Failed to delete old avatar (non-critical, background task)",
                extra={
                    "context": {
                        "user_id": user_id,
                        "avatar_url": avatar_url,
                        "error": str(exc),
                    }
                }
            )

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
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
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
        
        # Update role to Admin
        await self.profile_repo.update_profile(session, profile, role=ADMIN)
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        # User promoted to admin successfully
        return ProfileResponse(
            uuid=user.uuid,
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
        user = await self.user_repo.get_by_uuid(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"non_field_errors": ["User account is disabled"]}
            )
        
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
        
        # Update role to SuperAdmin
        await self.profile_repo.update_profile(session, profile, role=SUPER_ADMIN)
        
        # Refresh to get updated values
        await session.refresh(profile)
        await session.refresh(user)
        
        # Build response
        notifications = profile.notifications or {}
        # User promoted to super admin successfully
        return ProfileResponse(
            uuid=user.uuid,
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

