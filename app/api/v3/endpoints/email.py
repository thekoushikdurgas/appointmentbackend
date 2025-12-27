"""Email finder API endpoints."""

import asyncio
import json
from datetime import timedelta
from typing import Any, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.exports import ExportStatus, ExportType
from app.models.user import ActivityServiceType, ActivityStatus, User
from app.repositories.user import UserActivityRepository, UserProfileRepository
from app.schemas.email import (
    BulkEmailVerifierRequest,
    BulkEmailVerifierResponse,
    EmailExportRequest,
    EmailProvider,
    EmailVerificationStatus,
    EmailVerifierRequest,
    EmailVerifierResponse,
    SimpleEmailFinderResponse,
    SingleEmailRequest,
    SingleEmailResponse,
    SingleEmailVerifierFindResponse,
    SingleEmailVerifierRequest,
    SingleEmailVerifierResponse,
    VerifiedEmailResult,
)
from app.schemas.exports import EmailExportResponse
from app.services.activity_service import ActivityService
from app.services.bulkmailverifier_service import BulkMailVerifierService
from app.services.credit_service import CreditService
from app.services.email_finder_service import EmailFinderService
from app.services.export_service import ExportService
from app.services.icypeas_service import IcyPeasService
from app.services.truelist_service import TruelistService
from app.tasks.export_tasks import process_email_export
from app.utils.background_tasks import add_background_task_safe
from app.utils.catchall_handler import handle_catchall_email
from app.utils.domain import extract_domain_from_url
from app.utils.email_generator import generate_email_combinations
from app.utils.logger import get_logger, log_error, log_api_error
from app.utils.signed_url import generate_signed_url

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])
service = EmailFinderService()
export_service = ExportService()
activity_service = ActivityService()
credit_service = CreditService()
profile_repo = UserProfileRepository()
activity_repo = UserActivityRepository()
@router.get("/finder/", response_model=SimpleEmailFinderResponse)
async def find_emails(
    http_request: Request,
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
    logger.debug(
        "Email finder endpoint called",
        extra={
            "context": {
                "user_id": current_user.uuid if current_user else None,
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain,
                "website": website,
                "has_session": session is not None
            }
        }
    )
    try:
        result = await service.find_emails(
            session=session,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            website=website,
        )
        logger.debug(
            "Email finder service call completed",
            extra={
                "context": {
                    "user_id": current_user.uuid if current_user else None,
                    "result_total": result.total if result else None,
                    "result_type": type(result).__name__
                }
            }
        )
        
        # Log activity
        await activity_service.log_search_activity(
            session=session,
            user_id=current_user.uuid,
            service_type=ActivityServiceType.EMAIL,
            request_params={
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain or website,
            },
            result_count=result.total,
            result_summary={"emails_found": result.total},
            status=ActivityStatus.SUCCESS,
            request=http_request,
        )
        
        # Deduct credits for FreeUser and ProUser (after successful search)
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    new_balance = await credit_service.deduct_credits(
                        session, current_user.uuid, amount=1
                    )
        except Exception as credit_exc:
            credit_error_msg = str(credit_exc)
        
        return result
    except HTTPException:
        raise
    except Exception as exc:
        error_msg = str(exc)
        
        # Log error with full context
        log_error(
            "Error in email finder endpoint",
            exc,
            "app.api.v3.endpoints.email",
            context={
                "endpoint": "/email/finder/",
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain,
                "website": website,
                "user_id": current_user.uuid if current_user else None,
            },
        )
        
        logger.debug(
            "Exception caught in email finder",
            extra={
                "context": {
                    "user_id": current_user.uuid if current_user else None,
                    "error_msg": error_msg,
                    "error_type": type(exc).__name__
                }
            }
        )
        
        # Log failed activity
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain or website,
                },
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as log_exc:
            logger.warning(
                "Failed to log activity for email finder error",
                extra={"context": {"original_error": str(exc), "log_error": str(log_exc)}}
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find emails",
        ) from exc


async def _verify_email_batch(
    emails: list[str],
    batch_number: int,
    service: BulkMailVerifierService,
) -> tuple[list[str], int]:
    """
    Verify a batch of emails and return valid emails.
    
    Args:
        emails: List of email addresses to verify
        batch_number: Current batch number
        service: BulkMailVerifierService instance
        
    Returns:
        Tuple of (valid_emails_list, batches_processed)
    """
    valid_emails = []
    batches_processed = 0
    
    try:
        # Upload file
        try:
            upload_result = await service.upload_file(emails)
            slug = upload_result.get("slug")
            number_of_emails = upload_result.get("number_of_emails")
            upload_status = upload_result.get("status", "unknown")
        except HTTPException as http_exc:
            # Handle HTTPException from BulkMailVerifier service gracefully
            if "credentials not configured" in str(http_exc.detail).lower():
                # Return empty valid emails but don't raise - let the endpoint handle it
                return valid_emails, batches_processed
            else:
                # Re-raise other HTTPExceptions
                raise
        
        if not slug:
            return valid_emails, batches_processed
        
        slug = upload_result["slug"]
        
        try:
            # Start verification
            verification_start_result = await service.start_verification(slug)
            verification_start_status = verification_start_result.get("File Status", verification_start_result.get("status", "unknown"))
            
            # Poll for status until completed
            max_poll_attempts = 300  # 5 minutes max (300 * 1 second)
            poll_interval = 10  # Poll every 10 seconds
            poll_attempts = 0
            last_logged_attempt = 0
            log_interval = 20  # Log progress every 20 attempts (every ~3.3 minutes)
            
            # Start polling
            while poll_attempts < max_poll_attempts:
                await asyncio.sleep(poll_interval)
                status_result = await service.get_status(slug)
                status = status_result.get("status", "").lower()
                total_verified = status_result.get("total_verified")
                total_emails = status_result.get("total_emails")
                percentage = status_result.get("percentage", 0)
                
                # Log progress at INFO level periodically
                if poll_attempts - last_logged_attempt >= log_interval or poll_attempts == 0:
                    last_logged_attempt = poll_attempts
                
                if status == "completed":
                    break
                elif status not in ("verifying", "processing"):
                    break
                
                poll_attempts += 1
            
            if poll_attempts >= max_poll_attempts:
                await service.delete_list(slug)
                return valid_emails, batches_processed
            
            # Get results
            results = await service.get_results(slug)
            results_status = results.get("status", "unknown")
            
            # Download valid emails
            valid_email_file_url = results.get("valid_email_file")
            if valid_email_file_url:
                valid_emails = await service.download_valid_emails(valid_email_file_url)
            
            batches_processed = 1
            
        finally:
            # Clean up - delete the uploaded file
            try:
                delete_result = await service.delete_list(slug)
            except Exception as e:
                pass
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        raise
    
    return valid_emails, batches_processed


@router.post("/verifier/", response_model=EmailVerifierResponse)
async def start_email_verification(
    request: EmailVerifierRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailVerifierResponse:
    """
    Verify emails synchronously using direct email verification API.
    
    Generates random email combinations based on first name, last name, and domain,
    then verifies them through BulkMailVerifier direct email verification API 
    (/api/email/verify/) in batches. Returns verified results directly in the response.
    
    Args:
        request: EmailVerifierRequest with first_name, last_name, and domain/website
        current_user: Current authenticated user
        
    Returns:
        EmailVerifierResponse with verified email results
    """
    logger.debug(
        "Email verifier endpoint called",
        extra={
            "context": {
                "user_id": current_user.uuid if current_user else None,
                "first_name": request.first_name,
                "last_name": request.last_name,
                "domain": request.domain,
                "website": request.website
            }
        }
    )
    try:
        # Extract domain from website or domain parameter
        domain_input = request.domain or request.website
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        # Normalize domain
        domain_input = domain_input.strip()
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        
        # Validate first_name and last_name
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        
        if not first_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        
        if not last_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        
        # Get email_count from request (with default)
        email_count = request.email_count if request.email_count is not None else 1000
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        
        # Select provider
        provider = request.provider
        use_bmv = provider == EmailProvider.BULKMAILVERIFIER
        use_truelist = provider == EmailProvider.TRUELIST

        # Check if credentials are configured
        credentials_configured = (
            (use_bmv and settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD)
            or (use_truelist and settings.TRUELIST_API_KEY)
        )
        
        # Generate all unique email patterns once
        all_unique_emails = generate_email_combinations(
            first_name=first_name,
            last_name=last_name,
            domain=extracted_domain,
            count=email_count,
        )
        total_unique_patterns = len(all_unique_emails)
        
        if not credentials_configured:
            return EmailVerifierResponse(
                valid_emails=[],
                total_valid=0,
                generated_emails=all_unique_emails,
                total_generated=total_unique_patterns,
                total_batches_processed=0,
            )
        
        # Initialize provider service
        if use_bmv:
            service = BulkMailVerifierService()
        elif use_truelist:
            service = TruelistService()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        
        # Calculate number of batches needed
        total_batches = (total_unique_patterns + email_count - 1) // email_count
        
        all_valid_emails = []
        total_batches_processed = 0
        verification_error_occurred = False
        first_email = None
        first_email_status = None
        
        # Process all unique patterns in batches
        for batch_number in range(1, total_batches + 1):
            # Calculate batch slice
            start_idx = (batch_number - 1) * email_count
            end_idx = min(start_idx + email_count, total_unique_patterns)
            batch_emails = all_unique_emails[start_idx:end_idx]
            
            # Verify batch using direct API
            try:
                if use_truelist:
                    truelist_results = await service.verify_emails(batch_emails)
                    email_status_map = {
                        email.lower().strip(): EmailVerificationStatus(
                            truelist_results.get(email.lower().strip(), {}).get(
                                "mapped_status", EmailVerificationStatus.UNKNOWN
                            )
                        )
                        for email in batch_emails
                    }
                else:
                    email_status_map = await _verify_emails_batch_direct(
                        emails=batch_emails,
                        service=service,
                        batch_size=20,  # Process 20 emails concurrently per batch
                    )
                
                # Track first email found with valid, catchall, or risky status
                # Process emails in order to find the first one
                for email in batch_emails:
                    email_key = email.lower().strip()
                    email_status = email_status_map.get(email_key, EmailVerificationStatus.UNKNOWN)
                    
                    # If this is the first email with a meaningful status (valid, catchall)
                    # Note: "risky" from Truelist is already mapped to CATCHALL by TruelistService
                    if first_email is None and email_status in (
                        EmailVerificationStatus.VALID,
                        EmailVerificationStatus.CATCHALL,
                    ):
                        first_email = email  # Use original case from batch_emails
                        first_email_status = email_status
                        # Don't break here - continue to collect all valid emails
                        # But we'll stop processing more batches after this one
                
                # Extract valid emails from status map
                valid_emails = [
                    email for email, email_status in email_status_map.items()
                    if email_status == EmailVerificationStatus.VALID
                ]
                
                # Calculate batches processed (number of API batch calls made)
                batches_processed = (len(batch_emails) + 19) // 20  # ceil division for batch_size=20
                
                total_batches_processed += batches_processed
            except HTTPException as http_exc:
                # Handle HTTPException from verification (e.g., credentials not configured)
                if "credentials not configured" in str(http_exc.detail).lower():
                    verification_error_occurred = True
                    break
                else:
                    # Re-raise other HTTPExceptions
                    raise
            except Exception as batch_exc:
                # Log error but continue with next batch
                valid_emails = []
                batches_processed = 0
            
            if valid_emails:
                all_valid_emails.extend(valid_emails)
            
            # If we found first email (valid or catchall), we can stop
            if first_email is not None:
                break
        
        # Prepare response
        # If first_email is CATCHALL and provider is Truelist, try IcyPeas fallback
        icypeas_certainty: Optional[str] = None
        if first_email and first_email_status == EmailVerificationStatus.CATCHALL and use_truelist:
            try:
                icypeas_email, final_status, certainty = await handle_catchall_email(
                    first_name=first_name,
                    last_name=last_name,
                    domain=extracted_domain,
                    catchall_email=first_email,
                    catchall_status=first_email_status,
                )
                first_email = icypeas_email
                first_email_status = final_status
                icypeas_certainty = certainty
            except Exception:
                # On any IcyPeas error, keep original catchall
                pass

        response = EmailVerifierResponse(
            valid_emails=all_valid_emails,
            total_valid=len(all_valid_emails),
            first_email=first_email,
            first_email_status=first_email_status,
            generated_emails=all_unique_emails,
            total_generated=total_unique_patterns,
            total_batches_processed=total_batches_processed,
        )
        
        # Log activity for email verification
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain_input,
                    "email_count": email_count,
                },
                result_count=len(all_valid_emails),
                result_summary={
                    "valid_emails": len(all_valid_emails),
                    "total_generated": total_unique_patterns,
                    "total_batches_processed": total_batches_processed,
                },
                status=ActivityStatus.SUCCESS,
                request=http_request,
            )
        except Exception as log_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log email verification activity",
                log_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "success",
                },
            )
        
        return response
        
    except HTTPException as http_exc:
        # Log failed activity for HTTP exceptions
        try:
            # Use request object directly for logging
            domain_for_log = request.domain or request.website or ''
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "domain": domain_for_log,
                },
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(http_exc.detail) if hasattr(http_exc, 'detail') else str(http_exc),
                request=http_request,
            )
        except Exception as log_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log email verification activity (HTTP exception)",
                log_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "failed",
                    "http_status_code": http_exc.status_code if hasattr(http_exc, 'status_code') else None,
                },
            )
        raise
    except Exception as exc:
        
        # Log failed activity
        try:
            # Use request object directly for logging
            domain_for_log = request.domain or request.website or ''
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "domain": domain_for_log,
                },
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as log_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log email verification activity (exception)",
                log_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "failed",
                    "original_error": str(exc),
                },
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
        ) from exc


@router.post("/verifier/single/", response_model=SingleEmailVerifierFindResponse)
async def start_single_email_verification(
    request: EmailVerifierRequest,
    current_user: User = Depends(get_current_user),
) -> SingleEmailVerifierFindResponse:
    """
    Verify emails sequentially and return immediately when first VALID or CATCHALL email is found.
    
    Generates random email combinations based on first name, last name, and domain,
    then verifies them sequentially one at a time through email verification API. 
    Stops immediately when the first VALID or CATCHALL (risky) email is found and returns it.
    
    Args:
        request: EmailVerifierRequest with first_name, last_name, and domain/website
        current_user: Current authenticated user
        
    Returns:
        SingleEmailVerifierFindResponse with the first email found (valid or catchall) and its status, 
        or None if none found
    """
    try:
        # Extract domain from website or domain parameter
        domain_input = request.domain or request.website
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        
        # Normalize domain
        domain_input = domain_input.strip()
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        
        # Validate first_name and last_name
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        
        if not first_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        
        if not last_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        
        # Get email_count from request (with default)
        email_count = request.email_count if request.email_count is not None else 1000
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        
        provider = request.provider
        use_bmv = provider == EmailProvider.BULKMAILVERIFIER
        use_truelist = provider == EmailProvider.TRUELIST

        credentials_configured = (
            (use_bmv and settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD)
            or (use_truelist and settings.TRUELIST_API_KEY)
        )
        
        if not credentials_configured:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Email verifier credentials not configured for selected provider. "
                    "Please configure provider credentials."
                ),
            )
        # Initialize provider service
        if use_bmv:
            service = BulkMailVerifierService()
        elif use_truelist:
            service = TruelistService()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        
        # Generate all unique email patterns once at the start
        all_unique_emails = generate_email_combinations(
            first_name=first_name,
            last_name=last_name,
            domain=extracted_domain,
            count=email_count,
        )
        total_unique_patterns = len(all_unique_emails)
        
        if total_unique_patterns == 0:
            return SingleEmailVerifierFindResponse(valid_email=None, status=None)
        
        # Calculate number of batches needed
        total_batches = (total_unique_patterns + email_count - 1) // email_count
        
        # Track verified emails to prevent duplicates
        verified_emails_set = set()
        total_emails_checked = 0
        
        # Process emails in batches until we find a valid email or check all patterns
        for batch_number in range(1, total_batches + 1):
            # Calculate batch slice
            start_idx = (batch_number - 1) * email_count
            end_idx = min(start_idx + email_count, total_unique_patterns)
            batch_emails = all_unique_emails[start_idx:end_idx]
            
            # Filter out already verified emails
            batch_emails_to_check = [e for e in batch_emails if e not in verified_emails_set]
            skipped_count = len(batch_emails) - len(batch_emails_to_check)
            
            if not batch_emails_to_check:
                continue
            
            # Verify emails sequentially until first valid or catchall is found
            try:
                found_email, email_status, emails_checked = await _verify_emails_sequential_until_valid(
                    emails=batch_emails_to_check,
                    service=service,
                    verified_emails_set=verified_emails_set,
                )
                
                # Track verified emails
                verified_emails_set.update(batch_emails_to_check[:emails_checked])
                total_emails_checked += emails_checked
                
                if found_email:
                    # If Truelist and catchall, try IcyPeas fallback
                    if use_truelist and email_status == EmailVerificationStatus.CATCHALL:
                        try:
                            icypeas_email, final_status, certainty = await handle_catchall_email(
                                first_name=first_name,
                                last_name=last_name,
                                domain=extracted_domain,
                                catchall_email=found_email,
                                catchall_status=email_status,
                            )
                            found_email = icypeas_email
                            email_status = final_status
                        except Exception:
                            # On any IcyPeas error, keep original catchall
                            pass
                    
                    return SingleEmailVerifierFindResponse(valid_email=found_email, status=email_status)
                    
            except HTTPException as http_exc:
                # Handle HTTPException from verification (e.g., credentials not configured)
                if "credentials not configured" in str(http_exc.detail).lower():
                    raise
                else:
                    # Re-raise other HTTPExceptions
                    raise
            except Exception as batch_exc:
                # Log error but continue with next batch
                log_error(
                    "Email verification batch error (non-fatal, continuing)",
                    batch_exc,
                    "app.api.v3.endpoints.email",
                    context={
                        "user_id": current_user.uuid if current_user else None,
                        "batch_number": batch_number,
                        "emails_in_batch": len(batch_emails_to_check),
                        "failure_point": "batch_verification",
                    }
                )
                # Continue with next batch - don't fail entire operation for single batch failure
        
        # No valid or catchall email found after all patterns checked
        return SingleEmailVerifierFindResponse(valid_email=None, status=None)
        
    except HTTPException:
        raise
    except Exception as exc:
        log_error(
            "Email verification endpoint failed: unexpected error",
            exc,
            "app.api.v3.endpoints.email",
            context={
                "user_id": current_user.uuid if current_user else None,
                "first_name": request.first_name if request else None,
                "last_name": request.last_name if request else None,
                "domain": request.domain or request.website if request else None,
                "provider": request.provider if request else None,
                "failure_point": "endpoint_exception_handler",
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails. Please try again later.",
        ) from exc


async def _verify_emails_batch_direct(
    emails: list[str],
    service: BulkMailVerifierService,
    batch_size: int = 20,
) -> dict[str, EmailVerificationStatus]:
    """
    Verify a list of emails using direct API calls in batches.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        batch_size: Number of emails to process concurrently per batch
        
    Returns:
        Dictionary mapping email address to EmailVerificationStatus
    """
    email_status_map: dict[str, EmailVerificationStatus] = {}
    
    if not emails:
        return email_status_map
    
    # Initialize all emails as unknown (will be updated after verification)
    for email in emails:
        email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
    
    try:
        # Process emails in batches
        total_batches = (len(emails) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails))
            batch_emails = emails[start_idx:end_idx]
            
            # Create tasks for concurrent processing
            async def verify_email_task(email: str) -> tuple[str, EmailVerificationStatus]:
                """Verify a single email and return (email, status) tuple."""
                try:
                    result = await service.verify_single_email(email)
                    mapped_status = result.get("mapped_status", "unknown")
                    try:
                        status = EmailVerificationStatus(mapped_status)
                    except ValueError:
                        status = EmailVerificationStatus.UNKNOWN
                    return (email.lower().strip(), status)
                except Exception as e:
                    return (email.lower().strip(), EmailVerificationStatus.UNKNOWN)
            
            # Process batch concurrently
            tasks = [verify_email_task(email) for email in batch_emails]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update status map with results
            for result in results:
                if isinstance(result, Exception):
                    continue
                email_key, status = result
                email_status_map[email_key] = status
        
    except Exception as e:
        # Don't raise - return partial results
        pass
    
    return email_status_map


async def _get_email_from_activities(
    session: AsyncSession,
    user_id: str,
    first_name: str,
    last_name: str,
    domain: str,
) -> Optional[str]:
    """
    Get email from previous successful search in user_activities table.
    
    Args:
        session: Database session
        user_id: User ID
        first_name: First name
        last_name: Last name
        domain: Domain
        
    Returns:
        Email address if found in previous activity, None otherwise
    """
    try:
        activity = await activity_repo.find_previous_email_search(
            session=session,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
        )
        
        if activity and activity.result_summary:
            # Extract email from result_summary
            # Format: {"email": "user@example.com", "source": "verifier", "status": "valid"}
            email = activity.result_summary.get("email")
            if email and email.strip():
                return email.strip()
        
        return None
    except Exception:
        # If query fails, return None (don't block the main flow)
        return None


def detect_email_column(raw_headers: list[str]) -> Optional[str]:
    """
    Auto-detect email column from CSV headers.
    
    Searches for columns containing "email" (case-insensitive).
    Priority: exact "email" > columns containing "email"
    
    Args:
        raw_headers: List of CSV header names
        
    Returns:
        Column name if detected, None if not found or ambiguous
        
    Raises:
        ValueError: If multiple potential email columns found (ambiguous)
    """
    if not raw_headers:
        return None
    
    # Normalize headers for comparison (case-insensitive)
    normalized_headers = {h.lower(): h for h in raw_headers}
    
    # Priority 1: Exact match "email"
    if "email" in normalized_headers:
        return normalized_headers["email"]
    
    # Priority 2: Contains "email"
    email_matches = [
        h for h in raw_headers
        if "email" in h.lower()
    ]
    if len(email_matches) == 1:
        return email_matches[0]
    elif len(email_matches) > 1:
        raise ValueError(
            f"Multiple email columns found: {email_matches}. "
            "Please specify email_column explicitly."
        )
    
    return None


def _select_best_pattern_fallback(
    emails: list[str],
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Optional[str]:
    """
    Select the best email pattern for fallback when all verification results are invalid.
    
    Uses smart heuristics based on name characteristics:
    1. Very short first name (≤3 chars) → prefer first@domain
    2. Short last name (≤2 chars) → prefer first.last@domain
    3. Very long first (≥8) + very short last (≤3) → prefer first@domain (e.g., Sushant + Puri)
    4. Otherwise → default to first.last@domain (most common in corporate - ~70% of cases)
    
    Args:
        emails: List of email patterns (should be in order: first.last, firstlast, first, ...)
        first_name: First name for heuristic
        last_name: Last name for heuristic
        
    Returns:
        Selected email pattern or None if emails list is empty
    """
    if not emails:
        return None
    
    # Pattern indices: 0=first.last, 1=firstlast, 2=first
    if len(emails) >= 3:
        first_last_pattern = emails[0]  # first.last@domain
        firstlast_pattern = emails[1]   # firstlast@domain
        first_pattern = emails[2]       # first@domain
        
        first_name_len = len(first_name.strip()) if first_name else 0
        last_name_len = len(last_name.strip()) if last_name else 0
        
        # Heuristic priority:
        if first_name_len <= 3:
            # Very short first name - prefer first@domain
            return first_pattern
        elif last_name_len <= 2:
            # Short last name - prefer first.last@domain
            return first_last_pattern
        elif first_name_len >= 8 and last_name_len <= 3:
            # Very long first (≥8) + very short last (≤3) - prefer first@domain (e.g., Sushant + Puri)
            # More conservative to avoid regressions like mitchell+vaz, dharmesh+jain
            return first_pattern
        else:
            # Default: prefer first.last@domain (most common in corporate - ~70% of cases)
            return first_last_pattern
    elif len(emails) >= 2:
        first_name_len = len(first_name.strip()) if first_name else 0
        last_name_len = len(last_name.strip()) if last_name else 0
        
        if first_name_len <= 3:
            # Very short first name - prefer first@domain if available
            if len(emails) > 2:
                return emails[2]  # first
            else:
                return emails[0]  # first.last
        elif last_name_len <= 2:
            # Short last name - prefer first.last
            return emails[0]  # first.last
        elif first_name_len >= 8 and last_name_len <= 3 and len(emails) > 2:
            # Very long first (≥8) + very short last (≤3) - prefer first@domain if available
            # More conservative to avoid regressions
            return emails[2]  # first
        else:
            # Default: prefer first.last@domain
            return emails[0]  # first.last
    else:
        # Only one pattern - use it
        return emails[0]


async def _verify_emails_batch_truelist(
    emails: list[str],
    service: TruelistService,
    timeout: float = 0.5,  # OPTIMIZED: Reduced default from 5.0s to 0.5s for fast response
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> tuple[Optional[str], Optional[EmailVerificationStatus], int]:
    """
    Optimized batch verification for Truelist - verifies all emails in a single API call.
    
    Truelist supports up to 51 emails per API call via verify_emails().
    This function batches all emails and verifies them in one request.
    
    Args:
        emails: List of email addresses to verify (up to 51 recommended)
        service: TruelistService instance
        timeout: Maximum time to wait for verification (default: 1.5 seconds - optimized for speed)
        first_name: Optional first name for smart pattern prioritization in fallback scenarios
        last_name: Optional last name for smart pattern prioritization in fallback scenarios
        
    Returns:
        Tuple of (email: str | None, status: EmailVerificationStatus | None, emails_checked: int)
        - email: The first email found with valid or catchall status, or None
        - status: The verification status (VALID or CATCHALL), or None
        - emails_checked: Number of emails checked
    """
    if not emails:
        return None, None, 0
    
    try:
        # Use asyncio.wait_for to enforce timeout
        results = await asyncio.wait_for(
            service.verify_emails(emails),
            timeout=timeout
        )
        
        # Check results for first email with VALID or CATCHALL status
        # IMPORTANT: Check emails in priority order (Tier 1 -> Tier 2 -> Tier 3)
        # to ensure we return the most common pattern first
        
        valid_emails = []
        catchall_emails = []
        
        # First pass: Check all emails in priority order (preserves Tier 1 -> Tier 2 -> Tier 3)
        # Store tuples of (email, status, index) to prioritize by pattern order for determinism
        for idx, email in enumerate(emails):
            email_key = email.lower().strip()
            if email_key in results:
                result = results[email_key]
                mapped_status = result.get("mapped_status", "unknown")

                try:
                    status = EmailVerificationStatus(mapped_status)
                    # Collect VALID emails first (highest priority)
                    if status == EmailVerificationStatus.VALID:
                        valid_emails.append((email_key, status, idx))  # Include index for deterministic sorting
                    # Collect CATCHALL emails as fallback
                    elif status == EmailVerificationStatus.CATCHALL:
                        catchall_emails.append((email_key, status, idx))  # Include index for deterministic sorting
                except ValueError:
                    pass
        
        # Sort by pattern index for deterministic results (TrueList API is non-deterministic)
        # Pattern 0 (first.last@domain) is most common and should always be preferred
        # when multiple emails have the same verification status
        valid_emails.sort(key=lambda x: x[2])  # Sort by index (3rd element)
        catchall_emails.sort(key=lambda x: x[2])  # Sort by index (3rd element)
        
        # Return first VALID email (highest priority), or first CATCHALL if no VALID found
        # Now deterministic: pattern 0 (first.last@domain) always wins when tied
        if valid_emails:
            return valid_emails[0][0], valid_emails[0][1], len(emails)
        elif catchall_emails:
            return catchall_emails[0][0], catchall_emails[0][1], len(emails)
        
        # No valid or catchall emails found - return None (no email found)
        # Do NOT return pattern_fallback with unverified emails
        # User requirement: API should only return valid, catchall, or no email found
        return None, None, len(emails)
    except asyncio.TimeoutError:
        # OPTIMIZATION: Return emails_checked as len(emails) to indicate all were attempted but timed out
        # This allows pattern fallback to be used immediately
        return None, None, len(emails)
    except Exception as exc:
        # Return emails_checked as len(emails) to indicate all were attempted but failed
        return None, None, len(emails)


async def _verify_emails_concurrent_until_valid(
    emails: list[str],
    service: BulkMailVerifierService,
    verified_emails_set: Optional[set[str]] = None,
    max_concurrent: int = 5,
) -> tuple[Optional[str], Optional[EmailVerificationStatus], int]:
    """
    Verify emails concurrently until the first VALID or CATCHALL email is found.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        verified_emails_set: Optional set to track verified emails (will be updated in-place)
        max_concurrent: Maximum number of concurrent verifications (default: 5)
        
    Returns:
        Tuple of (email: str | None, status: EmailVerificationStatus | None, emails_checked: int)
        - email: The first email found with valid or catchall status, or None if none found
        - status: The verification status (VALID or CATCHALL), or None
        - emails_checked: Number of emails verified before stopping
    """
    if not emails:
        return None, None, 0
    
    if verified_emails_set is None:
        verified_emails_set = set()
    
    emails_checked = 0
    first_email_found = None
    first_email_status = None
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def verify_single(email: str) -> tuple[str, Optional[EmailVerificationStatus]]:
        """Verify a single email and return (email, status)."""
        nonlocal emails_checked, first_email_found, first_email_status
        if email in verified_emails_set or first_email_found:
            return email, None
        
        async with semaphore:
            if first_email_found:  # Check again after acquiring semaphore
                return email, None
            
            emails_checked += 1
            try:
                result = await service.verify_single_email(email)
                mapped_status = result.get("mapped_status", "unknown")
                verified_emails_set.add(email)
                
                try:
                    status = EmailVerificationStatus(mapped_status)
                except ValueError:
                    status = EmailVerificationStatus.UNKNOWN
                
                # Track first email with VALID or CATCHALL status
                if status in (EmailVerificationStatus.VALID, EmailVerificationStatus.CATCHALL):
                    if not first_email_found:  # First email with meaningful status found
                        first_email_found = email.lower().strip()
                        first_email_status = status
                    return email, status
                
                return email, None
            except Exception as e:
                verified_emails_set.add(email)
                return email, None
    
    try:
        # Create tasks for all emails
        filtered_emails = [email for email in emails if email not in verified_emails_set]
        tasks = [asyncio.create_task(verify_single(email)) for email in filtered_emails]
        
        # Wait for first email with VALID or CATCHALL status or all tasks complete
        for task in asyncio.as_completed(tasks):
            email, status = await task
            if status in (EmailVerificationStatus.VALID, EmailVerificationStatus.CATCHALL) and first_email_found:
                # Cancel remaining tasks
                remaining = [t for t in tasks if not t.done()]
                for t in remaining:
                    t.cancel()
                # Wait a bit for cancellations
                await asyncio.sleep(0.1)
                break
        
        return first_email_found, first_email_status, emails_checked
        
    except Exception as e:
        return first_email_found, first_email_status, emails_checked


async def _verify_emails_sequential_until_valid(
    emails: list[str],
    service: BulkMailVerifierService,
    verified_emails_set: Optional[set[str]] = None,
) -> tuple[Optional[str], Optional[EmailVerificationStatus], int]:
    """
    Verify emails sequentially until the first VALID or CATCHALL email is found.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        verified_emails_set: Optional set to track verified emails (will be updated in-place)
        
    Returns:
        Tuple of (email: str | None, status: EmailVerificationStatus | None, emails_checked: int)
        - email: The first email found with valid or catchall status, or None if none found
        - status: The verification status of the email (VALID or CATCHALL), or None
        - emails_checked: Number of emails verified before stopping
    """
    if not emails:
        return None, None, 0
    
    if verified_emails_set is None:
        verified_emails_set = set()
    
    emails_checked = 0
    
    try:
        for email in emails:
            # Skip if already verified
            if email in verified_emails_set:
                continue
            
            emails_checked += 1
            
            try:
                result = await service.verify_single_email(email)
                mapped_status = result.get("mapped_status", "unknown")
                
                # Add to verified set
                verified_emails_set.add(email)
                
                try:
                    status = EmailVerificationStatus(mapped_status)
                except ValueError:
                    status = EmailVerificationStatus.UNKNOWN
                
                # Return first email with VALID or CATCHALL status
                if status in (EmailVerificationStatus.VALID, EmailVerificationStatus.CATCHALL):
                    return email.lower().strip(), status, emails_checked
                
            except Exception as e:
                # Still add to verified set to avoid retrying failed emails
                verified_emails_set.add(email)
                # Continue to next email on error
                continue
        
        return None, None, emails_checked
        
    except Exception as e:
        # Return partial results
        return None, None, emails_checked


async def _verify_emails_with_status(
    emails: list[str],
    service: BulkMailVerifierService,
) -> dict[str, EmailVerificationStatus]:
    """
    Verify a list of emails and return a mapping of email -> verification status.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        
    Returns:
        Dictionary mapping email address to EmailVerificationStatus
    """
    email_status_map: dict[str, EmailVerificationStatus] = {}
    
    if not emails:
        return email_status_map
    
    # Initialize all emails as unknown (will be updated after verification)
    for email in emails:
        email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
    
    try:
        # Upload file
        try:
            upload_result = await service.upload_file(emails)
        except HTTPException as http_exc:
            if "credentials not configured" in str(http_exc.detail).lower():
                # Mark all as unknown
                for email in emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
                return email_status_map
            else:
                raise
        
        slug = upload_result.get("slug")
        if not slug:
            return email_status_map
        
        try:
            # Start verification
            await service.start_verification(slug)
            
            # Poll for status until completed
            max_poll_attempts = 300  # 5 minutes max
            poll_interval = 10  # Poll every 10 seconds
            poll_attempts = 0
            
            while poll_attempts < max_poll_attempts:
                await asyncio.sleep(poll_interval)
                status_result = await service.get_status(slug)
                status = status_result.get("status", "").lower()
                
                if status == "completed":
                    break
                elif status not in ("verifying", "processing"):
                    break
                
                poll_attempts += 1
            
            if poll_attempts >= max_poll_attempts:
                await service.delete_list(slug)
                return email_status_map
            
            # Get results
            results = await service.get_results(slug)
            
            # Download all result files and map emails to status
            valid_email_file_url = results.get("valid_email_file")
            invalid_email_file_url = results.get("invalid_email_file")
            catchall_email_file_url = results.get("catchall_email_file")
            unknown_email_file_url = results.get("unknown_email_file")
            
            # Download valid emails
            if valid_email_file_url and valid_email_file_url.strip():
                valid_emails = await service.download_valid_emails(valid_email_file_url)
                for email in valid_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.VALID
            
            # Download invalid emails
            if invalid_email_file_url and invalid_email_file_url.strip():
                invalid_emails = await service.download_invalid_emails(invalid_email_file_url)
                for email in invalid_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.INVALID
            
            # Download catchall emails
            if catchall_email_file_url and catchall_email_file_url.strip():
                catchall_emails = await service.download_catchall_emails(catchall_email_file_url)
                for email in catchall_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.CATCHALL
            
            # Download unknown emails
            if unknown_email_file_url and unknown_email_file_url.strip():
                unknown_emails = await service.download_unknown_emails(unknown_email_file_url)
                for email in unknown_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
            
        finally:
            # Clean up - delete the uploaded file
            try:
                await service.delete_list(slug)
            except Exception as e:
                pass
        
    except Exception as e:
        raise
    
    return email_status_map


@router.post("/bulk/verifier/", response_model=BulkEmailVerifierResponse)
async def bulk_email_verifier(
    request: BulkEmailVerifierRequest,
    current_user: User = Depends(get_current_user),
    http_request: Request = None,
    session: AsyncSession = Depends(get_db),
) -> BulkEmailVerifierResponse:
    """
    Verify multiple email addresses through BulkMailVerifier service.
    
    Accepts a list of email addresses and returns verification status for each email
    (valid, invalid, catchall, unknown).
    
    Supports CSV context preservation: if raw_headers and rows are provided,
    the endpoint will preserve original CSV columns while adding verification status
    and generate a downloadable CSV file.
    
    Args:
        request: BulkEmailVerifierRequest with list of emails and optional CSV context
        current_user: Current authenticated user
        
    Returns:
        BulkEmailVerifierResponse with verification results for each email.
        If CSV context provided, also includes download_url, export_id, and expires_at.
    """
    try:
        # Handle CSV context: extract emails from CSV rows if provided
        emails_to_verify = request.emails
        email_column = request.email_column
        emails_data = []  # Store email with CSV row mapping
        
        # If CSV context is provided, extract emails from rows
        if request.rows is not None and request.raw_headers is not None:
            # Auto-detect email column if not explicitly provided
            if not email_column:
                try:
                    email_column = detect_email_column(request.raw_headers)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e),
                    ) from e
            
            if not email_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not detect email column. Please provide email_column.",
                )
            
            # Extract emails from CSV rows
            extracted_emails = []
            for idx, row in enumerate(request.rows):
                email_value = row.get(email_column)
                if email_value and isinstance(email_value, str) and email_value.strip():
                    extracted_email = email_value.strip().lower()
                    extracted_emails.append(extracted_email)
                    emails_data.append({
                        "email": extracted_email,
                        "raw_row": row,
                        "original_email": email_value.strip(),  # Preserve original case
                    })
                elif idx < len(request.emails):
                    # Fallback to request.emails if row doesn't have email
                    emails_data.append({
                        "email": request.emails[idx].lower().strip(),
                        "raw_row": row,
                        "original_email": request.emails[idx],
                    })
            
            # Use extracted emails if found, otherwise use request.emails and match with rows
            if extracted_emails:
                emails_to_verify = extracted_emails
            else:
                # If no emails extracted from rows, use request.emails and match with rows
                for idx, email in enumerate(request.emails):
                    email_data = {
                        "email": email.lower().strip(),
                        "original_email": email,
                    }
                    if idx < len(request.rows):
                        email_data["raw_row"] = request.rows[idx]
                    emails_data.append(email_data)
        else:
            # No CSV context: create simple email data
            for email in request.emails:
                emails_data.append({
                    "email": email.lower().strip(),
                    "original_email": email,
                })
        
        provider = request.provider
        use_bmv = provider == EmailProvider.BULKMAILVERIFIER
        use_truelist = provider == EmailProvider.TRUELIST

        if use_bmv and (not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        if use_truelist and not settings.TRUELIST_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Truelist API key not configured. Please set TRUELIST_API_KEY.",
            )
        
        if use_bmv:
            service = BulkMailVerifierService()
            email_status_map = await _verify_emails_batch_direct(
                emails=emails_to_verify,
                service=service,
                batch_size=20,  # Process 20 emails concurrently per batch
            )
        elif use_truelist:
            service = TruelistService()
            truelist_results = await service.verify_emails(emails_to_verify)
            email_status_map = {
                email.lower().strip(): EmailVerificationStatus(
                    truelist_results.get(email.lower().strip(), {}).get(
                        "mapped_status", EmailVerificationStatus.UNKNOWN
                    )
                )
                for email in emails_to_verify
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        
        # Optional: IcyPeas fallback for catchall emails (Truelist only)
        if use_truelist:
            # Identify catchall emails
            catchall_emails = [
                email for email, status in email_status_map.items()
                if status == EmailVerificationStatus.CATCHALL
            ]
            # Process a limited number concurrently to avoid heavy load
            icypeas_tasks = []
            for email in catchall_emails[:10]:
                icypeas_tasks.append(
                    handle_catchall_email(
                        first_name="",  # First/last not available in bulk; domain only
                        last_name="",
                        domain=email.split("@", 1)[1] if "@" in email else "",
                        catchall_email=email,
                        catchall_status=EmailVerificationStatus.CATCHALL,
                    )
                )
            if icypeas_tasks:
                try:
                    icypeas_results = await asyncio.gather(*icypeas_tasks, return_exceptions=True)
                    for original_email, result in zip(catchall_emails[:10], icypeas_results):
                        if isinstance(result, Exception) or not result:
                            continue
                        icypeas_email, final_status, certainty = result
                        # Only update status map if we got a non-empty email
                        if icypeas_email and final_status == EmailVerificationStatus.VALID:
                            # For simplicity, keep the original key but treat as VALID
                            email_status_map[original_email] = EmailVerificationStatus.VALID
                except Exception:
                    # On any bulk IcyPeas error, keep original catchall statuses
                    pass

        # Build results list
        results = []
        valid_count = 0
        invalid_count = 0
        catchall_count = 0
        unknown_count = 0
        
        for email_data in emails_data:
            email = email_data["email"]
            original_email = email_data.get("original_email", email)
            verification_status = email_status_map.get(email, EmailVerificationStatus.UNKNOWN)
            
            results.append(VerifiedEmailResult(email=original_email, status=verification_status))
            
            if verification_status == EmailVerificationStatus.VALID:
                valid_count += 1
            elif verification_status == EmailVerificationStatus.INVALID:
                invalid_count += 1
            elif verification_status == EmailVerificationStatus.CATCHALL:
                catchall_count += 1
            else:
                unknown_count += 1
        
        # Handle CSV generation if CSV context provided
        download_url = None
        export_id = None
        expires_at = None
        
        if request.rows is not None and request.raw_headers is not None:
            # Merge verification results with CSV rows
            csv_rows = []
            for email_data in emails_data:
                email = email_data["email"]
                original_email = email_data.get("original_email", email)
                raw_row = email_data.get("raw_row", {})
                verification_status = email_status_map.get(email, EmailVerificationStatus.UNKNOWN)
                
                # Start with original CSV row
                row_for_csv: dict[str, Any] = {}
                if raw_row:
                    row_for_csv.update(raw_row)
                
                # Add/override verification_status column
                row_for_csv["verification_status"] = verification_status.value
                
                csv_rows.append(row_for_csv)
            
            # Create export record
            export = await export_service.create_export(
                session,
                current_user.uuid,
                ExportType.emails,  # Using emails type for bulk verifier exports
                contact_uuids=[],
                company_uuids=[],
            )
            
            # Store CSV context in export record
            verifier_data_json = json.dumps(
                {
                    "emails_data": emails_data,
                    "mapping": request.mapping,
                    "raw_headers": request.raw_headers,
                    "rows": request.rows,
                    "email_column": email_column,
                }
            )
            export.email_contacts_json = verifier_data_json
            export.contact_count = len(emails_data)
            export.total_records = len(emails_data)
            await session.flush()
            
            # Generate CSV file
            csv_headers = list(request.raw_headers)
            if "verification_status" not in csv_headers:
                csv_headers.append("verification_status")
            
            file_path = await export_service.generate_bulk_verifier_csv(
                session,
                export.export_id,
                csv_rows,
                csv_headers,
            )
            
            # Update export with file path
            export.file_path = file_path
            export.status = ExportStatus.completed
            await session.flush()
            
            # Generate signed download URL
            expires_at = export.created_at + timedelta(hours=24)
            download_token = generate_signed_url(export.export_id, current_user.uuid, expires_at)
            base_url = settings.BASE_URL.rstrip("/")
            download_url = f"{base_url}/api/v2/exports/{export.export_id}/download?token={download_token}"
            export_id = export.export_id
        
        response = BulkEmailVerifierResponse(
            results=results,
            total=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            catchall_count=catchall_count,
            unknown_count=unknown_count,
            download_url=download_url,
            export_id=export_id,
            expires_at=expires_at,
        )
        
        # Log activity (don't fail verification if activity logging fails)
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={"email_count": len(request.emails)},
                result_count=len(results),
                result_summary={
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "catchall": catchall_count,
                    "unknown": unknown_count,
                },
                status=ActivityStatus.SUCCESS,
                request=http_request,
            )
        except Exception as activity_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log bulk email verification activity",
                activity_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "success",
                    "email_count": len(request.emails),
                },
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        
        # Log failed activity
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={"email_count": len(request.emails)},
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as activity_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log bulk email verification activity (exception)",
                activity_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "failed",
                    "email_count": len(request.emails),
                    "original_error": str(exc),
                },
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
        ) from exc


@router.post("/single/verifier/", response_model=SingleEmailVerifierResponse)
async def single_email_verifier(
    request: SingleEmailVerifierRequest,
    current_user: User = Depends(get_current_user),
    http_request: Request = None,
    session: AsyncSession = Depends(get_db),
) -> SingleEmailVerifierResponse:
    """
    Verify a single email address through email verification service.
    
    Accepts a single email address and returns its verification status
    (valid, invalid, catchall, unknown).
    
    When using Truelist provider, the response includes additional fields:
    - email_state: The email state from Truelist (e.g., 'ok', 'risky', 'invalid')
    - email_sub_state: The email sub-state (e.g., 'accept_all', 'disposable', 'role')
    - domain: Domain extracted from email
    - canonical: Canonical email format
    - mx_record: MX record information
    - verified_at: Timestamp when email was verified
    - did_you_mean: Suggested email correction
    
    Args:
        request: SingleEmailVerifierRequest with single email and provider
        current_user: Current authenticated user
        
    Returns:
        SingleEmailVerifierResponse with verification result for the email.
        Includes Truelist-specific fields when using Truelist provider.
    """
    logger.debug(
        "Single email verifier endpoint called",
        extra={
            "context": {
                "user_id": current_user.uuid if current_user else None,
                "email": request.email,
                "provider": request.provider.value if request.provider else None
            }
        }
    )
    try:
        provider = request.provider
        use_bmv = provider == EmailProvider.BULKMAILVERIFIER
        use_truelist = provider == EmailProvider.TRUELIST

        if use_bmv and (not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        if use_truelist and not settings.TRUELIST_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Truelist API key not configured. Please set TRUELIST_API_KEY.",
            )
        
        if use_bmv:
            service = BulkMailVerifierService()
            result = await service.verify_single_email(request.email)
            # Map the result status to EmailVerificationStatus enum
            mapped_status = result.get("mapped_status", "unknown")
            try:
                verification_status = EmailVerificationStatus(mapped_status)
            except ValueError:
                verification_status = EmailVerificationStatus.UNKNOWN
            
            response = SingleEmailVerifierResponse(
                result=VerifiedEmailResult(email=request.email, status=verification_status),
            )
        elif use_truelist:
            service = TruelistService()
            result = await service.verify_single_email(request.email)
            # Map the result status to EmailVerificationStatus enum
            mapped_status = result.get("mapped_status", "unknown")
            try:
                verification_status = EmailVerificationStatus(mapped_status)
            except ValueError:
                verification_status = EmailVerificationStatus.UNKNOWN
            
                # Extract Truelist-specific fields from the result
            response = SingleEmailVerifierResponse(
                    result=VerifiedEmailResult(
                        email=request.email,
                        status=verification_status,
                        email_state=result.get("email_state"),
                        email_sub_state=result.get("email_sub_state"),
                        domain=result.get("domain"),
                        canonical=result.get("canonical"),
                        mx_record=result.get("mx_record"),
                        verified_at=result.get("verified_at"),
                        did_you_mean=result.get("did_you_mean"),
                    ),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
        )
        
        # Log activity (don't fail verification if activity logging fails)
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={"email": request.email},
                result_count=1,
                result_summary={"status": verification_status.value},
                status=ActivityStatus.SUCCESS,
                request=http_request,
            )
        except Exception as activity_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log single email verification activity",
                activity_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "success",
                    "email": request.email,
                    "provider": request.provider.value if request.provider else None,
                },
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        # Log error with full context
        log_error(
            "Error in single email verifier endpoint",
            exc,
            "app.api.v3.endpoints.email",
            context={
                "endpoint": "/email/single/verifier/",
                "email": request.email,
                "provider": request.provider.value if request.provider else None,
                "user_id": current_user.uuid if current_user else None,
            },
        )
        
        # Log failed activity
        try:
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={"email": request.email},
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as activity_exc:
            logger.warning(
                "Failed to log activity for single email verifier error",
                extra={"context": {"original_error": str(exc), "log_error": str(activity_exc)}}
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from exc


@router.get("/bulk/download/{file_type}/{slug}/")
async def download_result_file(
    file_type: str = Path(
        ...,
        description="Type of file to download: valid, invalid, c-all, or unknown",
    ),
    slug: str = Path(..., description="Slug identifier for the list"),
    provider: EmailProvider = Query(..., description="Email verification provider"),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Download a result file from BulkMailVerifier.
    
    Downloads a CSV file containing verification results for a specific list.
    The file_type parameter determines which results to download:
    - valid: Valid email addresses
    - invalid: Invalid email addresses
    - c-all: Catchall email addresses
    - unknown: Unknown email addresses
    
    Args:
        file_type: Type of file to download (valid, invalid, c-all, unknown)
        slug: Slug identifier for the list
        current_user: Current authenticated user
        
    Returns:
        CSV file as text/csv response
    """
    try:
        if provider == EmailProvider.BULKMAILVERIFIER:
            if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "BulkMailVerifier credentials not configured. "
                        "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                    ),
                )
            service = BulkMailVerifierService()
            csv_content = await service.download_result_file(file_type=file_type, slug=slug)
        elif provider == EmailProvider.TRUELIST:
            if not settings.TRUELIST_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Truelist API key not configured. Please set TRUELIST_API_KEY.",
                )
            # For Truelist, slug represents a batch id; decide which URL to fetch.
            service = TruelistService()
            batch = await service.get_batch(slug)
            # Default to annotated CSV if available, else highest_reach_csv_url, else safest_bet_csv_url
            csv_url = batch.get("annotated_csv_url") or batch.get("highest_reach_csv_url") or batch.get("safest_bet_csv_url")
            if not csv_url:
                log_api_error(
                    endpoint=f"/api/v3/email/bulk/download/{file_type}/{slug}/",
                    method="GET",
                    status_code=404,
                    error_type="NotFoundException",
                    error_message=f"No downloadable CSV available for batch: {slug}",
                    user_id=str(current_user.uuid),
                    context={"file_type": file_type, "slug": slug, "provider": provider.value}
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No downloadable CSV available for this batch",
                )
            csv_content = await service.download_csv(csv_url)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        # Return CSV file as response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{file_type}_{slug}.csv"',
            },
        )
        
    except HTTPException as exc:
        if exc.status_code == 404:
            log_api_error(
                endpoint=f"/api/v3/email/bulk/download/{file_type}/{slug}/",
                method="GET",
                status_code=404,
                error_type="NotFoundException",
                error_message=str(exc.detail),
                user_id=str(current_user.uuid),
                context={"file_type": file_type, "slug": slug, "provider": provider.value}
            )
        raise
    except Exception as exc:
        # error=%s
        error_msg = str(exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        ) from exc


@router.post("/export", response_model=EmailExportResponse, status_code=status.HTTP_201_CREATED)
async def export_emails(
    background_tasks: BackgroundTasks,
    request: EmailExportRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailExportResponse:
    """
    Export emails for a list of contacts to CSV.
    
    Creates an export job that processes a list of contacts and attempts to find their email addresses by:
    1. First trying to find emails in the database using the email finder service
    2. If not found, trying email verification using the single email verifier
    3. If still not found, leaving email empty
    
    Returns export metadata with download_url. The CSV file is generated asynchronously and available via download_url once processing completes.
    
    Args:
        request: EmailExportRequest with list of contacts
        current_user: Current authenticated user
        session: Database session
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        EmailExportResponse with export_id, download_url, expires_at, contact_count, company_count, and status
    """
    if not request.contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one contact is required",
        )
    
    try:
        # Serialize contacts to JSON for storage
        contacts_data = []
        for idx, contact in enumerate(request.contacts):
            contact_payload: dict[str, Any] = {
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "domain": contact.domain,
                "website": contact.website,
            }
            # Include optional existing email from the request, if present
            if getattr(contact, "email", None):
                contact_payload["email"] = contact.email

            # Attach raw CSV context when available
            if request.rows is not None and idx < len(request.rows):
                contact_payload["raw_row"] = request.rows[idx]
            if request.raw_headers is not None:
                contact_payload["raw_headers"] = request.raw_headers
            if request.contact_field_mappings is not None:
                contact_payload["contact_field_mappings"] = request.contact_field_mappings
            if request.company_field_mappings is not None:
                contact_payload["company_field_mappings"] = request.company_field_mappings

            contacts_data.append(contact_payload)

        # Persist full CSV context (normalized contacts + optional raw context) on the export
        contacts_json = json.dumps(
            {
                "contacts": contacts_data,
                "mapping": request.mapping,
                "raw_headers": request.raw_headers,
                "rows": request.rows,
                "contact_field_mappings": request.contact_field_mappings,
                "company_field_mappings": request.company_field_mappings,
            }
        )
        
        # Create export record with status "pending"
        export = await export_service.create_export(
            session,
            current_user.uuid,
            ExportType.emails,
            contact_uuids=[],  # No contact UUIDs for email exports
            company_uuids=[],
        )
        
        # Store email contacts JSON data
        export.email_contacts_json = contacts_json
        export.contact_count = len(request.contacts)
        export.total_records = len(request.contacts)
        # Flush to persist changes without committing (transaction managed by get_db())
        await session.flush()
        
        # Log export activity
        activity_id = await activity_service.log_export_activity(
            session=session,
            user_id=current_user.uuid,
            service_type=ActivityServiceType.EMAIL,
            request_params={
                "email_count": len(request.contacts),
            },
            export_id=export.export_id,
            result_count=0,  # Will be updated when export completes
            status=ActivityStatus.SUCCESS,
            request=http_request,
        )
        
        
        # Enqueue background task with activity_id for updating
        # Note: This is a long-running task that might be better suited for Celery in the future
        add_background_task_safe(
            background_tasks,
            process_email_export,
            export.export_id,
            contacts_data,
            activity_id,
            track_status=True,
            cpu_bound=False,  # I/O-bound task (database and file operations)
        )
        
        # Deduct credits for FreeUser and ProUser (after export is queued successfully)
        # Deduct 1 credit per contact
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = len(request.contacts)
                    new_balance = await credit_service.deduct_credits(
                        session, current_user.uuid, amount=credit_amount
                    )
        except Exception as credit_exc:
            pass
        
        # Set expiration to 24 hours from creation
        expires_at = export.created_at + timedelta(hours=24)
        
        # Generate initial download URL with signed token
        download_token = generate_signed_url(export.export_id, current_user.uuid, expires_at)
        base_url = settings.BASE_URL.rstrip("/")
        download_url = f"{base_url}/api/v2/exports/{export.export_id}/download?token={download_token}"
        
        return EmailExportResponse(
            export_id=export.export_id,
            download_url=download_url,
            expires_at=expires_at,
            contact_count=len(request.contacts),
            company_count=0,
            status=export.status,
        )
            
    except HTTPException:
        raise
    except Exception as exc:
        # Log failed activity
        try:
            await activity_service.log_export_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "email_count": len(request.contacts) if hasattr(request, 'contacts') else 0,
                },
                export_id="",  # No export_id if creation failed
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as log_exc:
            # Log activity logging failure without failing the main operation
            log_error(
                "Failed to log email export activity (exception)",
                log_exc,
                "app.api.v3.endpoints.email",
                context={
                    "user_id": current_user.uuid,
                    "service_type": "email",
                    "operation": "log_activity",
                    "activity_status": "failed",
                    "original_error": str(exc),
                },
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.post("/single/", response_model=SingleEmailResponse)
async def get_single_email(
    request: SingleEmailRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SingleEmailResponse:
    """
    Get a single email address for a contact using two-step approach.
    
    Attempts to find an email address for a single contact by:
    1. First trying to find emails in the database using the email finder service
    2. If not found, trying email verification using the single email verifier
    3. If verifier marks all patterns as invalid, returns best-guess pattern (pattern_fallback)
    4. If still not found, returns None
    
    When email is found via verifier, the response includes the verification status.
    If the email has status "catchall" (risky from Truelist), it is still returned.
    
    Pattern Fallback: When Truelist marks all email patterns as invalid/unknown, the API
    returns the first Tier-1 pattern (most common format) as a best-guess with source="pattern_fallback"
    and status=None. This helps when Truelist's strict verification incorrectly marks valid emails.
    
    Args:
        request: SingleEmailRequest with first_name, last_name, and domain/website
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        SingleEmailResponse with email address, source, and status (when found via verifier).
        - source="verifier": Email verified as valid/catchall, status indicates verification result
        - source="pattern_fallback": Best-guess pattern when all verifications failed, status=None
        - source="cache": Cached result, status=None
        - source=None: No email found
    """
    try:
        # Normalize inputs
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        domain_input = request.domain or request.website
        
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        
        domain_input = domain_input.strip()
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        
        # Check user_activities for previous successful search
        cached_email = await _get_email_from_activities(
            session=session,
            user_id=current_user.uuid,
            first_name=first_name,
            last_name=last_name,
            domain=extracted_domain,
        )
        
        if cached_email:
            return SingleEmailResponse(email=cached_email, source="user_activities", status=None)
        
        # Initialize services
        email_finder_service = EmailFinderService()
        provider = request.provider
        bulk_verifier_service = None
        use_truelist = provider == EmailProvider.TRUELIST
        if provider == EmailProvider.BULKMAILVERIFIER:
            if settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD:
                bulk_verifier_service = BulkMailVerifierService()
        elif use_truelist:
            if settings.TRUELIST_API_KEY:
                bulk_verifier_service = TruelistService()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        
        email_found = None
        source = None
        
        # Step 1: Skip database query (optimization - always times out ~2.4s)
        # Database finder consistently times out causing 2.4s delay, skip for speed
        
        # Step 1.5: OPTIMIZED - Skip IcyPeas for speed (was taking 1-4s). Go directly to Truelist verification.
        # IcyPeas polling with 5 attempts and exponential backoff was causing significant delays.
        # Optimization: Skip IcyPeas entirely to reduce latency from ~5.77s to <2s
        
        # Step 2: Email verification with Truelist (RE-ENABLED for accuracy)
        if not email_found and bulk_verifier_service:
            # Generate email patterns (increased from 5 to 10 for better coverage)
            all_emails = generate_email_combinations(
                first_name=first_name,
                last_name=last_name,
                domain=extracted_domain,
                count=10,
            )
        
        # Step 2.5: Run actual verification with Truelist
        if not email_found and bulk_verifier_service:
            try:
                if all_emails:
                    # Wrap verification step in timeout
                    async def _verification_work():
                        # Track verified emails to prevent duplicates
                        verified_emails_set = set()
                        
                        # Use optimized batch verification for Truelist (single API call for up to 51 emails)
                        if use_truelist and isinstance(bulk_verifier_service, TruelistService):
                            found_email, email_status, emails_checked = await _verify_emails_batch_truelist(
                                emails=all_emails,
                                service=bulk_verifier_service,
                                timeout=2.0,  # Increased from 0.5s to 2.0s for reliable verification
                                first_name=first_name,
                                last_name=last_name,
                            )
                        else:
                            # Use concurrent verification for other providers
                            max_concurrent = 5
                            found_email, email_status, emails_checked = await _verify_emails_concurrent_until_valid(
                                emails=all_emails,
                                service=bulk_verifier_service,
                                verified_emails_set=verified_emails_set,
                                max_concurrent=max_concurrent,
                            )
                        
                        if found_email:
                            return found_email, email_status, emails_checked
                        # No verified email found - return None (no email found)
                        # Do NOT use pattern_fallback for unverified emails
                        # API only returns valid, catchall, or no email found
                        return None, None, emails_checked
                    
                    # Execute verification with timeout
                    email_status = None
                    found_email = None
                    found_status = None
                    emails_checked = 0
                    try:
                        found_email, found_status, emails_checked = await asyncio.wait_for(
                            _verification_work(),
                            timeout=3.0  # Increased from 0.8s to 3.0s for reliable verification
                        )
                        
                        if found_email:
                            email_found = found_email
                            email_status = found_status
                            # Determine source based on status
                            if email_status is None:
                                # This shouldn't happen with the fix, but keep for safety
                                source = "pattern_fallback"
                            else:
                                source = "verifier"
                            
                            # Store in cache for future requests (only if email is verified as valid/catchall)
                            if email_found and email_status is not None:
                                _store_in_cache(cache_key, email_found)
                            
                            # Skip IcyPeas fallback for speed optimization (saves ~3.4s)
                            # Keep catchall as-is (don't convert to valid) for accurate status reporting
                            
                            # Optimization: Skip activity logging in the critical path to avoid 1.9s blocking DB operation
                            # Activity logging can be re-enabled via background tasks if needed for analytics
                    except asyncio.TimeoutError:
                        # Verification timeout exceeded - return None (no email found)
                        found_email = None
                        found_status = None
                        emails_checked = 0
                
            except HTTPException as verifier_exc:
                # Don't return fallback on errors - let it return None for accurate reporting
                pass  # Continue if verifier fails
            except Exception as verifier_exc:
                pass  # Continue if verifier fails
        
        # Log activity with email in result_summary for future lookups
        # Use background task to avoid blocking the response
        if email_found:
            result_summary = {
                "email": email_found,
                "source": source,
                "status": str(email_status) if email_status else None,
            }
        else:
            result_summary = None
        
        add_background_task_safe(
            background_tasks,
            activity_service.log_search_activity,
            session=session,
            user_id=current_user.uuid,
            service_type=ActivityServiceType.EMAIL,
            request_params={
                "first_name": first_name,
                "last_name": last_name,
                "domain": extracted_domain,
            },
            result_count=1 if email_found else 0,
            result_summary=result_summary,
            status=ActivityStatus.SUCCESS if email_found else ActivityStatus.FAILED,
            error_message=None,
            request=http_request,
        )
        
        # Return result
        final_response = SingleEmailResponse(
            email=email_found,
            source=source,
            status=email_status,
            certainty=None,
        )
        return final_response
        
    except HTTPException as http_exc:
        # Log failed activity for HTTP exceptions
        try:
            # Use request object directly for logging
            domain_for_log = request.domain or request.website or ''
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "domain": domain_for_log,
                },
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(http_exc.detail) if hasattr(http_exc, 'detail') else str(http_exc),
                request=http_request,
            )
        except Exception as log_exc:
            pass
        raise
    except Exception as exc:
        
        # Log failed activity
        try:
            # Use request object directly for logging
            domain_for_log = request.domain or request.website or ''
            await activity_service.log_search_activity(
                session=session,
                user_id=current_user.uuid,
                service_type=ActivityServiceType.EMAIL,
                request_params={
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                    "domain": domain_for_log,
                },
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as log_exc:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email",
        ) from exc
