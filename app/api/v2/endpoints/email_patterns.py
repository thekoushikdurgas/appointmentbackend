"""Email pattern API endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.email_patterns import (
    EmailPatternAnalyzeRequest,
    EmailPatternAnalyzeResponse,
    EmailPatternBulkCreate,
    EmailPatternCreate,
    EmailPatternImportResponse,
    EmailPatternListResponse,
    EmailPatternResponse,
    EmailPatternUpdate,
)
from app.services.email_pattern_service import EmailPatternService

router = APIRouter(prefix="/email-patterns", tags=["Email Patterns"])
service = EmailPatternService()


@router.get("/company/{company_uuid}", response_model=EmailPatternListResponse)
async def get_patterns_by_company(
    company_uuid: str = Path(..., description="Company UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternListResponse:
    """
    Get all email patterns for a company.
    
    Returns a list of all email patterns associated with the specified company UUID,
    ordered by contact count (descending) and creation date (descending).
    """
    try:
        patterns = await service.get_patterns_by_company(session, company_uuid)
        return EmailPatternListResponse(
            patterns=patterns,
            total=len(patterns),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve patterns: {str(e)}",
        )


@router.post("/", response_model=EmailPatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    pattern_data: EmailPatternCreate,
    upsert: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternResponse:
    """
    Create a new email pattern.
    
    Creates a new email pattern for a company. If a pattern with the same
    pattern_format already exists for the company:
    - If upsert=False (default): Returns 409 Conflict error
    - If upsert=True: Increments existing pattern's contact_count by 1 and preserves other fields
    """
    try:
        pattern = await service.create_pattern(session, pattern_data, upsert=upsert)
        return pattern
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pattern: {str(e)}",
        )


@router.put("/{pattern_uuid}", response_model=EmailPatternResponse)
async def update_pattern(
    pattern_uuid: str = Path(..., description="Pattern UUID"),
    pattern_data: EmailPatternUpdate = ...,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternResponse:
    """
    Update an existing email pattern.
    
    Updates the specified fields of an email pattern.     Only provided fields are updated.
    """
    try:
        pattern = await service.update_pattern(session, pattern_uuid, pattern_data)
        return pattern
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pattern: {str(e)}",
        )


@router.delete("/{pattern_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_uuid: str = Path(..., description="Pattern UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete an email pattern.
    
    Permanently deletes the email pattern with the specified UUID.
    """
    try:
        await service.delete_pattern(session, pattern_uuid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete pattern: {str(e)}",
        )


@router.post("/analyze/{company_uuid}", response_model=EmailPatternAnalyzeResponse)
async def analyze_company_emails(
    company_uuid: str = Path(..., description="Company UUID"),
    request: EmailPatternAnalyzeRequest = ...,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternAnalyzeResponse:
    """
    Analyze and extract email patterns from company contacts.
    
    Analyzes all contacts' emails for the specified company and extracts email patterns.
    Patterns are automatically created or updated in the database with contact counts.
    
    If patterns already exist and force_reanalyze is False, returns existing patterns.
    If force_reanalyze is True, reanalyzes all contacts and updates patterns.
    """
    try:
        result = await service.analyze_company_emails(
            session,
            company_uuid,
            request.force_reanalyze,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze company emails: {str(e)}",
        )


@router.post("/import", response_model=EmailPatternImportResponse)
async def import_patterns_from_csv(
    file: UploadFile = File(..., description="CSV file with email patterns"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternImportResponse:
    """
    Import email patterns from a CSV file.
    
    Supports two CSV formats:
    
    **Format 1: Direct Pattern Format**
    - company_uuid (required): Company UUID
    - pattern_format (required): Pattern format (e.g., 'first.last', 'firstlast')
    - pattern_string (optional): Pattern string used for generation
    - contact_count (optional): Contact count (default: 1 per row, aggregated for duplicates)
    - is_auto_extracted (optional): Boolean (default: false)
    - uuid (optional): Pattern UUID (auto-generated deterministically if not provided)
    
    **Format 2: Contact Data Format (Pattern Extraction)**
    - company (optional): Company name (used to generate company_uuid if company_uuid not provided)
    - company_linkedin_url (optional): Company LinkedIn URL (used to generate company_uuid)
    - company_name_for_emails (optional): Company name for emails (used to generate company_uuid)
    - first_name (required for pattern extraction): Contact first name
    - last_name (required for pattern extraction): Contact last name
    - email (required for pattern extraction): Contact email address
    
    If company_uuid is not provided, it will be generated deterministically from company, 
    company_linkedin_url, and company_name_for_emails fields.
    
    If pattern_format is not provided, it will be extracted from email, first_name, and last_name.
    In this case, is_auto_extracted will be set to True.
    
    Patterns are grouped by (company_uuid, pattern_format) and contact_count is aggregated.
    Pattern UUIDs are generated deterministically using uuid5(company_uuid + pattern_format).
    
    When a duplicate pattern is found (same company_uuid + pattern_format):
    - Increments existing contact_count by the aggregated batch count
    - Preserves existing pattern_string and is_auto_extracted
    - Updates updated_at timestamp
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File name is required",
        )

    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    try:
        # Read CSV content
        csv_content = await file.read()
        csv_content_str = csv_content.decode('utf-8')
        
        # Import patterns
        result = await service.import_patterns_from_csv(session, csv_content_str)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import patterns from CSV: {str(e)}",
        )


@router.post("/bulk", response_model=EmailPatternImportResponse)
async def import_patterns_bulk(
    bulk_data: EmailPatternBulkCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternImportResponse:
    """
    Import email patterns from a JSON array.
    
    Accepts an array of email pattern objects. Each pattern should have:
    - company_uuid (required): Company UUID
    - pattern_format (required): Pattern format
    - pattern_string (optional): Pattern string
    - contact_count (optional): Contact count (default: 0, aggregated for duplicates)
    - is_auto_extracted (optional): Boolean (default: false)
    - uuid (optional): Pattern UUID (auto-generated deterministically if not provided)
    
    Patterns are grouped by (company_uuid, pattern_format) and contact_count is aggregated.
    Pattern UUIDs are generated deterministically using uuid5(company_uuid + pattern_format).
    
    When a duplicate pattern is found (same company_uuid + pattern_format):
    - Increments existing contact_count by the aggregated batch count
    - Preserves existing pattern_string and is_auto_extracted
    - Updates updated_at timestamp
    """
    try:
        result = await service.import_patterns_bulk(session, bulk_data.patterns)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import patterns in bulk: {str(e)}",
        )

