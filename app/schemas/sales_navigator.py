"""Sales Navigator scraping API schemas."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SalesNavigatorScrapeRequest(BaseModel):
    """Request schema for Sales Navigator HTML scraping endpoint."""

    html: str = Field(..., description="Sales Navigator HTML content to scrape", min_length=1)
    # Default to False for fastest response; enable when persistence is needed.
    save: bool = Field(default=False, description="Persist scraped profiles to database")

    @field_validator("html")
    @classmethod
    def validate_html(cls, v: str) -> str:
        """Validate HTML is not empty."""
        if not v or not v.strip():
            raise ValueError("HTML content cannot be empty")
        return v.strip()

    model_config = {"from_attributes": True}


class SalesNavigatorScrapeResponse(BaseModel):
    """Response schema for Sales Navigator HTML scraping endpoint."""

    extraction_metadata: Dict[str, Any] = Field(..., description="Extraction metadata including timestamp and version")
    page_metadata: Dict[str, Any] = Field(..., description="Page-level metadata including search context and pagination")
    profiles: List[Dict[str, Any]] = Field(..., description="List of extracted profile data")
    saved_contacts: List[ContactDB] = Field(default_factory=list, description="List of saved contact records")
    saved_contacts_metadata: List[ContactMetadataOut] = Field(default_factory=list, description="List of saved contact metadata records")
    saved_companies: List[CompanyDB] = Field(default_factory=list, description="List of saved company records")
    saved_companies_metadata: List[CompanyMetadataOut] = Field(default_factory=list, description="List of saved company metadata records")
    save_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of save operation with counts and errors")

    model_config = {"from_attributes": True, "extra": "allow"}

