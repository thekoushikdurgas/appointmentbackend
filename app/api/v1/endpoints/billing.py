"""Billing API endpoints for subscription and usage management."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import (
    AddonPackageCreate,
    AddonPackagesResponse,
    AddonPackageUpdate,
    AddonPurchaseRequest,
    AddonPurchaseResponse,
    BillingInfoResponse,
    CancelSubscriptionResponse,
    InvoiceListResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionPeriodCreate,
    SubscriptionPlanCreate,
    SubscriptionPlansResponse,
    SubscriptionPlanUpdate,
)
from app.schemas.filters import UserFilterParams
from app.services.billing_service import BillingService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])
service = BillingService()


async def resolve_billing_filters(request: Request) -> UserFilterParams:
    """Build billing filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return UserFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/", response_model=BillingInfoResponse)
async def get_billing_info(
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BillingInfoResponse:
    """
    Get billing information for the currently authenticated user.
    
    Returns credits, subscription status, and usage information.
    """
    try:
        billing_info = await service.get_billing_info(session, current_user.uuid)
        return BillingInfoResponse(**billing_info)
    except HTTPException:
        raise
    except Exception as exc:
        # Error retrieving billing info
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing information"
        ) from exc


@router.get("/plans/", response_model=SubscriptionPlansResponse)
async def get_subscription_plans(
    filters: UserFilterParams = Depends(resolve_billing_filters),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionPlansResponse:
    """
    Get list of all available subscription plans with all periods.
    
    Returns all subscription tiers (5k, 25k, 100k, etc.) with monthly, quarterly, and yearly pricing.
    Optimized to use hardcoded data for sub-millisecond response times.
    """
    try:
        plans = await service.get_subscription_plans(session)
        return SubscriptionPlansResponse(plans=plans)
    except Exception as exc:
        # Error retrieving subscription plans
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription plans"
        ) from exc


@router.get("/addons/", response_model=AddonPackagesResponse)
async def get_addon_packages(
    filters: UserFilterParams = Depends(resolve_billing_filters),
    session: AsyncSession = Depends(get_db),
) -> AddonPackagesResponse:
    """
    Get list of all available addon credit packages.
    
    Returns all addon packages (Small, Basic, Standard, Plus, Pro, Advanced, Premium).
    """
    # Get addon packages request
    
    try:
        packages = await service.get_addon_packages(session)
        # Addon packages retrieved with count
        return AddonPackagesResponse(packages=packages)
    except Exception as exc:
        # Error handling: Get addon packages failed with exception details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve addon packages"
        ) from exc


@router.post("/subscribe/", response_model=SubscribeResponse, status_code=status.HTTP_200_OK)
async def subscribe_to_plan(
    request: SubscribeRequest,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SubscribeResponse:
    """
    Subscribe the currently authenticated user to a subscription plan.
    
    Requires tier (5k, 25k, 100k, etc.) and period (monthly, quarterly, yearly).
    This is a simplified implementation. In production, you would integrate
    with a payment processor like Stripe to handle actual payments.
    """
    try:
        result = await service.subscribe_to_plan(session, current_user.uuid, request.tier, request.period)
        return SubscribeResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        # Error subscribing to plan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to plan"
        ) from exc


@router.post("/addon/", response_model=AddonPurchaseResponse, status_code=status.HTTP_200_OK)
async def purchase_addon(
    request: AddonPurchaseRequest,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AddonPurchaseResponse:
    """
    Purchase addon credits for the currently authenticated user.
    
    Requires package_id (small, basic, standard, plus, pro, advanced, premium).
    This is a simplified implementation. In production, you would integrate
    with a payment processor like Stripe to handle actual payments.
    """
    try:
        result = await service.purchase_addon_credits(session, current_user.uuid, request.package_id)
        return AddonPurchaseResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        # Error purchasing addon credits
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purchase addon credits"
        ) from exc


@router.post("/cancel/", response_model=CancelSubscriptionResponse, status_code=status.HTTP_200_OK)
async def cancel_subscription(
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CancelSubscriptionResponse:
    """
    Cancel the currently authenticated user's subscription.
    
    The subscription will remain active until the end of the current billing period.
    """
    # Cancel subscription request with user ID
    
    try:
        result = await service.cancel_subscription(session, current_user.uuid)
        # Subscription cancelled with user ID
        return CancelSubscriptionResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        # Error handling: Cancel subscription failed with exception details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        ) from exc


@router.get("/invoices/", response_model=InvoiceListResponse)
async def get_invoices(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of invoices to return"),
    offset: int = Query(0, ge=0, description="Number of invoices to skip"),
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """
    Get invoice history for the currently authenticated user.
    
    Returns paginated list of invoices with status and amounts.
    """
    try:
        result = await service.get_invoices(session, current_user.uuid, limit, offset)
        return InvoiceListResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        # Error retrieving invoices
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invoices"
        ) from exc


# Admin endpoints for managing subscription plans and addon packages (Super Admin only)
@router.get("/admin/plans/", response_model=SubscriptionPlansResponse)
async def admin_get_subscription_plans(
    include_inactive: bool = Query(False, description="Include inactive plans"),
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionPlansResponse:
    """
    Get all subscription plans for admin management (Super Admin only).
    
    Returns all plans including inactive ones if requested.
    """
    try:
        if include_inactive:
            # Get all plans from database
            db_plans = await service.plan_repo.list_all(session, include_inactive=True)
            plans = []
            for plan in db_plans:
                periods = await service.period_repo.list_by_plan(session, plan.tier)
                formatted_plan = {
                    "tier": plan.tier,
                    "name": plan.name,
                    "category": plan.category,
                    "periods": {}
                }
                for period_obj in periods:
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
        else:
            plans = await service.get_subscription_plans(session)
        
        return SubscriptionPlansResponse(plans=plans)
    except Exception as exc:
        # Error retrieving subscription plans
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription plans"
        ) from exc


@router.post("/admin/plans/", status_code=status.HTTP_201_CREATED)
async def admin_create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new subscription plan (Super Admin only).
    """
    try:
        result = await service.create_subscription_plan(
            session,
            plan_data.model_dump()
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error creating subscription plan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription plan"
        ) from exc


@router.put("/admin/plans/{tier}/", status_code=status.HTTP_200_OK)
async def admin_update_subscription_plan(
    tier: str,
    update_data: SubscriptionPlanUpdate,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update a subscription plan (Super Admin only).
    """
    try:
        result = await service.update_subscription_plan(
            session,
            tier,
            update_data.model_dump(exclude_none=True)
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error updating subscription plan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription plan"
        ) from exc


@router.delete("/admin/plans/{tier}/", status_code=status.HTTP_200_OK)
async def admin_delete_subscription_plan(
    tier: str,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a subscription plan (Super Admin only).
    """
    try:
        result = await service.delete_subscription_plan(session, tier)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error deleting subscription plan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription plan"
        ) from exc


@router.post("/admin/plans/{tier}/periods/", status_code=status.HTTP_200_OK)
async def admin_create_subscription_plan_period(
    tier: str,
    period_data: SubscriptionPeriodCreate,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create or update a subscription plan period (Super Admin only).
    """
    try:
        result = await service.create_subscription_plan_period(
            session,
            tier,
            period_data.model_dump()
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error creating/updating period
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create/update period"
        ) from exc


@router.delete("/admin/plans/{tier}/periods/{period}/", status_code=status.HTTP_200_OK)
async def admin_delete_subscription_plan_period(
    tier: str,
    period: str,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a subscription plan period (Super Admin only).
    """
    try:
        result = await service.delete_subscription_plan_period(session, tier, period)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error deleting period
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete period"
        ) from exc


# Admin endpoints for managing addon packages (Super Admin only)
@router.get("/admin/addons/", response_model=AddonPackagesResponse)
async def admin_get_addon_packages(
    include_inactive: bool = Query(False, description="Include inactive packages"),
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> AddonPackagesResponse:
    """
    Get all addon packages for admin management (Super Admin only).
    
    Returns all packages including inactive ones if requested.
    """
    try:
        if include_inactive:
            db_packages = await service.addon_repo.list_all(session, include_inactive=True)
            packages = []
            for package in db_packages:
                packages.append({
                    "id": package.id,
                    "name": package.name,
                    "credits": package.credits,
                    "rate_per_credit": float(package.rate_per_credit),
                    "price": float(package.price),
                })
        else:
            packages = await service.get_addon_packages(session)
        
        return AddonPackagesResponse(packages=packages)
    except Exception as exc:
        # Error retrieving addon packages
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve addon packages"
        ) from exc


@router.post("/admin/addons/", status_code=status.HTTP_201_CREATED)
async def admin_create_addon_package(
    package_data: AddonPackageCreate,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new addon package (Super Admin only).
    """
    # Admin create addon package with package ID
    
    try:
        result = await service.create_addon_package(
            session,
            package_data.model_dump()
        )
        # Addon package created with package ID
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error handling: Create addon package failed with exception details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create addon package"
        ) from exc


@router.put("/admin/addons/{package_id}/", status_code=status.HTTP_200_OK)
async def admin_update_addon_package(
    package_id: str,
    update_data: AddonPackageUpdate,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update an addon package (Super Admin only).
    """
    # Admin update addon package with package ID
    
    try:
        result = await service.update_addon_package(
            session,
            package_id,
            update_data.model_dump(exclude_none=True)
        )
        # Addon package updated with package ID
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error handling: Update addon package failed with exception details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update addon package"
        ) from exc


@router.delete("/admin/addons/{package_id}/", status_code=status.HTTP_200_OK)
async def admin_delete_addon_package(
    package_id: str,
    filters: UserFilterParams = Depends(resolve_billing_filters),
    current_user: User = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an addon package (Super Admin only).
    """
    try:
        result = await service.delete_addon_package(session, package_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Error deleting addon package
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete addon package"
        ) from exc

