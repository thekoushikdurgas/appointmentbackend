"""SQLAlchemy model for user scraping metadata from Sales Navigator."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class UserScraping(Base):
    """
    User scraping model for tracking Sales Navigator scraping metadata.
    
    Stores extraction metadata, page metadata (search context, pagination, user info, 
    application info) from Sales Navigator HTML scraping operations.
    
    Note: user_id must be a valid UUID format (stored as text).
    """

    __tablename__ = "user_scraping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # User UUID (UUID format stored as text)
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Extraction metadata
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "2.0"
    source: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "api_request"
    # Page metadata - stored as JSON
    search_context: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    pagination: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    user_info: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    application_info: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    # Timestamps
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
        back_populates="scraping_records",
        primaryjoin="foreign(UserScraping.user_id) == User.uuid"
    )

    __table_args__ = (
        Index("idx_user_scraping_user_id", "user_id"),
        Index("idx_user_scraping_timestamp", "timestamp"),
        Index("idx_user_scraping_user_timestamp", "user_id", "timestamp"),
    )

