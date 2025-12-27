"""Public dashboard page API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_user_role_async
from app.models.user import User
from app.schemas.dashboard import DashboardPageListResponse, DashboardPageResponse
from app.services.dashboard_service import DashboardService
from app.utils.access_control import has_role_access
from app.utils.logger import get_logger, log_api_error
from app.core.exceptions import NotFoundException

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard-pages", tags=["Dashboard Pages"])
service = DashboardService()


@router.get("/{page_id}", response_model=DashboardPageResponse)
async def get_dashboard_page(
    page_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageResponse:
    """
    Get a dashboard page by page_id with access control.
    
    Requires authentication. Returns page data filtered by user role.
    """
    # Get user role
    user_role = await get_user_role_async(current_user, session)
    
    # Get page with access control filtering
    page = await service.get_page_by_id_with_access_control(
        page_id=page_id,
        user_role=user_role
    )
    
    if not page:
        log_api_error(
            endpoint=f"/api/v4/dashboard-pages/{page_id}",
            method="GET",
            status_code=404,
            error_type="NotFoundException",
            error_message=f"Dashboard page not found: {page_id}",
            user_id=str(current_user.uuid),
            context={"page_id": page_id, "user_role": user_role}
        )
        raise NotFoundException(f"Dashboard page '{page_id}' not found")
    
    return page


@router.get("/", response_model=DashboardPageListResponse)
async def list_dashboard_pages(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageListResponse:
    """
    List all dashboard pages.
    
    Requires authentication. Returns pages filtered by user role.
    """
    # Get user role
    user_role = await get_user_role_async(current_user, session)
    
    # List all pages (filtering happens in service)
    result = await service.list_pages()
    
    # Filter pages based on access control
    filtered_pages = []
    for page in result.pages:
        # Check page-level access
        allowed_roles = page.access_control.allowed_roles
        if has_role_access(user_role, allowed_roles):
            # Get filtered page data (for sections/components)
            filtered_page = await service.get_page_by_id_with_access_control(
                page.page_id,
                user_role
            )
            if filtered_page:
                filtered_pages.append(filtered_page)
    
    return DashboardPageListResponse(pages=filtered_pages, total=len(filtered_pages))

