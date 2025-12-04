"""Cleanup operation schemas for v3 API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CleanupRequest(BaseModel):
    """Request for batch cleanup operations."""

    uuids: List[str] = Field(..., description="List of UUIDs to clean", min_length=1)


class CleanupResult(BaseModel):
    """Result of cleaning a single record."""

    uuid: str = Field(..., description="UUID of the cleaned record")
    success: bool = Field(..., description="Whether cleaning was successful")
    fields_updated: int = Field(..., description="Number of fields that were updated")
    error: Optional[str] = Field(None, description="Error message if cleaning failed")


class CleanupResponse(BaseModel):
    """Response for cleanup operations."""

    total: int = Field(..., description="Total number of records processed")
    successful: int = Field(..., description="Number of successfully cleaned records")
    failed: int = Field(..., description="Number of failed cleanups")
    results: List[CleanupResult] = Field(..., description="Detailed results for each record")

