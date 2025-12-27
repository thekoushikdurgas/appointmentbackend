"""Public marketing page API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional, get_db, get_user_role_async
from app.models.user import User
from app.schemas.marketing import MarketingPageListResponse, MarketingPageResponse
from app.services.marketing_service import MarketingService
from app.utils.logger import get_logger, log_api_error
from app.core.exceptions import NotFoundException

logger = get_logger(__name__)
router = APIRouter(prefix="/marketing", tags=["Marketing"])
service = MarketingService()


@router.get("/{page_id}", response_model=MarketingPageResponse)
async def get_marketing_page(
    page_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_db),
) -> MarketingPageResponse:
    """
    Get a published marketing page by page_id with access control.
    
    - Public users (no auth): See all content with locked components showing upgrade prompts
    - Authenticated users: See content filtered by their role
    - Only returns pages with status 'published'. Use admin endpoints to access drafts.
    """
    # Get user role (None for public users)
    user_role = None
    if current_user:
        user_role = await get_user_role_async(current_user, session)
    
    # Get page with access control filtering
    page = await service.get_page_by_id_with_access_control(
        page_id=page_id,
        user_role=user_role,
        include_deleted=False
    )
    
    if not page:
        user_id = str(current_user.uuid) if current_user else None
        log_api_error(
            endpoint=f"/api/v4/marketing/{page_id}",
            method="GET",
            status_code=404,
            error_type="NotFoundException",
            error_message=f"Marketing page not found: {page_id}",
            user_id=user_id,
            context={"page_id": page_id, "user_role": user_role}
        )
        raise NotFoundException(f"Marketing page '{page_id}' not found")
    
    # Ensure page is published
    if page.metadata.status != "published":
        user_id = str(current_user.uuid) if current_user else None
        log_api_error(
            endpoint=f"/api/v4/marketing/{page_id}",
            method="GET",
            status_code=404,
            error_type="NotFoundException",
            error_message=f"Marketing page not published: {page_id}",
            user_id=user_id,
            context={"page_id": page_id, "status": page.metadata.status}
        )
        raise NotFoundException(f"Marketing page '{page_id}' not found")
    
    return page


@router.get("/", response_model=MarketingPageListResponse)
async def list_marketing_pages(
    include_drafts: bool = Query(False, description="Include draft pages (public endpoint ignores this)")
) -> MarketingPageListResponse:
    """
    List all published marketing pages.
    
    This endpoint only returns published pages. Use admin endpoints to access drafts.
    """
    # Public endpoint always excludes drafts
    result = await service.list_pages(include_drafts=False, include_deleted=False)
    return result

