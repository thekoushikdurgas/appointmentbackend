"""Pydantic schemas for LinkedIn URL-based CRUD operations."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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

    # Optional column mapping metadata from the original CSV file
    mapping: Optional[dict] = Field(
        default=None,
        description=(
            "Optional mapping metadata describing how the original CSV columns "
            "map to the normalized LinkedIn URL field."
        ),
    )

    # Extended CSV context and field mappings
    raw_headers: Optional[list[str]] = Field(
        default=None,
        description="Optional ordered list of all CSV headers from the original file.",
    )
    rows: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Optional raw rows from the CSV, keyed by header name. "
            "If provided, len(rows) must equal len(urls)."
        ),
    )
    linkedin_url_column: Optional[str] = Field(
        default=None,
        description=(
            "Explicit column name containing LinkedIn URLs. "
            "If not provided, will auto-detect from raw_headers."
        ),
    )
    contact_field_mappings: Optional[dict[str, Optional[str]]] = Field(
        default=None,
        description=(
            "Optional mapping from logical contact fields (e.g. title, departments, mobile_phone) "
            "to CSV column names."
        ),
    )
    company_field_mappings: Optional[dict[str, Optional[str]]] = Field(
        default=None,
        description=(
            "Optional mapping from logical company fields (e.g. company_name, employees_count, "
            "industry, keywords) to CSV column names."
        ),
    )

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        """Validate URLs list is not empty."""
        if not v:
            raise ValueError("urls list cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_csv_context(self) -> "LinkedInExportRequest":
        """Validate consistency between urls, rows, and headers."""
        if self.rows is not None and len(self.rows) != len(self.urls):
            raise ValueError("rows length must match urls length when provided")

        if self.raw_headers is not None:
            header_set = set(self.raw_headers)
            # Ensure all row keys are known headers
            if self.rows is not None:
                for row in self.rows:
                    unknown_keys = set(row.keys()) - header_set
                    if unknown_keys:
                        raise ValueError(
                            f"rows contain keys not present in raw_headers: {sorted(unknown_keys)}"
                        )

            # Ensure field mapping values reference known headers
            for mapping in (self.contact_field_mappings, self.company_field_mappings):
                if mapping:
                    invalid = {
                        col_name
                        for col_name in mapping.values()
                        if col_name is not None and col_name not in header_set
                    }
                    if invalid:
                        raise ValueError(
                            f"field mappings reference unknown headers: {sorted(invalid)}"
                        )

            # Validate linkedin_url_column if provided
            if self.linkedin_url_column is not None and self.linkedin_url_column not in header_set:
                raise ValueError(
                    f"linkedin_url_column '{self.linkedin_url_column}' not found in raw_headers"
                )

        return self


class LinkedInExportResponse(BaseModel):
    """Response schema for LinkedIn export creation."""

    export_id: str
    download_url: str
    expires_at: datetime
    contact_count: int
    company_count: int
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)
