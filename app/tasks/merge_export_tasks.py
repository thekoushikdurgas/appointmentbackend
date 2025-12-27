"""Background task for merging chunked exports."""

import asyncio
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.exports import ExportStatus, UserExport
from app.services.export_service import ExportService
from app.utils.logger import get_logger

export_service = ExportService()
logger = get_logger(__name__)


async def check_and_merge_chunks(
    main_export_id: str,
    chunk_export_ids: list[str],
    max_attempts: int = 60,
    check_interval: int = 5,
) -> None:
    """
    Check if all chunk exports are completed and merge them if requested.
    
    Args:
        main_export_id: Main export ID
        chunk_export_ids: List of chunk export IDs to check and merge
        max_attempts: Maximum number of polling attempts (default: 60 = 5 minutes)
        check_interval: Seconds between checks (default: 5)
    """
    async with AsyncSessionLocal() as session:
        try:
            for attempt in range(max_attempts):
                # Check if main export was cancelled
                stmt = select(UserExport).where(UserExport.export_id == main_export_id)
                result = await session.execute(stmt)
                main_export = result.scalar_one_or_none()
                
                if not main_export:
                    return
                
                if main_export.status == ExportStatus.cancelled:
                    return
                
                # Check status of all chunk exports
                stmt = select(UserExport).where(UserExport.export_id.in_(chunk_export_ids))
                result = await session.execute(stmt)
                chunk_exports = result.scalars().all()
                
                # Check if all chunks are completed
                completed_count = sum(
                    1 for exp in chunk_exports
                    if exp.status == ExportStatus.completed and exp.file_path
                )
                failed_count = sum(
                    1 for exp in chunk_exports
                    if exp.status == ExportStatus.failed
                )
                
                if failed_count > 0:
                    # Update main export to failed
                    main_export.status = ExportStatus.failed
                    main_export.error_message = f"{failed_count} chunk export(s) failed"
                    await session.commit()
                    return
                
                if completed_count == len(chunk_export_ids):
                    # All chunks completed, merge them
                    try:
                        # Update main export status to processing
                        main_export.status = ExportStatus.processing
                        await session.commit()
                        
                        # Merge CSV files
                        merged_file_path = await export_service.merge_csv_files(
                            session,
                            main_export_id,
                            chunk_export_ids,
                        )
                        
                        # Update main export with merged file
                        total_contacts = sum(exp.contact_count for exp in chunk_exports)
                        export = await export_service.update_export_status(
                            session,
                            main_export_id,
                            ExportStatus.completed,
                            merged_file_path,
                            contact_count=total_contacts,
                        )
                        
                        return
                    except Exception as merge_exc:
                        # Update main export to failed
                        logger.error(
                            "Export merge failed",
                            exc_info=True,
                            extra={
                                "context": {
                                    "main_export_id": main_export_id,
                                    "chunk_count": len(chunk_exports),
                                    "error_type": type(merge_exc).__name__,
                                    "error_message": str(merge_exc),
                                }
                            }
                        )
                        main_export.status = ExportStatus.failed
                        main_export.error_message = f"Merge failed: {str(merge_exc)}"
                        await session.commit()
                        return
                
                # Not all chunks completed yet, wait and retry
                if attempt < max_attempts - 1:
                    await asyncio.sleep(check_interval)
                else:
                    # Timeout
                    main_export.status = ExportStatus.failed
                    main_export.error_message = "Timeout waiting for chunk exports to complete"
                    await session.commit()
                    return
                    
        except Exception as exc:
            logger.error(
                "Export merge check failed",
                exc_info=True,
                extra={
                    "context": {
                        "main_export_id": main_export_id,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                }
            )
            # Try to update main export to failed
            try:
                stmt = select(UserExport).where(UserExport.export_id == main_export_id)
                result = await session.execute(stmt)
                main_export = result.scalar_one_or_none()
                if main_export:
                    main_export.status = ExportStatus.failed
                    main_export.error_message = f"Merge check failed: {str(exc)}"
                    await session.commit()
            except Exception as update_exc:
                logger.error(
                    "Failed to update export status after merge check failure",
                    exc_info=True,
                    extra={
                        "context": {
                            "main_export_id": main_export_id,
                            "original_error": str(exc),
                            "update_error_type": type(update_exc).__name__,
                            "update_error_message": str(update_exc),
                        }
                    }
                )

