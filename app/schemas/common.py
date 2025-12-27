"""Common Pydantic schema mixins and response wrappers used across endpoints."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """Standard envelope for cursor-driven list responses."""

    next: Optional[str]
    previous: Optional[str]
    results: List[T]
    meta: Optional[dict] = None  # Optional metadata field for frontend compatibility


class CountResponse(BaseModel):
    """Simple count payload used by aggregate endpoints."""

    count: int


class UuidListResponse(BaseModel):
    """Response payload containing count and list of UUIDs."""

    count: int
    uuids: List[str]


class MessageResponse(BaseModel):
    """Wrapper for simple status/message API responses."""

    message: str


class LinkedInSearchRequest(BaseModel):
    """Request payload for LinkedIn URL search."""

    urls: List[str] = Field(..., description="List of LinkedIn URLs to search for", min_length=1)
    return_format: Optional[str] = Field(
        default="uuids", 
        description="Return format: 'uuids' for UUIDs only, 'full' for full contact data"
    )


class LinkedInSearchResponse(BaseModel):
    """Response payload for LinkedIn URL search."""

    contact_ids: List[str] = Field(..., description="List of contact UUIDs matching the LinkedIn URLs")
    count: int = Field(..., description="Total count of matching contacts")


class PaginationParams(BaseModel):
    """Query parameters used to control offset-based pagination."""

    limit: int = 25
    offset: int = 0


class TimestampedModel(BaseModel):
    """Base model exposing created/updated fields for API serialization."""

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

