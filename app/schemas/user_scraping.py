"""Pydantic schemas for user scraping metadata from Sales Navigator."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


# Nested schemas for JSON fields
class SearchContextSchema(BaseModel):
    """Schema for search context metadata."""

    search_filters: Optional[Dict[str, Any]] = Field(None, description="Applied search filters")
    search_id: Optional[str] = Field(None, description="Search identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

    model_config = ConfigDict(from_attributes=True, extra="allow")


class PaginationSchema(BaseModel):
    """Schema for pagination metadata."""

    current_page: Optional[int] = Field(None, description="Current page number")
    total_pages: Optional[int] = Field(None, description="Total number of pages")
    results_per_page: Optional[int] = Field(None, description="Number of results per page")

    model_config = ConfigDict(from_attributes=True, extra="allow")


class UserInfoSchema(BaseModel):
    """Schema for user info metadata."""

    user_member_urn: Optional[str] = Field(None, description="LinkedIn member URN")
    user_name: Optional[str] = Field(None, description="User's name")

    model_config = ConfigDict(from_attributes=True, extra="allow")


class ApplicationInfoSchema(BaseModel):
    """Schema for application info metadata."""

    application_version: Optional[str] = Field(None, description="LinkedIn application version")
    client_page_instance_id: Optional[str] = Field(None, description="Client page instance ID")
    request_ip_country: Optional[str] = Field(None, description="Country code from request IP")
    tracking_id: Optional[str] = Field(None, description="Tracking identifier")
    tree_id: Optional[str] = Field(None, description="Tree identifier")

    model_config = ConfigDict(from_attributes=True, extra="allow")


# Base schema
class UserScrapingBase(BaseModel):
    """Base schema for user scraping metadata."""

    timestamp: datetime = Field(..., description="Timestamp of the scraping operation")
    version: str = Field(..., description="Version of the extraction logic")
    source: str = Field(..., description="Source identifier (e.g., 'api_request')")
    search_context: Optional[SearchContextSchema] = Field(None, description="Search context metadata")
    pagination: Optional[PaginationSchema] = Field(None, description="Pagination metadata")
    user_info: Optional[UserInfoSchema] = Field(None, description="User info metadata")
    application_info: Optional[ApplicationInfoSchema] = Field(None, description="Application info metadata")

    model_config = ConfigDict(from_attributes=True, extra="allow")


# Create schema
class UserScrapingCreate(UserScrapingBase):
    """Schema for creating a user scraping record."""

    user_id: str = Field(..., description="User ID (UUID format)")

    model_config = ConfigDict(from_attributes=True, extra="allow")


# Response schema
class UserScrapingResponse(UserScrapingBase):
    """Schema for user scraping response."""

    id: int = Field(..., description="Scraping record ID")
    user_id: str = Field(..., description="User ID (UUID format)")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record update timestamp")

    model_config = ConfigDict(from_attributes=True, extra="allow")


# List response schema
class UserScrapingListResponse(BaseModel):
    """Schema for user scraping list response with pagination."""

    items: List[UserScrapingResponse] = Field(..., description="List of scraping records")
    total: int = Field(..., description="Total number of records")
    limit: int = Field(..., description="Number of records per page")
    offset: int = Field(..., description="Number of records skipped")

    model_config = ConfigDict(from_attributes=True)

