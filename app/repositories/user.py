"""Repository providing user-specific query utilities."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Select, and_, func, inspect, select
from sqlalchemy import func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, noload

from app.models.user import (
    ActivityActionType,
    ActivityServiceType,
    ActivityStatus,
    User,
    UserActivity,
    UserHistory,
    UserHistoryEventType,
    UserProfile,
)
from app.repositories.base import AsyncRepository
from app.utils.logger import get_logger, log_database_query, log_error, log_database_error
from app.utils.query_cache import get_query_cache
from app.utils.validation import is_valid_uuid

logger = get_logger(__name__)


class UserRepository(AsyncRepository[User]):
    """Data access helpers for user-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the User model."""
        super().__init__(User)
        self.cache = get_query_cache()
        self.cache_ttl = 300  # 5 minutes for user data

    async def get_by_uuid(self, session: AsyncSession, uuid: str) -> Optional[User]:
        """Retrieve a user by UUID.
        
        Optimized query with timeout handling to prevent database hangs.
        Uses ORM query which properly attaches objects to the session.
        """
        start_time = time.time()
        
        # Use ORM query which properly handles session attachment
        # Load only necessary columns for authentication to reduce overhead
        stmt = (
            select(User)
            .options(
                load_only(
                    User.uuid,
                    User.email,
                    User.name,
                    User.is_active,
                    User.hashed_password,
                    User.id,
                    User.created_at,
                    User.updated_at,
                    User.last_sign_in_at,
                ),
                noload(User.profile),
                noload(User.history),
                noload(User.activities),
                noload(User.scraping_records),
                noload(User.feature_usage_records),
            )
            .where(User.uuid == uuid)
            .limit(1)
        )
        
        # CRITICAL FIX: Wrap query in asyncio.wait_for with aggressive 2-second timeout
        # Database is hanging for 12.6 seconds - we need to fail fast
        try:
            result = await asyncio.wait_for(
                session.execute(stmt),
                timeout=2.0  # 2 second timeout for auth query
            )
            user = result.scalar_one_or_none()
            duration_ms = (time.time() - start_time) * 1000
            
            if user:
                logger.debug(
                    "User found by UUID",
                    extra={"context": {"user_uuid": uuid}}
                )
            else:
                logger.debug(
                    "User not found by UUID",
                    extra={"context": {"user_uuid": uuid}}
                )
            
            # Log database query with performance metrics
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"uuid": uuid},
                result_count=1 if user else 0,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            # Database query timed out - return None and let cache work
            # This allows subsequent requests to potentially succeed if DB recovers
            logger.warning(
                "Database query timeout in get_by_uuid",
                extra={
                    "context": {
                        "user_uuid": uuid,
                        "timeout_seconds": 2.0,
                        "duration_ms": duration_ms
                    }
                }
            )
            return None
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Error retrieving user by UUID",
                exc,
                "app.repositories.user",
                context={
                    "user_uuid": uuid,
                    "duration_ms": duration_ms
                },
            )
            return None
        
        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieve a user by email address.
        
        Optimized to load only necessary scalar columns and skip relationships to
        avoid unnecessary joins/lazy loads during authentication.
        Uses timeout protection to prevent database hangs.
        """
        start_time = time.time()
        
        # Use ORM query which properly handles session attachment
        # Load only necessary columns for authentication to reduce overhead
        stmt = (
            select(User)
            .options(
                load_only(
                    User.uuid,
                    User.email,
                    User.is_active,
                    User.name,
                    User.hashed_password,
                    User.id,
                    User.created_at,
                    User.updated_at,
                    User.last_sign_in_at,
                ),
                noload(User.profile),
                noload(User.history),
                noload(User.activities),
                noload(User.scraping_records),
                noload(User.feature_usage_records),
            )
            .where(User.email == email)
            .limit(1)
        )
        
        # CRITICAL FIX: Wrap query in asyncio.wait_for with aggressive 2-second timeout
        # Database is hanging for 1.4-7.1 seconds - we need to fail fast
        try:
            result = await asyncio.wait_for(
                session.execute(stmt),
                timeout=2.0  # 2 second timeout for auth query
            )
            user = result.scalar_one_or_none()
            duration_ms = (time.time() - start_time) * 1000
            
            if user:
                logger.debug(
                    "User found by email",
                    extra={"context": {"email": email}}
                )
            else:
                logger.debug(
                    "User not found by email",
                    extra={"context": {"email": email}}
                )
            
            # Log database query with performance metrics
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"email": email},
                result_count=1 if user else 0,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            # Database query timed out - return None and let cache work
            # This allows subsequent requests to potentially succeed if DB recovers
            logger.warning(
                "Database query timeout in get_by_email",
                extra={
                    "context": {
                        "email": email,
                        "timeout_seconds": 2.0,
                        "duration_ms": duration_ms
                    }
                }
            )
            return None
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"email": email, "method": "get_by_email"}
            )
            raise
        
        return user

    async def get_by_uuid_cached(
        self,
        session: AsyncSession,
        uuid: str,
        use_cache: bool = True
    ) -> Optional[User]:
        """
        Retrieve a user by UUID with caching support.
        
        Args:
            session: Database session
            uuid: User UUID
            use_cache: Whether to use cache (default: True)
            
        Returns:
            User object or None if not found
        """
        if use_cache and self.cache.enabled:
            # Try to get from cache
            cached_data = await self.cache.get("user:uuid", uuid)
            if cached_data is not None:
                # Reconstruct User object from cached data
                # Parse datetime strings back to datetime objects
                user_dict = cached_data.copy()
                if user_dict.get("created_at"):
                    user_dict["created_at"] = datetime.fromisoformat(user_dict["created_at"].replace("Z", "+00:00"))
                if user_dict.get("updated_at"):
                    user_dict["updated_at"] = datetime.fromisoformat(user_dict["updated_at"].replace("Z", "+00:00"))
                if user_dict.get("last_sign_in_at"):
                    user_dict["last_sign_in_at"] = datetime.fromisoformat(user_dict["last_sign_in_at"].replace("Z", "+00:00"))
                
                # Create User object and merge into session
                user = User(**user_dict)
                user = await session.merge(user)
                logger.debug(
                    "User retrieved from cache",
                    extra={"context": {"user_uuid": uuid}}
                )
                return user
        
        # Cache miss or cache disabled - fetch from database
        user = await self.get_by_uuid(session, uuid)
        
        # Cache the result if found and caching is enabled
        if user and use_cache and self.cache.enabled:
            # Convert User to dict for caching (only essential fields)
            user_data = {
                "uuid": user.uuid,
                "email": user.email,
                "name": user.name,
                "is_active": user.is_active,
                "hashed_password": user.hashed_password,
                "id": user.id,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_sign_in_at": user.last_sign_in_at.isoformat() if user.last_sign_in_at else None,
            }
            await self.cache.set("user:uuid", user_data, ttl=self.cache_ttl, uuid=uuid)
        
        return user

    async def get_by_email_cached(
        self,
        session: AsyncSession,
        email: str,
        use_cache: bool = True
    ) -> Optional[User]:
        """
        Retrieve a user by email with caching support.
        
        Args:
            session: Database session
            email: User email
            use_cache: Whether to use cache (default: True)
            
        Returns:
            User object or None if not found
        """
        if use_cache and self.cache.enabled:
            # Try to get from cache
            cached_data = await self.cache.get("user:email", email)
            if cached_data is not None:
                # Reconstruct User object from cached data
                # Parse datetime strings back to datetime objects
                user_dict = cached_data.copy()
                if user_dict.get("created_at"):
                    user_dict["created_at"] = datetime.fromisoformat(user_dict["created_at"].replace("Z", "+00:00"))
                if user_dict.get("updated_at"):
                    user_dict["updated_at"] = datetime.fromisoformat(user_dict["updated_at"].replace("Z", "+00:00"))
                if user_dict.get("last_sign_in_at"):
                    user_dict["last_sign_in_at"] = datetime.fromisoformat(user_dict["last_sign_in_at"].replace("Z", "+00:00"))
                
                # Create User object and merge into session
                user = User(**user_dict)
                user = await session.merge(user)
                logger.debug(
                    "User retrieved from cache",
                    extra={"context": {"email": email}}
                )
                return user
        
        # Cache miss or cache disabled - fetch from database
        user = await self.get_by_email(session, email)
        
        # Cache the result if found and caching is enabled
        if user and use_cache and self.cache.enabled:
            # Convert User to dict for caching (only essential fields)
            user_data = {
                "uuid": user.uuid,
                "email": user.email,
                "name": user.name,
                "is_active": user.is_active,
                "hashed_password": user.hashed_password,
                "id": user.id,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_sign_in_at": user.last_sign_in_at.isoformat() if user.last_sign_in_at else None,
            }
            await self.cache.set("user:email", user_data, ttl=self.cache_ttl, email=email)
        
        return user

    async def create_user(
        self,
        session: AsyncSession,
        email: str,
        hashed_password: str,
        name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        start_time = time.time()
        try:
            user = User(
                email=email,
                hashed_password=hashed_password,
                name=name,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="INSERT",
                table=self.model.__tablename__,
                filters={"email": email},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return user
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="INSERT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"email": email, "method": "create_user"}
            )
            raise

    async def update_user(
        self,
        session: AsyncSession,
        user: User,
        **kwargs
    ) -> User:
        """Update user fields."""
        start_time = time.time()
        try:
            updated_fields = list(kwargs.keys())
            for key, value in kwargs.items():
                setattr(user, key, value)
            await session.flush()
            await session.refresh(user)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="UPDATE",
                table=self.model.__tablename__,
                filters={"uuid": user.uuid},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            logger.debug(
                "User updated",
                extra={
                    "context": {
                        "user_uuid": user.uuid,
                        "updated_fields": updated_fields,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            
            return user
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="UPDATE",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"user_uuid": user.uuid if user else None, "method": "update_user"}
            )
            raise

    async def list_all_users(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """List all users with pagination."""
        start_time = time.time()
        try:
            # Get total count
            count_stmt: Select[tuple[int]] = select(func.count(self.model.id))
            total_result = await session.execute(count_stmt)
            total = total_result.scalar_one()
            
            # Get users with pagination
            stmt: Select[tuple[User]] = (
                select(self.model)
                .order_by(self.model.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            users = list(result.scalars().all())
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"limit": limit, "offset": offset},
                result_count=len(users),
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return users, total
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to list users",
                exc,
                "app.repositories.user",
                context={"limit": limit, "offset": offset, "duration_ms": duration_ms}
            )
            raise

    async def delete_user(
        self,
        session: AsyncSession,
        user: User,
    ) -> None:
        """Delete a user (cascade will delete profile)."""
        start_time = time.time()
        user_uuid = user.uuid if user else None
        try:
            await session.delete(user)
            await session.flush()
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="DELETE",
                table=self.model.__tablename__,
                filters={"uuid": user_uuid},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            logger.info(
                "User deleted",
                extra={
                    "context": {"user_uuid": user_uuid},
                    "performance": {"duration_ms": duration_ms}
                }
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to delete user",
                exc,
                "app.repositories.user",
                context={"user_uuid": user_uuid, "duration_ms": duration_ms}
            )
            raise


class UserProfileRepository(AsyncRepository[UserProfile]):
    """Data access helpers for user profile queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserProfile model."""
        super().__init__(UserProfile)

    async def get_by_user_id(self, session: AsyncSession, user_id: str) -> Optional[UserProfile]:
        """Retrieve a profile by user ID.
        
        This method is frequently called and can be slow. Logging is added
        to track performance issues.
        """
        start_time = time.time()
        try:
            stmt: Select[tuple[UserProfile]] = select(self.model).where(self.model.user_id == user_id)
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"user_id": user_id},
                result_count=1 if profile else 0,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return profile
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to get user profile by user_id",
                exc,
                "app.repositories.user",
                context={"user_id": user_id, "duration_ms": duration_ms}
            )
            raise

    async def create_profile(
        self,
        session: AsyncSession,
        user_id: str,
        **kwargs
    ) -> UserProfile:
        """Create a new user profile."""
        start_time = time.time()
        try:
            profile = UserProfile(user_id=user_id, **kwargs)
            session.add(profile)
            await session.flush()
            await session.refresh(profile)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="INSERT",
                table=self.model.__tablename__,
                filters={"user_id": user_id},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return profile
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to create user profile",
                exc,
                "app.repositories.user",
                context={"user_id": user_id, "duration_ms": duration_ms}
            )
            raise

    async def update_profile(
        self,
        session: AsyncSession,
        profile: UserProfile,
        **kwargs
    ) -> UserProfile:
        """Update profile fields."""
        start_time = time.time()
        try:
            updated_fields = [key for key, value in kwargs.items() if value is not None]
            for key, value in kwargs.items():
                if value is not None:
                    setattr(profile, key, value)
            await session.flush()
            await session.refresh(profile)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="UPDATE",
                table=self.model.__tablename__,
                filters={"user_id": profile.user_id},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            logger.debug(
                "User profile updated",
                extra={
                    "context": {
                        "user_id": profile.user_id,
                        "updated_fields": updated_fields,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            
            return profile
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to update user profile",
                exc,
                "app.repositories.user",
                context={"user_id": profile.user_id if profile else None, "duration_ms": duration_ms}
            )
            raise


class UserHistoryRepository(AsyncRepository[UserHistory]):
    """Data access helpers for user history queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserHistory model."""
        super().__init__(UserHistory)

    async def create_history(
        self,
        session: AsyncSession,
        user_id: str,
        event_type: UserHistoryEventType,
        ip: Optional[str] = None,
        continent: Optional[str] = None,
        continent_code: Optional[str] = None,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
        region: Optional[str] = None,
        region_name: Optional[str] = None,
        city: Optional[str] = None,
        district: Optional[str] = None,
        zip: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        timezone: Optional[str] = None,
        currency: Optional[str] = None,
        isp: Optional[str] = None,
        org: Optional[str] = None,
        asname: Optional[str] = None,
        reverse: Optional[str] = None,
        device: Optional[str] = None,
        proxy: Optional[bool] = None,
        hosting: Optional[bool] = None,
    ) -> UserHistory:
        """
        Create a new user history record.
        
        Args:
            session: Database session
            user_id: User ID (must be a valid UUID format)
            event_type: Type of event (registration or login)
            ip: Optional IP address
            ... (other optional geolocation fields)
            
        Returns:
            Created UserHistory record
            
        Raises:
            ValueError: If user_id is not a valid UUID format
        """
        # Validate user_id is a valid UUID format
        if not is_valid_uuid(user_id):
            raise ValueError(f"user_id must be a valid UUID format, got: {user_id}")
        
        start_time = time.time()
        try:
            history = UserHistory(
                user_id=user_id,
                event_type=event_type,  # Pass enum object directly, let EnumValue type decorator handle conversion
                ip=ip,
                continent=continent,
                continent_code=continent_code,
                country=country,
                country_code=country_code,
                region=region,
                region_name=region_name,
                city=city,
                district=district,
                zip=zip,
                lat=lat,
                lon=lon,
                timezone=timezone,
                currency=currency,
                isp=isp,
                org=org,
                asname=asname,
                reverse=reverse,
                device=device,
                proxy=proxy if proxy is not None else False,
                hosting=hosting if hosting is not None else False,
            )
            session.add(history)
            await session.flush()
            await session.refresh(history)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="INSERT",
                table=self.model.__tablename__,
                filters={"user_id": user_id, "event_type": event_type.value if hasattr(event_type, 'value') else str(event_type)},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return history
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to create user history",
                exc,
                "app.repositories.user",
                context={"user_id": user_id, "event_type": str(event_type), "duration_ms": duration_ms}
            )
            raise

    async def list_history(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        event_type: Optional[UserHistoryEventType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[UserHistory], int]:
        """List user history records with optional filtering and pagination."""
        
        # Build query
        stmt: Select[tuple[UserHistory]] = select(self.model)
        
        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)
        if event_type:
            stmt = stmt.where(self.model.event_type == event_type.value)
        
        # Get total count
        count_stmt = select(func.count(self.model.id))
        if user_id:
            count_stmt = count_stmt.where(self.model.user_id == user_id)
        if event_type:
            count_stmt = count_stmt.where(self.model.event_type == event_type.value)
        
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        history_records = list(result.scalars().all())
        
        return history_records, total


class UserActivityRepository(AsyncRepository[UserActivity]):
    """Data access helpers for user activity queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserActivity model."""
        super().__init__(UserActivity)

    async def create_activity(
        self,
        session: AsyncSession,
        user_id: str,
        service_type: ActivityServiceType,
        action_type: ActivityActionType,
        status: ActivityStatus,
        request_params: Optional[dict] = None,
        result_count: int = 0,
        result_summary: Optional[dict] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserActivity:
        """
        Create a new user activity record.
        
        Args:
            session: Database session
            user_id: User ID (must be a valid UUID format)
            service_type: Type of service (linkedin or email)
            action_type: Type of action (search or export)
            status: Status of the activity (success, failed, or partial)
            request_params: Optional request parameters as dict
            result_count: Number of results returned
            result_summary: Optional summary of results as dict
            error_message: Optional error message if failed
            ip_address: Optional IP address
            user_agent: Optional User-Agent string
            
        Returns:
            Created UserActivity record
            
        Raises:
            ValueError: If user_id is not a valid UUID format
        """
        # Validate user_id is a valid UUID format
        if not is_valid_uuid(user_id):
            raise ValueError(f"user_id must be a valid UUID format, got: {user_id}")
        
        start_time = time.time()
        try:
            activity = UserActivity(
                user_id=user_id,
                service_type=service_type,
                action_type=action_type,
                status=status,
                request_params=request_params,
                result_count=result_count,
                result_summary=result_summary,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(activity)
            await session.flush()
            await session.refresh(activity)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="INSERT",
                table=self.model.__tablename__,
                filters={
                    "user_id": user_id,
                    "service_type": service_type.value if hasattr(service_type, 'value') else str(service_type),
                    "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                },
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            return activity
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to create user activity",
                exc,
                "app.repositories.user",
                context={
                    "user_id": user_id,
                    "service_type": str(service_type),
                    "action_type": str(action_type),
                    "duration_ms": duration_ms
                }
            )
            raise

    async def update_activity(
        self,
        session: AsyncSession,
        activity: UserActivity,
        **kwargs
    ) -> UserActivity:
        """Update activity fields (used for updating export activities when they complete)."""
        start_time = time.time()
        try:
            updated_fields = [key for key, value in kwargs.items() if value is not None]
            for key, value in kwargs.items():
                if value is not None:
                    setattr(activity, key, value)
            await session.flush()
            await session.refresh(activity)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="UPDATE",
                table=self.model.__tablename__,
                filters={"id": activity.id if activity else None},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.user",
            )
            
            logger.debug(
                "User activity updated",
                extra={
                    "context": {
                        "activity_id": activity.id if activity else None,
                        "user_id": activity.user_id if activity else None,
                        "updated_fields": updated_fields,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            
            return activity
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_error(
                "Failed to update user activity",
                exc,
                "app.repositories.user",
                context={
                    "activity_id": activity.id if activity else None,
                    "duration_ms": duration_ms
                }
            )
            raise

    async def list_activities(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        service_type: Optional[ActivityServiceType] = None,
        action_type: Optional[ActivityActionType] = None,
        status: Optional[ActivityStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[UserActivity], int]:
        """
        List user activity records with optional filtering and pagination.
        
        Args:
            session: Database session
            user_id: Optional user ID filter
            service_type: Optional service type filter
            action_type: Optional action type filter
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (list of activities, total count)
        """
        
        # Build query
        stmt: Select[tuple[UserActivity]] = select(self.model)
        count_stmt: Select[tuple[int]] = select(func.count(self.model.id))
        
        if user_id:
            stmt = stmt.where(self.model.user_id == user_id)
            count_stmt = count_stmt.where(self.model.user_id == user_id)
        if service_type:
            stmt = stmt.where(self.model.service_type == service_type.value)
            count_stmt = count_stmt.where(self.model.service_type == service_type.value)
        if action_type:
            stmt = stmt.where(self.model.action_type == action_type.value)
            count_stmt = count_stmt.where(self.model.action_type == action_type.value)
        if status:
            stmt = stmt.where(self.model.status == status.value)
            count_stmt = count_stmt.where(self.model.status == status.value)
        if start_date:
            stmt = stmt.where(self.model.created_at >= start_date)
            count_stmt = count_stmt.where(self.model.created_at >= start_date)
        if end_date:
            stmt = stmt.where(self.model.created_at <= end_date)
            count_stmt = count_stmt.where(self.model.created_at <= end_date)
        
        # Get total count
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get paginated results
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        activity_records = list(result.scalars().all())
        
        return activity_records, total

    async def find_previous_email_search(
        self,
        session: AsyncSession,
        user_id: str,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> Optional[UserActivity]:
        """
        Find a previous successful email search with matching parameters.
        
        Args:
            session: Database session
            user_id: User ID
            first_name: First name to match
            last_name: Last name to match
            domain: Domain to match
            
        Returns:
            Most recent matching UserActivity record if found, None otherwise
        """
        # Normalize inputs for matching (case-insensitive)
        first_name_norm = first_name.lower().strip()
        last_name_norm = last_name.lower().strip()
        domain_norm = domain.lower().strip()
        
        # Query for matching activities
        # Match: user_id, service_type='email', action_type='search', status='success'
        # and request_params JSONB matches first_name, last_name, domain
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.service_type == ActivityServiceType.EMAIL.value,
                    self.model.action_type == ActivityActionType.SEARCH.value,
                    self.model.status == ActivityStatus.SUCCESS.value,
                    # Match request_params JSONB fields (case-insensitive)
                    sql_func.lower(self.model.request_params['first_name'].astext) == first_name_norm,
                    sql_func.lower(self.model.request_params['last_name'].astext) == last_name_norm,
                    sql_func.lower(self.model.request_params['domain'].astext) == domain_norm,
                )
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        
        result = await session.execute(stmt)
        activity = result.scalar_one_or_none()
        return activity

    async def get_activity_stats(
        self,
        session: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """
        Get activity statistics for a user.
        
        Args:
            session: Database session
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with activity statistics
        """
        
        # Build base query
        base_stmt = select(self.model).where(self.model.user_id == user_id)
        if start_date:
            base_stmt = base_stmt.where(self.model.created_at >= start_date)
        if end_date:
            base_stmt = base_stmt.where(self.model.created_at <= end_date)
        
        # Get total count
        total_stmt = select(func.count(self.model.id)).where(self.model.user_id == user_id)
        if start_date:
            total_stmt = total_stmt.where(self.model.created_at >= start_date)
        if end_date:
            total_stmt = total_stmt.where(self.model.created_at <= end_date)
        total_result = await session.execute(total_stmt)
        total_activities = total_result.scalar_one()
        
        # Get counts by service type
        by_service_stmt = (
            select(self.model.service_type, func.count(self.model.id))
            .where(self.model.user_id == user_id)
            .group_by(self.model.service_type)
        )
        if start_date:
            by_service_stmt = by_service_stmt.where(self.model.created_at >= start_date)
        if end_date:
            by_service_stmt = by_service_stmt.where(self.model.created_at <= end_date)
        service_result = await session.execute(by_service_stmt)
        by_service_type = {row[0]: row[1] for row in service_result.all()}
        
        # Get counts by action type
        by_action_stmt = (
            select(self.model.action_type, func.count(self.model.id))
            .where(self.model.user_id == user_id)
            .group_by(self.model.action_type)
        )
        if start_date:
            by_action_stmt = by_action_stmt.where(self.model.created_at >= start_date)
        if end_date:
            by_action_stmt = by_action_stmt.where(self.model.created_at <= end_date)
        action_result = await session.execute(by_action_stmt)
        by_action_type = {row[0]: row[1] for row in action_result.all()}
        
        # Get counts by status
        by_status_stmt = (
            select(self.model.status, func.count(self.model.id))
            .where(self.model.user_id == user_id)
            .group_by(self.model.status)
        )
        if start_date:
            by_status_stmt = by_status_stmt.where(self.model.created_at >= start_date)
        if end_date:
            by_status_stmt = by_status_stmt.where(self.model.created_at <= end_date)
        status_result = await session.execute(by_status_stmt)
        by_status = {row[0]: row[1] for row in status_result.all()}
        
        # Get recent activities (last 24 hours)
        recent_date = datetime.now() - timedelta(hours=24)
        recent_stmt = select(func.count(self.model.id)).where(
            self.model.user_id == user_id,
            self.model.created_at >= recent_date
        )
        recent_result = await session.execute(recent_stmt)
        recent_activities = recent_result.scalar_one()
        
        stats = {
            "total_activities": total_activities,
            "by_service_type": by_service_type,
            "by_action_type": by_action_type,
            "by_status": by_status,
            "recent_activities": recent_activities,
        }
        
        return stats

