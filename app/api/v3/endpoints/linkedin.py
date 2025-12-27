"""LinkedIn URL-based search API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.linkedin import (
    LinkedInSearchRequest,
    LinkedInSearchResponse,
)
from app.services.linkedin_service import LinkedInService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])
service = LinkedInService()


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
    
    try:
        result = await service.search_by_url(
            linkedin_url=request.url.strip(),
            user_id=current_user.uuid,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search by LinkedIn URL",
        ) from exc

