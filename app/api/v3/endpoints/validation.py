"""Validation endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.validation import (
    CompanyValidationResult,
    ContactValidationResult,
    ValidationBatchRequest,
    ValidationBatchResponse,
    ValidationIssue,
    ValidationResponse,
)
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/validation", tags=["Validation"])
validation_service = ValidationService()


@router.get("/contact/{uuid}", response_model=ValidationResponse)
async def validate_contact_single(
    uuid: str = Path(..., description="Contact UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ValidationResponse:
    """
    Validate a single contact.
    
    Returns validation results including:
    - Overall validity status
    - List of issues found (errors and warnings)
    - Fields that were validated
    """
    try:
        result = await validation_service.validate_contact(session, uuid)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact with UUID '{uuid}' not found",
            )
        
        return ValidationResponse(
            validation=ContactValidationResult(
                contact_uuid=result["contact_uuid"],
                is_valid=result["is_valid"],
                issues=[
                    ValidationIssue(
                        field=issue["field"],
                        issue=issue["issue"],
                        severity=issue["severity"],
                    )
                    for issue in result.get("issues", [])
                ],
                fields_validated=result.get("fields_validated", []),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate contact: {str(e)}",
        ) from e


@router.post("/contact/batch/", response_model=ValidationBatchResponse)
async def validate_contacts_batch(
    request: ValidationBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ValidationBatchResponse:
    """
    Validate a batch of contacts.
    
    Processes multiple contacts and returns validation results for each.
    """
    try:
        results = await validation_service.validate_contacts_batch(session, request.uuids)
        
        validations = [
            ContactValidationResult(
                contact_uuid=r["contact_uuid"],
                is_valid=r["is_valid"],
                issues=[
                    ValidationIssue(
                        field=issue["field"],
                        issue=issue["issue"],
                        severity=issue["severity"],
                    )
                    for issue in r.get("issues", [])
                ],
                fields_validated=r.get("fields_validated", []),
            )
            for r in results
        ]
        
        return ValidationBatchResponse(
            total=len(request.uuids),
            validations=validations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate contacts batch: {str(e)}",
        ) from e


@router.get("/company/{uuid}", response_model=ValidationResponse)
async def validate_company_single(
    uuid: str = Path(..., description="Company UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ValidationResponse:
    """
    Validate a single company.
    
    Returns validation results including:
    - Overall validity status
    - List of issues found (errors and warnings)
    - Fields that were validated
    """
    try:
        result = await validation_service.validate_company(session, uuid)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with UUID '{uuid}' not found",
            )
        
        return ValidationResponse(
            validation=CompanyValidationResult(
                company_uuid=result["company_uuid"],
                is_valid=result["is_valid"],
                issues=[
                    ValidationIssue(
                        field=issue["field"],
                        issue=issue["issue"],
                        severity=issue["severity"],
                    )
                    for issue in result.get("issues", [])
                ],
                fields_validated=result.get("fields_validated", []),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate company: {str(e)}",
        ) from e


@router.post("/company/batch/", response_model=ValidationBatchResponse)
async def validate_companies_batch(
    request: ValidationBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ValidationBatchResponse:
    """
    Validate a batch of companies.
    
    Processes multiple companies and returns validation results for each.
    """
    try:
        results = await validation_service.validate_companies_batch(session, request.uuids)
        
        validations = [
            CompanyValidationResult(
                company_uuid=r["company_uuid"],
                is_valid=r["is_valid"],
                issues=[
                    ValidationIssue(
                        field=issue["field"],
                        issue=issue["issue"],
                        severity=issue["severity"],
                    )
                    for issue in r.get("issues", [])
                ],
                fields_validated=r.get("fields_validated", []),
            )
            for r in results
        ]
        
        return ValidationBatchResponse(
            total=len(request.uuids),
            validations=validations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate companies batch: {str(e)}",
        ) from e

