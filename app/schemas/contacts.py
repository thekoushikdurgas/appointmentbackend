"""Pydantic schemas describing contact entities and related metadata."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.companies import CompanySummary
from app.schemas.metadata import ContactMetadataOut
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactBase(BaseModel):
    """Shared fields for contact resources."""

    uuid: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_id: Optional[str] = Field(None, description="UUID of the related company")
    email: Optional[str] = None
    title: Optional[str] = None
    departments: Optional[list[str]] = None
    mobile_phone: Optional[str] = None
    email_status: Optional[str] = None
    text_search: Optional[str] = None
    seniority: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContactCreate(BaseModel):
    """Payload for creating a new contact."""

    uuid: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_id: Optional[str] = Field(None, description="UUID of the related company")
    email: Optional[str] = None
    title: Optional[str] = None
    departments: Optional[list[str]] = None
    mobile_phone: Optional[str] = None
    email_status: Optional[str] = None
    text_search: Optional[str] = Field(None, description="Free-form search text, e.g., location")
    seniority: Optional[str] = None


class ContactDB(ContactBase):
    """Database representation of a contact record."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContactListItem(BaseModel):
    """Flattened contact representation used for list endpoints."""

    uuid: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    company_name_for_emails: Optional[str] = None
    email: Optional[str] = None
    email_status: Optional[str] = None
    primary_email_catch_all_status: Optional[str] = None
    seniority: Optional[str] = None
    departments: Optional[str] = None
    work_direct_phone: Optional[str] = None
    home_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    corporate_phone: Optional[str] = None
    other_phone: Optional[str] = None
    stage: Optional[str] = None
    employees: Optional[int] = None
    industry: Optional[str] = None
    keywords: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    website: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    company_address: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    company_phone: Optional[str] = None
    technologies: Optional[str] = None
    annual_revenue: Optional[int] = None
    total_funding: Optional[int] = None
    latest_funding: Optional[str] = None
    latest_funding_amount: Optional[int] = None
    last_raised_at: Optional[str] = None
    meta_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContactDetail(ContactListItem):
    """Contact list item augmented with nested company and metadata objects."""

    company_detail: Optional[CompanySummary] = None
    metadata: Optional[ContactMetadataOut] = None


class ContactLocation(BaseModel):
    """Location object for the simple contact view."""

    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class ContactSimpleItem(BaseModel):
    """Simplified contact representation for view=simple."""

    uuid: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[ContactLocation] = None
    company_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_domain: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

