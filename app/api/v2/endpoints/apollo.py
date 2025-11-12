"""Apollo.io URL Analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.apollo import ApolloUrlAnalysisRequest, ApolloUrlAnalysisResponse
from app.services.apollo_analysis_service import ApolloAnalysisService

router = APIRouter(prefix="/apollo", tags=["Apollo"])
logger = get_logger(__name__)
service = ApolloAnalysisService()


@router.post("/analyze", response_model=ApolloUrlAnalysisResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def analyze_apollo_url(
    request_data: ApolloUrlAnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ApolloUrlAnalysisResponse:
    """
    Analyze an Apollo.io URL and return structured parameter breakdown.

    This endpoint parses Apollo.io search URLs (typically from the People Search page)
    and extracts all query parameters, categorizing them into logical groups such as:
    - Pagination (page numbers)
    - Sorting (sort field and direction)
    - Person Filters (titles, locations, seniorities, departments)
    - Organization Filters (employee ranges, locations, industries, revenue)
    - Email Filters (verification status, catch-all exclusion)
    - Keyword Filters (organization keywords, search fields)
    - And more...

    The analysis includes:
    - URL structure breakdown (base URL, hash path, query string)
    - Categorized parameters with descriptions
    - Parameter values (URL-decoded)
    - Statistics about the search criteria

    Args:
        request_data: Request containing the Apollo.io URL to analyze
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        ApolloUrlAnalysisResponse with complete URL analysis

    Raises:
        HTTPException: If URL is invalid, not from Apollo.io, or analysis fails
    """
    logger.info(
        "Apollo URL analysis request: user_id=%s url_length=%d",
        current_user.id,
        len(request_data.url),
    )

    try:
        result = service.analyze_url(request_data.url)
        logger.info(
            "Apollo URL analyzed successfully: user_id=%s total_params=%d categories=%d",
            current_user.id,
            result.statistics.total_parameters,
            result.statistics.categories_used,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Apollo URL analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing the URL",
        ) from exc

