"""Email pattern schemas for v3 API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class EmailPatternInfo(BaseModel):
    """Email pattern information for a contact."""

    contact_uuid: str = Field(..., description="Contact UUID")
    company_uuid: Optional[str] = Field(None, description="Company UUID (from contact's company_id)")
    pattern_format: Optional[str] = Field(None, description="Email pattern format (e.g., 'first.last')")
    pattern_string: Optional[str] = Field(None, description="Pattern string used for generation")
    contact_count: Optional[int] = Field(None, description="Number of contacts using this pattern")
    is_auto_extracted: Optional[bool] = Field(None, description="Whether pattern was auto-extracted")
    patterns: List[dict] = Field(default_factory=list, description="List of all patterns for the company")


class EmailPatternResponse(BaseModel):
    """Response for single contact email pattern."""

    pattern: EmailPatternInfo


class EmailPatternBatchRequest(BaseModel):
    """Request for batch email pattern lookup."""

    uuids: List[str] = Field(..., description="List of contact UUIDs", min_length=1)


class EmailPatternBatchResponse(BaseModel):
    """Response for batch email pattern lookup."""

    total: int = Field(..., description="Total number of contacts processed")
    patterns: List[EmailPatternInfo] = Field(..., description="Email pattern information for each contact")

