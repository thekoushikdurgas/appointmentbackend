"""Pydantic schemas for email finder operations."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut


class EmailResult(BaseModel):
    """Email result with full contact and company context."""

    email: str = Field(..., description="Email address from Contact.email")
    contact: ContactDB
    metadata: Optional[ContactMetadataOut] = None
    company: Optional[CompanyDB] = None
    company_metadata: Optional[CompanyMetadataOut] = None

    model_config = ConfigDict(from_attributes=True)


class EmailFinderResponse(BaseModel):
    """Response schema for email finder search results."""

    emails: list[EmailResult] = Field(default_factory=list, description="List of found emails with context")
    total: int = Field(0, description="Total number of emails found")


class SimpleEmailResult(BaseModel):
    """Simple email result with only uuid and email."""

    uuid: str = Field(..., description="Contact UUID")
    email: str = Field(..., description="Email address from Contact.email")

    model_config = ConfigDict(from_attributes=True)


class SimpleEmailFinderResponse(BaseModel):
    """Simple response schema for email finder search results."""

    emails: list[SimpleEmailResult] = Field(default_factory=list, description="List of found emails with uuid and email")
    total: int = Field(0, description="Total number of emails found")

