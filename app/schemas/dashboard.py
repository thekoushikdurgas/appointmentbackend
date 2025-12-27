"""Pydantic schemas for dashboard pages."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.marketing import AccessControlMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardPageMetadata(BaseModel):
    """Metadata for a dashboard page."""
    
    title: str
    description: str
    route: str = Field(..., description="Frontend route path (e.g., /finder)")
    last_updated: datetime
    version: int = Field(default=1, ge=1)
    
    model_config = ConfigDict(from_attributes=True)


class DashboardPageAccessControl(AccessControlMetadata):
    """Access control for dashboard pages with redirect support."""
    
    redirect_path: Optional[str] = Field(
        None,
        description="Path to redirect to if user lacks access (e.g., /billing)"
    )
    redirect_message: Optional[str] = Field(
        None,
        description="Message to show when redirecting"
    )
    
    model_config = ConfigDict(from_attributes=True)


class DashboardPageBase(BaseModel):
    """Base schema for dashboard pages."""
    
    page_id: str = Field(..., description="Unique identifier for the page (e.g., 'finder')")
    metadata: DashboardPageMetadata
    access_control: DashboardPageAccessControl
    sections: Dict[str, Any] = Field(
        default_factory=dict,
        description="Page sections with nested access control"
    )
    
    model_config = ConfigDict(from_attributes=True)


class DashboardPageCreate(BaseModel):
    """Schema for creating a new dashboard page."""
    
    page_id: str = Field(..., description="Unique identifier for the page")
    metadata: Optional[DashboardPageMetadata] = None
    access_control: Optional[DashboardPageAccessControl] = None
    sections: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


class DashboardPageUpdate(BaseModel):
    """Schema for updating a dashboard page."""
    
    metadata: Optional[DashboardPageMetadata] = None
    access_control: Optional[DashboardPageAccessControl] = None
    sections: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class DashboardPageResponse(DashboardPageBase):
    """Response schema for a dashboard page."""
    
    id: Optional[str] = Field(None, alias="_id", description="MongoDB document ID")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DashboardPageListResponse(BaseModel):
    """Response schema for listing dashboard pages."""
    
    pages: List[DashboardPageResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

