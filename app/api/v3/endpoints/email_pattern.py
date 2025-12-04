"""Email pattern endpoints for v3 API."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.v3.email_pattern import (
    EmailPatternBatchRequest,
    EmailPatternBatchResponse,
    EmailPatternInfo,
    EmailPatternResponse,
)
from app.services.email_pattern_service import EmailPatternService

router = APIRouter(prefix="/email_pattern", tags=["Email Pattern"])
logger = get_logger(__name__)
email_pattern_service = EmailPatternService()

# Maximum batch size for batch endpoint to prevent memory issues and timeouts
MAX_BATCH_SIZE = 1000


@router.get("/contact/{uuid}", response_model=EmailPatternResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def get_email_pattern_for_contact(
    uuid: str = Path(..., description="Contact UUID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternResponse:
    """
    Get email pattern for a single contact.
    
    Looks up the contact's company and returns email patterns associated with that company.
    If the contact has an email, attempts to extract the pattern format from the email.
    """
    logger.info(
        "GET /v3/email_pattern/contact/%s request received: user_id=%s",
        uuid,
        current_user.uuid,
    )

    try:
        pattern_info = await email_pattern_service.get_patterns_by_contact(session, uuid)
        
        if pattern_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact with UUID '{uuid}' not found",
            )
        
        return EmailPatternResponse(
            pattern=EmailPatternInfo(
                contact_uuid=pattern_info["contact_uuid"],
                company_uuid=pattern_info.get("company_uuid"),
                pattern_format=pattern_info.get("pattern_format"),
                pattern_string=pattern_info.get("pattern_string"),
                contact_count=pattern_info.get("contact_count"),
                is_auto_extracted=pattern_info.get("is_auto_extracted"),
                patterns=pattern_info.get("patterns", []),
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting email pattern for contact: uuid=%s error=%s",
            uuid,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email pattern: {str(e)}",
        ) from e


@router.post("/contact/batch/", response_model=EmailPatternBatchResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def get_email_patterns_for_contacts_batch(
    request: EmailPatternBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailPatternBatchResponse:
    """
    Get email patterns for a batch of contacts.
    
    Processes multiple contacts and returns email pattern information for each.
    Contacts without companies or patterns will still be included in the response.
    """
    logger.info(
        "POST /v3/email_pattern/contact/batch/ request received: count=%d user_id=%s",
        len(request.uuids),
        current_user.uuid,
    )

    # Validate batch size
    if len(request.uuids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_SIZE} contacts. Please split your request into smaller batches.",
        )

    try:
        # Use optimized batch method that uses batch database queries
        pattern_infos = await email_pattern_service.get_patterns_by_contacts_batch(
            session,
            request.uuids,
        )
        
        # Convert to response format
        patterns = [
            EmailPatternInfo(
                contact_uuid=info["contact_uuid"],
                company_uuid=info.get("company_uuid"),
                pattern_format=info.get("pattern_format"),
                pattern_string=info.get("pattern_string"),
                contact_count=info.get("contact_count"),
                is_auto_extracted=info.get("is_auto_extracted"),
                patterns=info.get("patterns", []),
            )
            for info in pattern_infos
        ]
        
        return EmailPatternBatchResponse(
            total=len(request.uuids),
            patterns=patterns,
        )
    except Exception as e:
        logger.error(
            "Error getting email patterns for contacts batch: count=%d error=%s",
            len(request.uuids),
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email patterns: {str(e)}",
        ) from e

