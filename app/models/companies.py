"""SQLAlchemy models describing company entities and metadata.

DEPRECATED FOR READS: These models are deprecated for READ operations.
All company data reads should use ConnectraClient via Connectra API.
Write operations (create/update/delete) may still use these models
until Connectra supports write operations.

Migration: Use app.clients.connectra_client.ConnectraClient for all queries.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import StringList
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.models.contacts import Contact


class Company(Base):
    """Represents a company record enriched with metadata and relationships."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    employees_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    industries: Mapped[Optional[list[str]]] = mapped_column(StringList())
    keywords: Mapped[Optional[list[str]]] = mapped_column(StringList())
    address: Mapped[Optional[str]] = mapped_column(Text)
    annual_revenue: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_funding: Mapped[Optional[int]] = mapped_column(BigInteger)
    technologies: Mapped[Optional[list[str]]] = mapped_column(StringList())
    text_search: Mapped[Optional[str]] = mapped_column(Text, index=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))

    metadata_: Mapped["CompanyMetadata"] = relationship(
        "CompanyMetadata",
        back_populates="company",
        uselist=False,
        primaryjoin="Company.uuid == foreign(CompanyMetadata.uuid)",
    )
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="company",
        primaryjoin="Company.uuid == foreign(Contact.company_id)",
    )

    __table_args__ = (
        Index("idx_companies_name", "name"),
        Index("idx_companies_employees_count", "employees_count"),
        Index("idx_companies_annual_revenue", "annual_revenue"),
        Index("idx_companies_total_funding", "total_funding"),
        Index(
            "idx_companies_industries_gin",
            "industries",
            postgresql_using="gin",
        ),
        Index(
            "idx_companies_keywords_gin",
            "keywords",
            postgresql_using="gin",
        ),
        Index(
            "idx_companies_technologies_gin",
            "technologies",
            postgresql_using="gin",
        ),
        Index(
            "idx_companies_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "idx_dec_trgm",
            "text_search",
            postgresql_using="gin",
            postgresql_ops={"text_search": "gin_trgm_ops"},
        ),
        Index("idx_companies_created_at", "created_at"),
        Index(
            "idx_companies_annual_revenue_industries",
            "annual_revenue",
            "industries",
        ),
    )


class CompanyMetadata(Base):
    """Detailed metadata associated with a company."""

    __tablename__ = "companies_metadata"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        Text,
        unique=True,
        index=True,
        nullable=False,
        doc="Matches Company.uuid",
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_sales_url: Mapped[Optional[str]] = mapped_column(Text)
    facebook_url: Mapped[Optional[str]] = mapped_column(Text)
    twitter_url: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(Text)
    normalized_domain: Mapped[Optional[str]] = mapped_column(Text)
    company_name_for_emails: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    latest_funding: Mapped[Optional[str]] = mapped_column(Text)
    latest_funding_amount: Mapped[Optional[int]] = mapped_column(BigInteger)
    last_raised_at: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(Text)
    state: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(Text)

    company: Mapped[Optional[Company]] = relationship(
        "Company",
        back_populates="metadata_",
        primaryjoin="foreign(CompanyMetadata.uuid) == Company.uuid",
    )

    __table_args__ = (
        Index(
            "idx_companies_metadata_company_name_for_emails",
            "company_name_for_emails",
        ),
        Index("idx_companies_metadata_city", "city"),
        Index("idx_companies_metadata_state", "state"),
        Index("idx_companies_metadata_country", "country"),
    )

