"""Common Pydantic schema mixins and response wrappers used across endpoints."""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """Standard envelope for cursor-driven list responses."""

    next: Optional[str]
    previous: Optional[str]
    results: List[T]


class CountResponse(BaseModel):
    """Simple count payload used by aggregate endpoints."""

    count: int


class MessageResponse(BaseModel):
    """Wrapper for simple status/message API responses."""

    message: str


class PaginationParams(BaseModel):
    """Query parameters used to control offset-based pagination."""

    limit: int = 25
    offset: int = 0


class TimestampedModel(BaseModel):
    """Base model exposing created/updated fields for API serialization."""

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

