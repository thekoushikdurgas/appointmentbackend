"""Gemini AI API endpoints."""

from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.models.user import User
from app.services.gemini_service import GeminiService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/gemini", tags=["Gemini AI"])
service = GeminiService()


class EmailRiskAnalysisRequest(BaseModel):
    """Request for email risk analysis."""

    email: EmailStr


class EmailRiskAnalysisResponse(BaseModel):
    """Response for email risk analysis."""

    riskScore: int
    analysis: str
    isRoleBased: bool
    isDisposable: bool


class CompanySummaryRequest(BaseModel):
    """Request for company summary generation."""

    company_name: str
    industry: str


class CompanySummaryResponse(BaseModel):
    """Response for company summary generation."""

    summary: str


class ParseFiltersRequest(BaseModel):
    """Request for parsing natural language query into filters."""

    query: str


class ParseFiltersResponse(BaseModel):
    """Response for filter parsing."""

    job_titles: Optional[list[str]] = None
    company_names: Optional[list[str]] = None
    industry: Optional[list[str]] = None
    location: Optional[list[str]] = None
    employees: Optional[Tuple[int, int]] = None
    seniority: Optional[list[str]] = None


@router.post("/email/analyze", response_model=EmailRiskAnalysisResponse)
async def analyze_email_risk(
    request: EmailRiskAnalysisRequest,
    current_user: User = Depends(get_current_user),
) -> EmailRiskAnalysisResponse:
    """
    Analyze email address for potential risk factors using Gemini AI.
    
    Args:
        request: Email address to analyze
        current_user: Current authenticated user
        
    Returns:
        EmailRiskAnalysisResponse with risk analysis
    """
    try:
        result = await service.analyze_email_risk(request.email)
        return EmailRiskAnalysisResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze email risk",
        ) from exc


@router.post("/company/summary", response_model=CompanySummaryResponse)
async def generate_company_summary(
    request: CompanySummaryRequest,
    current_user: User = Depends(get_current_user),
) -> CompanySummaryResponse:
    """
    Generate AI-powered company summary using Gemini AI.
    
    Args:
        request: Company name and industry
        current_user: Current authenticated user
        
    Returns:
        CompanySummaryResponse with generated summary
    """
    try:
        summary = await service.generate_company_summary(request.company_name, request.industry)
        return CompanySummaryResponse(summary=summary)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate company summary",
        ) from exc


@router.post("/parse-filters", response_model=ParseFiltersResponse)
async def parse_contact_filters(
    request: ParseFiltersRequest,
    current_user: User = Depends(get_current_user),
) -> ParseFiltersResponse:
    """
    Parse natural language query into structured contact filter parameters using Gemini AI.
    
    Args:
        request: ParseFiltersRequest with natural language query
        current_user: Current authenticated user
        
    Returns:
        ParseFiltersResponse with extracted filter parameters
    """
    try:
        result = await service.parse_contact_filters(request.query)
        
        # Convert employees list to tuple if present
        employees_tuple = None
        if result.get("employees") and isinstance(result["employees"], list) and len(result["employees"]) == 2:
            employees_tuple = (result["employees"][0], result["employees"][1])
        
        return ParseFiltersResponse(
            job_titles=result.get("job_titles"),
            company_names=result.get("company_names"),
            industry=result.get("industry"),
            location=result.get("location"),
            employees=employees_tuple,
            seniority=result.get("seniority"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse filters: {str(exc)}"
        ) from exc

