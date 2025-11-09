"""Endpoints supporting bulk contact import workflows."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.imports import ContactImportError, ImportJobStatus
from app.schemas.common import MessageResponse
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors
from app.services.import_service import ImportService
from app.tasks.import_tasks import process_contacts_import


settings = get_settings()
router = APIRouter(prefix="/contacts/import", tags=["Imports"])
service = ImportService()
logger = get_logger(__name__)


@router.get("/", response_model=MessageResponse)
async def import_info() -> MessageResponse:
    """Provide instructions for triggering a contacts import."""
    logger.info("Import info endpoint requested")
    payload = MessageResponse(
        message="Upload a CSV file via POST to /api/contacts/import/ to start a background import job."
    )
    logger.debug("Import info payload prepared")
    return payload


@router.post("/", response_model=ImportJobDetail, status_code=status.HTTP_202_ACCEPTED)
async def upload_contacts_import(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> ImportJobDetail:
    """Accept a CSV upload, persist job metadata, and enqueue background processing."""
    logger.info("Received contacts import upload request: filename=%s content_type=%s", file.filename, file.content_type)
    if not file.filename:
        logger.warning("Upload rejected: missing filename")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = upload_dir / temp_filename

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.debug("Persisted uploaded file to temporary path: temp_path=%s", temp_path)

    file_size = temp_path.stat().st_size
    if file_size == 0:
        temp_path.unlink(missing_ok=True)
        logger.warning("Upload rejected: file was empty filename=%s", file.filename)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    job_id = uuid.uuid4().hex
    job = await service.create_job(
        session,
        job_id=job_id,
        file_name=file.filename,
        file_path=str(temp_path),
        total_rows=0,
    )

    # Celery task scheduling will be wired in Step 9.
    process_contacts_import.delay(job.job_id, str(temp_path))
    logger.info(
        "Enqueued contacts import: job_id=%s filename=%s stored_path=%s size_bytes=%d",
        job.job_id,
        file.filename,
        temp_path,
        file_size,
    )

    response = ImportJobDetail.model_validate(job)
    logger.debug("Returning import job detail response: job_id=%s", job.job_id)
    return response


@router.get("/{job_id}/", response_model=ImportJobWithErrors | ImportJobDetail)
async def import_job_detail(
    job_id: str,
    include_errors: bool = False,
    session: AsyncSession = Depends(get_db),
) -> ImportJobWithErrors | ImportJobDetail:
    """Return a job record with optional error payload."""
    logger.info("Fetching import job detail: job_id=%s include_errors=%s", job_id, include_errors)
    job = await service.get_job(session, job_id, include_errors=include_errors)
    if not job:
        logger.warning("Import job not found: job_id=%s", job_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    logger.info(
        "Fetched import job detail: job_id=%s status=%s",
        job_id,
        job.status if isinstance(job, ImportJobDetail) else job.status,
    )
    return job


@router.get("/{job_id}/errors/", response_model=List[ImportErrorRecord])
async def download_import_errors(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> List[ImportErrorRecord]:
    """Return recorded row-level errors for a contacts import job."""
    logger.info("Fetching import job errors: job_id=%s", job_id)
    job = await service.get_job(session, job_id, include_errors=True)
    if not job or not isinstance(job, ImportJobWithErrors):
        logger.warning("Import job errors not found: job_id=%s", job_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    logger.info("Fetched import job errors: job_id=%s error_count=%d", job_id, len(job.errors))
    return job.errors

