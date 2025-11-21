"""Endpoints supporting contact and company export workflows."""

import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.exports import ExportStatus, ExportType, UserExport
from app.models.user import User
from app.schemas.exports import (
    ChunkedExportRequest,
    ChunkedExportResponse,
    CompanyExportRequest,
    CompanyExportResponse,
    ContactExportRequest,
    ContactExportResponse,
    ExportListResponse,
    ExportStatusResponse,
    UserExportDetail,
)
from app.schemas.filters import ExportFilterParams
from app.services.export_service import ExportService
from app.services.s3_service import S3Service
from app.tasks.export_tasks import process_company_export, process_contact_export
from app.utils.signed_url import verify_signed_url

router = APIRouter()
logger = get_logger(__name__)
service = ExportService()
s3_service = S3Service()


async def resolve_export_filters(request: Request) -> ExportFilterParams:
    """Build export filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return ExportFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.post("/contacts/export", response_model=ContactExportResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_export(
    request: ContactExportRequest,
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContactExportResponse:
    """
    Create a CSV export of selected contacts.
    
    Accepts a list of contact UUIDs and generates a CSV file containing all contact,
    company, and metadata fields. Returns a signed temporary download URL that expires
    after 24 hours.
    """
    logger.info(
        "Received contact export request: user_id=%s contact_count=%d",
        current_user.id,
        len(request.contact_uuids),
    )
    
    if not request.contact_uuids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one contact UUID is required",
        )
    
    try:
        # Create export record with status "pending"
        export = await service.create_export(
            session,
            current_user.id,
            ExportType.contacts,
            contact_uuids=request.contact_uuids,
        )
        
        # Set total_records for progress tracking
        export.total_records = len(request.contact_uuids)
        await session.commit()
        
        # Enqueue background task
        task = process_contact_export.delay(export.export_id, request.contact_uuids)
        
        logger.info(
            "Contact export queued: export_id=%s user_id=%s contact_count=%d task_id=%s",
            export.export_id,
            current_user.id,
            len(request.contact_uuids),
            task.id,
        )
        
        return ContactExportResponse(
            export_id=export.export_id,
            download_url="",  # Will be generated when export completes
            expires_at=export.expires_at or export.created_at,
            contact_count=len(request.contact_uuids),
            status=export.status,
            job_id=task.id,
        )
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Export creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.get("/{export_id}/status", response_model=ExportStatusResponse)
async def get_export_status(
    export_id: str,
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportStatusResponse:
    """
    Get the status of an export job.
    
    Returns detailed status information including progress percentage, estimated time
    remaining, error messages, and download URL if available.
    """
    logger.info("Status request: export_id=%s user_id=%s", export_id, current_user.id)
    
    try:
        export = await service.get_export(session, export_id, current_user.id)
        if not export:
            logger.warning("Export not found or access denied: export_id=%s user_id=%s", export_id, current_user.id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export not found or access denied",
            )
        
        # Calculate progress percentage if we have progress tracking
        progress_percentage = None
        if hasattr(export, 'progress_percentage') and export.progress_percentage is not None:
            progress_percentage = export.progress_percentage
        elif hasattr(export, 'total_records') and hasattr(export, 'records_processed'):
            if export.total_records > 0:
                progress_percentage = (export.records_processed / export.total_records) * 100
        
        # Get estimated time remaining
        estimated_time = None
        if hasattr(export, 'estimated_time_remaining') and export.estimated_time_remaining is not None:
            estimated_time = export.estimated_time_remaining
        
        # Get error message
        error_message = None
        if hasattr(export, 'error_message') and export.error_message:
            error_message = export.error_message
        elif export.status == ExportStatus.failed:
            error_message = "Export processing failed"
        
        return ExportStatusResponse(
            export_id=export.export_id,
            status=export.status,
            progress_percentage=progress_percentage,
            estimated_time=estimated_time,
            error_message=error_message,
            download_url=export.download_url,
            expires_at=export.expires_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get export status: export_id=%s", export_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export status",
        ) from exc


@router.get("/", response_model=ExportListResponse)
async def list_exports(
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportListResponse:
    """
    List all exports for the current user.
    
    Returns all exports created by the authenticated user, ordered by creation date
    (newest first). Includes both contact and company exports.
    """
    logger.info("Listing exports for user: user_id=%s", current_user.id)
    
    try:
        exports = await service.list_user_exports(
            session, current_user.id, filters=filters
        )
        
        export_details = [UserExportDetail.model_validate(export) for export in exports]
        
        logger.info("Found %d exports for user: user_id=%s", len(export_details), current_user.id)
        
        return ExportListResponse(
            exports=export_details,
            total=len(export_details),
        )
    except Exception as exc:
        logger.exception("Failed to list exports: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list exports",
        ) from exc


@router.get("/{export_id}/download")
async def download_export(
    export_id: str,
    token: str = Query(..., description="Signed URL token for authentication"),
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """
    Download a CSV export file using a signed URL.
    
    The token must be valid and the export must belong to the requesting user.
    The export must not have expired.
    """
    logger.info("Download request: export_id=%s user_id=%s", export_id, current_user.id)
    
    # Verify signed URL token
    token_payload = verify_signed_url(token)
    if not token_payload:
        logger.warning("Invalid signed URL token: export_id=%s", export_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired download token",
        )
    
    # Verify token matches export and user
    if token_payload.get("export_id") != export_id or token_payload.get("user_id") != current_user.id:
        logger.warning(
            "Token mismatch: export_id=%s user_id=%s token_export_id=%s token_user_id=%s",
            export_id,
            current_user.id,
            token_payload.get("export_id"),
            token_payload.get("user_id"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match export or user",
        )
    
    # Get export record
    export = await service.get_export(session, export_id, current_user.id)
    if not export:
        logger.warning("Export not found or access denied: export_id=%s user_id=%s", export_id, current_user.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found or access denied",
        )
    
    # Check if export has expired
    if export.expires_at and export.expires_at < datetime.now(timezone.utc):
        logger.warning("Export expired: export_id=%s expires_at=%s", export_id, export.expires_at)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Export has expired",
        )
    
    # Check if export is completed
    if export.status != ExportStatus.completed:
        logger.warning("Export not completed: export_id=%s status=%s", export_id, export.status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready (status: {export.status})",
        )
    
    # Check if file exists
    if not export.file_path:
        logger.error("Export file path missing: export_id=%s", export_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export file not found",
        )
    
    # Determine filename
    filename = export.file_name or f"export_{export_id}.csv"
    
    # Check if file is in S3 or local
    if s3_service.is_s3_key(export.file_path):
        # Download from S3 and stream to user
        try:
            s3_key = export.file_path
            # Extract key from full S3 URL if needed
            if s3_key.startswith("https://"):
                parts = s3_key.split(".s3.")
                if len(parts) > 1 and "/" in parts[1]:
                    s3_key = parts[1].split("/", 1)[1]
            
            file_content = await s3_service.download_file(s3_key)
            logger.debug("Downloaded file from S3: key=%s size=%d", s3_key, len(file_content))
            
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except FileNotFoundError:
            logger.error("Export file not found in S3: s3_key=%s", export.file_path)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        except Exception as exc:
            logger.exception("Failed to download file from S3: s3_key=%s", export.file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download export file: {str(exc)}",
            )
    else:
        # Local file
        file_path = Path(export.file_path)
        if not file_path.exists():
            logger.error("Export file does not exist: file_path=%s", export.file_path)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        
        logger.info("Serving export file: export_id=%s file_path=%s", export_id, file_path)
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )


@router.post("/companies/export", response_model=CompanyExportResponse, status_code=status.HTTP_201_CREATED)
async def create_company_export(
    request: CompanyExportRequest,
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyExportResponse:
    """
    Create a CSV export of selected companies.
    
    Accepts a list of company UUIDs and generates a CSV file containing all company
    and company metadata fields. Returns a signed temporary download URL that expires
    after 24 hours.
    """
    logger.info(
        "Received company export request: user_id=%s company_count=%d",
        current_user.id,
        len(request.company_uuids),
    )
    
    if not request.company_uuids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one company UUID is required",
        )
    
    try:
        # Create export record with status "pending"
        export = await service.create_export(
            session,
            current_user.id,
            ExportType.companies,
            company_uuids=request.company_uuids,
        )
        
        # Set total_records for progress tracking
        export.total_records = len(request.company_uuids)
        await session.commit()
        
        # Enqueue background task
        task = process_company_export.delay(export.export_id, request.company_uuids)
        
        logger.info(
            "Company export queued: export_id=%s user_id=%s company_count=%d task_id=%s",
            export.export_id,
            current_user.id,
            len(request.company_uuids),
            task.id,
        )
        
        return CompanyExportResponse(
            export_id=export.export_id,
            download_url="",  # Will be generated when export completes
            expires_at=export.expires_at or export.created_at,
            company_count=len(request.company_uuids),
            status=export.status,
            job_id=task.id,
        )
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Export creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.post("/contacts/export/chunked", response_model=ChunkedExportResponse, status_code=status.HTTP_201_CREATED)
async def create_chunked_contact_export(
    request: ChunkedExportRequest,
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChunkedExportResponse:
    """
    Create a chunked contact export.
    
    Accepts multiple chunks of contact UUIDs and creates separate export jobs for each chunk.
    If merge is True, the chunks will be processed and merged into a single export file.
    """
    logger.info(
        "Received chunked contact export request: user_id=%s chunk_count=%d merge=%s",
        current_user.id,
        len(request.chunks),
        request.merge,
    )
    
    if not request.chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one chunk is required",
        )
    
    # Calculate total count
    total_count = sum(len(chunk) for chunk in request.chunks)
    if total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one contact UUID is required across all chunks",
        )
    
    try:
        # Create main export record
        all_uuids = [uuid for chunk in request.chunks for uuid in chunk]
        main_export = await service.create_export(
            session,
            current_user.id,
            ExportType.contacts,
            contact_uuids=all_uuids,
        )
        
        # Set total_records for progress tracking
        main_export.total_records = total_count
        await session.commit()
        
        # Create chunk export records and enqueue tasks
        chunk_ids = []
        tasks = []
        
        for i, chunk_uuids in enumerate(request.chunks):
            if not chunk_uuids:
                continue
                
            # Create chunk export record
            chunk_export = await service.create_export(
                session,
                current_user.id,
                ExportType.contacts,
                contact_uuids=chunk_uuids,
            )
            chunk_export.total_records = len(chunk_uuids)
            await session.commit()
            
            chunk_ids.append(chunk_export.export_id)
            
            # Enqueue background task for this chunk
            task = process_contact_export.delay(chunk_export.export_id, chunk_uuids)
            tasks.append(task)
            
            logger.info(
                "Chunk export queued: chunk_index=%d export_id=%s chunk_size=%d task_id=%s",
                i,
                chunk_export.export_id,
                len(chunk_uuids),
                task.id,
            )
        
        # If merge is requested, we would need additional logic to merge the CSV files
        # For now, we'll just create separate exports and return the main export ID
        # TODO: Implement CSV merging logic if needed
        
        logger.info(
            "Chunked export created: main_export_id=%s chunk_count=%d total_count=%d",
            main_export.export_id,
            len(chunk_ids),
            total_count,
        )
        
        return ChunkedExportResponse(
            export_id=main_export.export_id,
            chunk_ids=chunk_ids,
            total_count=total_count,
            status=main_export.status,
            job_id=tasks[0].id if tasks else None,  # Return first task ID as main job ID
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chunked export creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chunked export",
        ) from exc


@router.delete("/{export_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_export(
    export_id: str,
    filters: ExportFilterParams = Depends(resolve_export_filters),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Cancel a pending or processing export.
    
    Sets the export status to "cancelled" and cleans up any partial resources.
    Cannot cancel exports that are already completed or failed.
    """
    logger.info("Cancel request: export_id=%s user_id=%s", export_id, current_user.id)
    
    try:
        export = await service.get_export(session, export_id, current_user.id)
        if not export:
            logger.warning("Export not found or access denied: export_id=%s user_id=%s", export_id, current_user.id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export not found or access denied",
            )
        
        # Check if export can be cancelled
        if export.status == ExportStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a completed export",
            )
        
        if export.status == ExportStatus.failed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a failed export",
            )
        
        if export.status == ExportStatus.cancelled:
            logger.info("Export already cancelled: export_id=%s", export_id)
            return {
                "message": "Export is already cancelled",
                "export_id": export_id,
                "status": export.status,
            }
        
        # Update status to cancelled
        export.status = ExportStatus.cancelled
        export.error_message = "Export cancelled by user"
        await session.commit()
        
        logger.info("Export cancelled: export_id=%s user_id=%s", export_id, current_user.id)
        
        return {
            "message": "Export cancelled successfully",
            "export_id": export_id,
            "status": export.status,
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to cancel export: export_id=%s", export_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel export",
        ) from exc


@router.delete("/files", status_code=status.HTTP_200_OK)
async def delete_all_csv_files(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """
    Delete all CSV files from the exports directory (admin only).
    
    This endpoint deletes all CSV files in the exports directory and optionally
    cleans up expired export records from the database.
    """
    logger.info("Admin CSV cleanup request: user_id=%s", current_user.id)
    
    try:
        deleted_count = await service.delete_all_csv_files(session)
        
        logger.info("CSV cleanup completed: deleted_count=%d", deleted_count)
        
        return {
            "message": "CSV files deleted successfully",
            "deleted_count": deleted_count,
        }
    except Exception as exc:
        logger.exception("Failed to delete CSV files: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete CSV files",
        ) from exc

