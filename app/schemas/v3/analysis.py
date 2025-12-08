"""Analysis schemas for v3 API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ContactAnalysisResult(BaseModel):
    """Analysis result for a contact."""

    contact_uuid: str = Field(..., description="Contact UUID")
    title: Optional[str] = Field(None, description="Contact title")
    title_valid: bool = Field(..., description="Whether title is valid")
    title_needs_cleaning: bool = Field(..., description="Whether title needs cleaning")
    title_cleaned: Optional[str] = Field(None, description="Cleaned title if applicable")
    title_issues: List[str] = Field(default_factory=list, description="List of title issues found")
    has_international_chars: bool = Field(..., description="Whether title contains international characters")
    has_encoding_issues: bool = Field(..., description="Whether title has encoding issues")
    has_emoji: bool = Field(..., description="Whether title contains emoji")


class CompanyAnalysisResult(BaseModel):
    """Analysis result for a company."""

    company_uuid: str = Field(..., description="Company UUID")
    name: Optional[str] = Field(None, description="Company name")
    name_valid: bool = Field(..., description="Whether company name is valid")
    name_needs_cleaning: bool = Field(..., description="Whether name needs cleaning")
    name_cleaned: Optional[str] = Field(None, description="Cleaned name if applicable")
    name_issues: List[str] = Field(default_factory=list, description="List of name issues found")
    has_international_chars: bool = Field(..., description="Whether name contains international characters")
    has_encoding_issues: bool = Field(..., description="Whether name has encoding issues")
    has_emoji: bool = Field(..., description="Whether name contains emoji")
    keywords_valid: bool = Field(..., description="Whether keywords are valid")
    keywords_needs_cleaning: bool = Field(..., description="Whether keywords need cleaning")
    keywords_issues: List[str] = Field(default_factory=list, description="List of keyword issues found")
    invalid_keywords_count: int = Field(..., description="Number of invalid keywords")


class AnalysisResponse(BaseModel):
    """Response for single contact/company analysis."""

    analysis: ContactAnalysisResult | CompanyAnalysisResult


class AnalysisBatchRequest(BaseModel):
    """Request for batch analysis."""

    uuids: List[str] = Field(..., description="List of UUIDs to analyze", min_length=1)


class AnalysisBatchResponse(BaseModel):
    """Response for batch analysis."""

    total: int = Field(..., description="Total number of records processed")
    analyses: List[ContactAnalysisResult | CompanyAnalysisResult] = Field(
        ..., description="Analysis results for each record"
    )

