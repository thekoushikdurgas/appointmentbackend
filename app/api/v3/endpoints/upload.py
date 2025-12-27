"""Upload operation endpoints for v3 API."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.schemas.v3.upload import (
    AbortUploadRequest,
    CompleteUploadRequest,
    CompleteUploadResponse,
    InitiateUploadRequest,
    InitiateUploadResponse,
    PresignedUrlResponse,
    RegisterPartRequest,
    UploadStatusResponse,
)
from app.services.s3_service import S3Service
from app.services.upload_session_manager import (
    UploadSession,
    get_upload_manager,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])
s3_service = S3Service()
upload_manager = get_upload_manager()
settings = get_settings()

# Configuration from settings with defaults
CHUNK_SIZE = getattr(settings, "S3_MULTIPART_CHUNK_SIZE", 100 * 1024 * 1024)  # 100MB
MAX_FILE_SIZE = getattr(
    settings, "S3_MULTIPART_MAX_FILE_SIZE", 10 * 1024 * 1024 * 1024
)  # 10GB
PRESIGNED_URL_EXPIRATION = getattr(
    settings, "S3_MULTIPART_URL_EXPIRATION", 3600
)  # 1 hour
UPLOAD_PREFIX = getattr(settings, "S3_UPLOAD_PREFIX", "uploads/")
BUCKET_NAME = settings.S3_BUCKET_NAME


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(
    request: InitiateUploadRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Initialize multipart upload session.

    Creates a new multipart upload session in S3 and stores session metadata
    for tracking upload progress and enabling resume functionality.
    """
    if request.file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {MAX_FILE_SIZE / (1024**3):.0f}GB limit",
        )

    if not BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 bucket not configured",
        )

    # Generate unique upload ID and file key
    upload_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_key = f"{UPLOAD_PREFIX}{current_user.id}/{timestamp}_{request.filename}"

    try:
        # Initiate S3 multipart upload
        s3_response = await s3_service.initiate_multipart_upload(
            file_key=file_key,
            content_type=request.content_type,
            bucket_name=BUCKET_NAME,
        )

        # Create upload session
        session = UploadSession(
            upload_id=upload_id,
            file_key=file_key,
            file_size=request.file_size,
            s3_upload_id=s3_response["upload_id"],
            chunk_size=CHUNK_SIZE,
        )
        await upload_manager.create_session(session)

        # Calculate number of parts
        num_parts = (request.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

        return InitiateUploadResponse(
            upload_id=upload_id,
            file_key=file_key,
            s3_upload_id=s3_response["upload_id"],
            chunk_size=CHUNK_SIZE,
            num_parts=num_parts,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate upload: {str(e)}",
        ) from e


@router.get(
    "/presigned-url/{upload_id}/{part_number}",
    response_model=PresignedUrlResponse,
)
async def get_presigned_url(
    upload_id: str = Path(..., description="Upload session identifier"),
    part_number: int = Path(..., gt=0, description="Part number (1-indexed)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get presigned URL for uploading a specific part.

    Returns a presigned URL that allows direct upload to S3 for the specified part.
    If the part was already uploaded, returns the existing ETag.
    """
    session = await upload_manager.get_session(upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or expired",
        )

    # Check if part already uploaded
    if part_number in session.parts:
        return PresignedUrlResponse(
            presigned_url=None,
            part_number=part_number,
            already_uploaded=True,
            etag=session.parts[part_number],
        )

    try:
        # Generate presigned URL
        presigned_url = await s3_service.generate_presigned_upload_url(
            file_key=session.file_key,
            upload_id=session.s3_upload_id,
            part_number=part_number,
            expiration=PRESIGNED_URL_EXPIRATION,
            bucket_name=BUCKET_NAME,
        )

        return PresignedUrlResponse(
            presigned_url=presigned_url,
            part_number=part_number,
            already_uploaded=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}",
        ) from e


@router.post("/parts")
async def register_part(
    request: RegisterPartRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Register a successfully uploaded part with its ETag.

    Called by the frontend after successfully uploading a chunk to S3.
    Stores the ETag for later use in completing the multipart upload.
    """
    session = await upload_manager.get_session(request.upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found",
        )

    try:
        await upload_manager.update_part(
            request.upload_id, request.part_number, request.etag
        )

        return {"status": "part_registered", "part_number": request.part_number}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register part: {str(e)}",
        ) from e


@router.post("/complete", response_model=CompleteUploadResponse)
async def complete_upload(
    request: CompleteUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Complete multipart upload.

    Finalizes the multipart upload in S3 by combining all uploaded parts.
    Cleans up the upload session after successful completion.
    """
    session = await upload_manager.get_session(request.upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found",
        )

    try:
        # Prepare parts list for S3
        parts = [
            {"PartNumber": part_num, "ETag": etag}
            for part_num, etag in sorted(session.parts.items())
        ]

        if not parts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No parts uploaded",
            )

        # Complete S3 multipart upload
        result = await s3_service.complete_multipart_upload(
            file_key=session.file_key,
            upload_id=session.s3_upload_id,
            parts=parts,
            bucket_name=BUCKET_NAME,
        )

        # Update session status
        session.status = "completed"

        # Cleanup session in background
        background_tasks.add_task(upload_manager.delete_session, request.upload_id)

        return CompleteUploadResponse(
            status="completed",
            file_key=session.file_key,
            s3_url=s3_service.get_public_url(session.file_key),
            location=result.get("location"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}",
        ) from e


@router.post("/abort")
async def abort_upload(
    request: AbortUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Abort incomplete multipart upload.

    Cancels the multipart upload in S3 and cleans up the session.
    This prevents orphaned multipart uploads and associated costs.
    """
    session = await upload_manager.get_session(request.upload_id)
    if not session:
        return {"status": "session_not_found", "upload_id": request.upload_id}

    try:
        # Abort S3 upload
        await s3_service.abort_multipart_upload(
            file_key=session.file_key,
            upload_id=session.s3_upload_id,
            bucket_name=BUCKET_NAME,
        )

        # Update session status
        session.status = "aborted"

        # Cleanup session
        background_tasks.add_task(upload_manager.delete_session, request.upload_id)

        return {"status": "aborted", "upload_id": request.upload_id}
    except Exception as e:
        # Log error but don't fail if abort fails (upload might already be completed/aborted)
        return {
            "status": "abort_attempted",
            "upload_id": request.upload_id,
            "error": str(e),
        }


@router.get("/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str = Path(..., description="Upload session identifier"),
    current_user: User = Depends(get_current_user),
):
    """
    Get upload session status (for resuming).

    Returns the current status of an upload session including which parts
    have been uploaded. Used for resuming interrupted uploads.
    """
    session = await upload_manager.get_session(upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or expired",
        )

    uploaded_parts = sorted(session.parts.keys())
    total_parts = (session.file_size + session.chunk_size - 1) // session.chunk_size
    
    # Calculate uploaded bytes more accurately
    # For all parts except the last, use chunk_size
    # For the last part, calculate actual size
    uploaded_bytes = 0
    for part_number in uploaded_parts:
        if part_number == total_parts:
            # Last part - calculate actual size
            start = (part_number - 1) * session.chunk_size
            uploaded_bytes += session.file_size - start
        else:
            # Regular part - use chunk size
            uploaded_bytes += session.chunk_size
    
    # Ensure uploaded_bytes doesn't exceed file_size
    uploaded_bytes = min(uploaded_bytes, session.file_size)

    return UploadStatusResponse(
        upload_id=upload_id,
        file_key=session.file_key,
        file_size=session.file_size,
        chunk_size=session.chunk_size,
        uploaded_parts=uploaded_parts,
        total_parts=total_parts,
        uploaded_bytes=uploaded_bytes,
        status=session.status,
    )

