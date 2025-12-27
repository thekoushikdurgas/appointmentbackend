"""Sales Navigator HTML scraping API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut
from app.schemas.sales_navigator import SalesNavigatorScrapeRequest, SalesNavigatorScrapeResponse
from app.services.sales_navigator_service import (
    create_output_structure,
    save_profiles_to_database,
    scrape_sales_navigator_html,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
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
        
        # Save profiles to database (optional)
        if request.save:
            saved_data = await save_profiles_to_database(session, profiles)
            # Convert saved database records to response schemas only when save=True
            saved_contacts = [ContactDB.model_validate(contact) for contact in saved_data['contacts']]
            saved_contacts_metadata = [
                ContactMetadataOut.model_validate(meta) for meta in saved_data['contacts_metadata']
            ]
            saved_companies = [CompanyDB.model_validate(company) for company in saved_data['companies']]
            saved_companies_metadata = [
                CompanyMetadataOut.model_validate(meta) for meta in saved_data['companies_metadata']
            ]
        else:
            # Empty lists when save=False to avoid unnecessary conversions
            saved_data = {
                "contacts": [],
                "contacts_metadata": [],
                "companies": [],
                "companies_metadata": [],
                "summary": {
                    "total_profiles": len(profiles),
                    "contacts_created": 0,
                    "contacts_updated": 0,
                    "companies_created": 0,
                    "companies_updated": 0,
                    "errors": []
                }
            }
            saved_contacts = []
            saved_contacts_metadata = []
            saved_companies = []
            saved_companies_metadata = []
        
        # Convert to response model
        response = SalesNavigatorScrapeResponse(
            extraction_metadata=output_data['extraction_metadata'],
            page_metadata=output_data['page_metadata'],
            profiles=output_data['profiles'],
            saved_contacts=saved_contacts,
            saved_contacts_metadata=saved_contacts_metadata,
            saved_companies=saved_companies,
            saved_companies_metadata=saved_companies_metadata,
            save_summary=saved_data['summary']
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

