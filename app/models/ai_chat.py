"""SQLAlchemy model for AI chat conversations."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class AIChat(Base):
    """Represents an AI chat conversation for a user."""

    __tablename__ = "ai_chats"

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid4()),
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), default="")
    messages: Mapped[Optional[list[dict]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    user: Mapped["User"] = relationship(
        "User",
        backref="ai_chats"
    )

    __table_args__ = (
        Index("idx_ai_chats_user_id", "user_id"),
        Index("idx_ai_chats_created_at", "created_at"),
        Index("idx_ai_chats_updated_at", "updated_at"),
    )

