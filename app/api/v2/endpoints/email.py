"""Email finder API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.email import SimpleEmailFinderResponse
from app.services.email_finder_service import EmailFinderService

router = APIRouter(prefix="/email", tags=["Email"])
logger = get_logger(__name__)
service = EmailFinderService()


@router.get("/finder/", response_model=SimpleEmailFinderResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def find_emails(
    first_name: str = Query(..., description="Contact first name (case-insensitive partial match)"),
    last_name: str = Query(..., description="Contact last name (case-insensitive partial match)"),
    domain: Optional[str] = Query(None, description="Company domain or website URL (can use website parameter instead)"),
    website: Optional[str] = Query(None, description="Company website URL (alias for domain parameter)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SimpleEmailFinderResponse:
    """
    Find emails by contact name and company domain.
    
    Searches for contacts matching the provided first name and last name
    whose company website domain matches the provided domain/website.
    Only returns contacts that have email addresses.
    
    The domain parameter can be:
    - A full URL: "https://www.example.com" or "http://example.com"
    - A domain: "example.com" or "www.example.com"
    
    The endpoint extracts and normalizes the domain from the input, removing
    protocols, www prefixes, and ports.
    
    Returns:
        Simple list of emails with contact UUIDs in format:
        {
          "emails": [
            { "uuid": "contact_uuid", "email": "email@example.com" }
          ],
          "total": 1
        }
    """
    logger.info(
        "GET /email/finder/ request received: first_name=%s last_name=%s domain=%s website=%s user_id=%s",
        first_name,
        last_name,
        domain,
        website,
        current_user.id,
    )
    
    try:
        logger.debug(
            "Calling service.find_emails with: first_name=%s last_name=%s domain=%s website=%s",
            first_name,
            last_name,
            domain,
            website,
        )
        result = await service.find_emails(
            session=session,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            website=website,
        )
        logger.info(
            "GET /email/finder/ completed successfully: found=%d (uuid, email) pairs",
            result.total,
        )
        logger.debug(
            "Response summary: total=%d, sample_emails=%s",
            result.total,
            [{"uuid": e.uuid, "email": e.email} for e in result.emails[:3]] if result.emails else [],
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error finding emails: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find emails",
        ) from exc

