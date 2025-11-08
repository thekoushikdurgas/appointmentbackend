from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.imports import ImportJobStatus


class ImportJobBase(BaseModel):
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
    file_path: Optional[str] = None


class ImportErrorRecord(BaseModel):
    row_number: int
    error_message: str
    payload: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ImportJobWithErrors(ImportJobDetail):
    errors: List[ImportErrorRecord] = []

