"""Repository providing user-specific query utilities."""

from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User, UserHistory, UserHistoryEventType, UserProfile
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
        stmt: Select[tuple[User]] = select(self.model).where(self.model.id == uuid)
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
        logger.debug("Created user: id=%s email=%s", user.id, user.email)
        return user

    async def update_user(
        self,
        session: AsyncSession,
        user: User,
        **kwargs
    ) -> User:
        """Update user fields."""
        logger.debug("Updating user: id=%s fields=%s", user.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            setattr(user, key, value)
        await session.flush()
        await session.refresh(user)
        logger.debug("Updated user: id=%s", user.id)
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
        logger.debug("Deleting user: id=%s", user.id)
        await session.delete(user)
        await session.flush()
        logger.debug("Deleted user: id=%s", user.id)


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

