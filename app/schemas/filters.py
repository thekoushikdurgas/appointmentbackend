from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContactFilterParams(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = Field(default=None, alias="departments")
    stage: Optional[str] = None
    company: Optional[str] = None
    company_id: Optional[str] = None
    company_name_for_emails: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    company_country: Optional[str] = None
    company_state: Optional[str] = None
    company_city: Optional[str] = None
    employees_min: Optional[int] = None
    employees_max: Optional[int] = None
    annual_revenue_min: Optional[int] = None
    annual_revenue_max: Optional[int] = None
    total_funding_min: Optional[int] = None
    total_funding_max: Optional[int] = None
    technologies: Optional[str] = None
    keywords: Optional[str] = None
    industries: Optional[str] = Field(default=None, alias="industry")
    search: Optional[str] = None
    ordering: Optional[str] = None
    distinct: bool = False
    page_size: Optional[int] = None
    cursor: Optional[str] = None
    latest_funding_amount_min: Optional[int] = None
    latest_funding_amount_max: Optional[int] = None
    created_at_after: Optional[datetime] = None
    updated_at_before: Optional[datetime] = None


class AttributeListParams(BaseModel):
    search: Optional[str] = None
    distinct: bool = False
    limit: int = 25
    offset: int = 0
    ordering: Optional[str] = None


class CountParams(BaseModel):
    search: Optional[str] = None
    distinct: bool = False

