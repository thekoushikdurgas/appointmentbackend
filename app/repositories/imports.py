"""Repositories handling contact import jobs and error records."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.repositories.base import AsyncRepository


logger = get_logger(__name__)


class ImportJobRepository(AsyncRepository[ContactImportJob]):
    """Repository for persisting and querying contact import jobs."""
    def __init__(self) -> None:
        """Initialize the repository for import job persistence."""
        logger.debug("Entering ImportJobRepository.__init__")
        super().__init__(ContactImportJob)
        logger.debug("Exiting ImportJobRepository.__init__")

    async def create_job(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        file_name: str,
        file_path: str,
        total_rows: int = 0,
    ) -> ContactImportJob:
        """Insert a new import job."""
        logger.debug(
            "Creating import job: job_id=%s file_name=%s total_rows=%d",
            job_id,
            file_name,
            total_rows,
        )
        job = ContactImportJob(
            job_id=job_id,
            file_name=file_name,
            file_path=file_path,
            total_rows=total_rows,
            status=ImportJobStatus.pending,
        )
        session.add(job)
        await session.flush()
        await session.refresh(job)
        logger.debug("Created import job db_id=%s job_id=%s", job.id, job.job_id)
        return job

    async def update_job_status(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        status: ImportJobStatus,
        processed_rows: Optional[int] = None,
        error_count: Optional[int] = None,
        message: Optional[str] = None,
        total_rows: Optional[int] = None,
    ) -> None:
        """Update the job status and progress counters."""
        logger.debug(
            "Entering ImportJobRepository.update_job_status job_id=%s status=%s",
            job_id,
            status,
        )
        values = {"status": status}
        if processed_rows is not None:
            values["processed_rows"] = processed_rows
        if error_count is not None:
            values["error_count"] = error_count
        if message is not None:
            values["message"] = message
        if total_rows is not None:
            values["total_rows"] = total_rows

        stmt = (
            update(ContactImportJob)
            .where(ContactImportJob.job_id == job_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(stmt)
        logger.debug("Updated job status: job_id=%s values=%s", job_id, values)

    async def increment_progress(
        self,
        session: AsyncSession,
        job_id: str,
        processed_delta: int = 1,
        error_delta: int = 0,
    ) -> None:
        """Increment job progress values in-place."""
        logger.debug(
            "Entering ImportJobRepository.increment_progress job_id=%s processed_delta=%d error_delta=%d",
            job_id,
            processed_delta,
            error_delta,
        )
        stmt = (
            update(ContactImportJob)
            .where(ContactImportJob.job_id == job_id)
            .values(
                processed_rows=ContactImportJob.processed_rows + processed_delta,
                error_count=ContactImportJob.error_count + error_delta,
            )
            .execution_options(synchronize_session="fetch")
        )
        await session.execute(stmt)
        logger.debug(
            "Incremented job progress: job_id=%s processed_delta=%d error_delta=%d",
            job_id,
            processed_delta,
            error_delta,
        )

    async def get_by_job_id(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> Optional[ContactImportJob]:
        """Fetch a job by its public identifier."""
        logger.debug("Entering ImportJobRepository.get_by_job_id job_id=%s", job_id)
        stmt: Select = select(ContactImportJob).where(ContactImportJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        logger.debug("Fetched job by job_id=%s found=%s", job_id, bool(job))
        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContactImportJob]:
        """List jobs ordered from newest to oldest."""
        logger.debug(
            "Entering ImportJobRepository.list_jobs limit=%d offset=%d", limit, offset
        )
        stmt = select(ContactImportJob).order_by(ContactImportJob.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        jobs = list(result.scalars().all())
        logger.debug("Listed %d jobs limit=%d offset=%d", len(jobs), limit, offset)
        return jobs


class ImportErrorRepository(AsyncRepository[ContactImportError]):
    """Repository for storing contact import error records."""
    def __init__(self) -> None:
        """Initialize repository for storing import error rows."""
        logger.debug("Entering ImportErrorRepository.__init__")
        super().__init__(ContactImportError)
        logger.debug("Exiting ImportErrorRepository.__init__")

    async def add_errors(
        self,
        session: AsyncSession,
        job_id: int,
        errors: Iterable[ContactImportError],
    ) -> None:
        """Persist a batch of import errors."""
        logger.debug(
            "Entering ImportErrorRepository.add_errors job_id=%d", job_id
        )
        error_list = list(errors)
        session.add_all(error_list)
        await session.flush()
        logger.debug("Inserted %d import errors for job_id=%d", len(error_list), job_id)

    async def list_errors_for_job(
        self,
        session: AsyncSession,
        job_id: int,
    ) -> list[ContactImportError]:
        """Return errors for the given job."""
        logger.debug(
            "Entering ImportErrorRepository.list_errors_for_job job_id=%d", job_id
        )
        stmt = select(ContactImportError).where(ContactImportError.job_id == job_id)
        stmt = stmt.order_by(ContactImportError.row_number.asc())
        result = await session.execute(stmt)
        errors = list(result.scalars().all())
        logger.debug("Listed %d errors for job_id=%d", len(errors), job_id)
        return errors

