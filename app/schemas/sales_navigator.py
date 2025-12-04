"""Sales Navigator scraping API schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SalesNavigatorScrapeRequest(BaseModel):
    """Request schema for Sales Navigator HTML scraping endpoint."""

    html: str = Field(..., description="Sales Navigator HTML content to scrape", min_length=1)

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

    model_config = {"from_attributes": True, "extra": "allow"}

