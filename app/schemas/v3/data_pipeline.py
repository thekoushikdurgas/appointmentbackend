"""Data pipeline schemas for v3 API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    """Request for data ingestion."""

    file_path: Optional[str] = Field(None, description="Local file path (for local ingestion)")
    object_key: Optional[str] = Field(None, description="S3 object key (for S3 ingestion)")
    batch_size: int = Field(1000, description="Number of rows to process per batch", ge=1, le=10000)
    max_threads: int = Field(3, description="Maximum number of concurrent threads", ge=1, le=10)


class IngestionResponse(BaseModel):
    """Response for data ingestion."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued", "running", "completed", "failed"] = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    error_count: int = Field(0, description="Number of errors encountered")
    error_log_path: Optional[str] = Field(None, description="Path to error log file if errors occurred")
    records_processed: Optional[int] = Field(None, description="Number of records processed")


class CleaningRequest(BaseModel):
    """Request for database cleaning."""

    batch_size: int = Field(1000, description="Number of rows to process per batch", ge=1, le=10000)
    table_filter: Optional[Literal["companies", "contacts", "all"]] = Field(
        "all", description="Which tables to clean"
    )


class CleaningResponse(BaseModel):
    """Response for database cleaning."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued", "running", "completed", "failed"] = Field(..., description="Job status")
    processed: int = Field(0, description="Number of records processed")
    updated: int = Field(0, description="Number of records updated")
    errors: int = Field(0, description="Number of errors encountered")
    invalid_names: int = Field(0, description="Number of invalid company names set to NULL")
    message: str = Field(..., description="Status message")
    error_log_path: Optional[str] = Field(None, description="Path to error log file if errors occurred")


class AnalysisRequest(BaseModel):
    """Request for data analysis."""

    analysis_type: Literal["company-names", "comprehensive"] = Field(
        ..., description="Type of analysis to run"
    )
    batch_size: int = Field(1000, description="Number of rows to process per batch", ge=1, le=10000)


class AnalysisResponse(BaseModel):
    """Response for data analysis."""

    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued", "running", "completed", "failed"] = Field(..., description="Job status")
    report_path: Optional[str] = Field(None, description="Path to generated report file")
    json_report_path: Optional[str] = Field(None, description="Path to JSON report file")
    statistics: Optional[dict] = Field(None, description="Analysis statistics")
    timestamp: str = Field(..., description="Analysis timestamp")
    message: str = Field(..., description="Status message")

