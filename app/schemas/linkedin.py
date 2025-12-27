"""Pydantic schemas for LinkedIn URL-based search operations."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LinkedInSearchRequest(BaseModel):
    """Request schema for searching by LinkedIn URL."""

    url: str = Field(..., description="LinkedIn URL to search for (person or company)")


class ContactWithRelations(BaseModel):
    """Contact with its metadata and related company data."""

    contact: ContactDB
    metadata: Optional[ContactMetadataOut] = None
    company: Optional[CompanyDB] = None
    company_metadata: Optional[CompanyMetadataOut] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyWithRelations(BaseModel):
    """Company with its metadata and related contacts."""

    company: CompanyDB
    metadata: Optional[CompanyMetadataOut] = None
    contacts: list[ContactWithRelations] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LinkedInSearchResponse(BaseModel):
    """Response schema for LinkedIn URL search results."""

    contacts: list[ContactWithRelations] = Field(default_factory=list)
    companies: list[CompanyWithRelations] = Field(default_factory=list)
    total_contacts: int = 0
    total_companies: int = 0


