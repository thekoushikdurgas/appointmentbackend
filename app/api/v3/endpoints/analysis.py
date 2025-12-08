"""Analysis endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.analysis import (
    AnalysisBatchRequest,
    AnalysisBatchResponse,
    CompanyAnalysisResult,
    ContactAnalysisResult,
)
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])
analysis_service = AnalysisService()


@router.get("/contact/{uuid}", response_model=dict)
async def analyze_contact_single(
    uuid: str = Path(..., description="Contact UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Analyze a single contact.
    
    Returns analysis of the contact's title including:
    - Validation status
    - Cleaning needs
    - Issues detected (encoding, emoji, international chars)
    """

    try:
        result = await analysis_service.analyze_contact(session, uuid)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact with UUID '{uuid}' not found",
            )
        
        return {
            "analysis": ContactAnalysisResult(
                contact_uuid=result["contact_uuid"],
                title=result.get("title"),
                title_valid=result["title_valid"],
                title_needs_cleaning=result["title_needs_cleaning"],
                title_cleaned=result.get("title_cleaned"),
                title_issues=result.get("title_issues", []),
                has_international_chars=result["has_international_chars"],
                has_encoding_issues=result["has_encoding_issues"],
                has_emoji=result["has_emoji"],
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze contact: {str(e)}",
        ) from e


@router.post("/contact/batch/", response_model=AnalysisBatchResponse)
async def analyze_contacts_batch(
    request: AnalysisBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalysisBatchResponse:
    """
    Analyze a batch of contacts.
    
    Processes multiple contacts and returns analysis results for each.
    """

    try:
        results = await analysis_service.analyze_contacts_batch(session, request.uuids)
        
        analyses = [
            ContactAnalysisResult(
                contact_uuid=r["contact_uuid"],
                title=r.get("title"),
                title_valid=r["title_valid"],
                title_needs_cleaning=r["title_needs_cleaning"],
                title_cleaned=r.get("title_cleaned"),
                title_issues=r.get("title_issues", []),
                has_international_chars=r["has_international_chars"],
                has_encoding_issues=r["has_encoding_issues"],
                has_emoji=r["has_emoji"],
            )
            for r in results
        ]
        
        return AnalysisBatchResponse(
            total=len(request.uuids),
            analyses=analyses,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze contacts batch: {str(e)}",
        ) from e


@router.get("/company/{uuid}", response_model=dict)
async def analyze_company_single(
    uuid: str = Path(..., description="Company UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Analyze a single company.
    
    Returns analysis of the company's name and keywords including:
    - Validation status
    - Cleaning needs
    - Issues detected (encoding, emoji, international chars)
    - Keyword validation
    """

    try:
        result = await analysis_service.analyze_company(session, uuid)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with UUID '{uuid}' not found",
            )
        
        return {
            "analysis": CompanyAnalysisResult(
                company_uuid=result["company_uuid"],
                name=result.get("name"),
                name_valid=result["name_valid"],
                name_needs_cleaning=result["name_needs_cleaning"],
                name_cleaned=result.get("name_cleaned"),
                name_issues=result.get("name_issues", []),
                has_international_chars=result["has_international_chars"],
                has_encoding_issues=result["has_encoding_issues"],
                has_emoji=result["has_emoji"],
                keywords_valid=result["keywords_valid"],
                keywords_needs_cleaning=result["keywords_needs_cleaning"],
                keywords_issues=result.get("keywords_issues", []),
                invalid_keywords_count=result["invalid_keywords_count"],
            )
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze company: {str(e)}",
        ) from e


@router.post("/company/batch/", response_model=AnalysisBatchResponse)
async def analyze_companies_batch(
    request: AnalysisBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalysisBatchResponse:
    """
    Analyze a batch of companies.
    
    Processes multiple companies and returns analysis results for each.
    """

    try:
        results = await analysis_service.analyze_companies_batch(session, request.uuids)
        
        analyses = [
            CompanyAnalysisResult(
                company_uuid=r["company_uuid"],
                name=r.get("name"),
                name_valid=r["name_valid"],
                name_needs_cleaning=r["name_needs_cleaning"],
                name_cleaned=r.get("name_cleaned"),
                name_issues=r.get("name_issues", []),
                has_international_chars=r["has_international_chars"],
                has_encoding_issues=r["has_encoding_issues"],
                has_emoji=r["has_emoji"],
                keywords_valid=r["keywords_valid"],
                keywords_needs_cleaning=r["keywords_needs_cleaning"],
                keywords_issues=r.get("keywords_issues", []),
                invalid_keywords_count=r["invalid_keywords_count"],
            )
            for r in results
        ]
        
        return AnalysisBatchResponse(
            total=len(request.uuids),
            analyses=analyses,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze companies batch: {str(e)}",
        ) from e

