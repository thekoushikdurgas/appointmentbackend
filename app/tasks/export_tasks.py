"""Background task functions for export processing.

This module provides async functions for processing exports in the background.
These functions are designed to be used with FastAPI's BackgroundTasks.
"""

import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.exports import ExportStatus, UserExport
from app.services.export_service import ExportService

settings = get_settings()
export_service = ExportService()
logger = get_logger(__name__)


async def _update_export_progress(
    session: AsyncSession,
    export_id: str,
    records_processed: int,
    total_records: int,
    start_time: float,
) -> None:
    """Update export progress in the database."""
    try:
        stmt = select(UserExport).where(UserExport.export_id == export_id)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if not export:
            logger.warning("Export not found for progress update: export_id=%s", export_id)
            return
        
        export.records_processed = records_processed
        export.total_records = total_records
        
        # Calculate progress percentage
        if total_records > 0:
            export.progress_percentage = (records_processed / total_records) * 100
        else:
            export.progress_percentage = 0.0
        
        # Estimate time remaining
        if records_processed > 0:
            elapsed_time = time.time() - start_time
            rate = records_processed / elapsed_time  # records per second
            remaining_records = total_records - records_processed
            if rate > 0:
                export.estimated_time_remaining = int(remaining_records / rate)
            else:
                export.estimated_time_remaining = None
        else:
            export.estimated_time_remaining = None
        
        await session.commit()
        logger.debug(
            "Updated export progress: export_id=%s progress=%.1f%% records=%d/%d",
            export_id,
            export.progress_percentage,
            records_processed,
            total_records,
        )
    except Exception as exc:
        logger.exception("Failed to update export progress: export_id=%s", export_id)
        await session.rollback()


async def _update_export_status(
    session: AsyncSession,
    export_id: str,
    status: ExportStatus,
    error_message: Optional[str] = None,
) -> None:
    """Update export status in the database."""
    try:
        stmt = select(UserExport).where(UserExport.export_id == export_id)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if not export:
            logger.warning("Export not found for status update: export_id=%s", export_id)
            return
        
        export.status = status
        if error_message:
            export.error_message = error_message
        
        await session.commit()
        logger.info("Updated export status: export_id=%s status=%s", export_id, status)
    except Exception as exc:
        logger.exception("Failed to update export status: export_id=%s", export_id)
        await session.rollback()


async def process_contact_export(export_id: str, contact_uuids: list[str]) -> None:
    """
    Process a contact export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It generates a CSV export of contacts and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        contact_uuids: List of contact UUIDs to export
    """
    logger.info(
        "Starting contact export task: export_id=%s contact_count=%d",
        export_id,
        len(contact_uuids),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Generate CSV with progress tracking
            total_records = len(contact_uuids)
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            # Generate CSV (this processes all contacts)
            file_path = await export_service.generate_csv(
                session,
                export_id,
                contact_uuids,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(contact_uuids),
            )
            
            logger.info(
                "Contact export completed: export_id=%s contact_count=%d duration=%.2fs",
                export_id,
                len(contact_uuids),
                time.time() - start_time,
            )
            
        except Exception as exc:
            logger.exception("Contact export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)


async def process_company_export(export_id: str, company_uuids: list[str]) -> None:
    """
    Process a company export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It generates a CSV export of companies and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        company_uuids: List of company UUIDs to export
    """
    logger.info(
        "Starting company export task: export_id=%s company_count=%d",
        export_id,
        len(company_uuids),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Generate CSV with progress tracking
            total_records = len(company_uuids)
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            file_path = await export_service.generate_company_csv(
                session,
                export_id,
                company_uuids,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                company_count=len(company_uuids),
            )
            
            logger.info(
                "Company export completed: export_id=%s company_count=%d duration=%.2fs",
                export_id,
                len(company_uuids),
                time.time() - start_time,
            )
            
        except Exception as exc:
            logger.exception("Company export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)


async def process_linkedin_export(export_id: str, linkedin_urls: list[str]) -> None:
    """
    Process a LinkedIn export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It searches for contacts and companies by multiple LinkedIn URLs, then generates
    a combined CSV export with contacts, companies, and unmatched URLs.
    
    Args:
        export_id: The UUID of the export record
        linkedin_urls: List of LinkedIn URLs to search and export
    """
    logger.info(
        "Starting LinkedIn export task: export_id=%s url_count=%d",
        export_id,
        len(linkedin_urls),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Import LinkedInService here to avoid circular imports
            from app.services.linkedin_service import LinkedInService
            
            linkedin_service = LinkedInService()
            
            # Search for contacts and companies by URLs
            logger.info("Searching LinkedIn URLs: export_id=%s url_count=%d", export_id, len(linkedin_urls))
            contact_uuids, company_uuids, unmatched_urls = await linkedin_service.search_by_multiple_urls(
                session, linkedin_urls
            )
            
            total_records = len(contact_uuids) + len(company_uuids) + len(unmatched_urls)
            logger.info(
                "LinkedIn search completed: export_id=%s contacts=%d companies=%d unmatched=%d total=%d",
                export_id,
                len(contact_uuids),
                len(company_uuids),
                len(unmatched_urls),
                total_records,
            )
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            # Generate combined CSV
            file_path = await export_service.generate_linkedin_export_csv(
                session,
                export_id,
                contact_uuids,
                company_uuids,
                unmatched_urls,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(contact_uuids),
                company_count=len(company_uuids),
            )
            
            logger.info(
                "LinkedIn export completed: export_id=%s contacts=%d companies=%d unmatched=%d duration=%.2fs",
                export_id,
                len(contact_uuids),
                len(company_uuids),
                len(unmatched_urls),
                time.time() - start_time,
            )
            
        except Exception as exc:
            logger.exception("LinkedIn export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)
