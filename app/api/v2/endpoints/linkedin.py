"""LinkedIn URL-based CRUD API endpoints."""

from datetime import datetime, timedelta, timezone

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
    
    #region agent log
    import json
    import time
    log_path = "d:\\code\\ayan\\contact360\\.cursor\\debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_endpoint_entry", "timestamp": int(time.time() * 1000), "location": "linkedin.py:64", "message": "endpoint_entry", "data": {"url": request.url.strip(), "user_id": current_user.uuid}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1,H2,H3,H4,H5,H6"}) + "\n")
    except: pass
    #endregion agent log
    try:
        #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_service_call", "timestamp": int(time.time() * 1000), "location": "linkedin.py:65", "message": "before_service_call", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1,H2"}) + "\n")
        except: pass
        #endregion agent log
        result = await service.search_by_url(
            linkedin_url=request.url.strip(),
            user_id=current_user.uuid,
        )
        #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_service_success", "timestamp": int(time.time() * 1000), "location": "linkedin.py:69", "message": "service_success", "data": {"total_contacts": result.total_contacts, "total_companies": result.total_companies, "contacts_len": len(result.contacts), "companies_len": len(result.companies)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
        except Exception as log_exc:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_log_error", "timestamp": int(time.time() * 1000), "location": "linkedin.py:69", "message": "log_error", "data": {"error": str(log_exc)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
            except: pass
        #endregion agent log
        #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_return", "timestamp": int(time.time() * 1000), "location": "linkedin.py:77", "message": "before_return", "data": {"result_type": type(result).__name__}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
        except: pass
        #endregion agent log
        return result
    except Exception as exc:
        #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_exception_caught", "timestamp": int(time.time() * 1000), "location": "linkedin.py:70", "message": "exception_caught", "data": {"exception_type": type(exc).__name__, "exception_msg": str(exc)[:500], "exception_repr": repr(exc)[:500]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1,H2,H3,H4,H5,H6"}) + "\n")
        except: pass
        #endregion agent log
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

