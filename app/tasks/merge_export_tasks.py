"""Background task for merging chunked exports."""

import asyncio
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.exports import ExportStatus, UserExport
from app.services.export_service import ExportService

logger = get_logger(__name__)
export_service = ExportService()


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
    logger.info(
        "Starting chunk merge check: main_export_id=%s chunk_count=%d",
        main_export_id,
        len(chunk_export_ids),
    )
    
    async with AsyncSessionLocal() as session:
        try:
            for attempt in range(max_attempts):
                # Check if main export was cancelled
                stmt = select(UserExport).where(UserExport.export_id == main_export_id)
                result = await session.execute(stmt)
                main_export = result.scalar_one_or_none()
                
                if not main_export:
                    logger.warning("Main export not found: export_id=%s", main_export_id)
                    return
                
                if main_export.status == ExportStatus.cancelled:
                    logger.info("Main export cancelled, aborting merge: export_id=%s", main_export_id)
                    return
                
                # Check status of all chunk exports
                stmt = select(UserExport).where(UserExport.export_id.in_(chunk_export_ids))
                result = await session.execute(stmt)
                chunk_exports = result.scalars().all()
                
                if len(chunk_exports) != len(chunk_export_ids):
                    logger.warning(
                        "Some chunk exports not found: expected=%d found=%d",
                        len(chunk_export_ids),
                        len(chunk_exports),
                    )
                
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
                    logger.error(
                        "Some chunk exports failed: main_export_id=%s failed_count=%d",
                        main_export_id,
                        failed_count,
                    )
                    # Update main export to failed
                    main_export.status = ExportStatus.failed
                    main_export.error_message = f"{failed_count} chunk export(s) failed"
                    await session.commit()
                    return
                
                if completed_count == len(chunk_export_ids):
                    # All chunks completed, merge them
                    logger.info(
                        "All chunks completed, merging: main_export_id=%s chunk_count=%d",
                        main_export_id,
                        len(chunk_export_ids),
                    )
                    
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
                        
                        logger.info(
                            "Chunked export merged successfully: main_export_id=%s total_contacts=%d",
                            main_export_id,
                            total_contacts,
                        )
                        return
                    except Exception as merge_exc:
                        logger.exception(
                            "Failed to merge chunked export: main_export_id=%s error=%s",
                            main_export_id,
                            merge_exc,
                        )
                        # Update main export to failed
                        main_export.status = ExportStatus.failed
                        main_export.error_message = f"Merge failed: {str(merge_exc)}"
                        await session.commit()
                        return
                
                # Not all chunks completed yet, wait and retry
                if attempt < max_attempts - 1:
                    logger.debug(
                        "Waiting for chunks to complete: main_export_id=%s completed=%d/%d attempt=%d/%d",
                        main_export_id,
                        completed_count,
                        len(chunk_export_ids),
                        attempt + 1,
                        max_attempts,
                    )
                    await asyncio.sleep(check_interval)
                else:
                    # Timeout
                    logger.error(
                        "Timeout waiting for chunks to complete: main_export_id=%s completed=%d/%d",
                        main_export_id,
                        completed_count,
                        len(chunk_export_ids),
                    )
                    main_export.status = ExportStatus.failed
                    main_export.error_message = "Timeout waiting for chunk exports to complete"
                    await session.commit()
                    return
                    
        except Exception as exc:
            logger.exception(
                "Error in chunk merge check: main_export_id=%s error=%s",
                main_export_id,
                exc,
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
                logger.exception("Failed to update main export status: %s", update_exc)

