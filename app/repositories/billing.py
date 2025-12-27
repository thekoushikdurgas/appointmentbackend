"""Repository providing billing-specific query utilities."""

import time
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.billing import AddonPackage, SubscriptionPlan, SubscriptionPlanPeriod
from app.repositories.base import AsyncRepository
from app.utils.logger import get_logger, log_database_query, log_database_error

logger = get_logger(__name__)


class SubscriptionPlanRepository(AsyncRepository[SubscriptionPlan]):
    """Data access helpers for subscription plan queries."""

    def __init__(self) -> None:
        """Initialize the repository for the SubscriptionPlan model."""
        super().__init__(SubscriptionPlan)

    async def get_by_tier(self, session: AsyncSession, tier: str) -> Optional[SubscriptionPlan]:
        """Retrieve a subscription plan by tier."""
        start_time = time.time()
        try:
            stmt: Select[tuple[SubscriptionPlan]] = select(self.model).where(self.model.tier == tier)
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"tier": tier},
                result_count=1 if plan else 0,
                duration_ms=duration_ms,
                logger_name="app.repositories.billing",
            )
            
            return plan
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"tier": tier, "method": "get_by_tier"}
            )
            raise

    async def list_all(self, session: AsyncSession, include_inactive: bool = False) -> list[SubscriptionPlan]:
        """List all subscription plans."""
        start_time = time.time()
        try:
            stmt: Select[tuple[SubscriptionPlan]] = select(self.model)
            if not include_inactive:
                stmt = stmt.where(self.model.is_active == True)
            stmt = stmt.order_by(self.model.tier)
            result = await session.execute(stmt)
            plans = list(result.scalars().all())
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"include_inactive": include_inactive},
                result_count=len(plans),
                duration_ms=duration_ms,
                logger_name="app.repositories.billing",
            )
            
            return plans
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"include_inactive": include_inactive, "method": "list_all"}
            )
            raise

    async def list_all_with_periods(self, session: AsyncSession, include_inactive: bool = False) -> list[SubscriptionPlan]:
        """List all subscription plans with their periods in a single query (optimized)."""
        stmt: Select[tuple[SubscriptionPlan]] = select(self.model).options(
            joinedload(self.model.periods)
        )
        if not include_inactive:
            stmt = stmt.where(self.model.is_active == True)
        stmt = stmt.order_by(self.model.tier)
        result = await session.execute(stmt)
        plans = list(result.unique().scalars().all())
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
        start_time = time.time()
        try:
            plan = SubscriptionPlan(
                tier=tier,
                name=name,
                category=category,
                is_active=is_active,
            )
            session.add(plan)
            await session.flush()
            await session.refresh(plan)
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="INSERT",
                table=self.model.__tablename__,
                filters={"tier": tier, "category": category},
                result_count=1,
                duration_ms=duration_ms,
                logger_name="app.repositories.billing",
            )
            
            return plan
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="INSERT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"tier": tier, "category": category, "method": "create_plan"}
            )
            raise

    async def update_plan(
        self,
        session: AsyncSession,
        plan: SubscriptionPlan,
        **kwargs
    ) -> SubscriptionPlan:
        """Update subscription plan fields."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(plan, key, value)
        await session.flush()
        await session.refresh(plan)
        return plan

    async def delete_plan(self, session: AsyncSession, plan: SubscriptionPlan) -> None:
        """Delete a subscription plan (cascade will delete periods)."""
        await session.delete(plan)
        await session.flush()


class SubscriptionPlanPeriodRepository(AsyncRepository[SubscriptionPlanPeriod]):
    """Data access helpers for subscription plan period queries."""

    def __init__(self) -> None:
        """Initialize the repository for the SubscriptionPlanPeriod model."""
        super().__init__(SubscriptionPlanPeriod)

    async def get_by_plan_and_period(
        self,
        session: AsyncSession,
        plan_tier: str,
        period: str,
    ) -> Optional[SubscriptionPlanPeriod]:
        """Retrieve a period by plan tier and period."""
        stmt: Select[tuple[SubscriptionPlanPeriod]] = select(self.model).where(
            self.model.plan_tier == plan_tier,
            self.model.period == period
        )
        result = await session.execute(stmt)
        period_obj = result.scalar_one_or_none()
        return period_obj

    async def list_by_plan(self, session: AsyncSession, plan_tier: str) -> list[SubscriptionPlanPeriod]:
        """List all periods for a subscription plan."""
        stmt: Select[tuple[SubscriptionPlanPeriod]] = select(self.model).where(
            self.model.plan_tier == plan_tier
        ).order_by(self.model.period)
        result = await session.execute(stmt)
        periods = list(result.scalars().all())
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
        return period_obj

    async def update_period(
        self,
        session: AsyncSession,
        period_obj: SubscriptionPlanPeriod,
        **kwargs
    ) -> SubscriptionPlanPeriod:
        """Update subscription plan period fields."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(period_obj, key, value)
        await session.flush()
        await session.refresh(period_obj)
        return period_obj

    async def delete_period(self, session: AsyncSession, period_obj: SubscriptionPlanPeriod) -> None:
        """Delete a subscription plan period."""
        await session.delete(period_obj)
        await session.flush()


class AddonPackageRepository(AsyncRepository[AddonPackage]):
    """Data access helpers for addon package queries."""

    def __init__(self) -> None:
        """Initialize the repository for the AddonPackage model."""
        super().__init__(AddonPackage)

    async def get_by_id(self, session: AsyncSession, package_id: str) -> Optional[AddonPackage]:
        """Retrieve an addon package by ID."""
        stmt: Select[tuple[AddonPackage]] = select(self.model).where(self.model.id == package_id)
        result = await session.execute(stmt)
        package = result.scalar_one_or_none()
        return package

    async def list_all(self, session: AsyncSession, include_inactive: bool = False) -> list[AddonPackage]:
        """List all addon packages."""
        stmt: Select[tuple[AddonPackage]] = select(self.model)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active == True)
        stmt = stmt.order_by(self.model.price)
        result = await session.execute(stmt)
        packages = list(result.scalars().all())
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
        return package

    async def update_package(
        self,
        session: AsyncSession,
        package: AddonPackage,
        **kwargs
    ) -> AddonPackage:
        """Update addon package fields."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(package, key, value)
        await session.flush()
        await session.refresh(package)
        return package

    async def delete_package(self, session: AsyncSession, package: AddonPackage) -> None:
        """Delete an addon package."""
        await session.delete(package)
        await session.flush()

