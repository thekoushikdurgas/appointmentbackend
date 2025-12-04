"""Email finder API endpoints."""

import asyncio
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.exports import ExportStatus, ExportType
from app.models.user import ActivityActionType, ActivityServiceType, ActivityStatus, User
from app.repositories.user import UserProfileRepository
from app.services.activity_service import ActivityService
from app.services.credit_service import CreditService
from app.schemas.email import (
    AllListsResponse,
    BulkEmailVerifierRequest,
    BulkEmailVerifierResponse,
    CreditsResponse,
    EmailExportRequest,
    EmailListInfo,
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
from app.services.bulkmailverifier_service import BulkMailVerifierService
from app.services.email_finder_service import EmailFinderService
from app.services.export_service import ExportService
from app.utils.domain import extract_domain_from_url
from app.utils.email_generator import generate_email_combinations
from app.utils.signed_url import generate_signed_url
from app.utils.background_tasks import add_background_task_safe

settings = get_settings()

router = APIRouter(prefix="/email", tags=["Email"])
logger = get_logger(__name__)
service = EmailFinderService()
export_service = ExportService()
activity_service = ActivityService()
credit_service = CreditService()
profile_repo = UserProfileRepository()


@router.get("/finder/", response_model=SimpleEmailFinderResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "GET /email/finder/ request received: first_name=%s last_name=%s domain=%s website=%s user_id=%s",
        first_name,
        last_name,
        domain,
        website,
        current_user.uuid,
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
                    logger.info(
                        "Credits deducted for email search: user_id=%s role=%s new_balance=%d",
                        current_user.uuid,
                        user_role,
                        new_balance,
                    )
                else:
                    logger.debug(
                        "Credits not deducted (unlimited credits): user_id=%s role=%s",
                        current_user.uuid,
                        user_role,
                    )
        except Exception as credit_exc:
            # Log error but don't fail the request
            logger.exception("Failed to deduct credits for email search: %s", credit_exc)
        
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error finding emails: %s", exc)
        
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
            logger.exception("Failed to log activity: %s", log_exc)
        
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
        logger.info(
            "Verifying batch %d with %d emails",
            batch_number,
            len(emails),
        )
        
        # Upload file
        logger.info("Upload: Starting upload for batch %d with %d emails", batch_number, len(emails))
        try:
            upload_result = await service.upload_file(emails)
            slug = upload_result.get("slug")
            number_of_emails = upload_result.get("number_of_emails")
            upload_status = upload_result.get("status", "unknown")
            logger.info(
                "Upload: Batch %d upload completed: slug=%s number_of_emails=%d status=%s",
                batch_number,
                slug,
                number_of_emails,
                upload_status,
            )
            logger.debug("Upload: Full upload result for batch %d: %s", batch_number, upload_result)
        except HTTPException as http_exc:
            # Handle HTTPException from BulkMailVerifier service gracefully
            if "credentials not configured" in str(http_exc.detail).lower():
                logger.error(
                    "Upload: BulkMailVerifier credentials not configured. Cannot verify emails. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                )
                # Return empty valid emails but don't raise - let the endpoint handle it
                return valid_emails, batches_processed
            else:
                logger.error(
                    "Upload: Batch %d upload failed with HTTPException: status_code=%d detail=%s",
                    batch_number,
                    http_exc.status_code,
                    http_exc.detail,
                )
                # Re-raise other HTTPExceptions
                raise
        
        if not slug:
            logger.error("Upload: Batch %d upload completed but slug is missing from result", batch_number)
            return valid_emails, batches_processed
        
        slug = upload_result["slug"]
        
        try:
            # Start verification
            logger.info("Verification start: Initiating verification for batch %d, slug=%s", batch_number, slug)
            verification_start_result = await service.start_verification(slug)
            verification_start_status = verification_start_result.get("File Status", verification_start_result.get("status", "unknown"))
            logger.info(
                "Verification start: Batch %d verification started successfully: slug=%s status=%s",
                batch_number,
                slug,
                verification_start_status,
            )
            logger.debug("Verification start: Full start result for batch %d: %s", batch_number, verification_start_result)
            
            # Poll for status until completed
            max_poll_attempts = 300  # 5 minutes max (300 * 1 second)
            poll_interval = 10  # Poll every 10 seconds
            poll_attempts = 0
            last_logged_attempt = 0
            log_interval = 20  # Log progress every 20 attempts (every ~3.3 minutes)
            
            logger.info(
                "Polling: Starting status polling for batch %d: max_attempts=%d interval=%ds slug=%s",
                batch_number,
                max_poll_attempts,
                poll_interval,
                slug,
            )
            
            while poll_attempts < max_poll_attempts:
                await asyncio.sleep(poll_interval)
                status_result = await service.get_status(slug)
                status = status_result.get("status", "").lower()
                total_verified = status_result.get("total_verified")
                total_emails = status_result.get("total_emails")
                percentage = status_result.get("percentage", 0)
                
                # Log detailed status at debug level every time
                logger.debug(
                    "Polling: Batch %d status check (attempt %d/%d): status=%s verified=%s/%s percentage=%s%%",
                    batch_number,
                    poll_attempts + 1,
                    max_poll_attempts,
                    status,
                    total_verified,
                    total_emails,
                    percentage,
                )
                
                # Log progress at INFO level periodically
                if poll_attempts - last_logged_attempt >= log_interval or poll_attempts == 0:
                    logger.info(
                        "Polling: Batch %d progress (attempt %d/%d): status=%s verified=%s/%s percentage=%s%%",
                        batch_number,
                        poll_attempts + 1,
                        max_poll_attempts,
                        status,
                        total_verified,
                        total_emails,
                        percentage,
                    )
                    last_logged_attempt = poll_attempts
                
                if status == "completed":
                    logger.info(
                        "Polling: Batch %d verification completed: verified=%s/%s percentage=%s%% (attempts=%d)",
                        batch_number,
                        total_verified,
                        total_emails,
                        percentage,
                        poll_attempts + 1,
                    )
                    break
                elif status not in ("verifying", "processing"):
                    logger.warning(
                        "Polling: Batch %d unexpected status: status=%s verified=%s/%s (attempts=%d)",
                        batch_number,
                        status,
                        total_verified,
                        total_emails,
                        poll_attempts + 1,
                    )
                    break
                
                poll_attempts += 1
            
            if poll_attempts >= max_poll_attempts:
                logger.warning(
                    "Polling: Batch %d verification timed out after %d attempts (%d seconds)",
                    batch_number,
                    max_poll_attempts,
                    max_poll_attempts * poll_interval,
                )
                logger.debug("Polling: Cleaning up timed out batch %d, slug=%s", batch_number, slug)
                await service.delete_list(slug)
                return valid_emails, batches_processed
            
            # Get results
            logger.info("Results retrieval: Getting results for batch %d, slug=%s", batch_number, slug)
            results = await service.get_results(slug)
            results_status = results.get("status", "unknown")
            logger.info(
                "Results retrieval: Batch %d results retrieved: status=%s",
                batch_number,
                results_status,
            )
            logger.debug("Results retrieval: Available result files for batch %d: %s", batch_number, {
                "valid_email_file": bool(results.get("valid_email_file")),
                "invalid_email_file": bool(results.get("invalid_email_file")),
                "catchall_email_file": bool(results.get("catchall_email_file")),
                "unknown_email_file": bool(results.get("unknown_email_file")),
            })
            
            # Download valid emails
            valid_email_file_url = results.get("valid_email_file")
            if valid_email_file_url:
                logger.info(
                    "Download: Starting download of valid emails for batch %d from URL: %s",
                    batch_number,
                    valid_email_file_url,
                )
                valid_emails = await service.download_valid_emails(valid_email_file_url)
                logger.info(
                    "Download: Batch %d download completed: found %d valid emails",
                    batch_number,
                    len(valid_emails),
                )
                if valid_emails:
                    logger.debug(
                        "Download: Sample valid emails from batch %d (first 3): %s",
                        batch_number,
                        valid_emails[:3],
                    )
            else:
                logger.warning(
                    "Download: No valid_email_file URL in results for batch %d. Available keys: %s",
                    batch_number,
                    list(results.keys()),
                )
            
            batches_processed = 1
            logger.debug("Batch processing: Batch %d marked as processed", batch_number)
            
        finally:
            # Clean up - delete the uploaded file
            logger.debug("Cleanup: Starting cleanup for batch %d, slug=%s", batch_number, slug)
            try:
                delete_result = await service.delete_list(slug)
                delete_status = delete_result.get("status", "unknown") if isinstance(delete_result, dict) else "unknown"
                logger.info(
                    "Cleanup: Batch %d cleanup completed: slug=%s status=%s",
                    batch_number,
                    slug,
                    delete_status,
                )
                logger.debug("Cleanup: Full delete result for batch %d: %s", batch_number, delete_result)
            except Exception as e:
                logger.warning(
                    "Cleanup: Failed to delete list for batch %d, slug=%s: error=%s",
                    batch_number,
                    slug,
                    str(e),
                )
                logger.debug("Cleanup: Exception details for batch %d: %s", batch_number, e, exc_info=True)
        
    except Exception as e:
        logger.exception(
            "Error: Exception occurred while verifying batch %d: error=%s type=%s",
            batch_number,
            str(e),
            type(e).__name__,
        )
        raise
    
    logger.info(
        "Batch completion: Batch %d verification completed: valid_emails=%d batches_processed=%d",
        batch_number,
        len(valid_emails),
        batches_processed,
    )
    return valid_emails, batches_processed


@router.post("/verifier/", response_model=EmailVerifierResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "POST /email/verifier/ request received: first_name=%s last_name=%s domain=%s website=%s user_id=%s",
        request.first_name,
        request.last_name,
        request.domain,
        request.website,
        current_user.uuid,
    )
    
    try:
        # Extract domain from website or domain parameter
        logger.debug("Validation: Checking domain/website parameter")
        domain_input = request.domain or request.website
        if not domain_input:
            logger.warning("Validation failed: Neither domain nor website parameter provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        logger.debug("Validation: Domain input found: domain=%s website=%s", request.domain, request.website)
        
        # Normalize domain
        logger.debug("Validation: Normalizing domain input")
        domain_input = domain_input.strip()
        if not domain_input:
            logger.warning("Validation failed: Domain/website is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        logger.info("Domain extraction: input=%s", domain_input)
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            logger.warning("Domain extraction failed: Could not extract valid domain from input=%s", domain_input)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        logger.info("Domain extraction: output=%s (input=%s)", extracted_domain, domain_input)
        
        # Validate first_name and last_name
        logger.debug("Validation: Checking first_name and last_name")
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        
        if not first_name:
            logger.warning("Validation failed: first_name is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        
        if not last_name:
            logger.warning("Validation failed: last_name is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        logger.debug("Validation: Names validated: first_name=%s last_name=%s", first_name, last_name)
        
        # Get email_count from request (with default)
        email_count = request.email_count if request.email_count is not None else 1000
        logger.info(
            "Parameters: email_count=%d (requested=%s)",
            email_count,
            request.email_count,
        )
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            logger.warning("Validation failed: email_count=%d is less than minimum of 1", email_count)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        logger.debug("Validation: All parameters validated successfully")
        
        # Check if BulkMailVerifier credentials are configured
        logger.debug("Configuration check: Verifying BulkMailVerifier credentials")
        credentials_configured = bool(settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD)
        logger.info(
            "Configuration: BulkMailVerifier credentials configured=%s (email_present=%s password_present=%s)",
            credentials_configured,
            bool(settings.BULKMAILVERIFIER_EMAIL),
            bool(settings.BULKMAILVERIFIER_PASSWORD),
        )
        
        # Generate all unique email patterns once
        logger.info(
            "Email generation: Generating all unique patterns for first_name=%s last_name=%s domain=%s",
            first_name,
            last_name,
            extracted_domain,
        )
        all_unique_emails = generate_email_combinations(
            first_name=first_name,
            last_name=last_name,
            domain=extracted_domain,
            count=email_count,
        )
        total_unique_patterns = len(all_unique_emails)
        
        if not credentials_configured:
            logger.warning(
                "BulkMailVerifier credentials not configured. Generating emails without verification."
            )
            logger.info(
                "Email generation completed: total_generated=%d (credentials not configured, no verification)",
                total_unique_patterns,
            )
            
            return EmailVerifierResponse(
                valid_emails=[],
                total_valid=0,
                generated_emails=all_unique_emails,
                total_generated=total_unique_patterns,
                total_batches_processed=0,
            )
        
        # Initialize BulkMailVerifier service
        logger.info("Service initialization: Creating BulkMailVerifierService instance")
        service = BulkMailVerifierService()
        logger.debug("Service initialization: BulkMailVerifierService created successfully")
        
        # Calculate number of batches needed
        total_batches = (total_unique_patterns + email_count - 1) // email_count
        
        logger.info(
            "Starting email verification flow: first_name=%s last_name=%s domain=%s total_unique_patterns=%d email_count=%d total_batches=%d",
            first_name,
            last_name,
            extracted_domain,
            total_unique_patterns,
            email_count,
            total_batches,
        )
        
        all_valid_emails = []
        total_batches_processed = 0
        verification_error_occurred = False
        
        # Process all unique patterns in batches
        logger.info("Batch loop: Starting batch processing loop (total_batches=%d, total_unique_patterns=%d)", total_batches, total_unique_patterns)
        for batch_number in range(1, total_batches + 1):
            # Calculate batch slice
            start_idx = (batch_number - 1) * email_count
            end_idx = min(start_idx + email_count, total_unique_patterns)
            batch_emails = all_unique_emails[start_idx:end_idx]
            
            logger.info(
                "Batch loop: Entering batch %d/%d for first_name=%s last_name=%s domain=%s (processing %d emails)",
                batch_number,
                total_batches,
                first_name,
                last_name,
                extracted_domain,
                len(batch_emails),
            )
            
            # Verify batch using direct API
            try:
                email_status_map = await _verify_emails_batch_direct(
                    emails=batch_emails,
                    service=service,
                    batch_size=20,  # Process 20 emails concurrently per batch
                )
                
                # Extract valid emails from status map
                valid_emails = [
                    email for email, status in email_status_map.items()
                    if status == EmailVerificationStatus.VALID
                ]
                
                # Calculate batches processed (number of API batch calls made)
                batches_processed = (len(batch_emails) + 19) // 20  # ceil division for batch_size=20
                
                total_batches_processed += batches_processed
            except HTTPException as http_exc:
                # Handle HTTPException from verification (e.g., credentials not configured)
                if "credentials not configured" in str(http_exc.detail).lower():
                    logger.error(
                        "BulkMailVerifier credentials not configured. Stopping verification."
                    )
                    verification_error_occurred = True
                    break
                else:
                    # Re-raise other HTTPExceptions
                    raise
            except Exception as batch_exc:
                # Log error but continue with next batch
                logger.warning(
                    "Error verifying batch %d: %s. Continuing with next batch.",
                    batch_number,
                    str(batch_exc),
                )
                valid_emails = []
                batches_processed = 0
            
            if valid_emails:
                all_valid_emails.extend(valid_emails)
                logger.info(
                    "Batch %d found %d valid emails (total so far: %d)",
                    batch_number,
                    len(valid_emails),
                    len(all_valid_emails),
                )
                
                # If we found valid emails, we can stop (or continue for more)
                # For now, we'll stop after finding at least one valid email
                if len(all_valid_emails) > 0:
                    logger.info(
                        "Found valid emails, completing verification: total_valid=%d",
                        len(all_valid_emails),
                    )
                    break
            else:
                logger.info(
                    "Batch %d found no valid emails, continuing...",
                    batch_number,
                )
            
            logger.debug("Batch loop: Completed iteration for batch %d, moving to next batch", batch_number)
        
        logger.info(
            "Batch loop: Exited batch processing loop after %d batches. Checked %d unique patterns.",
            total_batches,
            total_unique_patterns,
        )
        
        if verification_error_occurred:
            logger.warning(
                "Email verification stopped due to configuration error. "
                "Generated %d emails but could not verify them. "
                "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables.",
                total_unique_patterns,
            )
        else:
            logger.info(
                "Email verification completed successfully: total_valid=%d total_generated=%d batches_processed=%d",
                len(all_valid_emails),
                total_unique_patterns,
                total_batches_processed,
            )
        
        # Prepare response
        logger.debug(
            "Response preparation: Preparing EmailVerifierResponse with valid_emails=%d generated_emails=%d batches=%d",
            len(all_valid_emails),
            total_unique_patterns,
            total_batches_processed,
        )
        response = EmailVerifierResponse(
            valid_emails=all_valid_emails,
            total_valid=len(all_valid_emails),
            generated_emails=all_unique_emails,
            total_generated=total_unique_patterns,
            total_batches_processed=total_batches_processed,
        )
        logger.info(
            "Response prepared: Returning response with total_valid=%d total_generated=%d total_batches_processed=%d",
            response.total_valid,
            response.total_generated,
            response.total_batches_processed,
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
            logger.exception("Failed to log activity: %s", log_exc)
        
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
            logger.exception("Failed to log activity: %s", log_exc)
        raise
    except Exception as exc:
        logger.exception("Error verifying emails: %s", exc)
        
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
            logger.exception("Failed to log activity: %s", log_exc)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
        ) from exc


@router.post("/verifier/single/", response_model=SingleEmailVerifierFindResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def start_single_email_verification(
    request: EmailVerifierRequest,
    current_user: User = Depends(get_current_user),
) -> SingleEmailVerifierFindResponse:
    """
    Verify emails sequentially and return immediately when first VALID email is found.
    
    Generates random email combinations based on first name, last name, and domain,
    then verifies them sequentially one at a time through BulkMailVerifier direct email 
    verification API. Stops immediately when the first VALID email is found and returns it.
    
    Args:
        request: EmailVerifierRequest with first_name, last_name, and domain/website
        current_user: Current authenticated user
        
    Returns:
        SingleEmailVerifierFindResponse with the first valid email found, or None if none found
    """
    logger.info(
        "POST /email/verifier/single/ request received: first_name=%s last_name=%s domain=%s website=%s user_id=%s",
        request.first_name,
        request.last_name,
        request.domain,
        request.website,
        current_user.uuid,
    )
    
    try:
        # Extract domain from website or domain parameter
        logger.debug("Validation: Checking domain/website parameter")
        domain_input = request.domain or request.website
        if not domain_input:
            logger.warning("Validation failed: Neither domain nor website parameter provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        logger.debug("Validation: Domain input found: domain=%s website=%s", request.domain, request.website)
        
        # Normalize domain
        logger.debug("Validation: Normalizing domain input")
        domain_input = domain_input.strip()
        if not domain_input:
            logger.warning("Validation failed: Domain/website is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        logger.info("Domain extraction: input=%s", domain_input)
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            logger.warning("Domain extraction failed: Could not extract valid domain from input=%s", domain_input)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        logger.info("Domain extraction: output=%s (input=%s)", extracted_domain, domain_input)
        
        # Validate first_name and last_name
        logger.debug("Validation: Checking first_name and last_name")
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        
        if not first_name:
            logger.warning("Validation failed: first_name is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        
        if not last_name:
            logger.warning("Validation failed: last_name is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        logger.debug("Validation: Names validated: first_name=%s last_name=%s", first_name, last_name)
        
        # Get email_count from request (with default)
        email_count = request.email_count if request.email_count is not None else 1000
        logger.info(
            "Parameters: email_count=%d (requested=%s)",
            email_count,
            request.email_count,
        )
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            logger.warning("Validation failed: email_count=%d is less than minimum of 1", email_count)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        logger.debug("Validation: All parameters validated successfully")
        
        # Check if BulkMailVerifier credentials are configured
        logger.debug("Configuration check: Verifying BulkMailVerifier credentials")
        credentials_configured = bool(settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD)
        logger.info(
            "Configuration: BulkMailVerifier credentials configured=%s (email_present=%s password_present=%s)",
            credentials_configured,
            bool(settings.BULKMAILVERIFIER_EMAIL),
            bool(settings.BULKMAILVERIFIER_PASSWORD),
        )
        
        if not credentials_configured:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot verify emails."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        logger.info("Service initialization: Creating BulkMailVerifierService instance")
        service = BulkMailVerifierService()
        logger.debug("Service initialization: BulkMailVerifierService created successfully")
        
        # Generate all unique email patterns once at the start
        logger.info(
            "Email generation: Generating all unique patterns for first_name=%s last_name=%s domain=%s",
            first_name,
            last_name,
            extracted_domain,
        )
        all_unique_emails = generate_email_combinations(
            first_name=first_name,
            last_name=last_name,
            domain=extracted_domain,
            count=email_count,
        )
        total_unique_patterns = len(all_unique_emails)
        
        if total_unique_patterns == 0:
            logger.warning(
                "Email generation: No unique patterns generated for first_name=%s last_name=%s domain=%s",
                first_name,
                last_name,
                extracted_domain,
            )
            return SingleEmailVerifierFindResponse(valid_email=None)
        
        # Calculate number of batches needed
        total_batches = (total_unique_patterns + email_count - 1) // email_count
        
        logger.info(
            "Starting single email verification flow: first_name=%s last_name=%s domain=%s total_unique_patterns=%d email_count=%d total_batches=%d",
            first_name,
            last_name,
            extracted_domain,
            total_unique_patterns,
            email_count,
            total_batches,
        )
        
        # Track verified emails to prevent duplicates
        verified_emails_set = set()
        total_emails_checked = 0
        
        # Process emails in batches until we find a valid email or check all patterns
        logger.info("Batch loop: Starting batch processing loop (total_batches=%d, total_unique_patterns=%d)", total_batches, total_unique_patterns)
        for batch_number in range(1, total_batches + 1):
            # Calculate batch slice
            start_idx = (batch_number - 1) * email_count
            end_idx = min(start_idx + email_count, total_unique_patterns)
            batch_emails = all_unique_emails[start_idx:end_idx]
            
            # Filter out already verified emails
            batch_emails_to_check = [e for e in batch_emails if e not in verified_emails_set]
            skipped_count = len(batch_emails) - len(batch_emails_to_check)
            
            if skipped_count > 0:
                logger.debug(
                    "Batch loop: Skipping %d already-verified emails in batch %d",
                    skipped_count,
                    batch_number,
                )
            
            if not batch_emails_to_check:
                logger.info(
                    "Batch loop: All emails in batch %d already verified, skipping",
                    batch_number,
                )
                continue
            
            logger.info(
                "Batch loop: Entering batch %d/%d for first_name=%s last_name=%s domain=%s (checking %d emails, %d skipped)",
                batch_number,
                total_batches,
                first_name,
                last_name,
                extracted_domain,
                len(batch_emails_to_check),
                skipped_count,
            )
            
            # Verify emails sequentially until first valid is found
            try:
                valid_email, emails_checked = await _verify_emails_sequential_until_valid(
                    emails=batch_emails_to_check,
                    service=service,
                    verified_emails_set=verified_emails_set,
                )
                
                # Track verified emails
                verified_emails_set.update(batch_emails_to_check[:emails_checked])
                total_emails_checked += emails_checked
                
                if valid_email:
                    logger.info(
                        "Found valid email in batch %d: email=%s (checked %d emails in this batch, %d total, %d/%d unique patterns checked)",
                        batch_number,
                        valid_email,
                        emails_checked,
                        total_emails_checked,
                        len(verified_emails_set),
                        total_unique_patterns,
                    )
                    return SingleEmailVerifierFindResponse(valid_email=valid_email)
                else:
                    logger.info(
                        "Batch %d: No valid email found (checked %d emails in this batch, %d total, %d/%d unique patterns checked)",
                        batch_number,
                        emails_checked,
                        total_emails_checked,
                        len(verified_emails_set),
                        total_unique_patterns,
                    )
                    
            except HTTPException as http_exc:
                # Handle HTTPException from verification (e.g., credentials not configured)
                if "credentials not configured" in str(http_exc.detail).lower():
                    logger.error(
                        "BulkMailVerifier credentials not configured. Stopping verification."
                    )
                    raise
                else:
                    # Re-raise other HTTPExceptions
                    raise
            except Exception as batch_exc:
                # Log error but continue with next batch
                logger.warning(
                    "Error verifying batch %d: %s. Continuing with next batch.",
                    batch_number,
                    str(batch_exc),
                )
            
            logger.debug("Batch loop: Completed iteration for batch %d, moving to next batch", batch_number)
        
        logger.info(
            "Batch loop: Exited batch processing loop after %d batches. No valid email found after checking %d unique patterns.",
            total_batches,
            total_emails_checked,
        )
        
        # No valid email found after all patterns checked
        logger.info(
            "Single email verification completed: no valid email found after checking %d unique patterns across %d batches",
            total_emails_checked,
            total_batches,
        )
        
        return SingleEmailVerifierFindResponse(valid_email=None)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error verifying emails: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
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
        logger.warning("_verify_emails_batch_direct: Empty email list provided")
        return email_status_map
    
    # Initialize all emails as unknown (will be updated after verification)
    for email in emails:
        email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
    
    try:
        logger.info(
            "Verifying %d emails using direct API in batches of %d",
            len(emails),
            batch_size,
        )
        
        # Process emails in batches
        total_batches = (len(emails) + batch_size - 1) // batch_size
        logger.info("Processing %d emails in %d batches", len(emails), total_batches)
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails))
            batch_emails = emails[start_idx:end_idx]
            
            logger.info(
                "Processing batch %d/%d: emails %d-%d (%d emails)",
                batch_num + 1,
                total_batches,
                start_idx + 1,
                end_idx,
                len(batch_emails),
            )
            
            # Create tasks for concurrent processing
            async def verify_email_task(email: str) -> tuple[str, EmailVerificationStatus]:
                """Verify a single email and return (email, status) tuple."""
                try:
                    result = await service.verify_single_email(email)
                    mapped_status = result.get("mapped_status", "unknown")
                    try:
                        status = EmailVerificationStatus(mapped_status)
                    except ValueError:
                        logger.warning(
                            "Unknown mapped status '%s' for email %s, defaulting to UNKNOWN",
                            mapped_status,
                            email,
                        )
                        status = EmailVerificationStatus.UNKNOWN
                    return (email.lower().strip(), status)
                except Exception as e:
                    logger.warning(
                        "Error verifying email %s: %s. Defaulting to UNKNOWN.",
                        email,
                        str(e),
                    )
                    return (email.lower().strip(), EmailVerificationStatus.UNKNOWN)
            
            # Process batch concurrently
            tasks = [verify_email_task(email) for email in batch_emails]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update status map with results
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Exception in batch processing: %s", result)
                    continue
                email_key, status = result
                email_status_map[email_key] = status
            
            logger.info(
                "Batch %d/%d completed: processed %d emails",
                batch_num + 1,
                total_batches,
                len(batch_emails),
            )
        
        logger.info(
            "Batch verification completed: processed %d emails",
            len(email_status_map),
        )
        
    except Exception as e:
        logger.exception("Error in batch email verification: %s", e)
        # Don't raise - return partial results
    
    return email_status_map


async def _verify_emails_sequential_until_valid(
    emails: list[str],
    service: BulkMailVerifierService,
    verified_emails_set: Optional[set[str]] = None,
) -> tuple[Optional[str], int]:
    """
    Verify emails sequentially until the first VALID email is found.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        verified_emails_set: Optional set to track verified emails (will be updated in-place)
        
    Returns:
        Tuple of (valid_email: str | None, emails_checked: int)
        - valid_email: The first valid email found, or None if none found
        - emails_checked: Number of emails verified before stopping
    """
    if not emails:
        logger.warning("_verify_emails_sequential_until_valid: Empty email list provided")
        return None, 0
    
    if verified_emails_set is None:
        verified_emails_set = set()
    
    logger.info(
        "Sequential verification: Starting sequential verification of %d emails until first VALID found",
        len(emails),
    )
    
    emails_checked = 0
    
    try:
        for email in emails:
            # Skip if already verified
            if email in verified_emails_set:
                logger.debug(
                    "Sequential verification: Skipping already-verified email: %s",
                    email,
                )
                continue
            
            emails_checked += 1
            logger.debug(
                "Sequential verification: Verifying email %d/%d: %s",
                emails_checked,
                len(emails),
                email,
            )
            
            try:
                result = await service.verify_single_email(email)
                mapped_status = result.get("mapped_status", "unknown")
                
                # Add to verified set
                verified_emails_set.add(email)
                
                try:
                    status = EmailVerificationStatus(mapped_status)
                except ValueError:
                    logger.warning(
                        "Sequential verification: Unknown mapped status '%s' for email %s, defaulting to UNKNOWN",
                        mapped_status,
                        email,
                    )
                    status = EmailVerificationStatus.UNKNOWN
                
                logger.debug(
                    "Sequential verification: Email %s status: %s",
                    email,
                    status.value,
                )
                
                if status == EmailVerificationStatus.VALID:
                    logger.info(
                        "Sequential verification: Found VALID email at position %d/%d: %s",
                        emails_checked,
                        len(emails),
                        email,
                    )
                    return email.lower().strip(), emails_checked
                
            except Exception as e:
                logger.warning(
                    "Sequential verification: Error verifying email %s: %s. Continuing to next email.",
                    email,
                    str(e),
                )
                # Still add to verified set to avoid retrying failed emails
                verified_emails_set.add(email)
                # Continue to next email on error
                continue
        
        logger.info(
            "Sequential verification: No VALID email found after checking %d emails",
            emails_checked,
        )
        return None, emails_checked
        
    except Exception as e:
        logger.exception("Error in sequential email verification: %s", e)
        # Return partial results
        return None, emails_checked


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
        logger.warning("_verify_emails_with_status: Empty email list provided")
        return email_status_map
    
    # Initialize all emails as unknown (will be updated after verification)
    for email in emails:
        email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
    
    try:
        logger.info(
            "Verifying %d emails with status tracking",
            len(emails),
        )
        
        # Upload file
        logger.info("Uploading %d emails for verification", len(emails))
        try:
            upload_result = await service.upload_file(emails)
        except HTTPException as http_exc:
            if "credentials not configured" in str(http_exc.detail).lower():
                logger.error(
                    "BulkMailVerifier credentials not configured. Cannot verify emails."
                )
                # Mark all as unknown
                for email in emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
                return email_status_map
            else:
                raise
        
        slug = upload_result.get("slug")
        if not slug:
            logger.error("Upload completed but slug is missing")
            return email_status_map
        
        try:
            # Start verification
            logger.info("Starting verification for slug: %s", slug)
            await service.start_verification(slug)
            
            # Poll for status until completed
            max_poll_attempts = 300  # 5 minutes max
            poll_interval = 10  # Poll every 10 seconds
            poll_attempts = 0
            
            while poll_attempts < max_poll_attempts:
                await asyncio.sleep(poll_interval)
                status_result = await service.get_status(slug)
                status = status_result.get("status", "").lower()
                
                logger.debug(
                    "Status check: status=%s verified=%s/%s",
                    status,
                    status_result.get("total_verified"),
                    status_result.get("total_emails"),
                )
                
                if status == "completed":
                    logger.info("Verification completed")
                    break
                elif status not in ("verifying", "processing"):
                    logger.warning("Unexpected status: %s", status)
                    break
                
                poll_attempts += 1
            
            if poll_attempts >= max_poll_attempts:
                logger.warning("Verification timed out after %d attempts", max_poll_attempts)
                await service.delete_list(slug)
                return email_status_map
            
            # Get results
            logger.info("Getting results for slug: %s", slug)
            results = await service.get_results(slug)
            
            # Download all result files and map emails to status
            valid_email_file_url = results.get("valid_email_file")
            invalid_email_file_url = results.get("invalid_email_file")
            catchall_email_file_url = results.get("catchall_email_file")
            unknown_email_file_url = results.get("unknown_email_file")
            
            # Download valid emails
            if valid_email_file_url and valid_email_file_url.strip():
                logger.info("Downloading valid emails from URL: %s", valid_email_file_url)
                valid_emails = await service.download_valid_emails(valid_email_file_url)
                for email in valid_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.VALID
                logger.info("Found %d valid emails", len(valid_emails))
            else:
                logger.warning(
                    "No valid_email_file URL in results for slug %s. Available keys: %s",
                    slug,
                    list(results.keys()),
                )
            
            # Download invalid emails
            if invalid_email_file_url and invalid_email_file_url.strip():
                logger.info("Downloading invalid emails from URL: %s", invalid_email_file_url)
                invalid_emails = await service.download_invalid_emails(invalid_email_file_url)
                for email in invalid_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.INVALID
                logger.info("Found %d invalid emails", len(invalid_emails))
            else:
                logger.debug("No invalid_email_file URL in results for slug %s", slug)
            
            # Download catchall emails
            if catchall_email_file_url and catchall_email_file_url.strip():
                logger.info("Downloading catchall emails from URL: %s", catchall_email_file_url)
                catchall_emails = await service.download_catchall_emails(catchall_email_file_url)
                for email in catchall_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.CATCHALL
                logger.info("Found %d catchall emails", len(catchall_emails))
            else:
                logger.debug("No catchall_email_file URL in results for slug %s", slug)
            
            # Download unknown emails
            if unknown_email_file_url and unknown_email_file_url.strip():
                logger.info("Downloading unknown emails from URL: %s", unknown_email_file_url)
                unknown_emails = await service.download_unknown_emails(unknown_email_file_url)
                for email in unknown_emails:
                    email_status_map[email.lower().strip()] = EmailVerificationStatus.UNKNOWN
                logger.info("Found %d unknown emails", len(unknown_emails))
            else:
                logger.debug("No unknown_email_file URL in results for slug %s", slug)
            
        finally:
            # Clean up - delete the uploaded file
            try:
                await service.delete_list(slug)
                logger.debug("Cleaned up slug: %s", slug)
            except Exception as e:
                logger.warning("Failed to delete list for slug %s: %s", slug, e)
        
    except Exception as e:
        logger.exception("Error verifying emails with status: %s", e)
        raise
    
    logger.info(
        "Verification completed: processed %d emails",
        len(email_status_map),
    )
    return email_status_map


@router.post("/bulk/verifier/", response_model=BulkEmailVerifierResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    
    Args:
        request: BulkEmailVerifierRequest with list of emails
        current_user: Current authenticated user
        
    Returns:
        BulkEmailVerifierResponse with verification results for each email
    """
    logger.info(
        "POST /email/bulk/verifier/ request received: email_count=%d user_id=%s",
        len(request.emails),
        current_user.uuid,
    )
    
    try:
        # Check if BulkMailVerifier credentials are configured
        if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot verify emails."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        service = BulkMailVerifierService()
        
        # Verify emails using direct API calls in batches
        email_status_map = await _verify_emails_batch_direct(
            emails=request.emails,
            service=service,
            batch_size=20,  # Process 20 emails concurrently per batch
        )
        
        # Build results list
        results = []
        valid_count = 0
        invalid_count = 0
        catchall_count = 0
        unknown_count = 0
        
        for email in request.emails:
            normalized_email = email.lower().strip()
            verification_status = email_status_map.get(normalized_email, EmailVerificationStatus.UNKNOWN)
            
            results.append(VerifiedEmailResult(email=email, status=verification_status))
            
            if verification_status == EmailVerificationStatus.VALID:
                valid_count += 1
            elif verification_status == EmailVerificationStatus.INVALID:
                invalid_count += 1
            elif verification_status == EmailVerificationStatus.CATCHALL:
                catchall_count += 1
            else:
                unknown_count += 1
        
        logger.info(
            "Bulk verification completed: total=%d valid=%d invalid=%d catchall=%d unknown=%d",
            len(results),
            valid_count,
            invalid_count,
            catchall_count,
            unknown_count,
        )
        
        response = BulkEmailVerifierResponse(
            results=results,
            total=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            catchall_count=catchall_count,
            unknown_count=unknown_count,
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
            logger.exception("Failed to log activity for bulk email verification: %s", activity_exc)
        
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in bulk email verification: %s", exc)
        
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
            logger.exception("Failed to log failed activity for bulk email verification: %s", activity_exc)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
        ) from exc


@router.post("/single/verifier/", response_model=SingleEmailVerifierResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def single_email_verifier(
    request: SingleEmailVerifierRequest,
    current_user: User = Depends(get_current_user),
    http_request: Request = None,
    session: AsyncSession = Depends(get_db),
) -> SingleEmailVerifierResponse:
    """
    Verify a single email address through BulkMailVerifier service.
    
    Accepts a single email address and returns its verification status
    (valid, invalid, catchall, unknown).
    
    Args:
        request: SingleEmailVerifierRequest with single email
        current_user: Current authenticated user
        
    Returns:
        SingleEmailVerifierResponse with verification result for the email
    """
    logger.info(
        "POST /email/single/verifier/ request received: email=%s user_id=%s",
        request.email,
        current_user.uuid,
    )
    
    try:
        # Check if BulkMailVerifier credentials are configured
        if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot verify email."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        service = BulkMailVerifierService()
        
        # Verify email using direct API endpoint
        result = await service.verify_single_email(request.email)
        
        # Map the result status to EmailVerificationStatus enum
        mapped_status = result.get("mapped_status", "unknown")
        try:
            verification_status = EmailVerificationStatus(mapped_status)
        except ValueError:
            logger.warning(
                "Unknown mapped status '%s' for email %s, defaulting to UNKNOWN",
                mapped_status,
                request.email,
            )
            verification_status = EmailVerificationStatus.UNKNOWN
        
        logger.info(
            "Single email verification completed: email=%s status=%s",
            request.email,
            verification_status.value,
        )
        
        response = SingleEmailVerifierResponse(
            result=VerifiedEmailResult(email=request.email, status=verification_status),
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
            logger.exception("Failed to log activity for single email verification: %s", activity_exc)
        
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in single email verification: %s", exc)
        
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
            logger.exception("Failed to log failed activity for single email verification: %s", activity_exc)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from exc


@router.post("/bulk/credits/", response_model=CreditsResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def check_credits(
    current_user: User = Depends(get_current_user),
) -> CreditsResponse:
    """
    Check available email credits in BulkMailVerifier account.
    
    Returns the number of available email verification credits for the account.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        CreditsResponse with credits information
    """
    logger.info(
        "POST /email/bulk/credits/ request received: user_id=%s",
        current_user.uuid,
    )
    
    try:
        # Check if BulkMailVerifier credentials are configured
        if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot check credits."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        service = BulkMailVerifierService()
        
        # Check credits
        credits_data = await service.check_credits()
        
        logger.info(
            "Credits check completed: user_id=%s",
            current_user.uuid,
        )
        
        # Return response - handle both JSON and text responses
        return CreditsResponse(**credits_data)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error checking credits: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check credits",
        ) from exc


@router.post("/bulk/lists/", response_model=AllListsResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def get_all_lists(
    current_user: User = Depends(get_current_user),
) -> AllListsResponse:
    """
    Get all uploaded email lists from BulkMailVerifier.
    
    Returns a list of all email verification lists that have been uploaded,
    including their status, counts, and verification results.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        AllListsResponse with array of email list information
    """
    logger.info(
        "POST /email/bulk/lists/ request received: user_id=%s",
        current_user.uuid,
    )
    
    try:
        # Check if BulkMailVerifier credentials are configured
        if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot get lists."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        service = BulkMailVerifierService()
        
        # Get all lists
        lists_data = await service.get_all_lists()
        
        # Parse lists into EmailListInfo objects with better error handling
        lists = []
        raw_lists = lists_data.get("lists", [])
        logger.debug(
            "Parsing lists: raw_lists_count=%d",
            len(raw_lists),
        )
        
        for idx, list_item in enumerate(raw_lists):
            try:
                # Get slug first and validate it before creating mapped_item
                slug = list_item.get("slug") or ""
                # Skip items with missing or empty slug
                if not slug or not slug.strip():
                    logger.warning(
                        "Skipping list item %d: missing or empty slug. Item: %s",
                        idx,
                        list_item,
                    )
                    continue
                
                # Map fields if needed and ensure all required fields are present
                mapped_item = {
                    "slug": slug.strip(),  # Ensure slug is a non-empty string
                    "name": list_item.get("name"),  # Optional field
                    "status": list_item.get("status", "Unknown"),
                    "total_emails": int(list_item.get("total_emails", 0)),
                    "total_verified": int(list_item.get("total_verified", 0)),
                    "retry": int(list_item.get("retry", 0)),
                    "valid_emails": int(list_item.get("valid_emails", 0)),
                    "invalid_emails": int(list_item.get("invalid_emails", 0)),
                    "catchall_emails": int(list_item.get("catchall_emails", 0)),
                    "unknown_emails": int(list_item.get("unknown_emails", 0)),
                    "updated_at": list_item.get("updated_at"),  # Optional field
                }
                
                email_list_info = EmailListInfo(**mapped_item)
                lists.append(email_list_info)
            except Exception as parse_exc:
                logger.error(
                    "Error parsing list item %d: %s. Item data: %s",
                    idx,
                    str(parse_exc),
                    list_item,
                )
                # Continue with other items instead of failing completely
                continue
        
        logger.info(
            "Get all lists completed: user_id=%s lists_count=%d (parsed from %d raw items)",
            current_user.uuid,
            len(lists),
            len(raw_lists),
        )
        
        return AllListsResponse(lists=lists)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting lists: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lists: {str(exc)}",
        ) from exc


@router.get("/bulk/download/{file_type}/{slug}/")
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def download_result_file(
    file_type: str = Path(
        ...,
        description="Type of file to download: valid, invalid, c-all, or unknown",
    ),
    slug: str = Path(..., description="Slug identifier for the list"),
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
    logger.info(
        "GET /email/bulk/download/%s/%s/ request received: user_id=%s",
        file_type,
        slug,
        current_user.uuid,
    )
    
    try:
        # Check if BulkMailVerifier credentials are configured
        if not settings.BULKMAILVERIFIER_EMAIL or not settings.BULKMAILVERIFIER_PASSWORD:
            logger.warning(
                "BulkMailVerifier credentials not configured. Cannot download file."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "BulkMailVerifier credentials not configured. "
                    "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables."
                ),
            )
        
        # Initialize BulkMailVerifier service
        service = BulkMailVerifierService()
        
        # Download file
        csv_content = await service.download_result_file(file_type=file_type, slug=slug)
        
        logger.info(
            "File download completed: file_type=%s slug=%s user_id=%s size=%d bytes",
            file_type,
            slug,
            current_user.uuid,
            len(csv_content),
        )
        
        # Return CSV file as response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{file_type}_{slug}.csv"',
            },
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error downloading file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file",
        ) from exc


@router.post("/export", response_model=EmailExportResponse, status_code=status.HTTP_201_CREATED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "POST /email/export request received: contact_count=%d user_id=%s",
        len(request.contacts),
        current_user.uuid,
    )
    
    if not request.contacts:
        logger.warning(
            "Email export request rejected: empty contacts list user_id=%s",
            current_user.uuid,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one contact is required",
        )
    
    try:
        # Serialize contacts to JSON for storage
        logger.debug(
            "Serializing contacts data: contact_count=%d user_id=%s",
            len(request.contacts),
            current_user.uuid,
        )
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
        logger.debug(
            "Contacts serialized: json_size=%d bytes user_id=%s",
            len(contacts_json),
            current_user.uuid,
        )
        
        # Create export record with status "pending"
        logger.info(
            "Creating email export record: user_id=%s contact_count=%d",
            current_user.uuid,
            len(request.contacts),
        )
        export = await export_service.create_export(
            session,
            current_user.uuid,
            ExportType.emails,
            contact_uuids=[],  # No contact UUIDs for email exports
            company_uuids=[],
        )
        logger.info(
            "Export record created: export_id=%s user_id=%s",
            export.export_id,
            current_user.uuid,
        )
        
        # Store email contacts JSON data
        export.email_contacts_json = contacts_json
        export.contact_count = len(request.contacts)
        export.total_records = len(request.contacts)
        await session.commit()
        logger.debug(
            "Export record updated with contacts data: export_id=%s contact_count=%d",
            export.export_id,
            len(request.contacts),
        )
        
        # Log export activity
        logger.debug(
            "Logging export activity: export_id=%s user_id=%s",
            export.export_id,
            current_user.uuid,
        )
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
        logger.info(
            "Export activity logged: activity_id=%d export_id=%s user_id=%s",
            activity_id,
            export.export_id,
            current_user.uuid,
        )
        
        # Import background task function
        from app.tasks.export_tasks import process_email_export
        
        # Enqueue background task with activity_id for updating
        # Note: This is a long-running task that might be better suited for Celery in the future
        logger.info(
            "Enqueueing background task: export_id=%s contact_count=%d activity_id=%d",
            export.export_id,
            len(contacts_data),
            activity_id,
        )
        add_background_task_safe(
            background_tasks,
            process_email_export,
            export.export_id,
            contacts_data,
            activity_id,
            track_status=True,
            cpu_bound=False,  # I/O-bound task (database and file operations)
        )
        logger.debug(
            "Background task enqueued successfully: export_id=%s",
            export.export_id,
        )
        
        # Deduct credits for FreeUser and ProUser (after export is queued successfully)
        # Deduct 1 credit per contact
        logger.debug(
            "Checking credit deduction: export_id=%s user_id=%s contact_count=%d",
            export.export_id,
            current_user.uuid,
            len(request.contacts),
        )
        try:
            profile = await profile_repo.get_by_user_id(session, current_user.uuid)
            if profile:
                user_role = profile.role or "FreeUser"
                logger.debug(
                    "User profile retrieved: user_id=%s role=%s export_id=%s",
                    current_user.uuid,
                    user_role,
                    export.export_id,
                )
                if credit_service.should_deduct_credits(user_role):
                    credit_amount = len(request.contacts)
                    logger.info(
                        "Deducting credits: user_id=%s role=%s amount=%d export_id=%s",
                        current_user.uuid,
                        user_role,
                        credit_amount,
                        export.export_id,
                    )
                    new_balance = await credit_service.deduct_credits(
                        session, current_user.uuid, amount=credit_amount
                    )
                    logger.info(
                        "Credits deducted for email export: user_id=%s role=%s amount=%d new_balance=%d export_id=%s",
                        current_user.uuid,
                        user_role,
                        credit_amount,
                        new_balance,
                        export.export_id,
                    )
                else:
                    logger.debug(
                        "Credits not deducted (unlimited credits): user_id=%s role=%s contact_count=%d export_id=%s",
                        current_user.uuid,
                        user_role,
                        len(request.contacts),
                        export.export_id,
                    )
            else:
                logger.warning(
                    "User profile not found for credit deduction: user_id=%s export_id=%s",
                    current_user.uuid,
                    export.export_id,
                )
        except Exception as credit_exc:
            # Log error but don't fail the request
            logger.exception(
                "Failed to deduct credits for email export: export_id=%s user_id=%s error=%s",
                export.export_id,
                current_user.uuid,
                credit_exc,
            )
        
        logger.info(
            "Email export queued: export_id=%s user_id=%s contact_count=%d",
            export.export_id,
            current_user.uuid,
            len(request.contacts),
        )
        
        # Set expiration to 24 hours from creation
        expires_at = export.created_at + timedelta(hours=24)
        logger.debug(
            "Export expiration set: export_id=%s expires_at=%s",
            export.export_id,
            expires_at.isoformat(),
        )
        
        # Generate initial download URL with signed token
        logger.debug(
            "Generating signed download URL: export_id=%s user_id=%s",
            export.export_id,
            current_user.uuid,
        )
        download_token = generate_signed_url(export.export_id, current_user.uuid, expires_at)
        base_url = settings.BASE_URL.rstrip("/")
        download_url = f"{base_url}/api/v2/exports/{export.export_id}/download?token={download_token}"
        logger.debug(
            "Download URL generated: export_id=%s url_length=%d",
            export.export_id,
            len(download_url),
        )
        
        logger.info(
            "Email export request completed successfully: export_id=%s user_id=%s contact_count=%d status=%s",
            export.export_id,
            current_user.uuid,
            len(request.contacts),
            export.status,
        )
        
        return EmailExportResponse(
            export_id=export.export_id,
            download_url=download_url,
            expires_at=expires_at,
            contact_count=len(request.contacts),
            company_count=0,
            status=export.status,
        )
            
    except HTTPException:
        logger.warning(
            "Email export request failed with HTTPException: user_id=%s contact_count=%d",
            current_user.uuid,
            len(request.contacts) if hasattr(request, 'contacts') else 0,
        )
        raise
    except Exception as exc:
        logger.exception(
            "Export creation failed: user_id=%s contact_count=%d error=%s",
            current_user.uuid,
            len(request.contacts) if hasattr(request, 'contacts') else 0,
            exc,
        )
        
        # Log failed activity
        logger.debug(
            "Logging failed export activity: user_id=%s",
            current_user.uuid,
        )
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
            logger.debug(
                "Failed export activity logged: user_id=%s",
                current_user.uuid,
            )
        except Exception as log_exc:
            logger.exception(
                "Failed to log activity after export creation failure: user_id=%s error=%s",
                current_user.uuid,
                log_exc,
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.post("/single/", response_model=SingleEmailResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def get_single_email(
    request: SingleEmailRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SingleEmailResponse:
    """
    Get a single email address for a contact using two-step approach.
    
    Attempts to find an email address for a single contact by:
    1. First trying to find emails in the database using the email finder service
    2. If not found, trying email verification using the single email verifier
    3. If still not found, returns None
    
    Args:
        request: SingleEmailRequest with first_name, last_name, and domain/website
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        SingleEmailResponse with email address and source, or None if not found
    """
    logger.info(
        "POST /email/single/ request received: first_name=%s last_name=%s domain=%s website=%s user_id=%s",
        request.first_name,
        request.last_name,
        request.domain,
        request.website,
        current_user.uuid,
    )
    
    try:
        # Normalize inputs
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()
        domain_input = request.domain or request.website
        
        if not domain_input:
            logger.warning("Validation failed: Neither domain nor website parameter provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        
        domain_input = domain_input.strip()
        if not domain_input:
            logger.warning("Validation failed: Domain/website is empty after stripping")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain
        logger.debug("Domain extraction: input=%s", domain_input)
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            logger.warning("Domain extraction failed: Could not extract valid domain from input=%s", domain_input)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        logger.info("Domain extraction: output=%s (input=%s)", extracted_domain, domain_input)
        
        # Initialize services
        email_finder_service = EmailFinderService()
        bulk_verifier_service = BulkMailVerifierService() if (
            settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD
        ) else None
        
        email_found = None
        source = None
        
        # Step 1: Try email finder (database search)
        try:
            logger.debug(
                "Trying email finder: first_name=%s last_name=%s domain=%s",
                first_name,
                last_name,
                extracted_domain,
            )
            finder_result = await email_finder_service.find_emails(
                session=session,
                first_name=first_name,
                last_name=last_name,
                domain=extracted_domain,
            )
            
            if finder_result.emails and len(finder_result.emails) > 0:
                email_found = finder_result.emails[0].email
                source = "finder"
                logger.info(
                    "Email found via finder: email=%s",
                    email_found,
                )
                
                # Log activity for successful search
                try:
                    await activity_service.log_search_activity(
                        session=session,
                        user_id=current_user.uuid,
                        service_type=ActivityServiceType.EMAIL,
                        request_params={
                            "first_name": first_name,
                            "last_name": last_name,
                            "domain": domain_input,
                        },
                        result_count=1,
                        result_summary={
                            "email": email_found,
                            "source": source,
                            "emails_found": 1,
                        },
                        status=ActivityStatus.SUCCESS,
                        request=http_request,
                    )
                except Exception as log_exc:
                    logger.exception("Failed to log activity: %s", log_exc)
                
                return SingleEmailResponse(email=email_found, source=source)
            else:
                logger.debug("No emails found via finder")
        except HTTPException as http_exc:
            if http_exc.status_code == status.HTTP_404_NOT_FOUND:
                # Expected - no emails found in database
                logger.debug("No emails found in database (404), will try verifier")
            else:
                # Unexpected error, log and continue to verifier
                logger.warning(
                    "Email finder error: %s, will try verifier",
                    str(http_exc.detail),
                )
        except Exception as e:
            logger.warning(
                "Email finder exception: %s, will try verifier",
                str(e),
            )
        
        # Step 2: If not found, try email verifier
        if not email_found and bulk_verifier_service:
            try:
                logger.debug(
                    "Trying email verifier: first_name=%s last_name=%s domain=%s",
                    first_name,
                    last_name,
                    extracted_domain,
                )
                
                # Use the same logic as start_single_email_verification
                email_count = 1000
                
                # Generate all unique email patterns once
                all_unique_emails = generate_email_combinations(
                    first_name=first_name,
                    last_name=last_name,
                    domain=extracted_domain,
                    count=email_count,
                )
                total_unique_patterns = len(all_unique_emails)
                
                if total_unique_patterns == 0:
                    logger.debug("No unique patterns generated for verifier")
                else:
                    # Calculate number of batches needed
                    total_batches = (total_unique_patterns + email_count - 1) // email_count
                    
                    # Track verified emails to prevent duplicates
                    verified_emails_set = set()
                    
                    # Process emails in batches until we find a valid email
                    for batch_number in range(1, total_batches + 1):
                        # Calculate batch slice
                        start_idx = (batch_number - 1) * email_count
                        end_idx = min(start_idx + email_count, total_unique_patterns)
                        batch_emails = all_unique_emails[start_idx:end_idx]
                        
                        # Filter out already verified emails
                        batch_emails_to_check = [e for e in batch_emails if e not in verified_emails_set]
                        
                        if not batch_emails_to_check:
                            continue
                        
                        # Verify emails sequentially until first valid is found
                        valid_email, _ = await _verify_emails_sequential_until_valid(
                            emails=batch_emails_to_check,
                            service=bulk_verifier_service,
                            verified_emails_set=verified_emails_set,
                        )
                        
                        if valid_email:
                            email_found = valid_email
                            source = "verifier"
                            logger.info(
                                "Email found via verifier: email=%s (batch %d/%d)",
                                email_found,
                                batch_number,
                                total_batches,
                            )
                            break
                        
                        # Log activity for successful search via verifier
                        try:
                            await activity_service.log_search_activity(
                                session=session,
                                user_id=current_user.uuid,
                                service_type=ActivityServiceType.EMAIL,
                                request_params={
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "domain": domain_input,
                                },
                                result_count=1,
                                result_summary={
                                    "email": email_found,
                                    "source": source,
                                    "emails_found": 1,
                                },
                                status=ActivityStatus.SUCCESS,
                                request=http_request,
                            )
                        except Exception as log_exc:
                            logger.exception("Failed to log activity: %s", log_exc)
                        
                        break
                    
                    batch_number += 1
                
                if not found_valid:
                    logger.debug(
                        "No valid email found via verifier after checking %d unique patterns (%d batches)",
                        total_unique_patterns,
                        total_batches,
                    )
            except HTTPException as http_exc:
                logger.warning(
                    "Email verifier HTTP error: %s",
                    str(http_exc.detail),
                )
            except Exception as e:
                logger.warning(
                    "Email verifier exception: %s",
                    str(e),
                )
        elif not email_found and not bulk_verifier_service:
            logger.debug("Email verifier not available (credentials not configured)")
        
        # Log activity for no email found (successful search but no results)
        if not email_found:
            try:
                await activity_service.log_search_activity(
                    session=session,
                    user_id=current_user.uuid,
                    service_type=ActivityServiceType.EMAIL,
                    request_params={
                        "first_name": first_name,
                        "last_name": last_name,
                        "domain": domain_input,
                    },
                    result_count=0,
                    result_summary={
                        "emails_found": 0,
                        "source": None,
                    },
                    status=ActivityStatus.SUCCESS,
                    request=http_request,
                )
            except Exception as log_exc:
                logger.exception("Failed to log activity: %s", log_exc)
        
        # Return result
        logger.info(
            "Single email lookup completed: email=%s source=%s",
            email_found,
            source,
        )
        return SingleEmailResponse(email=email_found, source=source)
        
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
            logger.exception("Failed to log activity: %s", log_exc)
        raise
    except Exception as exc:
        logger.exception("Error getting single email: %s", exc)
        
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
            logger.exception("Failed to log activity: %s", log_exc)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email",
        ) from exc

