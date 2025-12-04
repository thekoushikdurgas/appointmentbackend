"""Cleanup operation endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.cleanup import CleanupRequest, CleanupResponse, CleanupResult
from app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])
logger = get_logger(__name__)
cleanup_service = CleanupService()


@router.post("/contact/single/{uuid}", response_model=CleanupResult, status_code=status.HTTP_200_OK)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def clean_contact_single(
    uuid: str = Path(..., description="Contact UUID"),
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
    logger.info(
        "POST /v3/cleanup/contact/single/%s request received: user_id=%s",
        uuid,
        current_user.uuid,
    )

    try:
        result = await cleanup_service.clean_contact(session, uuid)
        return CleanupResult(
            uuid=result["uuid"],
            success=result["success"],
            fields_updated=result["fields_updated"],
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(
            "Error cleaning contact: uuid=%s error=%s",
            uuid,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean contact: {str(e)}",
        ) from e


@router.post("/contact/batch/", response_model=CleanupResponse, status_code=status.HTTP_200_OK)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "POST /v3/cleanup/contact/batch/ request received: count=%d user_id=%s",
        len(request.uuids),
        current_user.uuid,
    )

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
        logger.error(
            "Error cleaning contacts batch: count=%d error=%s",
            len(request.uuids),
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean contacts batch: {str(e)}",
        ) from e


@router.post("/company/single/{uuid}", response_model=CleanupResult, status_code=status.HTTP_200_OK)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def clean_company_single(
    uuid: str = Path(..., description="Company UUID"),
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
    logger.info(
        "POST /v3/cleanup/company/single/%s request received: user_id=%s",
        uuid,
        current_user.uuid,
    )

    try:
        result = await cleanup_service.clean_company(session, uuid)
        return CleanupResult(
            uuid=result["uuid"],
            success=result["success"],
            fields_updated=result["fields_updated"],
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(
            "Error cleaning company: uuid=%s error=%s",
            uuid,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean company: {str(e)}",
        ) from e


@router.post("/company/batch/", response_model=CleanupResponse, status_code=status.HTTP_200_OK)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "POST /v3/cleanup/company/batch/ request received: count=%d user_id=%s",
        len(request.uuids),
        current_user.uuid,
    )

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
        logger.error(
            "Error cleaning companies batch: count=%d error=%s",
            len(request.uuids),
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean companies batch: {str(e)}",
        ) from e

