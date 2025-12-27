"""SQLAlchemy model for email patterns."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.models.companies import Company


class EmailPattern(Base):
    """Represents an email pattern for a company."""

    __tablename__ = "email_patterns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    company_uuid: Mapped[str] = mapped_column(
        Text,
        ForeignKey("companies.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pattern_format: Mapped[Optional[str]] = mapped_column(Text)
    pattern_string: Mapped[Optional[str]] = mapped_column(Text)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    is_auto_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))

    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        primaryjoin="foreign(EmailPattern.company_uuid) == Company.uuid",
    )

    __table_args__ = (
        Index("idx_email_patterns_uuid_unique", "uuid", unique=True),
        Index("idx_email_patterns_company_uuid", "company_uuid"),
        Index("idx_email_patterns_company_pattern", "company_uuid", "pattern_format"),
        Index("idx_email_patterns_created_at", "created_at"),
    )

