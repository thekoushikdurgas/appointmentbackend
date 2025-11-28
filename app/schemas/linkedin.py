"""Pydantic schemas for LinkedIn URL-based CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.exports import ExportStatus
from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut


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


class LinkedInUpsertRequest(BaseModel):
    """Request schema for creating or updating records by LinkedIn URL."""

    url: str = Field(..., description="LinkedIn URL (person or company)")
    contact_data: Optional[dict] = Field(
        None, description="Optional contact data for person LinkedIn URLs"
    )
    company_data: Optional[dict] = Field(
        None, description="Optional company data for company LinkedIn URLs"
    )
    contact_metadata: Optional[dict] = Field(
        None, description="Optional contact metadata (will set linkedin_url to url)"
    )
    company_metadata: Optional[dict] = Field(
        None, description="Optional company metadata (will set linkedin_url to url)"
    )


class LinkedInUpsertResponse(BaseModel):
    """Response schema for create/update operations."""

    created: bool = Field(..., description="Whether new records were created")
    updated: bool = Field(..., description="Whether existing records were updated")
    contacts: list[ContactWithRelations] = Field(default_factory=list)
    companies: list[CompanyWithRelations] = Field(default_factory=list)


class LinkedInExportRequest(BaseModel):
    """Request schema for exporting contacts and companies by LinkedIn URLs."""

    urls: list[str] = Field(..., description="List of LinkedIn URLs to export", min_length=1)


class LinkedInExportResponse(BaseModel):
    """Response schema for LinkedIn export creation."""

    export_id: str
    download_url: str
    expires_at: datetime
    contact_count: int
    company_count: int
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)
