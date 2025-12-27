"""SQLAlchemy models describing user export jobs."""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import StringList
from app.utils.logger import get_logger

logger = get_logger(__name__)


def datetime_utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp compatible with SQLAlchemy defaults."""
    return datetime.now(timezone.utc)


class ExportStatus(str, PyEnum):
    """Enumerates the possible lifecycle states of an export job."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ExportType(str, PyEnum):
    """Enumerates the types of exports."""

    contacts = "contacts"
    companies = "companies"
    emails = "emails"


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
        ForeignKey("users.uuid", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    export_type: Mapped[ExportType] = mapped_column(
        SQLEnum(ExportType, name="export_type"),
        default=ExportType.contacts,
        index=True,
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    file_name: Mapped[Optional[str]] = mapped_column(Text)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_uuids: Mapped[Optional[list[str]]] = mapped_column(StringList())
    company_count: Mapped[int] = mapped_column(Integer, default=0)
    company_uuids: Mapped[Optional[list[str]]] = mapped_column(StringList())
    linkedin_urls: Mapped[Optional[list[str]]] = mapped_column(
        StringList(), 
        default=None,
        comment="LinkedIn URLs used for LinkedIn exports. Only populated for exports created via POST /api/v2/linkedin/export."
    )
    email_contacts_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default=None,
        comment="JSON string of email contacts data. Only populated for exports created via POST /api/v2/email/export."
    )
    linkedin_urls_json: Mapped[Optional[str]] = mapped_column(
        Text,
        default=None,
        comment="JSON string of LinkedIn URLs data with CSV context. Only populated for exports created via POST /api/v2/linkedin/export with CSV context."
    )
    status: Mapped[ExportStatus] = mapped_column(
        SQLEnum(ExportStatus, name="export_status"),
        default=ExportStatus.pending,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime_utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    download_url: Mapped[Optional[str]] = mapped_column(Text)
    download_token: Mapped[Optional[str]] = mapped_column(Text)
    # Progress tracking fields
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    progress_percentage: Mapped[Optional[float]] = mapped_column(Float, default=None)
    estimated_time_remaining: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None)

    __table_args__ = (
        Index("idx_user_exports_user_id", "user_id"),
        Index("idx_user_exports_export_id", "export_id"),
        Index("idx_user_exports_expires_at", "expires_at"),
        Index("idx_user_exports_status", "status"),
        Index("idx_user_exports_created_at", "created_at"),
        Index("idx_user_exports_export_type", "export_type"),
    )

