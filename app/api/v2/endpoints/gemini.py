"""Gemini AI API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.models.user import User
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/gemini", tags=["Gemini AI"])
logger = get_logger(__name__)
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


@router.post("/email/analyze", response_model=EmailRiskAnalysisResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(f"POST /gemini/email/analyze request received: email={request.email} user_id={current_user.id}")

    try:
        result = await service.analyze_email_risk(request.email)
        return EmailRiskAnalysisResponse(**result)
    except Exception as exc:
        logger.error(f"Failed to analyze email risk: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze email risk",
        ) from exc


@router.post("/company/summary", response_model=CompanySummaryResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        f"POST /gemini/company/summary request received: company_name={request.company_name} industry={request.industry} user_id={current_user.id}"
    )

    try:
        summary = await service.generate_company_summary(request.company_name, request.industry)
        return CompanySummaryResponse(summary=summary)
    except Exception as exc:
        logger.error(f"Failed to generate company summary: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate company summary",
        ) from exc

