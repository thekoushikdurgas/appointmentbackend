from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.repositories.base import AsyncRepository


class ImportJobRepository(AsyncRepository[ContactImportJob]):
    def __init__(self) -> None:
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
        stmt: Select = select(ContactImportJob).where(ContactImportJob.job_id == job_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContactImportJob]:
        stmt = select(ContactImportJob).order_by(ContactImportJob.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class ImportErrorRepository(AsyncRepository[ContactImportError]):
    def __init__(self) -> None:
        super().__init__(ContactImportError)

    async def add_errors(
        self,
        session: AsyncSession,
        job_id: int,
        errors: Iterable[ContactImportError],
    ) -> None:
        session.add_all(errors)
        await session.flush()

    async def list_errors_for_job(
        self,
        session: AsyncSession,
        job_id: int,
    ) -> list[ContactImportError]:
        stmt = select(ContactImportError).where(ContactImportError.job_id == job_id)
        stmt = stmt.order_by(ContactImportError.row_number.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

