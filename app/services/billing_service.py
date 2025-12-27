"""Service layer for billing and subscription management."""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile
from app.repositories.billing import (
    AddonPackageRepository,
    SubscriptionPlanPeriodRepository,
    SubscriptionPlanRepository,
)
from app.repositories.user import UserProfileRepository
from app.utils.logger import get_logger, log_error, log_api_error

logger = get_logger(__name__)

# Billing periods
MONTHLY = "monthly"
QUARTERLY = "quarterly"
YEARLY = "yearly"

# Subscription tiers with all periods
SUBSCRIPTION_PLANS = {
    "5k": {
        "tier": "5k",
        "name": "5k Credits Tier",
        "category": "STARTER",
        "periods": {
            MONTHLY: {
                "credits": 5000,
                "rate_per_credit": 0.002,
                "price": 10.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 15000,
                "rate_per_credit": 0.0018,
                "price": 27.0,
                "savings": {"amount": 3.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 60000,
                "rate_per_credit": 0.0016,
                "price": 96.0,
                "savings": {"amount": 24.0, "percentage": 20},
            },
        },
    },
    "25k": {
        "tier": "25k",
        "name": "25k Credits Tier",
        "category": "STARTER",
        "periods": {
            MONTHLY: {
                "credits": 25000,
                "rate_per_credit": 0.0012,
                "price": 30.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 75000,
                "rate_per_credit": 0.00108,
                "price": 81.0,
                "savings": {"amount": 9.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 300000,
                "rate_per_credit": 0.00096,
                "price": 288.0,
                "savings": {"amount": 72.0, "percentage": 20},
            },
        },
    },
    "100k": {
        "tier": "100k",
        "name": "100k Credits Tier",
        "category": "PROFESSIONAL",
        "periods": {
            MONTHLY: {
                "credits": 100000,
                "rate_per_credit": 0.00099,
                "price": 99.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 300000,
                "rate_per_credit": 0.000891,
                "price": 267.0,
                "savings": {"amount": 30.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 1200000,
                "rate_per_credit": 0.000792,
                "price": 950.0,
                "savings": {"amount": 238.0, "percentage": 20},
            },
        },
    },
    "500k": {
        "tier": "500k",
        "name": "500k Credits Tier",
        "category": "PROFESSIONAL",
        "periods": {
            MONTHLY: {
                "credits": 500000,
                "rate_per_credit": 0.000398,
                "price": 199.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 1500000,
                "rate_per_credit": 0.0003582,
                "price": 537.0,
                "savings": {"amount": 60.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 6000000,
                "rate_per_credit": 0.0003184,
                "price": 1910.0,
                "savings": {"amount": 478.0, "percentage": 20},
            },
        },
    },
    "1M": {
        "tier": "1M",
        "name": "1M Credits Tier",
        "category": "BUSINESS",
        "periods": {
            MONTHLY: {
                "credits": 1000000,
                "rate_per_credit": 0.000299,
                "price": 299.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 3000000,
                "rate_per_credit": 0.0002691,
                "price": 807.0,
                "savings": {"amount": 90.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 12000000,
                "rate_per_credit": 0.0002392,
                "price": 2870.0,
                "savings": {"amount": 718.0, "percentage": 20},
            },
        },
    },
    "5M": {
        "tier": "5M",
        "name": "5M Credits Tier",
        "category": "BUSINESS",
        "periods": {
            MONTHLY: {
                "credits": 5000000,
                "rate_per_credit": 0.0001998,
                "price": 999.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 15000000,
                "rate_per_credit": 0.0001798,
                "price": 2697.0,
                "savings": {"amount": 300.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 60000000,
                "rate_per_credit": 0.0001598,
                "price": 9590.0,
                "savings": {"amount": 2398.0, "percentage": 20},
            },
        },
    },
    "10M": {
        "tier": "10M",
        "name": "10M Credits Tier",
        "category": "ENTERPRISE",
        "periods": {
            MONTHLY: {
                "credits": 10000000,
                "rate_per_credit": 0.0001599,
                "price": 1599.0,
                "savings": None,
            },
            QUARTERLY: {
                "credits": 30000000,
                "rate_per_credit": 0.0001439,
                "price": 4317.0,
                "savings": {"amount": 480.0, "percentage": 10},
            },
            YEARLY: {
                "credits": 120000000,
                "rate_per_credit": 0.0001279,
                "price": 15350.0,
                "savings": {"amount": 3838.0, "percentage": 20},
            },
        },
    },
}

# Addon credit packages (available for all tiers)
ADDON_PACKAGES = {
    "small": {
        "id": "small",
        "name": "Small",
        "credits": 5000,
        "rate_per_credit": 0.002,
        "price": 10.0,
    },
    "basic": {
        "id": "basic",
        "name": "Basic",
        "credits": 25000,
        "rate_per_credit": 0.0012,
        "price": 30.0,
    },
    "standard": {
        "id": "standard",
        "name": "Standard",
        "credits": 100000,
        "rate_per_credit": 0.00099,
        "price": 99.0,
    },
    "plus": {
        "id": "plus",
        "name": "Plus",
        "credits": 500000,
        "rate_per_credit": 0.000398,
        "price": 199.0,
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "credits": 1000000,
        "rate_per_credit": 0.000299,
        "price": 299.0,
    },
    "advanced": {
        "id": "advanced",
        "name": "Advanced",
        "credits": 5000000,
        "rate_per_credit": 0.0001998,
        "price": 999.0,
    },
    "premium": {
        "id": "premium",
        "name": "Premium",
        "credits": 10000000,
        "rate_per_credit": 0.0001599,
        "price": 1599.0,
    },
}


def calculate_subscription_end_date(period: str, start_date: Optional[datetime] = None) -> datetime:
    """
    Calculate subscription end date based on billing period.
    
    Args:
        period: Billing period (monthly, quarterly, yearly)
        start_date: Start date (defaults to now)
    
    Returns:
        End date for the subscription
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc)
    
    if period == MONTHLY:
        return start_date + timedelta(days=30)
    elif period == QUARTERLY:
        return start_date + timedelta(days=90)
    elif period == YEARLY:
        return start_date + timedelta(days=365)
    else:
        raise ValueError(f"Invalid period: {period}")


class BillingService:
    """Business logic for billing and subscription management."""

    def __init__(
        self,
        profile_repository: Optional[UserProfileRepository] = None,
        plan_repository: Optional[SubscriptionPlanRepository] = None,
        period_repository: Optional[SubscriptionPlanPeriodRepository] = None,
        addon_repository: Optional[AddonPackageRepository] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        self.profile_repo = profile_repository or UserProfileRepository()
        self.plan_repo = plan_repository or SubscriptionPlanRepository()
        self.period_repo = period_repository or SubscriptionPlanPeriodRepository()
        self.addon_repo = addon_repository or AddonPackageRepository()

    async def get_billing_info(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> dict:
        """
        Get billing information for a user.
        
        Returns billing info including credits, subscription, and usage.
        """
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Get subscription tier and period from profile
        subscription_tier = profile.subscription_plan or "free"
        subscription_period = profile.subscription_period or MONTHLY
        
        # Calculate credits limit based on subscription
        if subscription_tier == "free":
            credits_limit = 50  # Initial free credits
        else:
            # Try to get from database first
            plan = await self.plan_repo.get_by_tier(session, subscription_tier)
            if plan and plan.is_active:
                period_obj = await self.period_repo.get_by_plan_and_period(session, subscription_tier, subscription_period)
                if not period_obj:
                    # Fallback to monthly if period not found
                    period_obj = await self.period_repo.get_by_plan_and_period(session, subscription_tier, MONTHLY)
                if period_obj:
                    credits_limit = period_obj.credits
                else:
                    credits_limit = 50  # Default to free tier
            elif subscription_tier in SUBSCRIPTION_PLANS:
                # Fallback to hardcoded data
                plan_data = SUBSCRIPTION_PLANS[subscription_tier]
                period_data = plan_data["periods"].get(subscription_period, plan_data["periods"][MONTHLY])
                credits_limit = period_data["credits"]
            else:
                credits_limit = 50  # Default to free tier
        
        current_credits = max(0, profile.credits or 0)
        credits_used = max(0, credits_limit - current_credits)
        credits_used = min(credits_used, credits_limit)
        usage_percentage = (credits_used / credits_limit * 100) if credits_limit > 0 else 0.0
        
        return {
            "credits": current_credits,
            "credits_used": credits_used,
            "credits_limit": credits_limit,
            "subscription_plan": subscription_tier,
            "subscription_period": subscription_period,
            "subscription_status": profile.subscription_status or "active",
            "subscription_started_at": profile.subscription_started_at,
            "subscription_ends_at": profile.subscription_ends_at,
            "usage_percentage": round(usage_percentage, 2)
        }

    async def get_subscription_plans(self, session: Optional[AsyncSession] = None) -> list[dict]:
        """
        Get all available subscription plans with all periods (optimized).
        
        Uses hardcoded data directly for maximum performance since subscription plans
        are static data. This bypasses database queries entirely, resulting in
        sub-millisecond response times.
        """
        plans = []
        for plan_data in SUBSCRIPTION_PLANS.values():
            formatted_plan = {
                "tier": plan_data["tier"],
                "name": plan_data["name"],
                "category": plan_data["category"],
                "periods": {}
            }
            for period_key, period_data in plan_data["periods"].items():
                formatted_plan["periods"][period_key] = {
                    "period": period_key,
                    "credits": period_data["credits"],
                    "rate_per_credit": period_data["rate_per_credit"],
                    "price": period_data["price"],
                    "savings": period_data.get("savings")
                }
            plans.append(formatted_plan)
        return plans
        
        # OPTIMIZATION 2 & 3: Database path with caching and single JOIN query (if needed in future)
        # This code is kept for reference but currently bypassed for maximum performance
        # Uncomment if you need to use database instead of hardcoded data
        """
        cache = get_query_cache()
        cache_key = "subscription_plans_all"
        
        # Try cache first
        cached_plans = await cache.get(cache_key)
        if cached_plans is not None:
            return cached_plans
        
        # Try to get from database if session is provided
        if session:
            try:
                # OPTIMIZATION: Single query with JOIN instead of N+1
                query_start = time.time()
                db_plans = await self.plan_repo.list_all_with_periods(session, include_inactive=False)
                query_time = (time.time() - query_start) * 1000
                
                if db_plans:
                    plans = []
                    for plan in db_plans:
                        formatted_plan = {
                            "tier": plan.tier,
                            "name": plan.name,
                            "category": plan.category,
                            "periods": {}
                        }
                        # Periods are already loaded via joinedload
                        for period_obj in plan.periods:
                            savings = None
                            if period_obj.savings_amount or period_obj.savings_percentage:
                                savings = {}
                                if period_obj.savings_amount:
                                    savings["amount"] = float(period_obj.savings_amount)
                                if period_obj.savings_percentage:
                                    savings["percentage"] = period_obj.savings_percentage
                            
                            formatted_plan["periods"][period_obj.period] = {
                                "period": period_obj.period,
                                "credits": period_obj.credits,
                                "rate_per_credit": float(period_obj.rate_per_credit),
                                "price": float(period_obj.price),
                                "savings": savings
                            }
                        plans.append(formatted_plan)
                    
                    # Cache the result (5 minute TTL)
                    await cache.set(cache_key, plans, ttl=300)
                    return plans
            except Exception as exc:
                # Failed to get plans from database, falling back to hardcoded data
                logger.warning(
                    "Failed to get subscription plans from database, using fallback",
                    exc_info=True,
                    extra={
                        "context": {
                            "operation": "get_subscription_plans",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    }
                )
        
        # Fallback to hardcoded data
        plans = []
        for plan_data in SUBSCRIPTION_PLANS.values():
            formatted_plan = {
                "tier": plan_data["tier"],
                "name": plan_data["name"],
                "category": plan_data["category"],
                "periods": {}
            }
            for period_key, period_data in plan_data["periods"].items():
                formatted_plan["periods"][period_key] = {
                    "period": period_key,
                    "credits": period_data["credits"],
                    "rate_per_credit": period_data["rate_per_credit"],
                    "price": period_data["price"],
                    "savings": period_data.get("savings")
                }
            plans.append(formatted_plan)
        return plans
        """

    async def get_addon_packages(self, session: Optional[AsyncSession] = None) -> list[dict]:
        """Get all available addon credit packages."""
        # Try to get from database if session is provided
        if session:
            try:
                db_packages = await self.addon_repo.list_all(session, include_inactive=False)
                if db_packages:
                    packages = []
                    for package in db_packages:
                        packages.append({
                            "id": package.id,
                            "name": package.name,
                            "credits": package.credits,
                            "rate_per_credit": float(package.rate_per_credit),
                            "price": float(package.price),
                        })
                    return packages
            except Exception as exc:
                # Failed to get packages from database, falling back to hardcoded data
                logger.warning(
                    "Failed to get addon packages from database, using fallback",
                    exc_info=True,
                    extra={
                        "context": {
                            "operation": "get_addon_packages",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    }
                )
        
        # Fallback to hardcoded data
        return list(ADDON_PACKAGES.values())

    async def subscribe_to_plan(
        self,
        session: AsyncSession,
        user_id: str,
        tier: str,
        period: str,
    ) -> dict:
        """
        Subscribe a user to a subscription plan.
        
        Args:
            session: Database session
            user_id: User ID
            tier: Subscription tier (5k, 25k, 100k, etc.)
            period: Billing period (monthly, quarterly, yearly)
        
        Returns:
            Dictionary with subscription details
        """
        start_time = time.time()
        logger.info(
            "Subscription request",
            extra={
                "context": {
                    "user_id": user_id,
                    "tier": tier,
                    "period": period,
                }
            }
        )
        
        if period not in [MONTHLY, QUARTERLY, YEARLY]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period: {period}. Valid periods: {MONTHLY}, {QUARTERLY}, {YEARLY}"
            )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Try to get from database first
        plan = await self.plan_repo.get_by_tier(session, tier)
        period_obj = None
        plan_name = None
        period_data = None
        
        if plan and plan.is_active:
            period_obj = await self.period_repo.get_by_plan_and_period(session, tier, period)
            plan_name = plan.name
            # If period not found in database, fallback to hardcoded data
            if not period_obj:
                if tier not in SUBSCRIPTION_PLANS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid tier: {tier}. Valid tiers: {', '.join(SUBSCRIPTION_PLANS.keys())}"
                    )
                plan_data = SUBSCRIPTION_PLANS[tier]
                plan_name = plan_data["name"]
                period_data = plan_data["periods"].get(period)
                if not period_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid period: {period} for tier {tier}"
                    )
        else:
            # Fallback to hardcoded data
            if tier not in SUBSCRIPTION_PLANS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tier: {tier}. Valid tiers: {', '.join(SUBSCRIPTION_PLANS.keys())}"
                )
            plan_data = SUBSCRIPTION_PLANS[tier]
            plan_name = plan_data["name"]
            period_data = plan_data["periods"].get(period)
            if not period_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid period: {period} for tier {tier}"
                )
        
        # Get credits from period_obj or fallback data
        if period_obj:
            credits = period_obj.credits
        else:
            credits = period_data["credits"]
        
        # Update subscription
        now = datetime.now(timezone.utc)
        profile.subscription_plan = tier
        profile.subscription_period = period
        profile.subscription_status = "active"
        profile.subscription_started_at = now
        profile.subscription_ends_at = calculate_subscription_end_date(period, now)
        profile.credits = credits  # Set credits to plan amount
        
        await session.commit()
        await session.refresh(profile)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Subscription successful",
            extra={
                "context": {
                    "user_id": user_id,
                    "tier": tier,
                    "period": period,
                    "plan_name": plan_name,
                    "credits": credits,
                    "subscription_ends_at": profile.subscription_ends_at.isoformat() if profile.subscription_ends_at else None,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        return {
            "message": f"Successfully subscribed to {plan_name} ({period})",
            "subscription_plan": tier,
            "subscription_period": period,
            "credits": credits,
            "subscription_ends_at": profile.subscription_ends_at
        }

    async def purchase_addon_credits(
        self,
        session: AsyncSession,
        user_id: str,
        package_id: str,
    ) -> dict:
        """
        Purchase addon credits for a user.
        
        Args:
            session: Database session
            user_id: User ID
            package_id: Addon package ID (small, basic, standard, etc.)
        
        Returns:
            Dictionary with purchase details
        """
        start_time = time.time()
        logger.info(
            "Addon credit purchase request",
            extra={
                "context": {
                    "user_id": user_id,
                    "package_id": package_id,
                }
            }
        )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Try to get from database first
        package_obj = await self.addon_repo.get_by_id(session, package_id)
        if package_obj and package_obj.is_active:
            package_credits = package_obj.credits
        else:
            # Fallback to hardcoded data
            if package_id not in ADDON_PACKAGES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid package: {package_id}. Valid packages: {', '.join(ADDON_PACKAGES.keys())}"
                )
            package = ADDON_PACKAGES[package_id]
            package_credits = package["credits"]
        
        # Add credits to existing balance
        current_credits = profile.credits or 0
        profile.credits = current_credits + package_credits
        
        await session.commit()
        await session.refresh(profile)
        
        package_name = package_obj.name if package_obj else package.get("name", package_id)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Addon credit purchase successful",
            extra={
                "context": {
                    "user_id": user_id,
                    "package_id": package_id,
                    "package_name": package_name,
                    "credits_added": package_credits,
                    "total_credits": profile.credits,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        return {
            "message": f"Successfully purchased {package_name} addon package",
            "package": package_id,
            "credits_added": package_credits,
            "total_credits": profile.credits
        }

    async def cancel_subscription(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> dict:
        """
        Cancel a user's subscription.
        
        The subscription will remain active until the end of the billing period.
        """
        start_time = time.time()
        logger.info(
            "Subscription cancellation request",
            extra={
                "context": {
                    "user_id": user_id,
                }
            }
        )
        
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            logger.warning(
                "Subscription cancellation failed: user profile not found",
                extra={
                    "context": {
                        "user_id": user_id,
                    }
                }
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        if profile.subscription_status == "cancelled":
            log_api_error(
                endpoint="/api/v1/billing/cancel/",
                method="POST",
                status_code=400,
                error_type="BillingError",
                error_message="Cannot cancel - already cancelled",
                user_id=str(user_id),
                context={"current_plan": profile.subscription_plan, "subscription_status": profile.subscription_status}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is already cancelled"
            )
        
        # Mark as cancelled but keep active until end date
        previous_status = profile.subscription_status
        profile.subscription_status = "cancelled"
        
        await session.commit()
        await session.refresh(profile)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Subscription cancelled",
            extra={
                "context": {
                    "user_id": user_id,
                    "previous_status": previous_status,
                    "subscription_plan": profile.subscription_plan,
                    "subscription_ends_at": profile.subscription_ends_at.isoformat() if profile.subscription_ends_at else None,
                },
                "performance": {"duration_ms": duration_ms}
            }
        )
        
        return {
            "message": "Subscription cancelled. You will retain access until the end of your billing period.",
            "subscription_status": "cancelled"
        }

    async def get_invoices(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """
        Get invoice history for a user.
        
        This is a simplified implementation. In production, you would fetch
        invoices from a payment processor.
        """
        profile = await self.profile_repo.get_by_user_id(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Mock invoice data - in production, fetch from payment processor
        invoices = []
        
        if profile.subscription_started_at and profile.subscription_plan and profile.subscription_plan != "free":
            tier = profile.subscription_plan
            period = profile.subscription_period or MONTHLY
            
            if tier in SUBSCRIPTION_PLANS:
                plan = SUBSCRIPTION_PLANS[tier]
                period_data = plan["periods"].get(period, plan["periods"][MONTHLY])
                plan_price = period_data["price"]
                plan_name = plan["name"]
                
                # Generate invoices based on subscription history
                subscription_start = profile.subscription_started_at
                now = datetime.now(timezone.utc)
                end_date = profile.subscription_ends_at if profile.subscription_ends_at and profile.subscription_ends_at < now else now
                
                # Generate invoices based on period
                current_date = subscription_start
                invoice_number = 1
                days_per_period = 30 if period == MONTHLY else (90 if period == QUARTERLY else 365)
                
                while current_date < end_date and invoice_number <= 12:
                    if profile.subscription_status == "cancelled" and profile.subscription_ends_at and current_date >= profile.subscription_ends_at:
                        invoice_status = "failed"
                    elif current_date <= now:
                        invoice_status = "paid"
                    else:
                        invoice_status = "pending"
                    
                    invoices.append({
                        "id": f"inv_{user_id[:8]}_{invoice_number:03d}",
                        "amount": plan_price,
                        "status": invoice_status,
                        "created_at": current_date,
                        "description": f"Subscription to {plan_name} ({period})"
                    })
                    
                    current_date = current_date + timedelta(days=days_per_period)
                    invoice_number += 1
                
                # Sort invoices by date (newest first)
                invoices.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        total = len(invoices)
        paginated_invoices = invoices[offset:offset + limit]
        
        return {
            "invoices": paginated_invoices,
            "total": total
        }

    # Admin CRUD methods for Subscription Plans
    async def create_subscription_plan(
        self,
        session: AsyncSession,
        plan_data: dict,
    ) -> dict:
        """Create a new subscription plan with periods (Super Admin only)."""
        # Check if plan already exists
        existing_plan = await self.plan_repo.get_by_tier(session, plan_data["tier"])
        if existing_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan with tier {plan_data['tier']} already exists"
            )
        
        # Create plan
        plan = await self.plan_repo.create_plan(
            session,
            tier=plan_data["tier"],
            name=plan_data["name"],
            category=plan_data["category"],
            is_active=plan_data.get("is_active", True),
        )
        
        # Create periods
        for period_data in plan_data["periods"]:
            await self.period_repo.create_period(
                session,
                plan_tier=plan.tier,
                period=period_data["period"],
                credits=period_data["credits"],
                rate_per_credit=period_data["rate_per_credit"],
                price=period_data["price"],
                savings_amount=period_data.get("savings_amount"),
                savings_percentage=period_data.get("savings_percentage"),
            )
        
        await session.commit()
        await session.refresh(plan)
        
        return {"message": f"Plan {plan.tier} created successfully", "tier": plan.tier}

    async def update_subscription_plan(
        self,
        session: AsyncSession,
        tier: str,
        update_data: dict,
    ) -> dict:
        """Update a subscription plan (Super Admin only)."""
        plan = await self.plan_repo.get_by_tier(session, tier)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan with tier {tier} not found"
            )
        
        await self.plan_repo.update_plan(session, plan, **update_data)
        await session.commit()
        await session.refresh(plan)
        
        return {"message": f"Plan {tier} updated successfully", "tier": tier}

    async def delete_subscription_plan(
        self,
        session: AsyncSession,
        tier: str,
    ) -> dict:
        """Delete a subscription plan (Super Admin only)."""
        plan = await self.plan_repo.get_by_tier(session, tier)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan with tier {tier} not found"
            )
        
        await self.plan_repo.delete_plan(session, plan)
        await session.commit()
        
        return {"message": f"Plan {tier} deleted successfully"}

    async def create_subscription_plan_period(
        self,
        session: AsyncSession,
        tier: str,
        period_data: dict,
    ) -> dict:
        """Create or update a subscription plan period (Super Admin only)."""
        plan = await self.plan_repo.get_by_tier(session, tier)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan with tier {tier} not found"
            )
        
        # Check if period exists
        existing_period = await self.period_repo.get_by_plan_and_period(session, tier, period_data["period"])
        if existing_period:
            # Update existing period
            await self.period_repo.update_period(
                session,
                existing_period,
                credits=period_data.get("credits"),
                rate_per_credit=period_data.get("rate_per_credit"),
                price=period_data.get("price"),
                savings_amount=period_data.get("savings_amount"),
                savings_percentage=period_data.get("savings_percentage"),
            )
            message = f"Period {period_data['period']} updated successfully"
        else:
            # Create new period
            await self.period_repo.create_period(
                session,
                plan_tier=tier,
                period=period_data["period"],
                credits=period_data["credits"],
                rate_per_credit=period_data["rate_per_credit"],
                price=period_data["price"],
                savings_amount=period_data.get("savings_amount"),
                savings_percentage=period_data.get("savings_percentage"),
            )
            message = f"Period {period_data['period']} created successfully"
        
        await session.commit()
        return {"message": message, "tier": tier, "period": period_data["period"]}

    async def delete_subscription_plan_period(
        self,
        session: AsyncSession,
        tier: str,
        period: str,
    ) -> dict:
        """Delete a subscription plan period (Super Admin only)."""
        period_obj = await self.period_repo.get_by_plan_and_period(session, tier, period)
        if not period_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Period {period} not found for plan {tier}"
            )
        
        await self.period_repo.delete_period(session, period_obj)
        await session.commit()
        
        return {"message": f"Period {period} deleted successfully"}

    # Admin CRUD methods for Addon Packages
    async def create_addon_package(
        self,
        session: AsyncSession,
        package_data: dict,
    ) -> dict:
        """Create a new addon package (Super Admin only)."""
        # Check if package already exists
        existing_package = await self.addon_repo.get_by_id(session, package_data["id"])
        if existing_package:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Package with id {package_data['id']} already exists"
            )
        
        package = await self.addon_repo.create_package(
            session,
            package_id=package_data["id"],
            name=package_data["name"],
            credits=package_data["credits"],
            rate_per_credit=package_data["rate_per_credit"],
            price=package_data["price"],
            is_active=package_data.get("is_active", True),
        )
        
        await session.commit()
        await session.refresh(package)
        
        return {"message": f"Package {package.id} created successfully", "id": package.id}

    async def update_addon_package(
        self,
        session: AsyncSession,
        package_id: str,
        update_data: dict,
    ) -> dict:
        """Update an addon package (Super Admin only)."""
        package = await self.addon_repo.get_by_id(session, package_id)
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with id {package_id} not found"
            )
        
        await self.addon_repo.update_package(session, package, **update_data)
        await session.commit()
        await session.refresh(package)
        
        return {"message": f"Package {package_id} updated successfully", "id": package_id}

    async def delete_addon_package(
        self,
        session: AsyncSession,
        package_id: str,
    ) -> dict:
        """Delete an addon package (Super Admin only)."""
        package = await self.addon_repo.get_by_id(session, package_id)
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with id {package_id} not found"
            )
        
        await self.addon_repo.delete_package(session, package)
        await session.commit()
        
        return {"message": f"Package {package_id} deleted successfully"}
