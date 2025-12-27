"""Admin dashboard page API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_or_super_admin, get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardPageCreate,
    DashboardPageListResponse,
    DashboardPageResponse,
    DashboardPageUpdate,
)
from app.services.dashboard_service import DashboardService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/dashboard-pages", tags=["Admin Dashboard Pages"])
service = DashboardService()


@router.get("/", response_model=DashboardPageListResponse)
async def list_all_dashboard_pages(
    current_user: User = Depends(get_current_admin_or_super_admin),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageListResponse:
    """
    List all dashboard pages (admin only).
    
    Returns all pages without filtering.
    """
    result = await service.list_pages()
    return result


@router.get("/{page_id}", response_model=DashboardPageResponse)
async def get_dashboard_page_admin(
    page_id: str,
    current_user: User = Depends(get_current_admin_or_super_admin),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageResponse:
    """
    Get any dashboard page by page_id (admin only).
    
    Returns full page data without filtering.
    """
    page = await service.get_page_by_id(page_id)
    
    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard page '{page_id}' not found"
        )
    
    return page


@router.post("/", response_model=DashboardPageResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard_page(
    data: DashboardPageCreate,
    current_user: User = Depends(get_current_admin_or_super_admin),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageResponse:
    """
    Create a new dashboard page (admin only).
    """
    return await service.create_page(data)


@router.put("/{page_id}", response_model=DashboardPageResponse)
async def update_dashboard_page(
    page_id: str,
    data: DashboardPageUpdate,
    current_user: User = Depends(get_current_admin_or_super_admin),
    session: AsyncSession = Depends(get_db),
) -> DashboardPageResponse:
    """
    Update an existing dashboard page (admin only).
    
    Only provided fields will be updated. Version is automatically incremented.
    """
    return await service.update_page(page_id, data)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard_page(
    page_id: str,
    current_user: User = Depends(get_current_admin_or_super_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a dashboard page (admin only).
    """
    deleted = await service.delete_page(page_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard page '{page_id}' not found"
        )

