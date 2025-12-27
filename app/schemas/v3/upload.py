"""Upload operation schemas for v3 API."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class InitiateUploadRequest(BaseModel):
    """Request to initiate a multipart upload."""

    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_type: str = Field(
        "application/octet-stream", description="MIME type"
    )


class InitiateUploadResponse(BaseModel):
    """Response after initiating a multipart upload."""

    upload_id: str = Field(..., description="Unique upload identifier")
    file_key: str = Field(..., description="S3 object key (path)")
    s3_upload_id: str = Field(..., description="S3 multipart upload ID")
    chunk_size: int = Field(..., description="Chunk size in bytes")
    num_parts: int = Field(..., description="Total number of parts")


class PresignedUrlResponse(BaseModel):
    """Response containing presigned URL for uploading a part."""

    presigned_url: Optional[str] = Field(
        None, description="Presigned URL for uploading the part"
    )
    part_number: int = Field(..., description="Part number (1-indexed)")
    already_uploaded: bool = Field(
        False, description="Whether this part was already uploaded"
    )
    etag: Optional[str] = Field(
        None, description="ETag if part was already uploaded"
    )


class RegisterPartRequest(BaseModel):
    """Request to register a successfully uploaded part."""

    upload_id: str = Field(..., description="Upload session identifier")
    part_number: int = Field(..., gt=0, description="Part number (1-indexed)")
    etag: str = Field(..., description="ETag from S3 for this part")


class CompleteUploadRequest(BaseModel):
    """Request to complete a multipart upload."""

    upload_id: str = Field(..., description="Upload session identifier")


class CompleteUploadResponse(BaseModel):
    """Response after completing a multipart upload."""

    status: str = Field(..., description="Upload status")
    file_key: str = Field(..., description="S3 object key (path)")
    s3_url: str = Field(..., description="Public S3 URL")
    location: Optional[str] = Field(None, description="S3 location URL")


class AbortUploadRequest(BaseModel):
    """Request to abort an incomplete multipart upload."""

    upload_id: str = Field(..., description="Upload session identifier")


class UploadStatusResponse(BaseModel):
    """Response containing upload session status."""

    upload_id: str = Field(..., description="Upload session identifier")
    file_key: str = Field(..., description="S3 object key (path)")
    file_size: int = Field(..., description="Total file size in bytes")
    chunk_size: int = Field(..., description="Chunk size in bytes")
    uploaded_parts: List[int] = Field(
        ..., description="List of uploaded part numbers"
    )
    total_parts: int = Field(..., description="Total number of parts")
    uploaded_bytes: int = Field(..., description="Total bytes uploaded")
    status: str = Field(..., description="Upload status")

