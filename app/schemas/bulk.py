"""Pydantic schemas for bulk data insert operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BulkInsertRequest(BaseModel):
    """Request schema for bulk data insert endpoint."""

    data: List[Dict[str, Any]] = Field(
        ...,
        description="List of JSON objects containing contact and/or company data in raw CSV-like format",
        min_length=1,
    )

    model_config = ConfigDict(from_attributes=True)


class BulkInsertError(BaseModel):
    """Error details for a failed record."""

    index: int = Field(..., description="Index of the failed record in the input array")
    error: str = Field(..., description="Error message")
    record_type: Optional[str] = Field(None, description="Type of record that failed (contact/company)")


class BulkInsertResponse(BaseModel):
    """Response schema for bulk data insert endpoint."""

    contacts_inserted: int = Field(0, description="Number of contacts successfully inserted")
    contacts_updated: int = Field(0, description="Number of contacts successfully updated")
    contacts_skipped: int = Field(0, description="Number of contacts skipped (errors)")
    companies_inserted: int = Field(0, description="Number of companies successfully inserted")
    companies_updated: int = Field(0, description="Number of companies successfully updated")
    companies_skipped: int = Field(0, description="Number of companies skipped (errors)")
    total_processed: int = Field(..., description="Total number of records processed")
    errors: Optional[List[BulkInsertError]] = Field(
        None, description="List of errors encountered during processing"
    )

    model_config = ConfigDict(from_attributes=True)


# Rebuild models to resolve forward references
BulkInsertResponse.model_rebuild()
