"""SQLAlchemy models describing user export jobs."""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import StringList


def datetime_utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp compatible with SQLAlchemy defaults."""
    return datetime.now(timezone.utc)


class ExportStatus(str, PyEnum):
    """Enumerates the possible lifecycle states of an export job."""

    pending = "pending"
    completed = "completed"
    failed = "failed"


class UserExport(Base):
    """Represents a CSV export job tracked by the system."""

    __tablename__ = "user_exports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    export_id: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    file_name: Mapped[Optional[str]] = mapped_column(Text)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_uuids: Mapped[Optional[list[str]]] = mapped_column(StringList())
    status: Mapped[ExportStatus] = mapped_column(
        SQLEnum(ExportStatus, name="export_status"),
        default=ExportStatus.pending,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime_utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    download_url: Mapped[Optional[str]] = mapped_column(Text)
    download_token: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_user_exports_user_id", "user_id"),
        Index("idx_user_exports_export_id", "export_id"),
        Index("idx_user_exports_expires_at", "expires_at"),
        Index("idx_user_exports_status", "status"),
        Index("idx_user_exports_created_at", "created_at"),
    )

