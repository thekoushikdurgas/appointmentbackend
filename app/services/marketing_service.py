"""Service layer for marketing page operations."""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.repositories.marketing_repository import MarketingRepository
from app.schemas.marketing import (
    HeroSection,
    MarketingPageCreate,
    MarketingPageListResponse,
    MarketingPageMetadata,
    MarketingPageResponse,
    MarketingPageUpdate,
)
from app.services.access_control_service import AccessControlService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketingService:
    """Business logic for marketing page management."""
    
    def __init__(
        self, 
        repository: Optional[MarketingRepository] = None,
        access_control_service: Optional[AccessControlService] = None
    ):
        """Initialize the service with repository and access control service."""
        self.repository = repository or MarketingRepository()
        self.access_control_service = access_control_service or AccessControlService()
    
    async def get_page_by_id(
        self, 
        page_id: str, 
        include_deleted: bool = False
    ) -> Optional[MarketingPageResponse]:
        """Get a marketing page by page_id."""
        page = await self.repository.get_by_page_id(page_id, include_deleted)
        if not page:
            return None
        
        return MarketingPageResponse(**page)
    
    async def get_page_by_id_with_access_control(
        self,
        page_id: str,
        user_role: Optional[str] = None,
        include_deleted: bool = False
    ) -> Optional[MarketingPageResponse]:
        """
        Get a marketing page by page_id with access control filtering.
        
        Args:
            page_id: Page identifier
            user_role: User's role (None for public users)
            include_deleted: Whether to include deleted pages
            
        Returns:
            Filtered MarketingPageResponse or None if not found
        """
        page = await self.repository.get_by_page_id(page_id, include_deleted)
        if not page:
            return None
        
        # Apply access control filtering
        filtered_page = self.access_control_service.filter_page_by_role(page, user_role)
        
        return MarketingPageResponse(**filtered_page)
    
    async def list_pages(
        self,
        include_drafts: bool = False,
        include_deleted: bool = False
    ) -> MarketingPageListResponse:
        """List all marketing pages."""
        pages = await self.repository.list_all(include_drafts, include_deleted)
        total = await self.repository.count_pages(include_drafts, include_deleted)
        
        page_responses = [MarketingPageResponse(**page) for page in pages]
        
        return MarketingPageListResponse(pages=page_responses, total=total)
    
    async def create_page(self, data: MarketingPageCreate) -> MarketingPageResponse:
        """Create a new marketing page."""
        # Validate page_id format
        if not data.page_id or not data.page_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page_id is required"
            )
        
        # Prepare data for repository
        page_data = data.model_dump(exclude_none=True)
        
        # Ensure metadata is set with defaults
        if not page_data.get("metadata"):
            page_data["metadata"] = {
                "title": data.hero.title,
                "description": data.hero.description,
                "status": "draft",
                "version": 1,
            }
        
        # Validate metadata structure
        if "status" in page_data["metadata"]:
            status_val = page_data["metadata"]["status"]
            if status_val not in ["published", "draft", "deleted"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_val}. Must be 'published', 'draft', or 'deleted'"
                )
        
        try:
            created = await self.repository.create_page_content(page_data)
            return MarketingPageResponse(**created)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
    
    async def update_page(
        self, 
        page_id: str, 
        data: MarketingPageUpdate
    ) -> MarketingPageResponse:
        """Update an existing marketing page."""
        # Check if page exists
        existing = await self.repository.get_by_page_id(page_id, include_deleted=True)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        # Prepare update data
        update_data = data.model_dump(exclude_none=True)
        
        # Validate status if provided
        if "metadata" in update_data and "status" in update_data["metadata"]:
            status_val = update_data["metadata"]["status"]
            if status_val not in ["published", "draft", "deleted"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_val}. Must be 'published', 'draft', or 'deleted'"
                )
        
        updated = await self.repository.update_page_content(page_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        return MarketingPageResponse(**updated)
    
    async def delete_page(self, page_id: str, hard_delete: bool = False) -> bool:
        """Delete a marketing page."""
        existing = await self.repository.get_by_page_id(page_id, include_deleted=True)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        return await self.repository.delete_page(page_id, hard_delete)
    
    async def publish_page(self, page_id: str) -> MarketingPageResponse:
        """Publish a draft page."""
        existing = await self.repository.get_by_page_id(page_id, include_deleted=True)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        published = await self.repository.publish_page(page_id)
        if not published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        return MarketingPageResponse(**published)

