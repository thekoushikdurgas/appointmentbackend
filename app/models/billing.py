"""SQLAlchemy models for billing, subscription plans, and addon packages."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    pass


class SubscriptionPlan(Base):
    """Subscription plan model for different credit tiers."""

    __tablename__ = "subscription_plans"

    tier: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    periods: Mapped[list["SubscriptionPlanPeriod"]] = relationship(
        "SubscriptionPlanPeriod",
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_subscription_plans_tier", "tier"),
        Index("idx_subscription_plans_category", "category"),
        Index("idx_subscription_plans_is_active", "is_active"),
    )


class SubscriptionPlanPeriod(Base):
    """Subscription plan period pricing (monthly, quarterly, yearly)."""

    __tablename__ = "subscription_plan_periods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_tier: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("subscription_plans.tier", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, quarterly, yearly
    credits: Mapped[int] = mapped_column(nullable=False)
    rate_per_credit: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    savings_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    savings_percentage: Mapped[Optional[int]] = mapped_column()  # Percentage as integer (e.g., 10 for 10%)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    plan: Mapped["SubscriptionPlan"] = relationship(
        "SubscriptionPlan",
        back_populates="periods"
    )

    __table_args__ = (
        Index("idx_subscription_plan_periods_plan_tier", "plan_tier"),
        Index("idx_subscription_plan_periods_period", "period"),
        Index("idx_subscription_plan_periods_unique", "plan_tier", "period", unique=True),
    )


class AddonPackage(Base):
    """Addon credit package model."""

    __tablename__ = "addon_packages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(nullable=False)
    rate_per_credit: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_addon_packages_id", "id"),
        Index("idx_addon_packages_is_active", "is_active"),
    )

