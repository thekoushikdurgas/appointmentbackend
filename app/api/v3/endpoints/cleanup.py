"""Cleanup operation endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.cleanup import CleanupRequest, CleanupResponse, CleanupResult
from app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])
cleanup_service = CleanupService()


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
    try:
        result = await cleanup_service.clean_contact(session, uuid)
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

