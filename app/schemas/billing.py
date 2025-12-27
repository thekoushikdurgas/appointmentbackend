"""Pydantic schemas for billing and subscription management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionPeriod(BaseModel):
    """Schema for a subscription period (monthly, quarterly, yearly)."""
    
    period: str = Field(..., description="Billing period (monthly, quarterly, yearly)")
    credits: int = Field(..., description="Credits included in this period")
    rate_per_credit: float = Field(..., description="Rate per credit")
    price: float = Field(..., description="Price for this period")
    savings: Optional[dict] = Field(None, description="Savings information (amount and percentage)")


class SubscriptionPlanResponse(BaseModel):
    """Schema for a subscription plan with all periods."""
    
    tier: str = Field(..., description="Plan tier (5k, 25k, 100k, etc.)")
    name: str = Field(..., description="Plan display name")
    category: str = Field(..., description="Plan category (STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE)")
    periods: dict[str, SubscriptionPeriod] = Field(..., description="Pricing for all periods")


class AddonPackageResponse(BaseModel):
    """Schema for an addon credit package."""
    
    id: str = Field(..., description="Package identifier")
    name: str = Field(..., description="Package display name")
    credits: int = Field(..., description="Credits in this package")
    rate_per_credit: float = Field(..., description="Rate per credit")
    price: float = Field(..., description="Package price")


class BillingPlan(BaseModel):
    """Schema for a billing plan (legacy compatibility)."""

    id: str = Field(..., description="Plan identifier")
    name: str = Field(..., description="Plan display name")
    price: float = Field(..., description="Monthly price in USD")
    credits: int = Field(..., description="Credits included per month")
    features: list[str] = Field(default_factory=list, description="Plan features")


class BillingInfoResponse(BaseModel):
    """Schema for billing information response."""

    credits: int = Field(..., description="Current credit balance")
    credits_used: int = Field(default=0, description="Credits used this month")
    credits_limit: int = Field(..., description="Credits limit for current plan")
    subscription_plan: str = Field(..., description="Current subscription plan tier")
    subscription_period: Optional[str] = Field(None, description="Current subscription period (monthly, quarterly, yearly)")
    subscription_status: str = Field(..., description="Subscription status (active, cancelled, expired)")
    subscription_started_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    usage_percentage: float = Field(..., description="Percentage of credits used")

    model_config = ConfigDict(from_attributes=True)


class InvoiceItem(BaseModel):
    """Schema for an invoice item."""

    id: str = Field(..., description="Invoice ID")
    amount: float = Field(..., description="Invoice amount in USD")
    status: str = Field(..., description="Invoice status (paid, pending, failed)")
    created_at: datetime = Field(..., description="Invoice creation date")
    description: Optional[str] = Field(None, description="Invoice description")


class InvoiceListResponse(BaseModel):
    """Schema for invoice list response."""

    invoices: list[InvoiceItem] = Field(default_factory=list, description="List of invoices")
    total: int = Field(..., description="Total number of invoices")


class PlanListResponse(BaseModel):
    """Schema for available plans response (legacy)."""

    plans: list[BillingPlan] = Field(default_factory=list, description="Available plans")


class SubscriptionPlansResponse(BaseModel):
    """Schema for subscription plans response."""

    plans: list[SubscriptionPlanResponse] = Field(default_factory=list, description="Available subscription plans")


class AddonPackagesResponse(BaseModel):
    """Schema for addon packages response."""

    packages: list[AddonPackageResponse] = Field(default_factory=list, description="Available addon packages")


class SubscribeRequest(BaseModel):
    """Schema for subscription request."""

    tier: str = Field(..., description="Subscription tier (5k, 25k, 100k, 500k, 1M, 5M, 10M)")
    period: str = Field(..., description="Billing period (monthly, quarterly, yearly)")


class SubscribeResponse(BaseModel):
    """Schema for subscription response."""

    message: str = Field(..., description="Success message")
    subscription_plan: str = Field(..., description="New subscription plan tier")
    subscription_period: str = Field(..., description="Subscription period")
    credits: int = Field(..., description="Credits allocated")
    subscription_ends_at: Optional[datetime] = None


class AddonPurchaseRequest(BaseModel):
    """Schema for addon purchase request."""

    package_id: str = Field(..., description="Addon package ID (small, basic, standard, plus, pro, advanced, premium)")


class AddonPurchaseResponse(BaseModel):
    """Schema for addon purchase response."""

    message: str = Field(..., description="Success message")
    package: str = Field(..., description="Package ID")
    credits_added: int = Field(..., description="Credits added")
    total_credits: int = Field(..., description="Total credits after purchase")


class CancelSubscriptionResponse(BaseModel):
    """Schema for cancel subscription response."""

    message: str = Field(..., description="Success message")
    subscription_status: str = Field(..., description="Updated subscription status")


# Admin CRUD Schemas for Subscription Plans
class SubscriptionPeriodCreate(BaseModel):
    """Schema for creating a subscription plan period."""

    period: str = Field(..., description="Billing period (monthly, quarterly, yearly)")
    credits: int = Field(..., ge=1, description="Credits included in this period")
    rate_per_credit: float = Field(..., ge=0, description="Rate per credit")
    price: float = Field(..., ge=0, description="Price for this period")
    savings_amount: Optional[float] = Field(None, ge=0, description="Savings amount")
    savings_percentage: Optional[int] = Field(None, ge=0, le=100, description="Savings percentage")


class SubscriptionPeriodUpdate(BaseModel):
    """Schema for updating a subscription plan period."""

    credits: Optional[int] = Field(None, ge=1, description="Credits included in this period")
    rate_per_credit: Optional[float] = Field(None, ge=0, description="Rate per credit")
    price: Optional[float] = Field(None, ge=0, description="Price for this period")
    savings_amount: Optional[float] = Field(None, ge=0, description="Savings amount")
    savings_percentage: Optional[int] = Field(None, ge=0, le=100, description="Savings percentage")


class SubscriptionPlanCreate(BaseModel):
    """Schema for creating a subscription plan."""

    tier: str = Field(..., description="Plan tier (5k, 25k, 100k, etc.)")
    name: str = Field(..., description="Plan display name")
    category: str = Field(..., description="Plan category (STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE)")
    is_active: bool = Field(True, description="Whether the plan is active")
    periods: list[SubscriptionPeriodCreate] = Field(..., description="Pricing periods for this plan")


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating a subscription plan."""

    name: Optional[str] = Field(None, description="Plan display name")
    category: Optional[str] = Field(None, description="Plan category")
    is_active: Optional[bool] = Field(None, description="Whether the plan is active")


# Admin CRUD Schemas for Addon Packages
class AddonPackageCreate(BaseModel):
    """Schema for creating an addon package."""

    id: str = Field(..., description="Package identifier")
    name: str = Field(..., description="Package display name")
    credits: int = Field(..., ge=1, description="Credits in this package")
    rate_per_credit: float = Field(..., ge=0, description="Rate per credit")
    price: float = Field(..., ge=0, description="Package price")
    is_active: bool = Field(True, description="Whether the package is active")


class AddonPackageUpdate(BaseModel):
    """Schema for updating an addon package."""

    name: Optional[str] = Field(None, description="Package display name")
    credits: Optional[int] = Field(None, ge=1, description="Credits in this package")
    rate_per_credit: Optional[float] = Field(None, ge=0, description="Rate per credit")
    price: Optional[float] = Field(None, ge=0, description="Package price")
    is_active: Optional[bool] = Field(None, description="Whether the package is active")