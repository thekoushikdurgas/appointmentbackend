"""Cleanup operation endpoints for v3 API."""

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.cleanup import CleanupRequest, CleanupResponse, CleanupResult
from app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])
cleanup_service = CleanupService()

# #region agent log
# Use relative path from project root instead of hardcoded Windows path
DEBUG_LOG_PATH = Path(__file__).parent.parent.parent.parent.parent / ".cursor" / "debug.log"
# #endregion


@router.post("/contact/single/{uuid}", response_model=CleanupResult, status_code=status.HTTP_200_OK)
async def clean_contact_single(
    uuid: str = FastAPIPath(..., description="Contact UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleanupResult:
    """
    Clean a single contact and its metadata.
    
    Applies cleaning rules to normalize contact data:
    - Cleans title using title cleaning utilities
    - Cleans departments/keywords arrays
    - Removes special characters from text fields
    - Converts placeholder values ("_", "") to NULL
    """
    # Clean single contact endpoint

    # #region agent log
    endpoint_start = time.time()
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "ALL", "location": "cleanup.py:40", "message": "endpoint entry", "data": {"uuid": uuid, "user_id": str(current_user.uuid)}, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception: pass
    # #endregion
    try:
        # #region agent log
        service_start = time.time()
        # #endregion
        result = await cleanup_service.clean_contact(session, uuid)
        # #region agent log
        service_time = (time.time() - service_start) * 1000
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "ALL", "location": "cleanup.py:41", "message": "cleanup_service.clean_contact completed", "data": {"service_time_ms": service_time}, "timestamp": int(time.time() * 1000)}) + "\n")
        except Exception: pass
        # #endregion
        # #region agent log
        commit_start = time.time()
        # #endregion
        # Note: commit happens in get_db dependency after this function returns
        # #region agent log
        commit_time = (time.time() - commit_start) * 1000
        endpoint_time = (time.time() - endpoint_start) * 1000
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "C", "location": "cleanup.py:47", "message": "before commit (commit happens in get_db)", "data": {"commit_time_ms": commit_time, "endpoint_time_ms": endpoint_time}, "timestamp": int(time.time() * 1000)}) + "\n")
        except Exception: pass
        # #endregion
        return CleanupResult(
            uuid=result["uuid"],
            success=result["success"],
            fields_updated=result["fields_updated"],
            error=result.get("error"),
        )
    except Exception as e:
        # Error cleaning contact
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean contact: {str(e)}",
        ) from e


@router.post("/contact/batch/", response_model=CleanupResponse, status_code=status.HTTP_200_OK)
async def clean_contacts_batch(
    request: CleanupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleanupResponse:
    """
    Clean a batch of contacts and their metadata.
    
    Processes multiple contacts in a single request. Each contact is cleaned
    independently, and results are returned for all contacts.
    """
    # Clean batch of contacts endpoint

    try:
        result = await cleanup_service.clean_contacts_batch(session, request.uuids)
        return CleanupResponse(
            total=result["total"],
            successful=result["successful"],
            failed=result["failed"],
            results=[
                CleanupResult(
                    uuid=r["uuid"],
                    success=r["success"],
                    fields_updated=r["fields_updated"],
                    error=r.get("error"),
                )
                for r in result["results"]
            ],
        )
    except Exception as e:
        # Error cleaning contacts batch
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean contacts batch: {str(e)}",
        ) from e


@router.post("/company/single/{uuid}", response_model=CleanupResult, status_code=status.HTTP_200_OK)
async def clean_company_single(
    uuid: str = FastAPIPath(..., description="Company UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleanupResult:
    """
    Clean a single company and its metadata.
    
    Applies cleaning rules to normalize company data:
    - Cleans company name using specialized company name cleaning
    - Cleans keywords array using keyword cleaning utilities
    - Cleans industries and technologies arrays
    - Removes special characters from text fields
    - Converts placeholder values ("_", "") to NULL
    """
    # Clean single company endpoint

    try:
        result = await cleanup_service.clean_company(session, uuid)
        return CleanupResult(
            uuid=result["uuid"],
            success=result["success"],
            fields_updated=result["fields_updated"],
            error=result.get("error"),
        )
    except Exception as e:
        # Error cleaning company
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean company: {str(e)}",
        ) from e


@router.post("/company/batch/", response_model=CleanupResponse, status_code=status.HTTP_200_OK)
async def clean_companies_batch(
    request: CleanupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CleanupResponse:
    """
    Clean a batch of companies and their metadata.
    
    Processes multiple companies in a single request. Each company is cleaned
    independently, and results are returned for all companies.
    """
    # Clean batch of companies endpoint

    try:
        result = await cleanup_service.clean_companies_batch(session, request.uuids)
        return CleanupResponse(
            total=result["total"],
            successful=result["successful"],
            failed=result["failed"],
            results=[
                CleanupResult(
                    uuid=r["uuid"],
                    success=r["success"],
                    fields_updated=r["fields_updated"],
                    error=r.get("error"),
                )
                for r in result["results"]
            ],
        )
    except Exception as e:
        # Error cleaning companies batch
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean companies batch: {str(e)}",
        ) from e

