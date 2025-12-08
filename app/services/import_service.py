"""Service layer for managing contact import jobs and errors."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.repositories.imports import ImportErrorRepository, ImportJobRepository
from app.schemas.filters import ImportFilterParams
from app.schemas.imports import ImportErrorRecord, ImportJobDetail, ImportJobWithErrors


class ImportService:
    """Encapsulate import job orchestration across repositories."""

    def __init__(
        self,
        job_repository: Optional[ImportJobRepository] = None,
        error_repository: Optional[ImportErrorRepository] = None,
    ) -> None:
        """Initialize the import service with job and error repositories."""
        self.job_repository = job_repository or ImportJobRepository()
        self.error_repository = error_repository or ImportErrorRepository()

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
        job = await self.job_repository.create_job(
            session,
            job_id=job_id,
            file_name=file_name,
            file_path=file_path,
            total_rows=total_rows,
        )
        await session.commit()
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

    async def increment_progress(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        processed_delta: int = 1,
        error_delta: int = 0,
    ) -> None:
        """Increment processed and errored rows for a job."""
        await self.job_repository.increment_progress(
            session,
            job_id,
            processed_delta=processed_delta,
            error_delta=error_delta,
        )
        await session.commit()

    async def add_errors(
        self,
        session: AsyncSession,
        job_db_id: int,
        errors: Iterable[ContactImportError],
    ) -> None:
        """Persist a batch of import errors."""
        error_list = list(errors)
        await self.error_repository.add_errors(session, job_db_id, error_list)
        await session.commit()

    async def get_job(
        self,
        session: AsyncSession,
        job_id: str,
        include_errors: bool = False,
    ) -> Optional[ImportJobWithErrors | ImportJobDetail]:
        """Retrieve a job by its external identifier."""
        job = await self.job_repository.get_by_job_id(session, job_id)
        if not job:
            return None
        if include_errors:
            errors = await self.error_repository.list_errors_for_job(session, job.id)
            job_schema = ImportJobDetail.model_validate(job)
            error_schema = [ImportErrorRecord.model_validate(err) for err in errors]
            return ImportJobWithErrors(**job_schema.model_dump(), errors=error_schema)
        return ImportJobDetail.model_validate(job)

    async def list_jobs(
        self,
        session: AsyncSession,
        filters: Optional[ImportFilterParams] = None,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ImportJobDetail]:
        """List import jobs using pagination and optional filters."""
        # Use filters for pagination if provided
        if filters:
            if filters.page_size is not None:
                limit = filters.page_size
            if filters.page is not None:
                offset = (filters.page - 1) * (limit or 20)
        
        jobs = await self.job_repository.list_jobs(
            session, filters=filters, limit=limit, offset=offset
        )
        results = [ImportJobDetail.model_validate(job) for job in jobs]
        return results

