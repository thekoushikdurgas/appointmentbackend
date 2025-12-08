"""Repositories handling contact import jobs and error records."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import Select

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.repositories.base import AsyncRepository
from app.schemas.filters import ImportFilterParams


class ImportJobRepository(AsyncRepository[ContactImportJob]):
    """Repository for persisting and querying contact import jobs."""
    def __init__(self) -> None:
        """Initialize the repository for import job persistence."""
        super().__init__(ContactImportJob)

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

    async def increment_progress(
        self,
        session: AsyncSession,
        job_id: str,
        processed_delta: int = 1,
        error_delta: int = 0,
    ) -> None:
        """Increment job progress values in-place."""
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

    async def get_by_job_id(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> Optional[ContactImportJob]:
        """Fetch a job by its public identifier."""
        stmt: Select = select(ContactImportJob).where(ContactImportJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        return job

    async def list_jobs(
        self,
        session: AsyncSession,
        filters: Optional[ImportFilterParams] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContactImportJob]:
        """List jobs ordered from newest to oldest with optional filters."""
        stmt = select(ContactImportJob)
        
        # Apply filters if provided
        if filters:
            stmt = self._apply_filters(stmt, filters)
        
        stmt = stmt.order_by(ContactImportJob.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        jobs = list(result.scalars().all())
        return jobs
    
    def _apply_filters(
        self,
        stmt: Select,
        filters: ImportFilterParams,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement."""
        from sqlalchemy import func
        
        # Status filter
        if filters.status:
            try:
                status_enum = ImportJobStatus(filters.status.lower())
                stmt = stmt.where(ContactImportJob.status == status_enum)
            except ValueError:
                # Invalid status, ignore filter
                pass
        
        # File name filter (case-insensitive substring match)
        if filters.file_name:
            stmt = stmt.where(
                func.lower(ContactImportJob.file_name).contains(
                    filters.file_name.lower()
                )
            )
        
        # Date range filters
        if filters.created_at_after:
            stmt = stmt.where(ContactImportJob.created_at >= filters.created_at_after)
        if filters.created_at_before:
            stmt = stmt.where(ContactImportJob.created_at <= filters.created_at_before)
        
        return stmt


class ImportErrorRepository(AsyncRepository[ContactImportError]):
    """Repository for storing contact import error records."""
    def __init__(self) -> None:
        """Initialize repository for storing import error rows."""
        super().__init__(ContactImportError)

    async def add_errors(
        self,
        session: AsyncSession,
        job_id: int,
        errors: Iterable[ContactImportError],
    ) -> None:
        """Persist a batch of import errors."""
        error_list = list(errors)
        session.add_all(error_list)
        await session.flush()

    async def list_errors_for_job(
        self,
        session: AsyncSession,
        job_id: int,
    ) -> list[ContactImportError]:
        """Return errors for the given job."""
        stmt = select(ContactImportError).where(ContactImportError.job_id == job_id)
        stmt = stmt.order_by(ContactImportError.row_number.asc())
        result = await session.execute(stmt)
        errors = list(result.scalars().all())
        return errors

