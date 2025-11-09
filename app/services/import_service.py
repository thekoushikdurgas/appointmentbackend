"""Service layer for managing contact import jobs and errors."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.repositories.imports import ImportErrorRepository, ImportJobRepository
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors


class ImportService:
    """Encapsulate import job orchestration across repositories."""

    def __init__(
        self,
        job_repository: Optional[ImportJobRepository] = None,
        error_repository: Optional[ImportErrorRepository] = None,
    ) -> None:
        """Initialize the import service with job and error repositories."""
        self.logger = get_logger(__name__)
        self.logger.debug(
            "Entering ImportService.__init__ job_repository=%s error_repository=%s",
            job_repository,
            error_repository,
        )
        self.job_repository = job_repository or ImportJobRepository()
        self.error_repository = error_repository or ImportErrorRepository()
        self.logger.debug(
            "Exiting ImportService.__init__ job_repository=%s error_repository=%s",
            self.job_repository.__class__.__name__,
            self.error_repository.__class__.__name__,
        )

    async def create_job(
        self,
        session: AsyncSession,
        *,
        job_id: str,
        file_name: str,
        file_path: str,
        total_rows: int,
    ) -> ContactImportJob:
        """Create a new import job record."""
        self.logger.info(
            "Creating import job: job_id=%s file_name=%s total_rows=%d",
            job_id,
            file_name,
            total_rows,
        )
        job = await self.job_repository.create_job(
            session,
            job_id=job_id,
            file_name=file_name,
            file_path=file_path,
            total_rows=total_rows,
        )
        await session.commit()
        self.logger.debug("Created import job: job_id=%s db_id=%s", job_id, job.id)
        return job

    async def set_status(
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
        """Update an import job's status."""
        self.logger.info(
            "Updating import job status: job_id=%s status=%s processed_rows=%s error_count=%s",
            job_id,
            status,
            processed_rows,
            error_count,
        )
        await self.job_repository.update_job_status(
            session,
            job_id,
            status=status,
            processed_rows=processed_rows,
            error_count=error_count,
            message=message,
            total_rows=total_rows,
        )
        await session.commit()
        self.logger.debug("Updated status for import job: job_id=%s", job_id)

    async def increment_progress(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        processed_delta: int = 1,
        error_delta: int = 0,
    ) -> None:
        """Increment processed and errored rows for a job."""
        self.logger.debug(
            "Incrementing import job progress: job_id=%s processed_delta=%d error_delta=%d",
            job_id,
            processed_delta,
            error_delta,
        )
        await self.job_repository.increment_progress(
            session,
            job_id,
            processed_delta=processed_delta,
            error_delta=error_delta,
        )
        await session.commit()
        self.logger.debug("Incremented progress for import job: job_id=%s", job_id)

    async def add_errors(
        self,
        session: AsyncSession,
        job_db_id: int,
        errors: Iterable[ContactImportError],
    ) -> None:
        """Persist a batch of import errors."""
        error_list = list(errors)
        self.logger.info("Adding import errors: job_db_id=%d batch_size=%d", job_db_id, len(error_list))
        await self.error_repository.add_errors(session, job_db_id, error_list)
        await session.commit()
        self.logger.debug("Stored import errors: job_db_id=%d batch_size=%d", job_db_id, len(error_list))

    async def get_job(
        self,
        session: AsyncSession,
        job_id: str,
        include_errors: bool = False,
    ) -> Optional[ImportJobWithErrors | ImportJobDetail]:
        """Retrieve a job by its external identifier."""
        self.logger.info("Fetching import job: job_id=%s include_errors=%s", job_id, include_errors)
        job = await self.job_repository.get_by_job_id(session, job_id)
        if not job:
            self.logger.warning("Import job not found: job_id=%s", job_id)
            return None
        if include_errors:
            errors = await self.error_repository.list_errors_for_job(session, job.id)
            job_schema = ImportJobDetail.model_validate(job)
            error_schema = [ImportErrorRecord.model_validate(err) for err in errors]
            self.logger.debug(
                "Returning import job with errors: job_id=%s error_count=%d",
                job_id,
                len(error_schema),
            )
            return ImportJobWithErrors(**job_schema.model_dump(), errors=error_schema)
        self.logger.debug("Returning import job detail: job_id=%s", job_id)
        return ImportJobDetail.model_validate(job)

    async def list_jobs(
        self,
        session: AsyncSession,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ImportJobDetail]:
        """List import jobs using pagination."""
        self.logger.debug("Listing import jobs: limit=%d offset=%d", limit, offset)
        jobs = await self.job_repository.list_jobs(session, limit=limit, offset=offset)
        results = [ImportJobDetail.model_validate(job) for job in jobs]
        self.logger.debug(
            "Exiting ImportService.list_jobs result_count=%d", len(results)
        )
        return results

