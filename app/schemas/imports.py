"""Pydantic schemas for contact import job tracking and error reporting."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.imports import ImportJobStatus


class ImportJobBase(BaseModel):
    """Shared fields describing a contact import job."""

    job_id: str
    file_name: str
    status: ImportJobStatus
    total_rows: int = 0
    processed_rows: int = 0
    error_count: int = 0
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ImportJobDetail(ImportJobBase):
    """Detailed import job information that includes file storage paths."""

    file_path: Optional[str] = None


class ImportErrorRecord(BaseModel):
    """Represents a single row-level import error."""

    row_number: int
    error_message: str
    payload: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ImportJobWithErrors(ImportJobDetail):
    """Import job payload that embeds error records."""

    errors: List[ImportErrorRecord] = Field(default_factory=list)

