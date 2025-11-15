"""Pydantic schemas for contact export job tracking."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.exports import ExportStatus, ExportType


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

