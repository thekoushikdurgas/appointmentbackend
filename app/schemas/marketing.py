"""Pydantic schemas for marketing pages."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AccessControlMetadata(BaseModel):
    """Access control metadata for sections and components."""
    
    allowed_roles: List[str] = Field(
        default_factory=list,
        description="List of roles that can access this content. Empty list means accessible to all."
    )
    restriction_type: str = Field(
        default="full",
        pattern="^(full|partial|none|hidden)$",
        description="Type of restriction: full (locked), partial (teaser), none (no restriction), hidden (not shown)"
    )
    upgrade_message: Optional[str] = Field(
        None,
        description="Message to show when content is locked"
    )
    required_role: Optional[str] = Field(
        None,
        description="Minimum required role to access this content"
    )
    redirect_path: Optional[str] = Field(
        None,
        description="Path to redirect to if user lacks access (e.g., /billing)"
    )
    redirect_message: Optional[str] = Field(
        None,
        description="Message to show when redirecting"
    )
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageMetadata(BaseModel):
    """Metadata for a marketing page."""
    
    title: str
    description: str
    keywords: Optional[List[str]] = None
    last_updated: datetime
    status: str = Field(default="draft", pattern="^(published|draft|deleted)$")
    version: int = Field(default=1, ge=1)
    
    model_config = ConfigDict(from_attributes=True)


class HeroSection(BaseModel):
    """Hero section of a marketing page."""
    
    title: str
    subtitle: Optional[str] = None
    description: str
    features: List[str] = Field(default_factory=list)
    cta_text: Optional[str] = None
    cta_href: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageBase(BaseModel):
    """Base schema for marketing pages."""
    
    page_id: str = Field(..., description="Unique identifier for the page")
    metadata: MarketingPageMetadata
    hero: HeroSection
    sections: Dict[str, Any] = Field(default_factory=dict, description="Page-specific sections")
    hero_stats: Optional[List[Dict[str, str]]] = None
    hero_table: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageCreate(BaseModel):
    """Schema for creating a new marketing page."""
    
    page_id: str = Field(..., description="Unique identifier for the page")
    metadata: Optional[MarketingPageMetadata] = None
    hero: HeroSection
    sections: Dict[str, Any] = Field(default_factory=dict)
    hero_stats: Optional[List[Dict[str, str]]] = None
    hero_table: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageUpdate(BaseModel):
    """Schema for updating a marketing page."""
    
    metadata: Optional[MarketingPageMetadata] = None
    hero: Optional[HeroSection] = None
    sections: Optional[Dict[str, Any]] = None
    hero_stats: Optional[List[Dict[str, str]]] = None
    hero_table: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageResponse(MarketingPageBase):
    """Response schema for a marketing page."""
    
    id: Optional[str] = Field(None, alias="_id", description="MongoDB document ID")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MarketingPageListItem(BaseModel):
    """Schema for marketing page list item."""
    
    page_id: str
    metadata: MarketingPageMetadata
    hero: HeroSection
    
    model_config = ConfigDict(from_attributes=True)


class MarketingPageListResponse(BaseModel):
    """Response schema for listing marketing pages."""
    
    pages: List[MarketingPageResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

