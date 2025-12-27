"""Credit management service for handling user credit operations."""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ADMIN, FREE_USER, PRO_USER, SUPER_ADMIN, UNLIMITED_CREDITS_ROLES
from app.repositories.user import UserProfileRepository
from app.utils.logger import get_logger, log_error

logger = get_logger(__name__)


class CreditService:
    """Business logic for credit management and deduction."""

    def __init__(self, profile_repo: UserProfileRepository | None = None) -> None:
        """Initialize the credit service with repository dependencies."""
        self.profile_repo = profile_repo or UserProfileRepository()

    def should_deduct_credits(self, user_role: str) -> bool:
        """
        Check if user role requires credit deduction.
        
        Args:
            user_role: User role string (SuperAdmin, Admin, FreeUser, ProUser)
            
        Returns:
            True if credits should be deducted (FreeUser/ProUser), False otherwise (SuperAdmin/Admin)
        """
        if user_role in UNLIMITED_CREDITS_ROLES:
            return False
        return True

    async def deduct_credits(
        self,
        session: AsyncSession,
        user_id: str,
        amount: int = 1,
    ) -> int:
        """
        Deduct credits from user profile.
        
        Args:
            session: Database session
            user_id: User UUID
            amount: Number of credits to deduct (default: 1)
            
        Returns:
            New credit balance after deduction (can be negative)
        """
        start_time = time.time()
        logger.debug(
            "Credit deduction request",
            extra={
                "context": {
                    "user_id": user_id,
                    "amount": amount,
                }
            }
        )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.error(
                "Credit deduction failed: user profile not found",
                extra={
                    "context": {
                        "user_id": user_id,
                    }
                }
            )
            raise ValueError(f"User profile not found for user_id: {user_id}")
        
        current_credits = profile.credits or 0
        new_credits = current_credits - amount
        
        # Update profile with new credit balance
        await self.profile_repo.update_profile(session, profile, credits=new_credits)
        await session.flush()
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Credits deducted",
            extra={
                "context": {
                    "user_id": user_id,
                    "amount": amount,
                    "previous_balance": current_credits,
                    "new_balance": new_credits,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        return new_credits

    async def get_user_credits(self, session: AsyncSession, user_id: str) -> int:
        """
        Get current credit balance for a user.
        
        Args:
            session: Database session
            user_id: User UUID
            
        Returns:
            Current credit balance (0 if profile not found or credits is None)
        """
        start_time = time.time()
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.warning(
                "User profile not found when getting credits",
                extra={
                    "context": {
                        "user_id": user_id,
                    }
                }
            )
            return 0
        
        credits = profile.credits or 0
        duration_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "User credits retrieved",
            extra={
                "context": {
                    "user_id": user_id,
                    "credits": credits,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        return credits

