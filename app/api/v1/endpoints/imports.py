"""Endpoints supporting bulk contact import workflows."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.imports import ContactImportError, ImportJobStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.filters import ImportFilterParams
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors
from app.services.import_service import ImportService
from app.tasks.import_tasks import process_contacts_import
from app.utils.background_tasks import add_background_task_safe


settings = get_settings()
router = APIRouter(prefix="/contacts/import", tags=["Imports"])
service = ImportService()


async def resolve_import_filters(request: Request) -> ImportFilterParams:
    """Build import filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return ImportFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/", response_model=MessageResponse)
async def import_info(
    filters: ImportFilterParams = Depends(resolve_import_filters),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Provide instructions for triggering a contacts import."""
    payload = MessageResponse(
        message="Upload a CSV file via POST to /api/contacts/import/ to start a background import job."
    )
    return payload


@router.post("/", response_model=ImportJobDetail, status_code=status.HTTP_202_ACCEPTED)
async def upload_contacts_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    filters: ImportFilterParams = Depends(resolve_import_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> ImportJobDetail:
    """Accept a CSV upload, persist job metadata, and enqueue background processing."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File name is required")

    upload_dir = Path(settings.UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to prepare upload directory",
        ) from exc
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = upload_dir / temp_filename

    # Chunked async file upload for large files
    # Optimized chunk size based on file size (if known) or use default
    chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE
    total_bytes = 0
    chunks_written = 0
    
    try:
        async with aiofiles.open(temp_path, "wb") as async_file:
            while True:
                try:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    
                    await async_file.write(chunk)
                    total_bytes += len(chunk)
                    chunks_written += 1
                    
                    # Check file size limit if configured
                    if settings.MAX_UPLOAD_SIZE and total_bytes > settings.MAX_UPLOAD_SIZE:
                        await async_file.close()
                        temp_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes",
                        )
                except asyncio.CancelledError:
                    # Handle cancellation gracefully
                    await async_file.close()
                    temp_path.unlink(missing_ok=True)
                    raise
                except Exception as chunk_exc:
                    # Better error recovery - log and re-raise
                    await async_file.close()
                    temp_path.unlink(missing_ok=True)
                    raise
        
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded file",
        ) from exc

    file_size = temp_path.stat().st_size
    if file_size == 0:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    job_id = uuid.uuid4().hex
    try:
        job = await service.create_job(
            session,
            job_id=job_id,
            file_name=file.filename,
            file_path=str(temp_path),
            total_rows=0,
        )
    except Exception as exc:  # noqa: BLE001
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create import job",
        ) from exc

    # Add background task to process the import
    # Note: This is a long-running task that might be better suited for Celery in the future
    # For now, using BackgroundTasks with proper monitoring
    add_background_task_safe(
        background_tasks,
        process_contacts_import,
        job.job_id,
        str(temp_path),
        track_status=True,
        cpu_bound=False,  # I/O-bound task (database and file operations)
    )

    response = ImportJobDetail.model_validate(job)
    return response


@router.get("/{job_id}/", response_model=ImportJobWithErrors | ImportJobDetail)
async def import_job_detail(
    job_id: str,
    include_errors: bool = False,
    filters: ImportFilterParams = Depends(resolve_import_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportJobWithErrors | ImportJobDetail:
    """Return a job record with optional error payload."""
    job = await service.get_job(session, job_id, include_errors=include_errors)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job


@router.get("/{job_id}/errors/", response_model=List[ImportErrorRecord])
async def download_import_errors(
    job_id: str,
    filters: ImportFilterParams = Depends(resolve_import_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ImportErrorRecord]:
    """Return recorded row-level errors for a contacts import job."""
    job = await service.get_job(session, job_id, include_errors=True)
    if not job or not isinstance(job, ImportJobWithErrors):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job.errors

