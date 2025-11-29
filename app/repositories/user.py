"""Repository providing user-specific query utilities."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
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
from app.utils.validation import is_valid_uuid

logger = get_logger(__name__)


class UserRepository(AsyncRepository[User]):
    """Data access helpers for user-centric queries."""

    def __init__(self) -> None:
        """Initialize the repository for the User model."""
        logger.debug("Entering UserRepository.__init__")
        super().__init__(User)
        logger.debug("Exiting UserRepository.__init__")

    async def get_by_uuid(self, session: AsyncSession, uuid: str) -> Optional[User]:
        """Retrieve a user by UUID."""
        logger.debug("Getting user by UUID: uuid=%s", uuid)
        stmt: Select[tuple[User]] = select(self.model).where(self.model.uuid == uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        logger.debug("User %sfound for uuid=%s", "" if user else "not ", uuid)
        return user

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """Retrieve a user by email address."""
        logger.debug("Getting user by email: email=%s", email)
        stmt: Select[tuple[User]] = select(self.model).where(self.model.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        logger.debug("User %sfound for email=%s", "" if user else "not ", email)
        return user

    async def create_user(
        self,
        session: AsyncSession,
        email: str,
        hashed_password: str,
        name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        logger.debug("Creating user: email=%s", email)
        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        logger.debug("Created user: uuid=%s email=%s", user.uuid, user.email)
        return user

    async def update_user(
        self,
        session: AsyncSession,
        user: User,
        **kwargs
    ) -> User:
        """Update user fields."""
        logger.debug("Updating user: uuid=%s fields=%s", user.uuid, list(kwargs.keys()))
        for key, value in kwargs.items():
            setattr(user, key, value)
        await session.flush()
        await session.refresh(user)
        logger.debug("Updated user: uuid=%s", user.uuid)
        return user

    async def list_all_users(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """List all users with pagination."""
        logger.debug("Listing all users: limit=%d offset=%d", limit, offset)
        
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
        
        logger.debug("Listed users: returned=%d total=%d", len(users), total)
        return users, total

    async def delete_user(
        self,
        session: AsyncSession,
        user: User,
    ) -> None:
        """Delete a user (cascade will delete profile)."""
        logger.debug("Deleting user: uuid=%s", user.uuid)
        await session.delete(user)
        await session.flush()
        logger.debug("Deleted user: uuid=%s", user.uuid)


class UserProfileRepository(AsyncRepository[UserProfile]):
    """Data access helpers for user profile queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserProfile model."""
        logger.debug("Entering UserProfileRepository.__init__")
        super().__init__(UserProfile)
        logger.debug("Exiting UserProfileRepository.__init__")

    async def get_by_user_id(self, session: AsyncSession, user_id: str) -> Optional[UserProfile]:
        """Retrieve a profile by user ID."""
        logger.debug("Getting profile by user_id: user_id=%s", user_id)
        stmt: Select[tuple[UserProfile]] = select(self.model).where(self.model.user_id == user_id)
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()
        logger.debug("Profile %sfound for user_id=%s", "" if profile else "not ", user_id)
        return profile

    async def create_profile(
        self,
        session: AsyncSession,
        user_id: str,
        **kwargs
    ) -> UserProfile:
        """Create a new user profile."""
        logger.debug("Creating profile: user_id=%s", user_id)
        profile = UserProfile(user_id=user_id, **kwargs)
        session.add(profile)
        await session.flush()
        await session.refresh(profile)
        logger.debug("Created profile: id=%d user_id=%s", profile.id, profile.user_id)
        return profile

    async def update_profile(
        self,
        session: AsyncSession,
        profile: UserProfile,
        **kwargs
    ) -> UserProfile:
        """Update profile fields."""
        logger.debug("Updating profile: id=%d fields=%s", profile.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(profile, key, value)
        await session.flush()
        await session.refresh(profile)
        logger.debug("Updated profile: id=%d", profile.id)
        return profile


class UserHistoryRepository(AsyncRepository[UserHistory]):
    """Data access helpers for user history queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserHistory model."""
        logger.debug("Entering UserHistoryRepository.__init__")
        super().__init__(UserHistory)
        logger.debug("Exiting UserHistoryRepository.__init__")

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
        
        logger.debug("Creating user history: user_id=%s event_type=%s", user_id, event_type.value)
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
        logger.debug("Created user history: id=%d user_id=%s event_type=%s", history.id, history.user_id, history.event_type)
        return history

    async def list_history(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        event_type: Optional[UserHistoryEventType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[UserHistory], int]:
        """List user history records with optional filtering and pagination."""
        logger.debug("Listing user history: user_id=%s event_type=%s limit=%d offset=%d", user_id, event_type, limit, offset)
        
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
        
        logger.debug("Listed user history: returned=%d total=%d", len(history_records), total)
        return history_records, total


class UserActivityRepository(AsyncRepository[UserActivity]):
    """Data access helpers for user activity queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserActivity model."""
        logger.debug("Entering UserActivityRepository.__init__")
        super().__init__(UserActivity)
        logger.debug("Exiting UserActivityRepository.__init__")

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
        
        logger.debug(
            "Creating user activity: user_id=%s service_type=%s action_type=%s status=%s",
            user_id,
            service_type.value,
            action_type.value,
            status.value,
        )
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
        logger.debug(
            "Created user activity: id=%d user_id=%s service_type=%s action_type=%s",
            activity.id,
            activity.user_id,
            activity.service_type,
            activity.action_type,
        )
        return activity

    async def update_activity(
        self,
        session: AsyncSession,
        activity: UserActivity,
        **kwargs
    ) -> UserActivity:
        """Update activity fields (used for updating export activities when they complete)."""
        logger.debug("Updating activity: id=%d fields=%s", activity.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(activity, key, value)
        await session.flush()
        await session.refresh(activity)
        logger.debug("Updated activity: id=%d", activity.id)
        return activity

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
        logger.debug(
            "Listing user activities: user_id=%s service_type=%s action_type=%s status=%s limit=%d offset=%d",
            user_id,
            service_type.value if service_type else None,
            action_type.value if action_type else None,
            status.value if status else None,
            limit,
            offset,
        )
        
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
        
        logger.debug("Listed user activities: returned=%d total=%d", len(activity_records), total)
        return activity_records, total

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
        logger.debug("Getting activity stats: user_id=%s", user_id)
        
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
        from datetime import timedelta
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
        
        logger.debug("Activity stats: total=%d", total_activities)
        return stats

