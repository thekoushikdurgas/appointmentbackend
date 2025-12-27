"""Pydantic schemas describing company resources exposed by the API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompanyBase(BaseModel):
    """Shared fields for primary company representations."""

    uuid: str
    name: Optional[str] = None
    employees_count: Optional[int] = None
    industries: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    address: Optional[str] = None
    annual_revenue: Optional[int] = None
    total_funding: Optional[int] = None
    technologies: Optional[list[str]] = None
    text_search: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyDB(CompanyBase):
    """Representation of a company row retrieved from persistence."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyMetadataOut(BaseModel):
    """Expose metadata enrichment associated with a company."""

    uuid: str
    linkedin_url: Optional[str] = None
    linkedin_sales_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website: Optional[str] = None
    company_name_for_emails: Optional[str] = None
    phone_number: Optional[str] = None
    latest_funding: Optional[str] = None
    latest_funding_amount: Optional[int] = None
    last_raised_at: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanySummary(BaseModel):
    """Lightweight summary used for company list views."""

    uuid: str
    name: Optional[str] = None
    employees_count: Optional[int] = None
    annual_revenue: Optional[int] = None
    total_funding: Optional[int] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone_number: Optional[str] = None
    technologies: Optional[list[str]] = None


class CompanyListItem(CompanySummary):
    """Augments the company summary with additional list metadata."""

    keywords: Optional[list[str]] = None
    metadata: Optional[CompanyMetadataOut] = None


class CompanyCreate(BaseModel):
    """Payload for creating a new company."""

    uuid: Optional[str] = None
    name: Optional[str] = None
    employees_count: Optional[int] = None
    industries: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    address: Optional[str] = None
    annual_revenue: Optional[int] = None
    total_funding: Optional[int] = None
    technologies: Optional[list[str]] = None
    text_search: Optional[str] = Field(None, description="Free-form search text for location")

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    """Payload for updating an existing company."""

    name: Optional[str] = None
    employees_count: Optional[int] = None
    industries: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    address: Optional[str] = None
    annual_revenue: Optional[int] = None
    total_funding: Optional[int] = None
    technologies: Optional[list[str]] = None
    text_search: Optional[str] = Field(None, description="Free-form search text for location")

    model_config = ConfigDict(from_attributes=True)


class CompanyDetail(CompanyListItem):
    """Company list item augmented with full metadata and timestamps."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

