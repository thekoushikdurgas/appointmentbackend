from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.generics import GenericModel

T = TypeVar("T")


class CursorPage(GenericModel, Generic[T]):
    next: Optional[str]
    previous: Optional[str]
    results: List[T]


class CountResponse(BaseModel):
    count: int


class MessageResponse(BaseModel):
    message: str


class PaginationParams(BaseModel):
    limit: int = 25
    offset: int = 0


class TimestampedModel(BaseModel):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

