"""Email finder API endpoints."""

import asyncio
import csv
import io
import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
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
from app.services.bulkmailverifier_service import BulkMailVerifierService
from app.services.truelist_service import TruelistService
from app.services.email_finder_service import EmailFinderService
from app.services.export_service import ExportService
from app.utils.domain import extract_domain_from_url
from app.utils.email_generator import generate_email_combinations, _get_name_variations, _generate_tier1_patterns
from app.utils.signed_url import generate_signed_url
from app.utils.background_tasks import add_background_task_safe

settings = get_settings()

router = APIRouter(prefix="/email", tags=["Email"])
service = EmailFinderService()
export_service = ExportService()
activity_service = ActivityService()
credit_service = CreditService()
profile_repo = UserProfileRepository()

# Simple in-memory cache for recent email lookups (LRU cache with max 1000 entries)
_email_lookup_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
_cache_max_size = 1000
_cache_ttl_seconds = 300  # 5 minutes
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
    try:
        result = await service.find_emails(
            session=session,
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            website=website,
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
            pass
        
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
                
                # If we found valid emails, we can stop (or continue for more)
                # For now, we'll stop after finding at least one valid email
                if len(all_valid_emails) > 0:
                    break
        
        # Prepare response
        response = EmailVerifierResponse(
            valid_emails=all_valid_emails,
            total_valid=len(all_valid_emails),
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
            pass
        
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
            detail="Failed to verify emails",
        ) from exc


@router.post("/verifier/single/", response_model=SingleEmailVerifierFindResponse)
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
            return SingleEmailVerifierFindResponse(valid_email=None)
        
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
                    return SingleEmailVerifierFindResponse(valid_email=valid_email)
                    
            except HTTPException as http_exc:
                # Handle HTTPException from verification (e.g., credentials not configured)
                if "credentials not configured" in str(http_exc.detail).lower():
                    raise
                else:
                    # Re-raise other HTTPExceptions
                    raise
            except Exception as batch_exc:
                # Log error but continue with next batch
                pass
        
        # No valid email found after all patterns checked
        return SingleEmailVerifierFindResponse(valid_email=None)
        
    except HTTPException:
        raise
    except Exception as exc:
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


def _get_cache_key(first_name: str, last_name: str, domain: str) -> str:
    """Generate cache key for email lookup."""
    return f"{first_name.lower().strip()}|{last_name.lower().strip()}|{domain.lower().strip()}"


def _get_from_cache(cache_key: str) -> Optional[str]:
    """Get email from cache if valid."""
    global _email_lookup_cache
    if cache_key in _email_lookup_cache:
        email, timestamp = _email_lookup_cache[cache_key]
        if time.time() - timestamp < _cache_ttl_seconds:
            # Move to end (most recently used)
            _email_lookup_cache.move_to_end(cache_key)
            return email
        else:
            # Expired, remove it
            del _email_lookup_cache[cache_key]
    return None


def _store_in_cache(cache_key: str, email: str) -> None:
    """Store email in cache with LRU eviction."""
    global _email_lookup_cache
    # Remove oldest entries if cache is full
    while len(_email_lookup_cache) >= _cache_max_size:
        _email_lookup_cache.popitem(last=False)  # Remove oldest
    _email_lookup_cache[cache_key] = (email, time.time())


async def _verify_emails_batch_truelist(
    emails: list[str],
    service: TruelistService,
    timeout: float = 2.0,
) -> tuple[Optional[str], int]:
    """
    Optimized batch verification for Truelist - verifies all emails in a single API call.
    
    Truelist supports up to 3 emails per API call via verify_emails().
    This function batches all emails and verifies them in one request.
    
    Args:
        emails: List of email addresses to verify (up to 3 recommended)
        service: TruelistService instance
        timeout: Maximum time to wait for verification (default: 2.0 seconds)
        
    Returns:
        Tuple of (valid_email: str | None, emails_checked: int)
    """
    if not emails:
        return None, 0
    
    try:
        # Use asyncio.wait_for to enforce timeout
        results = await asyncio.wait_for(
            service.verify_emails(emails),
            timeout=timeout
        )
        
        # Check results for first valid email
        for email in emails:
            email_key = email.lower().strip()
            if email_key in results:
                result = results[email_key]
                mapped_status = result.get("mapped_status", "unknown")
                try:
                    status = EmailVerificationStatus(mapped_status)
                    if status == EmailVerificationStatus.VALID:
                        return email_key, len(emails)
                except ValueError:
                    pass
        
        return None, len(emails)
    except asyncio.TimeoutError:
        print(f"[BATCH_VERIFY] Timeout after {timeout}s for {len(emails)} emails")
        return None, 0
    except Exception as e:
        print(f"[BATCH_VERIFY] Error in batch verification: {type(e).__name__}: {str(e)}")
        return None, 0


async def _verify_emails_concurrent_until_valid(
    emails: list[str],
    service: BulkMailVerifierService,
    verified_emails_set: Optional[set[str]] = None,
    max_concurrent: int = 5,
) -> tuple[Optional[str], int]:
    """
    Verify emails concurrently until the first VALID email is found.
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        verified_emails_set: Optional set to track verified emails (will be updated in-place)
        max_concurrent: Maximum number of concurrent verifications (default: 5)
        
    Returns:
        Tuple of (valid_email: str | None, emails_checked: int)
        - valid_email: The first valid email found, or None if none found
        - emails_checked: Number of emails verified before stopping
    """
    print(f"[CONCURRENT_VERIFY] Starting concurrent verification: {len(emails)} emails, max_concurrent={max_concurrent}")
    # #region agent log
    import json as json_lib
    import time
    log_path = r"d:\code\ayan\contact360\.cursor\debug.log"
    verify_func_start = time.time()
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json_lib.dumps({"id": f"log_{int(verify_func_start * 1000)}_verify_concurrent_start", "timestamp": int(verify_func_start * 1000), "location": "email.py:717", "message": "_verify_emails_concurrent_until_valid start", "data": {"total_emails": len(emails), "max_concurrent": max_concurrent}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except: pass
    # #endregion agent log
    if not emails:
        print(f"[CONCURRENT_VERIFY] No emails to verify, returning None")
        return None, 0
    
    if verified_emails_set is None:
        verified_emails_set = set()
    
    emails_checked = 0
    valid_email_found = None
    semaphore = asyncio.Semaphore(max_concurrent)
    print(f"[CONCURRENT_VERIFY] Semaphore created with max_concurrent={max_concurrent}")
    
    async def verify_single(email: str) -> tuple[str, Optional[str]]:
        """Verify a single email and return (email, status)."""
        nonlocal emails_checked, valid_email_found
        if email in verified_emails_set or valid_email_found:
            print(f"[VERIFY_SINGLE] Skipping {email} - already verified or valid email found")
            return email, None
        
        async with semaphore:
            if valid_email_found:  # Check again after acquiring semaphore
                print(f"[VERIFY_SINGLE] Skipping {email} - valid email already found: {valid_email_found}")
                return email, None
            
            emails_checked += 1
            print(f"[VERIFY_SINGLE] [{emails_checked}/{len(emails)}] Verifying email: {email}")
            # #region agent log
            single_email_start = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(single_email_start * 1000)}_single_email_start", "timestamp": int(single_email_start * 1000), "location": "email.py:752", "message": "Single email verification start (concurrent)", "data": {"email_index": emails_checked, "email": email[:20] + "..." if len(email) > 20 else email}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except: pass
            # #endregion agent log
            try:
                result = await service.verify_single_email(email)
                # #region agent log
                single_email_end = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(single_email_end * 1000)}_single_email_end", "timestamp": int(single_email_end * 1000), "location": "email.py:753", "message": "Single email verification end (concurrent)", "data": {"elapsed_ms": (single_email_end - single_email_start) * 1000, "status": result.get("mapped_status", "unknown")}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except: pass
                # #endregion agent log
                mapped_status = result.get("mapped_status", "unknown")
                verified_emails_set.add(email)
                print(f"[VERIFY_SINGLE] Result for {email}: status={mapped_status}, result_keys={list(result.keys())}")
                
                try:
                    status = EmailVerificationStatus(mapped_status)
                except ValueError:
                    status = EmailVerificationStatus.UNKNOWN
                
                if status == EmailVerificationStatus.VALID:
                    if not valid_email_found:  # First valid email found
                        valid_email_found = email.lower().strip()
                        print(f"[VERIFY_SINGLE] ✓ VALID EMAIL FOUND: {valid_email_found}")
                    return email, "valid"
                
                print(f"[VERIFY_SINGLE] Email {email} status: {mapped_status} (not valid)")
                return email, mapped_status
            except Exception as e:
                print(f"[VERIFY_SINGLE] ✗ Error verifying {email}: {type(e).__name__}: {str(e)}")
                # #region agent log
                single_email_error = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(single_email_error * 1000)}_single_email_error", "timestamp": int(single_email_error * 1000), "location": "email.py:766", "message": "Single email verification error (concurrent)", "data": {"elapsed_ms": (single_email_error - single_email_start) * 1000, "error": str(e)[:100]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except: pass
                # #endregion agent log
                verified_emails_set.add(email)
                return email, None
    
    try:
        # Create tasks for all emails
        filtered_emails = [email for email in emails if email not in verified_emails_set]
        print(f"[CONCURRENT_VERIFY] Creating {len(filtered_emails)} verification tasks (filtered from {len(emails)} total)")
        tasks = [asyncio.create_task(verify_single(email)) for email in filtered_emails]
        
        # Wait for first valid email or all tasks complete
        for task in asyncio.as_completed(tasks):
            email, status = await task
            print(f"[CONCURRENT_VERIFY] Task completed for {email}: status={status}, valid_email_found={valid_email_found}")
            if status == "valid" and valid_email_found:
                # Cancel remaining tasks
                remaining = [t for t in tasks if not t.done()]
                print(f"[CONCURRENT_VERIFY] Valid email found! Cancelling {len(remaining)} remaining tasks")
                for t in remaining:
                    t.cancel()
                # Wait a bit for cancellations
                await asyncio.sleep(0.1)
                break
        
        # #region agent log
        verify_func_end = time.time()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"id": f"log_{int(verify_func_end * 1000)}_verify_concurrent_end", "timestamp": int(verify_func_end * 1000), "location": "email.py:772", "message": "_verify_emails_concurrent_until_valid end", "data": {"total_elapsed_ms": (verify_func_end - verify_func_start) * 1000, "emails_checked": emails_checked, "found": valid_email_found is not None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
        except: pass
        # #endregion agent log
        print(f"[CONCURRENT_VERIFY] Final result: valid_email={valid_email_found}, emails_checked={emails_checked}")
        return valid_email_found, emails_checked
        
    except Exception as e:
        print(f"[CONCURRENT_VERIFY] ✗ Exception in concurrent verification: {type(e).__name__}: {str(e)}")
        return valid_email_found, emails_checked


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
    # #region agent log
    import json as json_lib
    import time
    log_path = r"d:\code\ayan\contact360\.cursor\debug.log"
    verify_func_start = time.time()
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json_lib.dumps({"id": f"log_{int(verify_func_start * 1000)}_verify_func_start", "timestamp": int(verify_func_start * 1000), "location": "email.py:717", "message": "_verify_emails_sequential_until_valid start", "data": {"total_emails": len(emails)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
    except: pass
    # #endregion agent log
    if not emails:
        return None, 0
    
    if verified_emails_set is None:
        verified_emails_set = set()
    
    emails_checked = 0
    
    try:
        for email in emails:
            # Skip if already verified
            if email in verified_emails_set:
                continue
            
            emails_checked += 1
            
            # #region agent log
            single_email_start = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(single_email_start * 1000)}_single_email_start", "timestamp": int(single_email_start * 1000), "location": "email.py:752", "message": "Single email verification start", "data": {"email_index": emails_checked, "email": email[:20] + "..." if len(email) > 20 else email}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except: pass
            # #endregion agent log
            try:
                result = await service.verify_single_email(email)
                # #region agent log
                single_email_end = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(single_email_end * 1000)}_single_email_end", "timestamp": int(single_email_end * 1000), "location": "email.py:753", "message": "Single email verification end", "data": {"elapsed_ms": (single_email_end - single_email_start) * 1000, "status": result.get("mapped_status", "unknown")}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except: pass
                # #endregion agent log
                mapped_status = result.get("mapped_status", "unknown")
                
                # Add to verified set
                verified_emails_set.add(email)
                
                try:
                    status = EmailVerificationStatus(mapped_status)
                except ValueError:
                    status = EmailVerificationStatus.UNKNOWN
                
                if status == EmailVerificationStatus.VALID:
                    # #region agent log
                    verify_func_end = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(verify_func_end * 1000)}_verify_func_end", "timestamp": int(verify_func_end * 1000), "location": "email.py:764", "message": "_verify_emails_sequential_until_valid end (found)", "data": {"total_elapsed_ms": (verify_func_end - verify_func_start) * 1000, "emails_checked": emails_checked}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                    except: pass
                    # #endregion agent log
                    return email.lower().strip(), emails_checked
                
            except Exception as e:
                # #region agent log
                single_email_error = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(single_email_error * 1000)}_single_email_error", "timestamp": int(single_email_error * 1000), "location": "email.py:766", "message": "Single email verification error", "data": {"elapsed_ms": (single_email_error - single_email_start) * 1000, "error": str(e)[:100]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                except: pass
                # #endregion agent log
                # Still add to verified set to avoid retrying failed emails
                verified_emails_set.add(email)
                # Continue to next email on error
                continue
        
        # #region agent log
        verify_func_end = time.time()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"id": f"log_{int(verify_func_end * 1000)}_verify_func_end", "timestamp": int(verify_func_end * 1000), "location": "email.py:772", "message": "_verify_emails_sequential_until_valid end (not found)", "data": {"total_elapsed_ms": (verify_func_end - verify_func_start) * 1000, "emails_checked": emails_checked}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
        except: pass
        # #endregion agent log
        return None, emails_checked
        
    except Exception as e:
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
    
    Args:
        request: BulkEmailVerifierRequest with list of emails
        current_user: Current authenticated user
        
    Returns:
        BulkEmailVerifierResponse with verification results for each email
    """
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
            email_status_map = await _verify_emails_batch_direct(
                emails=request.emails,
                service=service,
                batch_size=20,  # Process 20 emails concurrently per batch
            )
        elif use_truelist:
            service = TruelistService()
            truelist_results = await service.verify_emails(request.emails)
            email_status_map = {
                email.lower().strip(): EmailVerificationStatus(
                    truelist_results.get(email.lower().strip(), {}).get(
                        "mapped_status", EmailVerificationStatus.UNKNOWN
                    )
                )
                for email in request.emails
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
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
            pass
        
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
            pass
        
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
    Verify a single email address through BulkMailVerifier service.
    
    Accepts a single email address and returns its verification status
    (valid, invalid, catchall, unknown).
    
    Args:
        request: SingleEmailVerifierRequest with single email
        current_user: Current authenticated user
        
    Returns:
        SingleEmailVerifierResponse with verification result for the email
    """
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
        elif use_truelist:
            service = TruelistService()
            result = await service.verify_single_email(request.email)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        
        # Map the result status to EmailVerificationStatus enum
        mapped_status = result.get("mapped_status", "unknown")
        try:
            verification_status = EmailVerificationStatus(mapped_status)
        except ValueError:
            verification_status = EmailVerificationStatus.UNKNOWN
        
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
            pass
        
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
                request_params={"email": request.email},
                result_count=0,
                status=ActivityStatus.FAILED,
                error_message=str(exc),
                request=http_request,
            )
        except Exception as activity_exc:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from exc


@router.post("/bulk/credits/", response_model=CreditsResponse)
async def check_credits(
    provider: EmailProvider = Query(..., description="Email verification provider"),
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
            credits_data = await service.check_credits()
            return CreditsResponse(**credits_data)

        elif provider == EmailProvider.TRUELIST:
            if not settings.TRUELIST_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Truelist API key not configured. Please set TRUELIST_API_KEY.",
                )
            # Truelist docs do not expose credits; return placeholder unknown
            return CreditsResponse(credits=None, raw_response="Truelist credits API not available")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        # Return response - handle both JSON and text responses
        return CreditsResponse(**credits_data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check credits",
        ) from exc


@router.post("/bulk/lists/", response_model=AllListsResponse)
async def get_all_lists(
    provider: EmailProvider = Query(..., description="Email verification provider"),
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
            lists_data = await service.get_all_lists()
        elif provider == EmailProvider.TRUELIST:
            if not settings.TRUELIST_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Truelist API key not configured. Please set TRUELIST_API_KEY.",
                )
            service = TruelistService()
            lists_data = await service.list_batches()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider}",
            )
        # Parse lists into EmailListInfo objects with better error handling
        lists = []
        raw_lists = lists_data.get("lists", [])
        
        for idx, list_item in enumerate(raw_lists):
            try:
                # Get slug first and validate it before creating mapped_item
                slug = list_item.get("slug") or ""
                # Skip items with missing or empty slug
                if not slug or not slug.strip():
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
                # Continue with other items instead of failing completely
                continue
        
        return AllListsResponse(lists=lists)
        
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lists: {str(exc)}",
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
        
    except HTTPException:
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
        await session.commit()
        
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
        
        # Import background task function
        from app.tasks.export_tasks import process_email_export
        
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
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export",
        ) from exc


@router.post("/single/", response_model=SingleEmailResponse)
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
    # #region agent log
    import json as json_lib
    start_time = time.time()
    log_path = r"d:\code\ayan\contact360\.cursor\debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json_lib.dumps({"id": f"log_{int(start_time * 1000)}_entry", "timestamp": int(start_time * 1000), "location": "email.py:1479", "message": "get_single_email entry", "data": {"first_name": request.first_name, "last_name": request.last_name, "domain": request.domain or request.website}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "ALL"}) + "\n")
    except: pass
    # #endregion agent log
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
        
        # Check cache first for fast response
        cache_key = _get_cache_key(first_name, last_name, extracted_domain)
        cached_email = _get_from_cache(cache_key)
        if cached_email:
            print(f"[EMAIL_SINGLE] Cache hit for {cache_key}: {cached_email}")
            # #region agent log
            cache_hit_time = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(cache_hit_time * 1000)}_cache_hit", "timestamp": int(cache_hit_time * 1000), "location": "email.py:cache", "message": "Cache hit", "data": {"elapsed_ms": (cache_hit_time - start_time) * 1000, "email": cached_email}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "CACHE"}) + "\n")
            except: pass
            # #endregion agent log
            return SingleEmailResponse(email=cached_email, source="cache")
        
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
        
        # Step 1: Try email finder (database search) with timeout
        # #region agent log
        step1_start = time.time()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"id": f"log_{int(step1_start * 1000)}_step1_start", "timestamp": int(step1_start * 1000), "location": "email.py:1516", "message": "Step 1: Database search start", "data": {"elapsed_ms": (step1_start - start_time) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
        except: pass
        # #endregion agent log
        try:
            # Add timeout to database query (tight 0.75s to avoid long waits)
            finder_result = await asyncio.wait_for(
                email_finder_service.find_emails(
                    session=session,
                    first_name=first_name,
                    last_name=last_name,
                    domain=extracted_domain,
                ),
                timeout=0.75
            )
            # #region agent log
            step1_end = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(step1_end * 1000)}_step1_end", "timestamp": int(step1_end * 1000), "location": "email.py:1523", "message": "Step 1: Database search end", "data": {"elapsed_ms": (step1_end - step1_start) * 1000, "found": len(finder_result.emails) if finder_result.emails else 0}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
            except: pass
            # #endregion agent log
            
            if finder_result.emails and len(finder_result.emails) > 0:
                email_found = finder_result.emails[0].email
                source = "finder"
                
                # Store in cache for future requests
                _store_in_cache(cache_key, email_found)
                
                # Log activity for successful search
                # #region agent log
                activity_log_start = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(activity_log_start * 1000)}_activity_start", "timestamp": int(activity_log_start * 1000), "location": "email.py:1529", "message": "Activity logging start", "data": {"elapsed_ms": (activity_log_start - start_time) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "D"}) + "\n")
                except: pass
                # #endregion agent log
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
                    # #region agent log
                    activity_log_end = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(activity_log_end * 1000)}_activity_end", "timestamp": int(activity_log_end * 1000), "location": "email.py:1548", "message": "Activity logging end", "data": {"elapsed_ms": (activity_log_end - activity_log_start) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "D"}) + "\n")
                    except: pass
                    # #endregion agent log
                except Exception as log_exc:
                    print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Failed to log activity (finder): {type(log_exc).__name__}: {str(log_exc)}")
                    try:
                        await session.rollback()
                        print("[EMAIL_VERIFIER][ACTIVITY] Rolled back session after logging failure (finder)")
                    except Exception as rb_exc:
                        print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Rollback failed after logging failure (finder): {type(rb_exc).__name__}: {str(rb_exc)}")
                
                # #region agent log
                total_time = time.time()
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"id": f"log_{int(total_time * 1000)}_exit", "timestamp": int(total_time * 1000), "location": "email.py:1551", "message": "get_single_email exit (finder)", "data": {"total_elapsed_ms": (total_time - start_time) * 1000, "source": "finder"}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "ALL"}) + "\n")
                except: pass
                # #endregion agent log
                return SingleEmailResponse(email=email_found, source=source)
        except asyncio.TimeoutError:
            # Database query timed out (>5s), skip to verifier
            # #region agent log
            step1_timeout = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(step1_timeout * 1000)}_step1_timeout", "timestamp": int(step1_timeout * 1000), "location": "email.py:1552", "message": "Step 1: Database search timeout", "data": {"elapsed_ms": (step1_timeout - step1_start) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}) + "\n")
            except: pass
            # #endregion agent log
            pass
        except HTTPException as http_exc:
            if http_exc.status_code == status.HTTP_404_NOT_FOUND:
                # Expected - no emails found in database
                pass
            else:
                # Unexpected error, continue to verifier
                pass
        except Exception as e:
            # Continue to verifier
            pass
        
        # Step 2: If not found, try email verifier with overall timeout
        if not email_found:
            if not bulk_verifier_service:
                print(f"[EMAIL_VERIFIER] BulkMailVerifier service not available (credentials not configured)")
            else:
                print(f"[EMAIL_VERIFIER] Email not found in database, proceeding to verification step")
        if not email_found and bulk_verifier_service:
            print(f"[EMAIL_VERIFIER] Step 2: Starting email verification for {first_name} {last_name} @ {extracted_domain}")
            # #region agent log
            step2_start = time.time()
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"id": f"log_{int(step2_start * 1000)}_step2_start", "timestamp": int(step2_start * 1000), "location": "email.py:1564", "message": "Step 2: Email verifier start", "data": {"elapsed_ms": (step2_start - start_time) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
            except: pass
            # #endregion agent log
            tier1_emails = []  # Initialize for exception handler
            try:
                # Wrap entire verification step in timeout (3 seconds max)
                async def _verification_work():
                    nonlocal tier1_emails
                    # OPTIMIZATION: Generate only Tier 1 patterns first (most common, 60-70% coverage)
                    print(f"[EMAIL_VERIFIER] Generating Tier 1 email patterns...")
                    # #region agent log
                    pattern_gen_start = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(pattern_gen_start * 1000)}_pattern_start", "timestamp": int(pattern_gen_start * 1000), "location": "email.py:1570", "message": "Email pattern generation start (Tier 1 only)", "data": {"elapsed_ms": (pattern_gen_start - start_time) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
                    except: pass
                    # #endregion agent log
                    
                    # Generate Tier 1 patterns first (most common patterns)
                    vars = _get_name_variations(first_name, last_name)
                    print(f"[EMAIL_VERIFIER] Name variations: fn={vars.get('fn')}, ln={vars.get('ln')}, f_initial={vars.get('f_initial')}, l_initial={vars.get('l_initial')}")
                    tier1_patterns = _generate_tier1_patterns(vars)
                    print(f"[EMAIL_VERIFIER] Generated {len(tier1_patterns)} Tier 1 patterns: {tier1_patterns}")
                    tier1_emails = [f"{pattern}@{extracted_domain}" for pattern in tier1_patterns if pattern and len(pattern) <= 64]
                    # Limit to top 3 patterns for fast verification (Truelist rate limit friendly)
                    tier1_emails = tier1_emails[:3]
                    print(f"[EMAIL_VERIFIER] Created {len(tier1_emails)} email addresses to verify (trimmed): {tier1_emails}")
                    # #region agent log
                    tier1_log_ts = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(tier1_log_ts * 1000)}_tier1_count", "timestamp": int(tier1_log_ts * 1000), "location": "email.py:1573", "message": "Tier1 patterns ready", "data": {"tier1_count": len(tier1_emails)}, "sessionId": "debug-session", "runId": "run-debug1", "hypothesisId": "H2"}) + "\n")
                    except:
                        pass
                    # #endregion agent log
                    
                    # #region agent log
                    pattern_gen_end = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(pattern_gen_end * 1000)}_pattern_end", "timestamp": int(pattern_gen_end * 1000), "location": "email.py:1576", "message": "Email pattern generation end (Tier 1 only)", "data": {"elapsed_ms": (pattern_gen_end - pattern_gen_start) * 1000, "total_patterns": len(tier1_emails)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
                    except: pass
                    # #endregion agent log
                    
                    if not tier1_emails:
                        print(f"[EMAIL_VERIFIER] No Tier 1 email patterns generated, skipping verification")
                        return None, 0
                    
                    # Track verified emails to prevent duplicates
                    verified_emails_set = set()
                    
                    # OPTIMIZATION: Use batch verification for Truelist (single API call for all 3 emails)
                    # #region agent log
                    verify_start = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(verify_start * 1000)}_verify_start", "timestamp": int(verify_start * 1000), "location": "email.py:1599", "message": "Email verification start", "data": {"elapsed_ms": (verify_start - start_time) * 1000, "emails_to_check": len(tier1_emails), "use_batch": use_truelist}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                    except: pass
                    # #endregion agent log
                    
                    # Use optimized batch verification for Truelist (single API call)
                    if use_truelist and isinstance(bulk_verifier_service, TruelistService):
                        print(f"[EMAIL_VERIFIER] Using batch verification for Truelist ({len(tier1_emails)} emails in one call)")
                        valid_email, emails_checked = await _verify_emails_batch_truelist(
                            emails=tier1_emails,
                            service=bulk_verifier_service,
                            timeout=2.0,  # 2 second timeout for batch call
                        )
                    else:
                        # Use concurrent verification for other providers
                        print(f"[EMAIL_VERIFIER] Starting concurrent verification of {len(tier1_emails)} emails (max 5 concurrent)")
                        max_concurrent = 5
                        valid_email, emails_checked = await _verify_emails_concurrent_until_valid(
                            emails=tier1_emails,
                            service=bulk_verifier_service,
                            verified_emails_set=verified_emails_set,
                            max_concurrent=max_concurrent,
                        )
                    print(f"[EMAIL_VERIFIER] Verification completed: checked {emails_checked} emails, valid_email={valid_email}")
                    # #region agent log
                    post_verify_ts = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(post_verify_ts * 1000)}_verify_summary", "timestamp": int(post_verify_ts * 1000), "location": "email.py:1602", "message": "Verification summary", "data": {"emails_checked": emails_checked, "valid_email": bool(valid_email), "max_concurrent": max_concurrent if not use_truelist else "batch"}, "sessionId": "debug-session", "runId": "run-debug1", "hypothesisId": "H3"}) + "\n")
                    except:
                        pass
                    # #endregion agent log
                    verify_end = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(verify_end * 1000)}_verify_end", "timestamp": int(verify_end * 1000), "location": "email.py:1604", "message": "Email verification end", "data": {"elapsed_ms": (verify_end - verify_start) * 1000, "found": valid_email is not None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
                    except: pass
                    # #endregion agent log
                    
                    if valid_email:
                        return valid_email, emails_checked
                    return None, emails_checked
                
                # Execute verification with overall timeout (3 seconds)
                try:
                    valid_email, emails_checked = await asyncio.wait_for(
                        _verification_work(),
                        timeout=3.0
                    )
                    if valid_email:
                        email_found = valid_email
                        source = "verifier"
                        print(f"[EMAIL_VERIFIER] ✓ Valid email found: {valid_email} (source: {source})")
                        
                        # Store in cache for future requests
                        _store_in_cache(cache_key, email_found)
                        
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
                            print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Failed to log activity (verifier): {type(log_exc).__name__}: {str(log_exc)}")
                            try:
                                await session.rollback()
                                print("[EMAIL_VERIFIER][ACTIVITY] Rolled back session after logging failure (verifier)")
                            except Exception as rb_exc:
                                print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Rollback failed after logging failure (verifier): {type(rb_exc).__name__}: {str(rb_exc)}")
                except asyncio.TimeoutError:
                    print(f"[EMAIL_VERIFIER] Verification step timed out after 3 seconds")
                    # #region agent log
                    timeout_ts = time.time()
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"id": f"log_{int(timeout_ts * 1000)}_verify_timeout", "timestamp": int(timeout_ts * 1000), "location": "email.py:verify_timeout", "message": "Verification timeout", "data": {"elapsed_ms": (timeout_ts - step2_start) * 1000}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "TIMEOUT"}) + "\n")
                    except: pass
                    # #endregion agent log
                
            except HTTPException as verifier_exc:
                print(f"[EMAIL_VERIFIER] ✗ Verification failed with HTTP exception: {type(verifier_exc).__name__}: {str(verifier_exc.detail) if hasattr(verifier_exc, 'detail') else str(verifier_exc)}")
                # If rate limited, return fast with best-guess pattern
                if getattr(verifier_exc, "status_code", None) == status.HTTP_429_TOO_MANY_REQUESTS and tier1_emails and len(tier1_emails) > 0:
                    fallback_email = tier1_emails[0]
                    source = "pattern_fallback"
                    return SingleEmailResponse(email=fallback_email, source=source)
                # Otherwise continue
                pass  # Continue if verifier fails
            except Exception as verifier_exc:
                print(f"[EMAIL_VERIFIER] ✗ Verification failed with exception: {type(verifier_exc).__name__}: {str(verifier_exc)}")
                pass  # Continue if verifier fails
        
        # Log activity for no email found (successful search but no results)
        if not email_found:
            print(f"[EMAIL_VERIFIER] No email found after verification step")
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
                print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Failed to log activity (no results): {type(log_exc).__name__}: {str(log_exc)}")
                try:
                    await session.rollback()
                    print("[EMAIL_VERIFIER][ACTIVITY] Rolled back session after logging failure (no results)")
                except Exception as rb_exc:
                    print(f"[EMAIL_VERIFIER][ACTIVITY] ✗ Rollback failed after logging failure (no results): {type(rb_exc).__name__}: {str(rb_exc)}")
        
        # Return result
        # #region agent log
        total_time = time.time()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"id": f"log_{int(total_time * 1000)}_exit", "timestamp": int(total_time * 1000), "location": "email.py:1664", "message": "get_single_email exit", "data": {"total_elapsed_ms": (total_time - start_time) * 1000, "source": source, "email_found": email_found is not None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "ALL"}) + "\n")
        except: pass
        # #endregion agent log
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
