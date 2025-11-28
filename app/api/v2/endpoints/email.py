"""Email finder API endpoints."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.email import (
    AllListsResponse,
    BulkEmailVerifierRequest,
    BulkEmailVerifierResponse,
    CreditsResponse,
    EmailListInfo,
    EmailVerificationStatus,
    EmailVerifierRequest,
    EmailVerifierResponse,
    SimpleEmailFinderResponse,
    SingleEmailVerifierFindResponse,
    SingleEmailVerifierRequest,
    SingleEmailVerifierResponse,
    VerifiedEmailResult,
)
from app.services.bulkmailverifier_service import BulkMailVerifierService
from app.services.email_finder_service import EmailFinderService
from app.utils.domain import extract_domain_from_url
from app.utils.email_generator import generate_email_combinations

settings = get_settings()

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
    current_user: User = Depends(get_current_user),
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
        current_user.id,
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
        
        # Get email_count and max_retries from request (with defaults)
        email_count = request.email_count if request.email_count is not None else 1000
        max_retries = request.max_retries if request.max_retries is not None else settings.BULKMAILVERIFIER_MAX_RETRIES
        logger.info(
            "Parameters: email_count=%d (requested=%s) max_retries=%d (requested=%s, config_default=%s)",
            email_count,
            request.email_count,
            max_retries,
            request.max_retries,
            settings.BULKMAILVERIFIER_MAX_RETRIES,
        )
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            logger.warning("Validation failed: email_count=%d is less than minimum of 1", email_count)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        
        if max_retries < 1:
            logger.warning("Validation failed: max_retries=%d is less than minimum of 1", max_retries)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_retries must be at least 1",
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
                "BulkMailVerifier credentials not configured. Generating emails without verification."
            )
            # Generate emails but skip verification
            all_generated_emails = []
            logger.info("Email generation: Starting generation without verification for %d batches", max_retries)
            for batch_num in range(1, max_retries + 1):
                logger.debug("Email generation: Generating batch %d/%d", batch_num, max_retries)
                batch_emails = generate_email_combinations(
                    first_name=first_name,
                    last_name=last_name,
                    domain=extracted_domain,
                    count=email_count,
                )
                logger.debug("Email generation: Batch %d generated %d emails", batch_num, len(batch_emails))
                all_generated_emails.extend(batch_emails)
            
            # Remove duplicates
            before_dedup = len(all_generated_emails)
            all_generated_emails = list(set(all_generated_emails))
            after_dedup = len(all_generated_emails)
            logger.debug(
                "Email generation: Deduplication: before=%d after=%d duplicates_removed=%d",
                before_dedup,
                after_dedup,
                before_dedup - after_dedup,
            )
            
            logger.info(
                "Email generation completed: total_generated=%d (credentials not configured, no verification)",
                len(all_generated_emails),
            )
            
            return EmailVerifierResponse(
                valid_emails=[],
                total_valid=0,
                generated_emails=all_generated_emails,
                total_generated=len(all_generated_emails),
                total_batches_processed=0,
            )
        
        # Initialize BulkMailVerifier service
        logger.info("Service initialization: Creating BulkMailVerifierService instance")
        service = BulkMailVerifierService()
        logger.debug("Service initialization: BulkMailVerifierService created successfully")
        
        # Generate first batch of emails to track all generated emails
        logger.info(
            "Starting email verification flow: first_name=%s last_name=%s domain=%s email_count=%d max_retries=%d",
            first_name,
            last_name,
            extracted_domain,
            email_count,
            max_retries,
        )
        
        all_generated_emails = []
        all_valid_emails = []
        total_batches_processed = 0
        batch_number = 1
        verification_error_occurred = False
        
        # Keep trying batches until we find valid emails or hit max retries
        logger.info("Batch loop: Starting batch processing loop (max_retries=%d)", max_retries)
        while batch_number <= max_retries:
            logger.info(
                "Batch loop: Entering batch %d/%d for first_name=%s last_name=%s domain=%s",
                batch_number,
                max_retries,
                first_name,
                last_name,
                extracted_domain,
            )
            
            # Generate emails for this batch
            logger.debug("Email generation: Generating emails for batch %d", batch_number)
            batch_emails = generate_email_combinations(
                first_name=first_name,
                last_name=last_name,
                domain=extracted_domain,
                count=email_count,
            )
            logger.info(
                "Email generation: Batch %d generated %d emails (requested=%d)",
                batch_number,
                len(batch_emails),
                email_count,
            )
            all_generated_emails.extend(batch_emails)
            logger.debug(
                "Email generation: Total generated so far: %d emails across %d batches",
                len(all_generated_emails),
                batch_number,
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
            
            batch_number += 1
            logger.debug("Batch loop: Completed iteration for batch %d, moving to next batch", batch_number - 1)
        
        logger.info("Batch loop: Exited batch processing loop after %d batches", batch_number - 1)
        
        # Remove duplicates from generated emails list
        before_dedup = len(all_generated_emails)
        all_generated_emails = list(set(all_generated_emails))
        after_dedup = len(all_generated_emails)
        logger.info(
            "Deduplication: Removed duplicates from generated emails: before=%d after=%d duplicates_removed=%d",
            before_dedup,
            after_dedup,
            before_dedup - after_dedup,
        )
        
        if verification_error_occurred:
            logger.warning(
                "Email verification stopped due to configuration error. "
                "Generated %d emails but could not verify them. "
                "Please configure BULKMAILVERIFIER_EMAIL and BULKMAILVERIFIER_PASSWORD environment variables.",
                len(all_generated_emails),
            )
        else:
            logger.info(
                "Email verification completed successfully: total_valid=%d total_generated=%d batches_processed=%d",
                len(all_valid_emails),
                len(all_generated_emails),
                total_batches_processed,
            )
        
        # Prepare response
        logger.debug(
            "Response preparation: Preparing EmailVerifierResponse with valid_emails=%d generated_emails=%d batches=%d",
            len(all_valid_emails),
            len(all_generated_emails),
            total_batches_processed,
        )
        response = EmailVerifierResponse(
            valid_emails=all_valid_emails,
            total_valid=len(all_valid_emails),
            generated_emails=all_generated_emails,
            total_generated=len(all_generated_emails),
            total_batches_processed=total_batches_processed,
        )
        logger.info(
            "Response prepared: Returning response with total_valid=%d total_generated=%d total_batches_processed=%d",
            response.total_valid,
            response.total_generated,
            response.total_batches_processed,
        )
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error verifying emails: %s", exc)
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
        current_user.id,
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
        
        # Get email_count and max_retries from request (with defaults)
        email_count = request.email_count if request.email_count is not None else 1000
        max_retries = request.max_retries if request.max_retries is not None else settings.BULKMAILVERIFIER_MAX_RETRIES
        logger.info(
            "Parameters: email_count=%d (requested=%s) max_retries=%d (requested=%s, config_default=%s)",
            email_count,
            request.email_count,
            max_retries,
            request.max_retries,
            settings.BULKMAILVERIFIER_MAX_RETRIES,
        )
        
        # Validate minimum values (schema validation handles this, but double-check for safety)
        if email_count < 1:
            logger.warning("Validation failed: email_count=%d is less than minimum of 1", email_count)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email_count must be at least 1",
            )
        
        if max_retries < 1:
            logger.warning("Validation failed: max_retries=%d is less than minimum of 1", max_retries)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_retries must be at least 1",
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
        
        # Start email verification flow
        logger.info(
            "Starting single email verification flow: first_name=%s last_name=%s domain=%s email_count=%d max_retries=%d",
            first_name,
            last_name,
            extracted_domain,
            email_count,
            max_retries,
        )
        
        batch_number = 1
        total_emails_checked = 0
        
        # Keep trying batches until we find a valid email or hit max retries
        logger.info("Batch loop: Starting batch processing loop (max_retries=%d)", max_retries)
        while batch_number <= max_retries:
            logger.info(
                "Batch loop: Entering batch %d/%d for first_name=%s last_name=%s domain=%s",
                batch_number,
                max_retries,
                first_name,
                last_name,
                extracted_domain,
            )
            
            # Generate emails for this batch
            logger.debug("Email generation: Generating emails for batch %d", batch_number)
            batch_emails = generate_email_combinations(
                first_name=first_name,
                last_name=last_name,
                domain=extracted_domain,
                count=email_count,
            )
            logger.info(
                "Email generation: Batch %d generated %d emails (requested=%d)",
                batch_number,
                len(batch_emails),
                email_count,
            )
            
            # Verify emails sequentially until first valid is found
            try:
                valid_email, emails_checked = await _verify_emails_sequential_until_valid(
                    emails=batch_emails,
                    service=service,
                )
                
                total_emails_checked += emails_checked
                
                if valid_email:
                    logger.info(
                        "Found valid email in batch %d: email=%s (checked %d emails in this batch, %d total)",
                        batch_number,
                        valid_email,
                        emails_checked,
                        total_emails_checked,
                    )
                    return SingleEmailVerifierFindResponse(valid_email=valid_email)
                else:
                    logger.info(
                        "Batch %d: No valid email found (checked %d emails in this batch, %d total)",
                        batch_number,
                        emails_checked,
                        total_emails_checked,
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
            
            batch_number += 1
            logger.debug("Batch loop: Completed iteration for batch %d, moving to next batch", batch_number - 1)
        
        logger.info(
            "Batch loop: Exited batch processing loop after %d batches. No valid email found after checking %d emails.",
            batch_number - 1,
            total_emails_checked,
        )
        
        # No valid email found after all batches
        logger.info(
            "Single email verification completed: no valid email found after checking %d emails across %d batches",
            total_emails_checked,
            batch_number - 1,
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
) -> tuple[Optional[str], int]:
    """
    Verify emails sequentially until the first VALID email is found.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        
    Returns:
        Tuple of (valid_email: str | None, emails_checked: int)
        - valid_email: The first valid email found, or None if none found
        - emails_checked: Number of emails verified before stopping
    """
    if not emails:
        logger.warning("_verify_emails_sequential_until_valid: Empty email list provided")
        return None, 0
    
    logger.info(
        "Sequential verification: Starting sequential verification of %d emails until first VALID found",
        len(emails),
    )
    
    emails_checked = 0
    
    try:
        for email in emails:
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
        current_user.id,
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
        
        return BulkEmailVerifierResponse(
            results=results,
            total=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            catchall_count=catchall_count,
            unknown_count=unknown_count,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in bulk email verification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify emails",
        ) from exc


@router.post("/single/verifier/", response_model=SingleEmailVerifierResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
async def single_email_verifier(
    request: SingleEmailVerifierRequest,
    current_user: User = Depends(get_current_user),
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
        current_user.id,
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
        
        return SingleEmailVerifierResponse(
            result=VerifiedEmailResult(email=request.email, status=verification_status),
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error in single email verification: %s", exc)
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
        current_user.id,
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
            current_user.id,
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
        current_user.id,
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
        
        # Parse lists into EmailListInfo objects
        lists = [
            EmailListInfo(**list_item) for list_item in lists_data.get("lists", [])
        ]
        
        logger.info(
            "Get all lists completed: user_id=%s lists_count=%d",
            current_user.id,
            len(lists),
        )
        
        return AllListsResponse(lists=lists)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting lists: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get lists",
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
        current_user.id,
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
            current_user.id,
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

