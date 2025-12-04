"""Pydantic schemas for email pattern operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationParams


class EmailPatternBase(BaseModel):
    """Base schema with common email pattern fields."""

    company_uuid: str = Field(..., description="Company UUID")
    pattern_format: Optional[str] = Field(None, description="Extracted pattern format (e.g., 'first.last', 'firstlast')")
    pattern_string: Optional[str] = Field(None, description="Actual pattern string used for generation")
    contact_count: int = Field(0, description="Number of contacts using this pattern", ge=0)
    is_auto_extracted: bool = Field(False, description="Whether pattern was auto-extracted")


class EmailPatternCreate(EmailPatternBase):
    """Schema for creating a new email pattern."""

    uuid: Optional[str] = Field(None, description="Pattern UUID (auto-generated if not provided)")


class EmailPatternUpdate(BaseModel):
    """Schema for updating an existing email pattern."""

    pattern_format: Optional[str] = Field(None, description="Extracted pattern format")
    pattern_string: Optional[str] = Field(None, description="Actual pattern string")
    contact_count: Optional[int] = Field(None, description="Number of contacts using this pattern", ge=0)
    is_auto_extracted: Optional[bool] = Field(None, description="Whether pattern was auto-extracted")


class EmailPatternResponse(EmailPatternBase):
    """Response schema for email pattern with all fields."""

    id: int = Field(..., description="Pattern ID")
    uuid: str = Field(..., description="Pattern UUID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class EmailPatternListResponse(BaseModel):
    """Response schema for listing email patterns."""

    patterns: list[EmailPatternResponse] = Field(default_factory=list, description="List of email patterns")
    total: int = Field(0, description="Total number of patterns")


class EmailPatternAnalyzeRequest(BaseModel):
    """Request schema for analyzing company emails."""

    force_reanalyze: bool = Field(
        False,
        description="If true, reanalyze even if patterns already exist for the company",
    )


class PatternAnalysisResult(BaseModel):
    """Result of pattern analysis for a single pattern."""

    pattern_format: str = Field(..., description="Extracted pattern format")
    pattern_string: str = Field(..., description="Pattern string")
    contact_count: int = Field(..., description="Number of contacts using this pattern")
    sample_emails: list[str] = Field(default_factory=list, description="Sample emails matching this pattern")


class EmailPatternAnalyzeResponse(BaseModel):
    """Response schema for email pattern analysis."""

    company_uuid: str = Field(..., description="Company UUID that was analyzed")
    patterns_found: int = Field(..., description="Number of unique patterns found")
    contacts_analyzed: int = Field(..., description="Number of contacts analyzed")
    patterns: list[PatternAnalysisResult] = Field(default_factory=list, description="List of extracted patterns")
    created: int = Field(0, description="Number of new patterns created")
    updated: int = Field(0, description="Number of existing patterns updated")


class EmailPatternBulkCreate(BaseModel):
    """Schema for bulk creating email patterns."""

    patterns: list[EmailPatternCreate] = Field(..., description="List of email patterns to create")


class EmailPatternImportResponse(BaseModel):
    """Response schema for email pattern import operations."""

    total_rows: int = Field(..., description="Total number of rows processed")
    created: int = Field(0, description="Number of new patterns created")
    updated: int = Field(0, description="Number of existing patterns updated (contact_count incremented)")
    errors: int = Field(0, description="Number of rows that failed to process")
    error_details: list[str] = Field(default_factory=list, description="Optional list of error messages")

