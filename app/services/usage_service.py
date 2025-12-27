"""Feature usage tracking service for managing user feature usage limits."""

from datetime import datetime, timezone
from typing import Dict

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ADMIN, FREE_USER, PRO_USER, SUPER_ADMIN
from app.models.user import FeatureType, FeatureUsage, UserProfile
from app.repositories.user import UserProfileRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Feature limits configuration matching frontend FEATURE_ACCESS
FEATURE_LIMITS = {
    FeatureType.AI_CHAT: {FREE_USER: 0, PRO_USER: None},  # None = unlimited
    FeatureType.BULK_EXPORT: {FREE_USER: 0, PRO_USER: None},
    FeatureType.API_KEYS: {FREE_USER: 0, PRO_USER: None},
    FeatureType.TEAM_MANAGEMENT: {FREE_USER: 0, PRO_USER: None},  # Admin only
    FeatureType.EMAIL_FINDER: {FREE_USER: 10, PRO_USER: None},
    FeatureType.VERIFIER: {FREE_USER: 5, PRO_USER: None},
    FeatureType.LINKEDIN: {FREE_USER: 5, PRO_USER: None},
    FeatureType.DATA_SEARCH: {FREE_USER: 20, PRO_USER: None},
    FeatureType.ADVANCED_FILTERS: {FREE_USER: 0, PRO_USER: None},
    FeatureType.AI_SUMMARIES: {FREE_USER: 0, PRO_USER: None},
    FeatureType.SAVE_SEARCHES: {FREE_USER: 0, PRO_USER: None},
    FeatureType.BULK_VERIFICATION: {FREE_USER: 0, PRO_USER: None},
}


class UsageService:
    """Business logic for feature usage tracking and management."""

    def __init__(self, profile_repo: UserProfileRepository | None = None) -> None:
        """Initialize the usage service with repository dependencies."""
        self.profile_repo = profile_repo or UserProfileRepository()

    def _get_user_role_level(self, user_role: str) -> str:
        """
        Normalize user role to FREE_USER or PRO_USER level.
        
        Args:
            user_role: User role string
            
        Returns:
            FREE_USER or PRO_USER
        """
        if user_role in [SUPER_ADMIN, ADMIN]:
            return PRO_USER  # Admins get pro-level access
        if user_role == PRO_USER:
            return PRO_USER
        return FREE_USER

    def _get_feature_limit(self, feature: str, user_role: str) -> int | None:
        """
        Get usage limit for a feature based on user role.
        
        Args:
            feature: Feature name (e.g., "AI_CHAT")
            user_role: User role string
            
        Returns:
            Limit as integer, or None for unlimited
        """
        try:
            feature_enum = FeatureType(feature)
        except ValueError:
            return None
        
        role_level = self._get_user_role_level(user_role)
        limits = FEATURE_LIMITS.get(feature_enum, {})
        limit = limits.get(role_level)
        
        # None means unlimited for pro users
        if limit is None and role_level == PRO_USER:
            return None  # Unlimited
        
        return limit or 0

    async def _get_or_create_usage(
        self,
        session: AsyncSession,
        user_id: str,
        feature: str,
        user_role: str,
    ) -> FeatureUsage:
        """
        Get existing usage record or create a new one.
        
        Args:
            session: Database session
            user_id: User UUID
            feature: Feature name
            user_role: User role string
            
        Returns:
            FeatureUsage record
        """
        try:
            feature_enum = FeatureType(feature)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feature: {feature}"
            )
        
        # Check if usage record exists
        stmt = select(FeatureUsage).where(
            and_(
                FeatureUsage.user_id == user_id,
                FeatureUsage.feature == feature_enum.value
            )
        )
        result = await session.execute(stmt)
        usage = result.scalar_one_or_none()
        
        if usage:
            # Check if we need to reset based on billing period
            # For now, we'll use monthly periods
            now = datetime.now(timezone.utc)
            if usage.period_end and now > usage.period_end:
                # Reset usage for new period
                usage.used = 0
                usage.period_start = now
                # Set period_end to end of current month
                if now.month == 12:
                    usage.period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    usage.period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
                usage.limit = self._get_feature_limit(feature, user_role) or 0
            elif not usage.period_end:
                # Initialize period_end if not set
                if now.month == 12:
                    usage.period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    usage.period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
            return usage
        
        # Create new usage record
        limit = self._get_feature_limit(feature, user_role) or 0
        now = datetime.now(timezone.utc)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        usage = FeatureUsage(
            user_id=user_id,
            feature=feature_enum.value,
            used=0,
            limit=limit,
            period_start=now,
            period_end=period_end
        )
        session.add(usage)
        await session.flush()
        return usage

    async def track_usage(
        self,
        session: AsyncSession,
        user_id: str,
        feature: str,
        amount: int = 1,
    ) -> Dict[str, int | bool]:
        """
        Track feature usage for a user.
        
        Args:
            session: Database session
            user_id: User UUID
            feature: Feature name
            amount: Amount to increment (default: 1)
            
        Returns:
            Dict with feature, used, limit, and success
        """
        # Get user profile to determine role
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for user_id: {user_id}"
            )
        
        user_role = profile.role or FREE_USER
        
        # Get or create usage record
        usage = await self._get_or_create_usage(session, user_id, feature, user_role)
        
        # Update limit if it changed (e.g., user upgraded)
        limit = self._get_feature_limit(feature, user_role)
        if limit is not None:
            usage.limit = limit
        
        # Increment usage (only if not unlimited)
        if usage.limit is None or usage.limit == 0:
            # Unlimited or no access
            usage.used = 0
        else:
            usage.used = min(usage.used + amount, usage.limit)
        
        usage.updated_at = datetime.now(timezone.utc)
        await session.flush()
        
        return {
            "feature": feature,
            "used": usage.used,
            "limit": usage.limit if usage.limit is not None else 999999,  # Large number for unlimited
            "success": True
        }

    async def get_current_usage(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> Dict[str, Dict[str, int]]:
        """
        Get current usage for all features for a user.
        
        Args:
            session: Database session
            user_id: User UUID
            
        Returns:
            Dict mapping feature names to {used: int, limit: int}
        """
        # Get user profile to determine role
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for user_id: {user_id}"
            )
        
        user_role = profile.role or FREE_USER
        
        # Get all existing usage records
        stmt = select(FeatureUsage).where(FeatureUsage.user_id == user_id)
        result = await session.execute(stmt)
        usages = result.scalars().all()
        
        # Create a dict of existing usages
        usage_dict = {usage.feature: usage for usage in usages}
        
        # Build response with all features
        response = {}
        for feature_enum in FeatureType:
            feature_name = feature_enum.value
            usage = usage_dict.get(feature_name)
            
            if usage:
                # Check if period needs reset
                now = datetime.now(timezone.utc)
                if usage.period_end and now > usage.period_end:
                    usage.used = 0
                    usage.period_start = now
                    if now.month == 12:
                        usage.period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                    else:
                        usage.period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
                    await session.flush()
                
                limit = usage.limit if usage.limit is not None else 999999
                response[feature_name] = {
                    "used": usage.used,
                    "limit": limit
                }
            else:
                # Create default entry for feature
                limit = self._get_feature_limit(feature_name, user_role)
                response[feature_name] = {
                    "used": 0,
                    "limit": limit if limit is not None else 999999
                }
        
        return response

    async def reset_usage(
        self,
        session: AsyncSession,
        user_id: str,
        feature: str,
    ) -> Dict[str, int | bool]:
        """
        Reset usage counter for a specific feature.
        
        Args:
            session: Database session
            user_id: User UUID
            feature: Feature name to reset
            
        Returns:
            Dict with feature, used (0), limit, and success
        """
        # Get user profile to determine role
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile not found for user_id: {user_id}"
            )
        
        user_role = profile.role or FREE_USER
        
        # Get or create usage record
        usage = await self._get_or_create_usage(session, user_id, feature, user_role)
        
        # Reset usage to 0
        usage.used = 0
        
        # Update period if needed
        now = datetime.now(timezone.utc)
        if usage.period_end and now > usage.period_end:
            usage.period_start = now
            if now.month == 12:
                usage.period_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                usage.period_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        
        await session.flush()
        await session.commit()
        
        limit = usage.limit if usage.limit is not None else 999999
        
        return {
            "feature": feature,
            "used": 0,
            "limit": limit,
            "success": True
        }
