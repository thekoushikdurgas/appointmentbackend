"""S3 file operation endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.schemas.v3.s3 import S3FileDataResponse, S3FileDataRow, S3FileInfo, S3FileListResponse
from app.services.s3_service import S3Service
from app.utils.logger import get_logger, log_api_error

logger = get_logger(__name__)
router = APIRouter(prefix="/s3/files", tags=["S3 Files"])
s3_service = S3Service()
settings = get_settings()
V3_BUCKET_NAME = settings.S3_V3_BUCKET_NAME


@router.get("", response_model=S3FileListResponse)
async def list_csv_files(
    prefix: str = Query("", description="Optional prefix to filter files"),
    current_user: User = Depends(get_current_user),
) -> S3FileListResponse:
    """
    List all CSV files in the S3 bucket.
    
    Returns a list of all CSV files with their metadata (key, filename, size, last_modified).
    """
    try:
        files = await s3_service.list_csv_files(prefix=prefix, bucket_name=V3_BUCKET_NAME)
        
        file_infos = [
            S3FileInfo(
                key=f["key"],
                filename=f["filename"],
                size=f.get("size"),
                last_modified=f.get("last_modified"),
                content_type=f.get("content_type"),
            )
            for f in files
        ]
        return S3FileListResponse(files=file_infos, total=len(file_infos))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list CSV files: {str(e)}",
        ) from e


@router.get("/{file_id:path}", response_class=Response)
async def get_csv_file(
    file_id: str = Path(..., description="S3 object key (full path)"),
    limit: int = Query(None, ge=1, le=1000, description="Maximum number of rows to return (for pagination)"),
    offset: int = Query(None, ge=0, description="Number of rows to skip (for pagination)"),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Get a CSV file from S3 bucket.
    
    If limit and offset are provided, returns paginated CSV data as JSON.
    Otherwise, returns the full CSV file for download.
    """
    try:
        # If limit is provided, return paginated data as JSON
        if limit is not None:
            rows, total_rows = await s3_service.read_csv_paginated(
                s3_key=file_id,
                limit=limit,
                offset=offset or 0,
                bucket_name=V3_BUCKET_NAME,
            )

            response_data = S3FileDataResponse(
                file_key=file_id,
                rows=[S3FileDataRow(data=row) for row in rows],
                limit=limit,
                offset=offset or 0,
                total_rows=total_rows,
            )
            return JSONResponse(content=response_data.model_dump())
        
        # Otherwise, return the full CSV file for download
        file_content = await s3_service.download_csv_file(s3_key=file_id, bucket_name=V3_BUCKET_NAME)
        filename = file_id.split("/")[-1] if "/" in file_id else file_id
        
        return Response(
            content=file_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except FileNotFoundError as e:
        log_api_error(
            endpoint=f"/api/v3/s3/files/{file_id}",
            method="GET",
            status_code=404,
            error_type="FileNotFoundError",
            error_message=f"CSV file not found: {file_id}",
            user_id=str(current_user.uuid),
            context={"file_id": file_id, "limit": limit, "offset": offset}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file not found: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get CSV file: {str(e)}",
        ) from e

