"""SQLAlchemy models and enums describing contact import jobs and errors."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ImportJobStatus(str, PyEnum):
    """Enumerates the possible lifecycle states of an import job."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ContactImportJob(Base):
    """Represents a CSV import job tracked by the system."""

    __tablename__ = "contact_import_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
    file_name: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(Text)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ImportJobStatus] = mapped_column(
        SQLEnum(ImportJobStatus, name="import_job_status"),
        default=ImportJobStatus.pending,
        index=True,
    )
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    errors: Mapped[list["ContactImportError"]] = relationship(
        "ContactImportError",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class ContactImportError(Base):
    """Records a row-level import error for post-processing and debugging."""

    __tablename__ = "contact_import_errors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contact_import_jobs.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str] = mapped_column(Text)
    payload: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    job: Mapped[ContactImportJob] = relationship("ContactImportJob", back_populates="errors")

