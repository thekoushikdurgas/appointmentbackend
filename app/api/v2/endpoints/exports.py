"""Endpoints supporting contact export workflows."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.exports import ExportStatus
from app.models.user import User
from app.schemas.exports import ContactExportRequest, ContactExportResponse
from app.services.export_service import ExportService
from app.utils.signed_url import verify_signed_url

router = APIRouter()
logger = get_logger(__name__)
service = ExportService()


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
            request.contact_uuids,
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
                len(request.contact_uuids),
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
                from sqlalchemy import select
                from app.models.exports import UserExport
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
    from datetime import datetime, timezone
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
    
    file_path = Path(export.file_path)
    if not file_path.exists():
        logger.error("Export file does not exist: file_path=%s", export.file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found",
        )
    
    # Determine filename
    filename = export.file_name or f"export_{export_id}.csv"
    
    logger.info("Serving export file: export_id=%s file_path=%s", export_id, file_path)
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

