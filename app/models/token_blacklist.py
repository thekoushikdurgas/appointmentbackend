"""SQLAlchemy model for token blacklist."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class TokenBlacklist(Base):
    """
    Token blacklist model for storing blacklisted refresh tokens.
    
    Tokens are blacklisted when users logout to prevent reuse.
    """

    __tablename__ = "token_blacklist"

    token: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id]
    )

    __table_args__ = (
        Index("idx_token_blacklist_user_id", "user_id"),
        Index("idx_token_blacklist_blacklisted_at", "blacklisted_at"),
        Index("idx_token_blacklist_expires_at", "expires_at"),
    )

