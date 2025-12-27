"""Service layer for dashboard page operations."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardPageCreate,
    DashboardPageListResponse,
    DashboardPageResponse,
    DashboardPageUpdate,
)
from app.services.access_control_service import AccessControlService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardService:
    """Business logic for dashboard page management."""
    
    def __init__(
        self, 
        repository: Optional[DashboardRepository] = None,
        access_control_service: Optional[AccessControlService] = None
    ):
        """Initialize the service with repository and access control service."""
        self.repository = repository or DashboardRepository()
        self.access_control_service = access_control_service or AccessControlService()
    
    async def get_page_by_id(
        self, 
        page_id: str
    ) -> Optional[DashboardPageResponse]:
        """Get a dashboard page by page_id."""
        page = await self.repository.get_by_page_id(page_id)
        if not page:
            return None
        
        return DashboardPageResponse(**page)
    
    async def get_page_by_id_with_access_control(
        self,
        page_id: str,
        user_role: Optional[str] = None
    ) -> Optional[DashboardPageResponse]:
        """
        Get a dashboard page by page_id with access control filtering.
        
        Args:
            page_id: Page identifier
            user_role: User's role (None for public users, but dashboard requires auth)
            
        Returns:
            Filtered DashboardPageResponse or None if not found
        """
        page = await self.repository.get_by_page_id(page_id)
        if not page:
            return None
        
        # Apply access control filtering
        filtered_page = self.access_control_service.filter_page_by_role(page, user_role)
        
        return DashboardPageResponse(**filtered_page)
    
    async def list_pages(self) -> DashboardPageListResponse:
        """List all dashboard pages."""
        pages = await self.repository.list_all()
        total = await self.repository.count_pages()
        
        page_responses = [DashboardPageResponse(**page) for page in pages]
        
        return DashboardPageListResponse(pages=page_responses, total=total)
    
    async def create_page(self, data: DashboardPageCreate) -> DashboardPageResponse:
        """Create a new dashboard page."""
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
                "title": data.page_id.replace("-", " ").title(),
                "description": f"Dashboard page for {data.page_id}",
                "route": f"/{data.page_id}",
                "version": 1,
            }
        
        # Ensure access_control has defaults
        if not page_data.get("access_control"):
            page_data["access_control"] = {
                "allowed_roles": ["FreeUser", "ProUser", "Admin", "SuperAdmin"],
                "restriction_type": "none",
                "redirect_path": "/billing",
            }
        
        try:
            created = await self.repository.create_page_content(page_data)
            return DashboardPageResponse(**created)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
    
    async def update_page(
        self, 
        page_id: str, 
        data: DashboardPageUpdate
    ) -> DashboardPageResponse:
        """Update an existing dashboard page."""
        # Check if page exists
        existing = await self.repository.get_by_page_id(page_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        # Prepare update data
        update_data = data.model_dump(exclude_none=True)
        
        updated = await self.repository.update_page_content(page_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        return DashboardPageResponse(**updated)
    
    async def delete_page(self, page_id: str) -> bool:
        """Delete a dashboard page."""
        existing = await self.repository.get_by_page_id(page_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with page_id '{page_id}' not found"
            )
        
        return await self.repository.delete_page(page_id)

