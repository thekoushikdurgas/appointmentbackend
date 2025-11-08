from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.imports import ContactImportError, ImportJobStatus
from app.schemas.common import MessageResponse
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors
from app.services.import_service import ImportService
from app.tasks.import_tasks import process_contacts_import


settings = get_settings()
router = APIRouter(prefix="/contacts/import", tags=["Imports"])
service = ImportService()


@router.get("/", response_model=MessageResponse)
async def import_info() -> MessageResponse:
    return MessageResponse(
        message="Upload a CSV file via POST to /api/contacts/import/ to start a background import job."
    )


@router.post("/", response_model=ImportJobDetail, status_code=status.HTTP_202_ACCEPTED)
async def upload_contacts_import(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> ImportJobDetail:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = upload_dir / temp_filename

    with temp_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = temp_path.stat().st_size
    if file_size == 0:
        temp_path.unlink(missing_ok=True)
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

    return ImportJobDetail.model_validate(job)


@router.get("/{job_id}/", response_model=ImportJobWithErrors | ImportJobDetail)
async def import_job_detail(
    job_id: str,
    include_errors: bool = False,
    session: AsyncSession = Depends(get_db),
) -> ImportJobWithErrors | ImportJobDetail:
    job = await service.get_job(session, job_id, include_errors=include_errors)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job


@router.get("/{job_id}/errors/", response_model=List[ImportErrorRecord])
async def download_import_errors(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> List[ImportErrorRecord]:
    job = await service.get_job(session, job_id, include_errors=True)
    if not job or not isinstance(job, ImportJobWithErrors):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return job.errors

