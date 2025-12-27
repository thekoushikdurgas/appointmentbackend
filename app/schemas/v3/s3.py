"""S3 file operation schemas for v3 API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class S3FileInfo(BaseModel):
    """S3 file information."""

    key: str = Field(..., description="S3 object key (full path)")
    filename: str = Field(..., description="Filename extracted from key")
    size: Optional[int] = Field(None, description="File size in bytes")
    last_modified: Optional[datetime] = Field(None, description="Last modified timestamp")
    content_type: Optional[str] = Field(None, description="Content type/MIME type")


class S3FileListResponse(BaseModel):
    """Response for listing S3 CSV files."""

    files: List[S3FileInfo] = Field(..., description="List of CSV files in S3 bucket")
    total: int = Field(..., description="Total number of CSV files")


class S3FileDataRow(BaseModel):
    """A single row of CSV data."""

    data: dict = Field(..., description="Row data as dictionary")


class S3FileDataResponse(BaseModel):
    """Response for paginated CSV file data."""

    file_key: str = Field(..., description="S3 object key")
    rows: List[S3FileDataRow] = Field(..., description="Paginated rows")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")
    total_rows: Optional[int] = Field(None, description="Total number of rows in file (if available)")

