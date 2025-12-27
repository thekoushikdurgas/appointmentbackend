"""Pydantic schemas for AI chat conversations."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactInMessage(BaseModel):
    """Contact object included in AI message responses."""

    uuid: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class Message(BaseModel):
    """Message in a chat conversation."""

    sender: Literal["user", "ai"] = Field(..., description="Message sender: 'user' or 'ai'")
    text: str = Field(..., description="Message text content")
    contacts: Optional[list[ContactInMessage]] = Field(
        default=None, description="Array of contact objects when AI returns search results"
    )

    @field_validator("sender")
    @classmethod
    def validate_sender(cls, v: str) -> str:
        """Validate sender is 'user' or 'ai'."""
        if v not in ("user", "ai"):
            raise ValueError("Sender must be 'user' or 'ai'")
        return v


class AIChatCreate(BaseModel):
    """Schema for creating a new AI chat."""

    title: Optional[str] = Field(default="", max_length=255, description="Chat title")
    messages: Optional[list[Message]] = Field(default_factory=list, description="List of messages")


class AIChatUpdate(BaseModel):
    """Schema for updating an AI chat (partial update)."""

    title: Optional[str] = Field(None, max_length=255, description="Chat title")
    messages: Optional[list[Message]] = Field(None, description="List of messages")


class ModelSelection(str, Enum):
    """Available Gemini models."""

    FLASH = "gemini-1.5-flash"
    PRO = "gemini-1.5-pro"
    FLASH_2_0 = "gemini-2.0-flash-exp"
    PRO_2_5 = "gemini-2.5-pro"


class AIChatMessageRequest(BaseModel):
    """Schema for sending a message in a chat."""

    message: str = Field(..., min_length=1, description="User message text")
    model: Optional[ModelSelection] = Field(
        default=None,
        description="Optional model selection override (defaults to configured model)"
    )


class AIChatListItem(BaseModel):
    """Schema for AI chat in list responses."""

    uuid: str = Field(..., description="Chat UUID")
    title: str = Field(..., description="Chat title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AIChatResponse(BaseModel):
    """Schema for full AI chat response."""

    uuid: str = Field(..., description="Chat UUID")
    user_id: str = Field(..., description="User UUID who owns this chat")
    title: str = Field(..., description="Chat title")
    messages: list[dict[str, Any]] = Field(..., description="List of messages as JSON objects")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PaginatedAIChatResponse(BaseModel):
    """Schema for paginated AI chat list response."""

    count: int = Field(..., description="Total number of chats")
    next: Optional[str] = Field(None, description="URL for next page")
    previous: Optional[str] = Field(None, description="URL for previous page")
    results: list[AIChatListItem] = Field(..., description="List of chats")


class ChatStreamRequest(BaseModel):
    """Schema for streaming chat requests."""

    message: str = Field(..., min_length=1, description="User message text")
    model: Optional[ModelSelection] = Field(
        default=None,
        description="Optional model selection override (defaults to configured model)"
    )


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""

    chunk: str = Field(..., description="Text chunk from AI response")
    done: bool = Field(default=False, description="Whether this is the final chunk")

