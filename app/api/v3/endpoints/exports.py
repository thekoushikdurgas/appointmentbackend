"""Endpoints supporting contact and company export workflows."""

import io
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.exports import ExportStatus, ExportType
from app.models.user import User
from app.repositories.user import UserProfileRepository
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
from app.services.credit_service import CreditService
from app.services.export_service import ExportService
from app.services.s3_service import S3Service
from app.tasks.export_tasks import process_company_export, process_contact_export
from app.tasks.merge_export_tasks import check_and_merge_chunks
from app.utils.background_tasks import add_background_task_safe
from app.utils.logger import get_logger, log_error, log_api_error
from app.utils.signed_url import verify_signed_url

router = APIRouter()
service = ExportService()
s3_service = S3Service()
credit_service = CreditService()
profile_repo = UserProfileRepository()
logger = get_logger(__name__)


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
    background_tasks: BackgroundTasks,
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
    if not request.contact_uuids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one contact UUID is required",
        )
    
    start_time = time.time()
    logger.info(
        "Contact export request received",
        extra={
            "context": {
                "user_id": current_user.uuid,
                "contact_count": len(request.contact_uuids),
            },
            "user_id": current_user.uuid,
        }
    )
    
    try:
        # Create export record with status "pending"
        export = await service.create_export(
            session,
            current_user.uuid,
            ExportType.contacts,
            contact_uuids=request.contact_uuids,
        )
        
        # Set total_records for progress tracking
        export.total_records = len(request.contact_uuids)
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
        logger.debug(
            "Export record created",
            extra={
                "context": {
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                    "contact_count": len(request.contact_uuids),
                },
                "user_id": current_user.uuid,
            }
        )
        
        # Enqueue background task
        # Note: This is a long-running task that might be better suited for Celery in the future
        add_background_task_safe(
            background_tasks,
            process_contact_export,
            export.export_id,
            request.contact_uuids,
            track_status=True,
            cpu_bound=False,  # I/O-bound task (database and file operations)
        )
        
        # Deduct credits for FreeUser and ProUser (after export is queued successfully)
        # Deduct 1 credit per contact UUID
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = len(request.contact_uuids)
                    await credit_service.deduct_credits(
                        session, current_user.uuid, amount=credit_amount
                    )
                    logger.debug(
                        "Credits deducted for export",
                        extra={
                            "context": {
                                "user_id": current_user.uuid,
                                "credit_amount": credit_amount,
                            },
                            "user_id": current_user.uuid,
                        }
                    )
        except Exception as credit_exc:
            log_error(
                "Credit deduction failed for export",
                credit_exc,
                "app.api.v3.endpoints.exports",
                context={
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                },
                user_id=current_user.uuid,
            )
            # Credit deduction failed but export continues
        
        # Set expiration to 24 hours from creation
        expires_at = export.created_at + timedelta(hours=24)
        
        duration = (time.time() - start_time) * 1000
        logger.info(
            "Contact export request completed",
            extra={
                "context": {
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                    "contact_count": len(request.contact_uuids),
                },
                "user_id": current_user.uuid,
                "performance": {"duration_ms": duration},
            }
        )
        
        return ContactExportResponse(
            export_id=export.export_id,
            download_url="",  # Will be generated when export completes
            expires_at=expires_at,
            contact_count=len(request.contact_uuids),
            status=export.status,
        )
            
    except HTTPException:
        raise
    except Exception as exc:
        duration = (time.time() - start_time) * 1000
        log_error(
            "Failed to create contact export",
            exc,
            "app.api.v3.endpoints.exports",
            context={
                "user_id": current_user.uuid,
                "contact_count": len(request.contact_uuids),
            },
            user_id=current_user.uuid,
        )
        # Error handling: Export creation failed with error details
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
    try:
        export = await service.get_export(session, export_id, current_user.uuid)
        if not export:
            # Export not found or access denied
            log_api_error(
                endpoint=f"/api/v3/exports/{export_id}/status",
                method="GET",
                status_code=404,
                error_type="NotFoundException",
                error_message=f"Export not found or access denied: {export_id}",
                user_id=str(current_user.uuid),
                context={"export_id": export_id}
            )
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
        # Failed to get export status
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
    try:
        exports = await service.list_user_exports(
            session, current_user.uuid, filters=filters
        )
        
        export_details = [UserExportDetail.model_validate(export) for export in exports]
        
        return ExportListResponse(
            exports=export_details,
            total=len(export_details),
        )
    except Exception as exc:
        # Failed to list exports
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
    # Verify signed URL token
    token_payload = verify_signed_url(token)
    if not token_payload:
        # Invalid signed URL token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired download token",
        )
    
    # Verify token matches export and user
    export_id_mismatch = token_payload.get("export_id") != export_id
    user_id_mismatch = token_payload.get("user_id") != current_user.uuid
    if export_id_mismatch or user_id_mismatch:
        # Token mismatch - access denied
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match export or user",
        )
    
    # Get export record
    export = await service.get_export(session, export_id, current_user.uuid)
    if not export:
        # Export not found or access denied
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found or access denied",
        )
    
    # Check if export has expired
    if export.expires_at and export.expires_at < datetime.now(timezone.utc):
        # Export has expired
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Export has expired",
        )
    
    # Check if export is completed
    if export.status != ExportStatus.completed:
        # Export not completed yet
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready (status: {export.status})",
        )
    
    # Check if file exists
    if not export.file_path:
        # Export file path missing
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
            # File downloaded from S3 successfully
            
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except FileNotFoundError:
            # Export file not found in S3
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        except Exception as exc:
            # Failed to download file from S3
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download export file: {str(exc)}",
            )
    else:
        # Local file
        file_path = Path(export.file_path)
        if not file_path.exists():
            # Export file does not exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found",
            )
        
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
    background_tasks: BackgroundTasks,
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
    # Processing: Received company export request with user ID and company count
    
    start_time = time.time()
    logger.info(
        "Company export request received",
        extra={
            "context": {
                "user_id": current_user.uuid,
                "company_count": len(request.company_uuids),
            },
            "user_id": current_user.uuid,
        }
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
            current_user.uuid,
            ExportType.companies,
            company_uuids=request.company_uuids,
        )
        
        # Set total_records for progress tracking
        export.total_records = len(request.company_uuids)
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
        logger.debug(
            "Export record created",
            extra={
                "context": {
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                    "company_count": len(request.company_uuids),
                },
                "user_id": current_user.uuid,
            }
        )
        
        # Enqueue background task
        # Note: This is a long-running task that might be better suited for Celery in the future
        add_background_task_safe(
            background_tasks,
            process_company_export,
            export.export_id,
            request.company_uuids,
            track_status=True,
            cpu_bound=False,  # I/O-bound task (database and file operations)
        )
        
        # Deduct credits for FreeUser and ProUser (after export is queued successfully)
        # Deduct 1 credit per company UUID
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = len(request.company_uuids)
                    await credit_service.deduct_credits(
                        session, current_user.uuid, amount=credit_amount
                    )
                    logger.debug(
                        "Credits deducted for export",
                        extra={
                            "context": {
                                "user_id": current_user.uuid,
                                "credit_amount": credit_amount,
                            },
                            "user_id": current_user.uuid,
                        }
                    )
        except Exception as credit_exc:
            log_error(
                "Credit deduction failed for export",
                credit_exc,
                "app.api.v3.endpoints.exports",
                context={
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                },
                user_id=current_user.uuid,
            )
            # Credit deduction failed but export continues
        
        # Set expiration to 24 hours from creation
        expires_at = export.created_at + timedelta(hours=24)
        
        duration = (time.time() - start_time) * 1000
        logger.info(
            "Company export request completed",
            extra={
                "context": {
                    "export_id": export.export_id,
                    "user_id": current_user.uuid,
                    "company_count": len(request.company_uuids),
                },
                "user_id": current_user.uuid,
                "performance": {"duration_ms": duration},
            }
        )
        
        return CompanyExportResponse(
            export_id=export.export_id,
            download_url="",  # Will be generated when export completes
            expires_at=expires_at,
            company_count=len(request.company_uuids),
            status=export.status,
        )
            
    except HTTPException:
        raise
    except Exception as exc:
        duration = (time.time() - start_time) * 1000
        log_error(
            "Failed to create company export",
            exc,
            "app.api.v3.endpoints.exports",
            context={
                "user_id": current_user.uuid,
                "company_count": len(request.company_uuids),
            },
            user_id=current_user.uuid,
        )
        # Error handling: Export creation failed with error details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.post("/contacts/export/chunked", response_model=ChunkedExportResponse, status_code=status.HTTP_201_CREATED)
async def create_chunked_contact_export(
    background_tasks: BackgroundTasks,
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
            current_user.uuid,
            ExportType.contacts,
            contact_uuids=all_uuids,
        )
        
        # Set total_records for progress tracking
        main_export.total_records = total_count
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
        # Create chunk export records and enqueue tasks
        chunk_ids = []
        
        for i, chunk_uuids in enumerate(request.chunks):
            if not chunk_uuids:
                continue
                
            # Create chunk export record
            chunk_export = await service.create_export(
                session,
                current_user.uuid,
                ExportType.contacts,
                contact_uuids=chunk_uuids,
            )
            chunk_export.total_records = len(chunk_uuids)
            # Flush to persist changes without committing (transaction managed by get_db())
            await session.flush()
            
            chunk_ids.append(chunk_export.export_id)
            
            # Enqueue background task for this chunk
            # Note: This is a long-running task that might be better suited for Celery in the future
            add_background_task_safe(
                background_tasks,
                process_contact_export,
                chunk_export.export_id,
                chunk_uuids,
                track_status=True,
                cpu_bound=False,  # I/O-bound task (database and file operations)
            )
        
        # If merge is requested, start background task to monitor chunk completion and merge
        if request.merge:
            add_background_task_safe(
                background_tasks,
                check_and_merge_chunks,
                main_export.export_id,
                chunk_ids,
                track_status=False,
                cpu_bound=False,
            )
        
        # Deduct credits for FreeUser and ProUser (after chunked export is created successfully)
        # Deduct credits for total count across all chunks (1 credit per contact UUID)
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = total_count
                    await credit_service.deduct_credits(
                        session, current_user.uuid, amount=credit_amount
                    )
        except Exception:
            pass  # Credit deduction failed but export continues
        
        return ChunkedExportResponse(
            export_id=main_export.export_id,
            chunk_ids=chunk_ids,
            total_count=total_count,
            status=main_export.status,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        # Chunked export creation failed
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
    # Processing: Cancel request with export ID and user ID
    
    try:
        export = await service.get_export(session, export_id, current_user.uuid)
        if not export:
            # Warning condition: Export not found or access denied with export ID and user ID
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
            # Export already cancelled
            return {
                "message": "Export is already cancelled",
                "export_id": export_id,
                "status": export.status,
            }
        
        # Update status to cancelled
        export.status = ExportStatus.cancelled
        export.error_message = "Export cancelled by user"
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
        return {
            "message": "Export cancelled successfully",
            "export_id": export_id,
            "status": export.status,
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to cancel export
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
    try:
        deleted_count = await service.delete_all_csv_files(session)
        
        return {
            "message": "CSV files deleted successfully",
            "deleted_count": deleted_count,
        }
    except Exception as exc:
        # Failed to delete CSV files
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete CSV files",
        ) from exc

