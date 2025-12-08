"""Endpoints supporting bulk data insert operations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.bulk import BulkInsertRequest, BulkInsertResponse
from app.services.bulk_service import BulkService

router = APIRouter(prefix="/bulk", tags=["Bulk"])


@router.post("/insert/", response_model=BulkInsertResponse, status_code=status.HTTP_200_OK)
async def bulk_insert(
    payload: BulkInsertRequest,
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
) -> BulkInsertResponse:
    """
    Bulk upsert contacts and/or companies from raw CSV-like JSON data.
    
    This endpoint accepts a list of JSON objects in the same format as the data ingestion scripts.
    It automatically detects whether each record contains contact data, company data, or both,
    and applies the same transformation logic (title cleaning, company name cleaning, keyword cleaning).
    
    **Upsert Behavior:**
    - If a record with the same LinkedIn URL already exists, it will be updated
    - If no matching LinkedIn URL is found, a new record will be inserted
    - Updates all fields in both main and metadata tables
    
    **Request Body:**
    - `data`: List of JSON objects with fields like:
      - Contact fields: `first_name`, `last_name`, `email`, `person_linkedin_url`, `title`, etc.
      - Company fields: `company`, `company_linkedin_url`, `company_name_for_emails`, etc.
    
    **Response:**
    - Summary statistics including:
      - `contacts_inserted`: Number of contacts successfully inserted (new records)
      - `contacts_updated`: Number of contacts successfully updated (existing records by LinkedIn URL)
      - `contacts_skipped`: Number of contacts skipped (errors)
      - `companies_inserted`: Number of companies successfully inserted (new records)
      - `companies_updated`: Number of companies successfully updated (existing records by LinkedIn URL)
      - `companies_skipped`: Number of companies skipped (errors)
      - `errors`: List of errors encountered (if any)
    
    **Authentication:**
    - Requires admin role (Bearer token with admin role)
    
    **Notes:**
    - Uses `on_conflict_do_update` for upsert behavior (updates existing records)
    - Searches for existing records by LinkedIn URL before processing
    - Processes companies first, then contacts (contacts may reference companies)
    - Uses consistent UUID generation logic
    - Updates all fields in both main tables and metadata tables
    """
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data list cannot be empty",
        )
    
    try:
        service = BulkService()
        result = await service.bulk_insert(session, payload.data)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk insert",
        ) from exc

