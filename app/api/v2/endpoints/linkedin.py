"""LinkedIn URL-based CRUD API endpoints."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import ActivityServiceType, ActivityStatus, User
from app.repositories.user import UserProfileRepository
from app.services.activity_service import ActivityService
from app.services.credit_service import CreditService
from app.utils.background_tasks import add_background_task_safe
from app.schemas.linkedin import (
    LinkedInExportRequest,
    LinkedInExportResponse,
    LinkedInSearchRequest,
    LinkedInSearchResponse,
    LinkedInUpsertRequest,
    LinkedInUpsertResponse,
)
from app.models.exports import ExportStatus, ExportType
from app.services.export_service import ExportService
from app.services.linkedin_service import LinkedInService
from app.tasks.export_tasks import process_linkedin_export


def detect_linkedin_url_column(raw_headers: list[str]) -> Optional[str]:
    """
    Auto-detect LinkedIn URL column from CSV headers.
    
    Searches for columns containing "linkedin" or "url" (case-insensitive).
    Priority: exact "linkedin_url" > "linkedin" > "url"
    
    Args:
        raw_headers: List of CSV header names
        
    Returns:
        Column name if detected, None if not found or ambiguous
        
    Raises:
        ValueError: If multiple potential LinkedIn URL columns found (ambiguous)
    """
    if not raw_headers:
        return None
    
    # Normalize headers for comparison (case-insensitive)
    normalized_headers = {h.lower(): h for h in raw_headers}
    
    # Priority 1: Exact match "linkedin_url"
    if "linkedin_url" in normalized_headers:
        return normalized_headers["linkedin_url"]
    
    # Priority 2: Contains "linkedin"
    linkedin_matches = [
        h for h in raw_headers
        if "linkedin" in h.lower() and "url" in h.lower()
    ]
    if len(linkedin_matches) == 1:
        return linkedin_matches[0]
    elif len(linkedin_matches) > 1:
        raise ValueError(
            f"Multiple LinkedIn URL columns found: {linkedin_matches}. "
            "Please specify linkedin_url_column explicitly."
        )
    
    # Priority 3: Contains "url" (but not "linkedin" already checked)
    url_matches = [
        h for h in raw_headers
        if "url" in h.lower() and "linkedin" not in h.lower()
    ]
    if len(url_matches) == 1:
        return url_matches[0]
    elif len(url_matches) > 1:
        raise ValueError(
            f"Multiple URL columns found: {url_matches}. "
            "Please specify linkedin_url_column explicitly."
        )
    
    return None


router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])
service = LinkedInService()
export_service = ExportService()
activity_service = ActivityService()
credit_service = CreditService()
profile_repo = UserProfileRepository()


@router.post("/", response_model=LinkedInSearchResponse)
async def search_by_linkedin_url(
    request: LinkedInSearchRequest,
    current_user: User = Depends(get_current_user),
) -> LinkedInSearchResponse:
    """
    Search for contacts and companies by LinkedIn URL.
    
    Searches both person LinkedIn URLs (ContactMetadata.linkedin_url) and
    company LinkedIn URLs (CompanyMetadata.linkedin_url), returning all
    matching records with their related data.
    
    The service manages its own database session internally and handles
    credit deduction automatically for FreeUser and ProUser roles.
    
    Request body:
    - url: LinkedIn URL to search for (person or company) (required)
    
    Returns:
        Combined results with contacts and companies, including their metadata
        and relationships.
    """
    if not request.url or not request.url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn URL cannot be empty",
        )
    
    try:
        result = await service.search_by_url(
            linkedin_url=request.url.strip(),
            user_id=current_user.uuid,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search by LinkedIn URL",
        ) from exc


@router.post("/", response_model=LinkedInUpsertResponse, status_code=status.HTTP_200_OK)
async def upsert_by_linkedin_url(
    request: LinkedInUpsertRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LinkedInUpsertResponse:
    """
    Create or update records based on LinkedIn URL.
    
    If a contact or company with the LinkedIn URL exists, it will be updated.
    Otherwise, new records will be created.
    
    The request body should contain:
    - url: LinkedIn URL (required)
    - contact_data: Optional contact fields to create/update
    - company_data: Optional company fields to create/update
    - contact_metadata: Optional contact metadata fields (linkedin_url will be set to url)
    - company_metadata: Optional company metadata fields (linkedin_url will be set to url)
    
    Returns:
        Created/updated records with their metadata and         relationships.
    """
    if not request.url or not request.url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn URL cannot be empty",
        )
    
    try:
        result = await service.upsert_by_url(
            session=session,
            linkedin_url=request.url.strip(),
            contact_data=request.contact_data,
            company_data=request.company_data,
            contact_metadata=request.contact_metadata,
            company_metadata=request.company_metadata,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create/update records by LinkedIn URL",
        ) from exc


@router.post("/export", response_model=LinkedInExportResponse, status_code=status.HTTP_201_CREATED)
async def create_linkedin_export(
    request: LinkedInExportRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LinkedInExportResponse:
    """
    Create a CSV export of contacts and companies by LinkedIn URLs.
    
    Accepts a list of LinkedIn URLs, searches for matching contacts and companies,
    and generates a combined CSV file containing all matches plus unmatched URLs
    marked as "not_found". Returns a signed temporary download URL that expires
    after 24 hours.
    
    Supports CSV context preservation: if raw_headers and rows are provided,
    the export will preserve original CSV columns while enriching with LinkedIn data.
    
    The export is processed asynchronously via a background job. The response
    includes an export_id and job_id for tracking progress.
    """
    if not request.urls or len(request.urls) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one LinkedIn URL is required",
        )
    
    # Validate URLs are not empty
    valid_urls = [url.strip() for url in request.urls if url and url.strip()]
    if not valid_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid LinkedIn URL is required",
        )
    
    try:
        # Handle CSV context: extract URLs from CSV rows if provided
        linkedin_urls_data = []
        linkedin_url_column = request.linkedin_url_column
        
        # If CSV context is provided, extract URLs from rows
        if request.rows is not None and request.raw_headers is not None:
            # Auto-detect LinkedIn URL column if not explicitly provided
            if not linkedin_url_column:
                try:
                    linkedin_url_column = detect_linkedin_url_column(request.raw_headers)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e),
                    ) from e
            
            if not linkedin_url_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not detect LinkedIn URL column. Please provide linkedin_url_column.",
                )
            
            # Extract URLs from CSV rows
            extracted_urls = []
            for idx, row in enumerate(request.rows):
                url_value = row.get(linkedin_url_column)
                if url_value and isinstance(url_value, str) and url_value.strip():
                    extracted_url = url_value.strip()
                    extracted_urls.append(extracted_url)
                    
                    # Create URL data with CSV context
                    url_payload: dict[str, Any] = {
                        "linkedin_url": extracted_url,
                        "raw_row": row,
                    }
                    linkedin_urls_data.append(url_payload)
                elif idx < len(valid_urls):
                    # Fallback to request.urls if row doesn't have URL
                    url_payload: dict[str, Any] = {
                        "linkedin_url": valid_urls[idx],
                        "raw_row": row,
                    }
                    linkedin_urls_data.append(url_payload)
            
            # Use extracted URLs if found, otherwise use request.urls
            if extracted_urls:
                valid_urls = extracted_urls
            else:
                # If no URLs extracted from rows, use request.urls and match with rows
                for idx, url in enumerate(valid_urls):
                    url_payload: dict[str, Any] = {
                        "linkedin_url": url,
                    }
                    if idx < len(request.rows):
                        url_payload["raw_row"] = request.rows[idx]
                    linkedin_urls_data.append(url_payload)
        else:
            # No CSV context: create simple URL data
            for url in valid_urls:
                linkedin_urls_data.append({
                    "linkedin_url": url,
                })
        
        # Create export record with status "pending"
        # Use ExportType.contacts since it's a combined export but we'll track both counts
        export = await export_service.create_export(
            session,
            current_user.uuid,
            ExportType.contacts,  # Using contacts type for LinkedIn exports
            contact_uuids=[],  # Will be populated by background task
            company_uuids=[],  # Will be populated by background task
            linkedin_urls=valid_urls,  # Store original LinkedIn URLs for reference
        )
        
        # Store LinkedIn URLs JSON data with CSV context if available
        if request.rows is not None or request.raw_headers is not None:
            linkedin_urls_json = json.dumps(
                {
                    "urls": linkedin_urls_data,
                    "mapping": request.mapping,
                    "raw_headers": request.raw_headers,
                    "rows": request.rows,
                    "linkedin_url_column": linkedin_url_column,
                    "contact_field_mappings": request.contact_field_mappings,
                    "company_field_mappings": request.company_field_mappings,
                }
            )
            export.linkedin_urls_json = linkedin_urls_json
        
        # Set total_records for progress tracking (will be updated by task)
        export.total_records = len(valid_urls)
        # Flush to persist changes to database without committing the transaction
        # The transaction will be committed automatically by get_db() dependency
        # when the endpoint completes successfully
        await session.flush()
        
        # Log export activity
        activity_id = await activity_service.log_export_activity(
            session=session,
            user_id=current_user.uuid,
            service_type=ActivityServiceType.LINKEDIN,
            request_params={
                "urls": valid_urls,
                "url_count": len(valid_urls),
            },
            export_id=export.export_id,
            result_count=0,  # Will be updated when export completes
            status=ActivityStatus.SUCCESS,
            request=http_request,
        )
        
        # Enqueue background task with activity_id for updating
        # Note: This is a long-running task that might be better suited for Celery in the future
        add_background_task_safe(
            background_tasks,
            process_linkedin_export,
            export.export_id,
            valid_urls,
            activity_id,
            track_status=True,
            cpu_bound=False,  # I/O-bound task (database and file operations)
        )
        
        # Deduct credits for FreeUser and ProUser (after export is queued successfully)
        # Deduct 1 credit per URL
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = len(valid_urls)
                    await credit_service.deduct_credits(session, current_user.uuid, amount=credit_amount)
        except Exception:
            pass  # Credit deduction failed but export continues
        
        # Generate initial download URL (will be updated when export completes)
        from app.core.config import get_settings
        from app.utils.signed_url import generate_signed_url
        
        settings = get_settings()
        expires_at = export.expires_at or (datetime.now(timezone.utc) + timedelta(hours=24))
        download_token = generate_signed_url(export.export_id, current_user.uuid, expires_at)
        base_url = settings.BASE_URL.rstrip("/")
        download_url = f"{base_url}/api/v2/exports/{export.export_id}/download?token={download_token}"
        
        return LinkedInExportResponse(
            export_id=export.export_id,
            download_url=download_url,
            expires_at=expires_at,
            contact_count=0,  # Will be updated when export completes
            company_count=0,  # Will be updated when export completes
            status=ExportStatus.pending,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Log failed activity
        try:
            await activity_service.log_export_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.LINKEDIN,
                request_params={
                    "urls": valid_urls if 'valid_urls' in locals() else [],
                    "url_count": len(valid_urls) if 'valid_urls' in locals() else 0,
                },
                export_id="",  # No export_id if creation failed
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as log_exc:
            # Failed to log activity
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create LinkedIn export",
        ) from exc

