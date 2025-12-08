"""Sales Navigator HTML scraping API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sales_navigator import SalesNavigatorScrapeRequest, SalesNavigatorScrapeResponse
from app.services.sales_navigator_service import (
    create_output_structure,
    scrape_sales_navigator_html,
)

router = APIRouter(prefix="/sales-navigator", tags=["Sales Navigator"])


@router.post("/scrape", response_model=SalesNavigatorScrapeResponse)
async def scrape_sales_navigator(
    request: SalesNavigatorScrapeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalesNavigatorScrapeResponse:
    """
    Scrape Sales Navigator HTML and extract profile data.
    
    Accepts HTML content from a Sales Navigator search results page and extracts
    all profile information into a structured JSON format.
    
    Request body:
    - html: Sales Navigator HTML content (required)
    
    Returns:
        Structured JSON with extraction metadata, page metadata, and profiles array
    """
    try:
        # Scrape the HTML content
        profiles, page_metadata = scrape_sales_navigator_html(
            html_content=request.html,
            include_metadata=True
        )
        
        # Create output structure
        output_data = create_output_structure(
            profiles=profiles,
            page_metadata=page_metadata,
            source_file=None,  # API request, not file
            output_format='hierarchical'
        )
        
        # Convert to response model
        response = SalesNavigatorScrapeResponse(
            extraction_metadata=output_data['extraction_metadata'],
            page_metadata=output_data['page_metadata'],
            profiles=output_data['profiles']
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid HTML content: {str(e)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape HTML: {str(exc)}",
        )

