"""Repository providing billing-specific query utilities."""

from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.billing import AddonPackage, SubscriptionPlan, SubscriptionPlanPeriod
from app.repositories.base import AsyncRepository

logger = get_logger(__name__)


class SubscriptionPlanRepository(AsyncRepository[SubscriptionPlan]):
    """Data access helpers for subscription plan queries."""

    def __init__(self) -> None:
        """Initialize the repository for the SubscriptionPlan model."""
        logger.debug("Entering SubscriptionPlanRepository.__init__")
        super().__init__(SubscriptionPlan)
        logger.debug("Exiting SubscriptionPlanRepository.__init__")

    async def get_by_tier(self, session: AsyncSession, tier: str) -> Optional[SubscriptionPlan]:
        """Retrieve a subscription plan by tier."""
        logger.debug("Getting subscription plan by tier: tier=%s", tier)
        stmt: Select[tuple[SubscriptionPlan]] = select(self.model).where(self.model.tier == tier)
        result = await session.execute(stmt)
        plan = result.scalar_one_or_none()
        logger.debug("Plan %sfound for tier=%s", "" if plan else "not ", tier)
        return plan

    async def list_all(self, session: AsyncSession, include_inactive: bool = False) -> list[SubscriptionPlan]:
        """List all subscription plans."""
        logger.debug("Listing subscription plans: include_inactive=%s", include_inactive)
        stmt: Select[tuple[SubscriptionPlan]] = select(self.model)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active == True)
        stmt = stmt.order_by(self.model.tier)
        result = await session.execute(stmt)
        plans = list(result.scalars().all())
        logger.debug("Listed subscription plans: count=%d", len(plans))
        return plans

    async def create_plan(
        self,
        session: AsyncSession,
        tier: str,
        name: str,
        category: str,
        is_active: bool = True,
    ) -> SubscriptionPlan:
        """Create a new subscription plan."""
        logger.debug("Creating subscription plan: tier=%s name=%s", tier, name)
        plan = SubscriptionPlan(
            tier=tier,
            name=name,
            category=category,
            is_active=is_active,
        )
        session.add(plan)
        await session.flush()
        await session.refresh(plan)
        logger.debug("Created subscription plan: tier=%s", plan.tier)
        return plan

    async def update_plan(
        self,
        session: AsyncSession,
        plan: SubscriptionPlan,
        **kwargs
    ) -> SubscriptionPlan:
        """Update subscription plan fields."""
        logger.debug("Updating subscription plan: tier=%s fields=%s", plan.tier, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(plan, key, value)
        await session.flush()
        await session.refresh(plan)
        logger.debug("Updated subscription plan: tier=%s", plan.tier)
        return plan

    async def delete_plan(self, session: AsyncSession, plan: SubscriptionPlan) -> None:
        """Delete a subscription plan (cascade will delete periods)."""
        logger.debug("Deleting subscription plan: tier=%s", plan.tier)
        await session.delete(plan)
        await session.flush()
        logger.debug("Deleted subscription plan: tier=%s", plan.tier)


class SubscriptionPlanPeriodRepository(AsyncRepository[SubscriptionPlanPeriod]):
    """Data access helpers for subscription plan period queries."""

    def __init__(self) -> None:
        """Initialize the repository for the SubscriptionPlanPeriod model."""
        logger.debug("Entering SubscriptionPlanPeriodRepository.__init__")
        super().__init__(SubscriptionPlanPeriod)
        logger.debug("Exiting SubscriptionPlanPeriodRepository.__init__")

    async def get_by_plan_and_period(
        self,
        session: AsyncSession,
        plan_tier: str,
        period: str,
    ) -> Optional[SubscriptionPlanPeriod]:
        """Retrieve a period by plan tier and period."""
        logger.debug("Getting period: plan_tier=%s period=%s", plan_tier, period)
        stmt: Select[tuple[SubscriptionPlanPeriod]] = select(self.model).where(
            self.model.plan_tier == plan_tier,
            self.model.period == period
        )
        result = await session.execute(stmt)
        period_obj = result.scalar_one_or_none()
        logger.debug("Period %sfound for plan_tier=%s period=%s", "" if period_obj else "not ", plan_tier, period)
        return period_obj

    async def list_by_plan(self, session: AsyncSession, plan_tier: str) -> list[SubscriptionPlanPeriod]:
        """List all periods for a subscription plan."""
        logger.debug("Listing periods for plan: plan_tier=%s", plan_tier)
        stmt: Select[tuple[SubscriptionPlanPeriod]] = select(self.model).where(
            self.model.plan_tier == plan_tier
        ).order_by(self.model.period)
        result = await session.execute(stmt)
        periods = list(result.scalars().all())
        logger.debug("Listed periods: plan_tier=%s count=%d", plan_tier, len(periods))
        return periods

    async def create_period(
        self,
        session: AsyncSession,
        plan_tier: str,
        period: str,
        credits: int,
        rate_per_credit: float,
        price: float,
        savings_amount: Optional[float] = None,
        savings_percentage: Optional[int] = None,
    ) -> SubscriptionPlanPeriod:
        """Create a new subscription plan period."""
        logger.debug("Creating period: plan_tier=%s period=%s", plan_tier, period)
        period_obj = SubscriptionPlanPeriod(
            plan_tier=plan_tier,
            period=period,
            credits=credits,
            rate_per_credit=rate_per_credit,
            price=price,
            savings_amount=savings_amount,
            savings_percentage=savings_percentage,
        )
        session.add(period_obj)
        await session.flush()
        await session.refresh(period_obj)
        logger.debug("Created period: id=%d plan_tier=%s period=%s", period_obj.id, plan_tier, period)
        return period_obj

    async def update_period(
        self,
        session: AsyncSession,
        period_obj: SubscriptionPlanPeriod,
        **kwargs
    ) -> SubscriptionPlanPeriod:
        """Update subscription plan period fields."""
        logger.debug("Updating period: id=%d fields=%s", period_obj.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(period_obj, key, value)
        await session.flush()
        await session.refresh(period_obj)
        logger.debug("Updated period: id=%d", period_obj.id)
        return period_obj

    async def delete_period(self, session: AsyncSession, period_obj: SubscriptionPlanPeriod) -> None:
        """Delete a subscription plan period."""
        logger.debug("Deleting period: id=%d", period_obj.id)
        await session.delete(period_obj)
        await session.flush()
        logger.debug("Deleted period: id=%d", period_obj.id)


class AddonPackageRepository(AsyncRepository[AddonPackage]):
    """Data access helpers for addon package queries."""

    def __init__(self) -> None:
        """Initialize the repository for the AddonPackage model."""
        logger.debug("Entering AddonPackageRepository.__init__")
        super().__init__(AddonPackage)
        logger.debug("Exiting AddonPackageRepository.__init__")

    async def get_by_id(self, session: AsyncSession, package_id: str) -> Optional[AddonPackage]:
        """Retrieve an addon package by ID."""
        logger.debug("Getting addon package by id: id=%s", package_id)
        stmt: Select[tuple[AddonPackage]] = select(self.model).where(self.model.id == package_id)
        result = await session.execute(stmt)
        package = result.scalar_one_or_none()
        logger.debug("Package %sfound for id=%s", "" if package else "not ", package_id)
        return package

    async def list_all(self, session: AsyncSession, include_inactive: bool = False) -> list[AddonPackage]:
        """List all addon packages."""
        logger.debug("Listing addon packages: include_inactive=%s", include_inactive)
        stmt: Select[tuple[AddonPackage]] = select(self.model)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active == True)
        stmt = stmt.order_by(self.model.price)
        result = await session.execute(stmt)
        packages = list(result.scalars().all())
        logger.debug("Listed addon packages: count=%d", len(packages))
        return packages

    async def create_package(
        self,
        session: AsyncSession,
        package_id: str,
        name: str,
        credits: int,
        rate_per_credit: float,
        price: float,
        is_active: bool = True,
    ) -> AddonPackage:
        """Create a new addon package."""
        logger.debug("Creating addon package: id=%s name=%s", package_id, name)
        package = AddonPackage(
            id=package_id,
            name=name,
            credits=credits,
            rate_per_credit=rate_per_credit,
            price=price,
            is_active=is_active,
        )
        session.add(package)
        await session.flush()
        await session.refresh(package)
        logger.debug("Created addon package: id=%s", package.id)
        return package

    async def update_package(
        self,
        session: AsyncSession,
        package: AddonPackage,
        **kwargs
    ) -> AddonPackage:
        """Update addon package fields."""
        logger.debug("Updating addon package: id=%s fields=%s", package.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(package, key, value)
        await session.flush()
        await session.refresh(package)
        logger.debug("Updated addon package: id=%s", package.id)
        return package

    async def delete_package(self, session: AsyncSession, package: AddonPackage) -> None:
        """Delete an addon package."""
        logger.debug("Deleting addon package: id=%s", package.id)
        await session.delete(package)
        await session.flush()
        logger.debug("Deleted addon package: id=%s", package.id)

