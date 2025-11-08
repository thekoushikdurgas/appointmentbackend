from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
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
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyMetadataOut(BaseModel):
    uuid: str
    linkedin_url: Optional[str] = None
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
    keywords: Optional[list[str]] = None
    metadata: Optional[CompanyMetadataOut] = None

