"""Endpoints supporting contact and company export workflows."""

import io
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.exports import ExportStatus, ExportType, UserExport
from app.models.user import User
from app.schemas.exports import (
    CompanyExportRequest,
    CompanyExportResponse,
    ContactExportRequest,
    ContactExportResponse,
    ExportListResponse,
    UserExportDetail,
)
from app.services.export_service import ExportService
from app.services.s3_service import S3Service
from app.utils.signed_url import verify_signed_url

router = APIRouter()
logger = get_logger(__name__)
service = ExportService()
s3_service = S3Service()


@router.post("/contacts/export", response_model=ContactExportResponse, status_code=status.HTTP_201_CREATED)
async def create_contact_export(
    request: ContactExportRequest,
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
        # Create export record
        export = await service.create_export(
            session,
            current_user.id,
            ExportType.contacts,
            contact_uuids=request.contact_uuids,
        )
        
        # Generate CSV file
        try:
            file_path = await service.generate_csv(
                session,
                export.export_id,
                request.contact_uuids,
            )
            
            # Update export with file path and generate signed URL
            export = await service.update_export_status(
                session,
                export.export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(request.contact_uuids),
            )
            
            logger.info(
                "Export completed: export_id=%s user_id=%s contact_count=%d",
                export.export_id,
                current_user.id,
                export.contact_count,
            )
            
            return ContactExportResponse(
                export_id=export.export_id,
                download_url=export.download_url or "",
                expires_at=export.expires_at or export.created_at,
                contact_count=export.contact_count,
                status=export.status,
            )
            
        except Exception as csv_exc:
            logger.exception("Failed to generate CSV: export_id=%s", export.export_id)
            # Update export status to failed
            try:
                stmt = select(UserExport).where(UserExport.export_id == export.export_id)
                result = await session.execute(stmt)
                failed_export = result.scalar_one_or_none()
                if failed_export:
                    failed_export.status = ExportStatus.failed
                    await session.commit()
            except Exception:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate CSV: {str(csv_exc)}",
            ) from csv_exc
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Export creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.get("/", response_model=ExportListResponse)
async def list_exports(
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
        exports = await service.list_user_exports(session, current_user.id)
        
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
        # Create export record
        export = await service.create_export(
            session,
            current_user.id,
            ExportType.companies,
            company_uuids=request.company_uuids,
        )
        
        # Generate CSV file
        try:
            file_path = await service.generate_company_csv(
                session,
                export.export_id,
                request.company_uuids,
            )
            
            # Update export with file path and generate signed URL
            export = await service.update_export_status(
                session,
                export.export_id,
                ExportStatus.completed,
                file_path,
                company_count=len(request.company_uuids),
            )
            
            logger.info(
                "Export completed: export_id=%s user_id=%s company_count=%d",
                export.export_id,
                current_user.id,
                export.company_count,
            )
            
            return CompanyExportResponse(
                export_id=export.export_id,
                download_url=export.download_url or "",
                expires_at=export.expires_at or export.created_at,
                company_count=export.company_count,
                status=export.status,
            )
            
        except Exception as csv_exc:
            logger.exception("Failed to generate CSV: export_id=%s", export.export_id)
            # Update export status to failed
            try:
                stmt = select(UserExport).where(UserExport.export_id == export.export_id)
                result = await session.execute(stmt)
                failed_export = result.scalar_one_or_none()
                if failed_export:
                    failed_export.status = ExportStatus.failed
                    await session.commit()
            except Exception:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate CSV: {str(csv_exc)}",
            ) from csv_exc
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Export creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
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

