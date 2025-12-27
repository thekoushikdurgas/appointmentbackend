"""Admin marketing page API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.user import User
from app.schemas.marketing import (
    MarketingPageCreate,
    MarketingPageListResponse,
    MarketingPageResponse,
    MarketingPageUpdate,
)
from app.services.marketing_service import MarketingService
from app.utils.logger import get_logger, log_api_error
from app.core.exceptions import NotFoundException

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/marketing", tags=["Admin Marketing"])
service = MarketingService()


@router.get("/", response_model=MarketingPageListResponse)
async def list_all_marketing_pages(
    include_drafts: bool = Query(True, description="Include draft pages"),
    include_deleted: bool = Query(False, description="Include deleted pages"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageListResponse:
    """
    List all marketing pages (admin only).
    
    Includes drafts and optionally deleted pages.
    """
    result = await service.list_pages(include_drafts, include_deleted)
    return result


@router.get("/{page_id}", response_model=MarketingPageResponse)
async def get_marketing_page_admin(
    page_id: str,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageResponse:
    """
    Get any marketing page by page_id (admin only).
    
    Returns pages regardless of status (published, draft, or deleted).
    """
    page = await service.get_page_by_id(page_id, include_deleted=True)
    
    if not page:
        log_api_error(
            endpoint=f"/api/v4/admin/marketing/{page_id}",
            method="GET",
            status_code=404,
            error_type="NotFoundException",
            error_message=f"Marketing page not found: {page_id}",
            user_id=str(current_user.uuid),
            context={"page_id": page_id}
        )
        raise NotFoundException(f"Marketing page '{page_id}' not found")
    
    return page


@router.post("/", response_model=MarketingPageResponse, status_code=status.HTTP_201_CREATED)
async def create_marketing_page(
    data: MarketingPageCreate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageResponse:
    """
    Create a new marketing page (admin only).
    
    Pages are created as drafts by default unless status is explicitly set to 'published'.
    """
    return await service.create_page(data)


@router.put("/{page_id}", response_model=MarketingPageResponse)
async def update_marketing_page(
    page_id: str,
    data: MarketingPageUpdate,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageResponse:
    """
    Update an existing marketing page (admin only).
    
    Only provided fields will be updated. Version is automatically incremented.
    """
    return await service.update_page(page_id, data)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marketing_page(
    page_id: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a marketing page (admin only).
    
    By default, performs a soft delete (sets status to 'deleted').
    Set hard_delete=true to permanently remove the page.
    """
    deleted = await service.delete_page(page_id, hard_delete)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marketing page '{page_id}' not found"
        )


@router.post("/{page_id}/publish", response_model=MarketingPageResponse)
async def publish_marketing_page(
    page_id: str,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageResponse:
    """
    Publish a draft marketing page (admin only).
    
    Changes the page status from 'draft' to 'published'.
    """
    return await service.publish_page(page_id)

