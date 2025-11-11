"""SQLAlchemy models representing contacts and their enriched metadata."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import StringList

if TYPE_CHECKING:  # pragma: no cover
    from app.models.companies import Company


class Contact(Base):
    """Represents an individual contact that can be queried through the API."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(
        Text, ForeignKey("companies.uuid", ondelete="SET NULL"), index=True
    )
    email: Mapped[Optional[str]] = mapped_column(Text, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, index=True)
    departments: Mapped[Optional[list[str]]] = mapped_column(StringList())
    mobile_phone: Mapped[Optional[str]] = mapped_column(Text, index=True)
    email_status: Mapped[Optional[str]] = mapped_column(Text, index=True)
    text_search: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    seniority: Mapped[Optional[str]] = mapped_column(Text, default="_", index=True)

    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        back_populates="contacts",
        primaryjoin="foreign(Contact.company_id) == Company.uuid",
    )
    metadata_: Mapped[Optional["ContactMetadata"]] = relationship(
        "ContactMetadata",
        back_populates="contact",
        uselist=False,
        primaryjoin="foreign(ContactMetadata.uuid) == Contact.uuid",
    )

    __table_args__ = (
        Index("idx_contacts_first_name", "first_name"),
        Index("idx_contacts_last_name", "last_name"),
        Index("idx_contacts_company_id", "company_id"),
        Index("idx_contacts_email", "email"),
        Index("idx_contacts_mobile_phone", "mobile_phone"),
        Index("idx_contacts_email_status", "email_status"),
        Index("idx_contacts_title", "title"),
        Index(
            "idx_contacts_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("idx_contacts_email_company", "email", "company_id"),
        Index("idx_contacts_name_company", "first_name", "last_name", "company_id"),
        Index("idx_contacts_created_at", "created_at"),
        Index("idx_contacts_seniority", "seniority"),
        Index("idx_contacts_seniority_company_id", "seniority", "company_id"),
        Index(
            "idx_contacts_departments_gin",
            "departments",
            postgresql_using="gin",
        ),
        Index(
            "idx_contacts_company_department",
            "company_id",
            "departments",
        ),
        Index(
            "idx_contacts_seniority_department",
            "seniority",
            "departments",
        ),
        Index(
            "idx_contacts_dec_trgm",
            "text_search",
            postgresql_using="gin",
            postgresql_ops={"text_search": "gin_trgm_ops"},
        ),
    )


class ContactMetadata(Base):
    """Detailed metadata sourced from enrichment providers for contacts."""

    __tablename__ = "contacts_metadata"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, default="_")
    facebook_url: Mapped[Optional[str]] = mapped_column(Text, default="_")
    twitter_url: Mapped[Optional[str]] = mapped_column(Text, default="_")
    website: Mapped[Optional[str]] = mapped_column(Text, default="_")
    work_direct_phone: Mapped[Optional[str]] = mapped_column(Text, default="_")
    home_phone: Mapped[Optional[str]] = mapped_column(Text, default="_")
    city: Mapped[Optional[str]] = mapped_column(Text, default="_")
    state: Mapped[Optional[str]] = mapped_column(Text, default="_")
    country: Mapped[Optional[str]] = mapped_column(Text, default="_")
    other_phone: Mapped[Optional[str]] = mapped_column(Text, default="_")
    stage: Mapped[Optional[str]] = mapped_column(Text, default="_")

    contact: Mapped[Optional[Contact]] = relationship(
        "Contact",
        back_populates="metadata_",
        primaryjoin="foreign(ContactMetadata.uuid) == Contact.uuid",
    )

    __table_args__ = (
        Index("idx_contacts_metadata_city", "city"),
        Index("idx_contacts_metadata_state", "state"),
        Index("idx_contacts_metadata_country", "country"),
    )

