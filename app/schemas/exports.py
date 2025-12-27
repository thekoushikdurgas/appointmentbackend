"""Pydantic schemas for contact export job tracking."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.exports import ExportStatus, ExportType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContactExportRequest(BaseModel):
    """Request schema for creating a contact export."""

    contact_uuids: List[str] = Field(..., description="List of contact UUIDs to export", min_length=1)


class ContactExportResponse(BaseModel):
    """Response schema for contact export creation."""

    export_id: str
    download_url: str
    expires_at: datetime
    contact_count: int
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)


class CompanyExportRequest(BaseModel):
    """Request schema for creating a company export."""

    company_uuids: List[str] = Field(..., description="List of company UUIDs to export", min_length=1)


class CompanyExportResponse(BaseModel):
    """Response schema for company export creation."""

    export_id: str
    download_url: str
    expires_at: datetime
    company_count: int
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)


class UserExportDetail(BaseModel):
    """Full export record schema with all fields."""

    export_id: str
    user_id: str
    export_type: ExportType
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    contact_count: int = 0
    contact_uuids: Optional[List[str]] = None
    company_count: int = 0
    company_uuids: Optional[List[str]] = None
    linkedin_urls: Optional[List[str]] = Field(None, description="LinkedIn URLs used for LinkedIn exports. Only populated for exports created via POST /api/v2/linkedin/export.")
    status: ExportStatus
    created_at: datetime
    expires_at: Optional[datetime] = None
    download_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExportListResponse(BaseModel):
    """Response schema for listing user exports."""

    exports: List[UserExportDetail]
    total: int

    model_config = ConfigDict(from_attributes=True)


class ExportStatusResponse(BaseModel):
    """Response schema for export status endpoint."""

    export_id: str
    status: ExportStatus
    progress_percentage: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    estimated_time: Optional[int] = Field(None, ge=0, description="Estimated time remaining in seconds")
    error_message: Optional[str] = Field(None, description="Error message if export failed")
    download_url: Optional[str] = Field(None, description="Download URL if export is completed")
    expires_at: Optional[datetime] = Field(None, description="Expiration time of the download URL")

    model_config = ConfigDict(from_attributes=True)


class ChunkedExportRequest(BaseModel):
    """Request schema for chunked export."""

    chunks: List[List[str]] = Field(..., description="List of UUID chunks to export", min_length=1)
    merge: bool = Field(True, description="Whether to merge chunks into a single export file")


class ChunkedExportResponse(BaseModel):
    """Response schema for chunked export creation."""

    export_id: str
    chunk_ids: List[str] = Field(..., description="List of chunk export IDs")
    total_count: int = Field(..., description="Total number of records across all chunks")
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)


class EmailExportResponse(BaseModel):
    """Response schema for email export creation."""

    export_id: str
    download_url: str
    expires_at: datetime
    contact_count: int
    company_count: int
    status: ExportStatus

    model_config = ConfigDict(from_attributes=True)