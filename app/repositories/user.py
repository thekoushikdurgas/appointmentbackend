"""Repository providing user-specific query utilities."""

from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User, UserProfile
from app.repositories.base import AsyncRepository

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

