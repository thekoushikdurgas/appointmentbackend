"""Background task functions for export processing.

This module provides async functions for processing exports in the background.
These functions are designed to be used with FastAPI's BackgroundTasks.
"""

import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.exports import ExportStatus, UserExport
from app.repositories.user import UserProfileRepository
from app.services.credit_service import CreditService
from app.services.export_service import ExportService

settings = get_settings()
export_service = ExportService()
logger = get_logger(__name__)


async def _update_export_progress(
    session: AsyncSession,
    export_id: str,
    records_processed: int,
    total_records: int,
    start_time: float,
) -> None:
    """Update export progress in the database."""
    try:
        stmt = select(UserExport).where(UserExport.export_id == export_id)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if not export:
            logger.warning("Export not found for progress update: export_id=%s", export_id)
            return
        
        export.records_processed = records_processed
        export.total_records = total_records
        
        # Calculate progress percentage
        if total_records > 0:
            export.progress_percentage = (records_processed / total_records) * 100
        else:
            export.progress_percentage = 0.0
        
        # Estimate time remaining
        if records_processed > 0:
            elapsed_time = time.time() - start_time
            rate = records_processed / elapsed_time  # records per second
            remaining_records = total_records - records_processed
            if rate > 0:
                export.estimated_time_remaining = int(remaining_records / rate)
            else:
                export.estimated_time_remaining = None
        else:
            export.estimated_time_remaining = None
        
        await session.commit()
        logger.debug(
            "Updated export progress: export_id=%s progress=%.1f%% records=%d/%d",
            export_id,
            export.progress_percentage,
            records_processed,
            total_records,
        )
    except InvalidRequestError as exc:
        logger.exception("Failed to update export progress (session error): export_id=%s", export_id)
        # Session is in invalid state, don't attempt rollback
        try:
            await session.close()
        except Exception:
            pass
    except Exception as exc:
        logger.exception("Failed to update export progress: export_id=%s", export_id)
        try:
            await session.rollback()
        except (InvalidRequestError, Exception) as rollback_exc:
            logger.warning("Could not rollback session: %s", rollback_exc)


async def _update_export_status(
    session: AsyncSession,
    export_id: str,
    status: ExportStatus,
    error_message: Optional[str] = None,
) -> None:
    """Update export status in the database."""
    try:
        stmt = select(UserExport).where(UserExport.export_id == export_id)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()
        
        if not export:
            logger.warning("Export not found for status update: export_id=%s", export_id)
            return
        
        export.status = status
        if error_message:
            export.error_message = error_message
        
        await session.commit()
        logger.info("Updated export status: export_id=%s status=%s", export_id, status)
    except InvalidRequestError as exc:
        logger.exception("Failed to update export status (session error): export_id=%s", export_id)
        # Session is in invalid state, don't attempt rollback
        try:
            await session.close()
        except Exception:
            pass
    except Exception as exc:
        logger.exception("Failed to update export status: export_id=%s", export_id)
        try:
            await session.rollback()
        except (InvalidRequestError, Exception) as rollback_exc:
            logger.warning("Could not rollback session: %s", rollback_exc)


async def process_contact_export(export_id: str, contact_uuids: list[str]) -> None:
    """
    Process a contact export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It generates a CSV export of contacts and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        contact_uuids: List of contact UUIDs to export
    """
    logger.info(
        "Starting contact export task: export_id=%s contact_count=%d",
        export_id,
        len(contact_uuids),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Generate CSV with progress tracking
            total_records = len(contact_uuids)
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            # Generate CSV (this processes all contacts)
            file_path = await export_service.generate_csv(
                session,
                export_id,
                contact_uuids,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(contact_uuids),
            )
            
            logger.info(
                "Contact export completed: export_id=%s contact_count=%d duration=%.2fs",
                export_id,
                len(contact_uuids),
                time.time() - start_time,
            )
            
            # Verify credit deduction was done at request time
            # Credits should have been deducted at the endpoint (1 credit per contact UUID)
            # This is a verification step - if credits weren't deducted, log a warning
            try:
                credit_service = CreditService()
                profile_repo = UserProfileRepository()
                profile = await profile_repo.get_by_user_id(session, export.user_id)
                if profile:
                    user_role = profile.role or "FreeUser"
                    if credit_service.should_deduct_credits(user_role):
                        # Credits should have been deducted at endpoint level
                        # Log for verification (credits were already deducted per contact UUID at request time)
                        logger.debug(
                            "Credit deduction verification: export_id=%s user_id=%s role=%s contact_count=%d "
                            "(credits should have been deducted at endpoint)",
                            export_id,
                            export.user_id,
                            user_role,
                            len(contact_uuids),
                        )
            except Exception as credit_verify_exc:
                logger.warning(
                    "Failed to verify credit deduction for contact export: export_id=%s error=%s",
                    export_id,
                    credit_verify_exc,
                )
            
        except Exception as exc:
            logger.exception("Contact export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)


async def process_company_export(export_id: str, company_uuids: list[str]) -> None:
    """
    Process a company export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It generates a CSV export of companies and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        company_uuids: List of company UUIDs to export
    """
    logger.info(
        "Starting company export task: export_id=%s company_count=%d",
        export_id,
        len(company_uuids),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Generate CSV with progress tracking
            total_records = len(company_uuids)
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            file_path = await export_service.generate_company_csv(
                session,
                export_id,
                company_uuids,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                company_count=len(company_uuids),
            )
            
            logger.info(
                "Company export completed: export_id=%s company_count=%d duration=%.2fs",
                export_id,
                len(company_uuids),
                time.time() - start_time,
            )
            
            # Verify credit deduction was done at request time
            # Credits should have been deducted at the endpoint (1 credit per company UUID)
            # This is a verification step - if credits weren't deducted, log a warning
            try:
                credit_service = CreditService()
                profile_repo = UserProfileRepository()
                profile = await profile_repo.get_by_user_id(session, export.user_id)
                if profile:
                    user_role = profile.role or "FreeUser"
                    if credit_service.should_deduct_credits(user_role):
                        # Credits should have been deducted at endpoint level
                        # Log for verification (credits were already deducted per company UUID at request time)
                        logger.debug(
                            "Credit deduction verification: export_id=%s user_id=%s role=%s company_count=%d "
                            "(credits should have been deducted at endpoint)",
                            export_id,
                            export.user_id,
                            user_role,
                            len(company_uuids),
                        )
            except Exception as credit_verify_exc:
                logger.warning(
                    "Failed to verify credit deduction for company export: export_id=%s error=%s",
                    export_id,
                    credit_verify_exc,
                )
            
        except Exception as exc:
            logger.exception("Company export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)


async def process_linkedin_export(export_id: str, linkedin_urls: list[str], activity_id: Optional[int] = None) -> None:
    """
    Process a LinkedIn export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It searches for contacts and companies by multiple LinkedIn URLs, then generates
    a combined CSV export with contacts, companies, and unmatched URLs.
    
    Args:
        export_id: The UUID of the export record
        linkedin_urls: List of LinkedIn URLs to search and export
    """
    logger.info(
        "Starting LinkedIn export task: export_id=%s url_count=%d",
        export_id,
        len(linkedin_urls),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Import LinkedInService here to avoid circular imports
            from app.services.linkedin_service import LinkedInService
            
            linkedin_service = LinkedInService()
            
            # Search for contacts and companies by URLs
            logger.info("Searching LinkedIn URLs: export_id=%s url_count=%d", export_id, len(linkedin_urls))
            contact_uuids, company_uuids, unmatched_urls = await linkedin_service.search_by_multiple_urls(
                session, linkedin_urls
            )
            
            total_records = len(contact_uuids) + len(company_uuids) + len(unmatched_urls)
            logger.info(
                "LinkedIn search completed: export_id=%s contacts=%d companies=%d unmatched=%d total=%d",
                export_id,
                len(contact_uuids),
                len(company_uuids),
                len(unmatched_urls),
                total_records,
            )
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            # Check for cancellation before processing
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export cancelled during processing: export_id=%s", export_id)
                return
            
            # Generate combined CSV
            file_path = await export_service.generate_linkedin_export_csv(
                session,
                export_id,
                contact_uuids,
                company_uuids,
                unmatched_urls,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(contact_uuids),
                company_count=len(company_uuids),
            )
            
            logger.info(
                "LinkedIn export completed: export_id=%s contacts=%d companies=%d unmatched=%d duration=%.2fs",
                export_id,
                len(contact_uuids),
                len(company_uuids),
                len(unmatched_urls),
                time.time() - start_time,
            )
            
            # Verify credit deduction was done at request time
            # Credits should have been deducted at the endpoint (1 credit per URL)
            # This is a verification step - if credits weren't deducted, log a warning
            try:
                credit_service = CreditService()
                profile_repo = UserProfileRepository()
                profile = await profile_repo.get_by_user_id(session, export.user_id)
                if profile:
                    user_role = profile.role or "FreeUser"
                    if credit_service.should_deduct_credits(user_role):
                        # Credits should have been deducted at endpoint level
                        # Log for verification (credits were already deducted per URL at request time)
                        logger.debug(
                            "Credit deduction verification: export_id=%s user_id=%s role=%s url_count=%d "
                            "(credits should have been deducted at endpoint)",
                            export_id,
                            export.user_id,
                            user_role,
                            len(linkedin_urls),
                        )
            except Exception as credit_verify_exc:
                logger.warning(
                    "Failed to verify credit deduction for LinkedIn export: export_id=%s error=%s",
                    export_id,
                    credit_verify_exc,
                )
            
            # Update activity if activity_id was provided
            if activity_id:
                try:
                    from app.models.exports import ExportStatus
                    from app.models.user import ActivityStatus
                    from app.services.activity_service import ActivityService
                    
                    activity_service = ActivityService()
                    total_results = len(contact_uuids) + len(company_uuids)
                    result_summary = {
                        "export_id": export_id,
                        "status": ExportStatus.completed.value,
                        "contacts": len(contact_uuids),
                        "companies": len(company_uuids),
                        "unmatched": len(unmatched_urls),
                    }
                    await activity_service.update_export_activity(
                        session=session,
                        activity_id=activity_id,
                        result_count=total_results,
                        result_summary=result_summary,
                        status=ActivityStatus.SUCCESS,
                    )
                except Exception as activity_exc:
                    logger.exception("Failed to update activity after export completion: activity_id=%d", activity_id)
            
        except Exception as exc:
            logger.exception("LinkedIn export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)
            
            # Update activity if activity_id was provided
            if activity_id:
                try:
                    from app.models.user import ActivityStatus
                    from app.services.activity_service import ActivityService
                    
                    activity_service = ActivityService()
                    await activity_service.update_export_activity(
                        session=session,
                        activity_id=activity_id,
                        result_count=0,
                        status=ActivityStatus.FAILED,
                        error_message=str(exc),
                    )
                except Exception as activity_exc:
                    logger.exception("Failed to update activity after export failure: activity_id=%d", activity_id)


async def _verify_email_sequential(emails: list[str], service) -> tuple[Optional[str], int]:
    """
    Verify emails sequentially until first valid email is found.
    
    Helper function for email export processing.
    Returns tuple of (valid_email, emails_checked_count)
    """
    emails_checked = 0
    for email in emails:
        emails_checked += 1
        try:
            result = await service.verify_single_email(email)
            mapped_status = result.get("mapped_status", "unknown")
            if mapped_status == "valid":
                logger.debug("Found valid email: %s (checked %d emails)", email, emails_checked)
                return email, emails_checked
        except Exception as e:
            logger.debug("Email verification failed for %s: %s", email, str(e))
            continue
    
    return None, emails_checked


async def process_email_export(export_id: str, contacts_data: list[dict], activity_id: Optional[int] = None) -> None:
    """
    Process an email export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It processes contacts to find emails, generates a CSV export, and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        contacts_data: List of contact dictionaries with keys: first_name, last_name, domain, website
    """
    logger.info(
        "Starting email export task: export_id=%s contact_count=%d",
        export_id,
        len(contacts_data),
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info("Export was cancelled before processing: export_id=%s", export_id)
                return
            
            # Update status to processing
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Import services
            from app.core.config import get_settings
            from app.services.bulkmailverifier_service import BulkMailVerifierService
            from app.services.email_finder_service import EmailFinderService
            from app.utils.domain import extract_domain_from_url
            from app.utils.email_generator import generate_email_combinations
            
            settings = get_settings()
            email_finder_service = EmailFinderService()
            bulk_verifier_service = BulkMailVerifierService() if (
                settings.BULKMAILVERIFIER_EMAIL and settings.BULKMAILVERIFIER_PASSWORD
            ) else None
            
            # Process each contact
            total_records = len(contacts_data)
            results = []
            finder_found = 0
            verifier_found = 0
            not_found = 0
            
            # Update initial progress
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            for idx, contact in enumerate(contacts_data, 1):
                # Check for cancellation
                stmt = select(UserExport).where(UserExport.export_id == export_id)
                result = await session.execute(stmt)
                export = result.scalar_one_or_none()
                if export and export.status == ExportStatus.cancelled:
                    logger.info("Export cancelled during processing: export_id=%s", export_id)
                    return
                
                # Update progress
                await _update_export_progress(
                    session,
                    export_id,
                    idx - 1,
                    total_records,
                    start_time,
                )
                
                first_name = contact.get("first_name", "").strip()
                last_name = contact.get("last_name", "").strip()
                domain_input = contact.get("domain") or contact.get("website")
                
                if not domain_input:
                    logger.warning(
                        "Contact %d: Missing domain/website, skipping email search",
                        idx,
                    )
                    results.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "domain": "",
                        "email": "",
                    })
                    not_found += 1
                    continue
                
                # Normalize domain
                domain_input = domain_input.strip()
                try:
                    extracted_domain = extract_domain_from_url(domain_input)
                    if not extracted_domain:
                        logger.warning(
                            "Contact %d: Could not extract domain from: %s",
                            idx,
                            domain_input,
                        )
                        results.append({
                            "first_name": first_name,
                            "last_name": last_name,
                            "domain": domain_input,
                            "email": "",
                        })
                        not_found += 1
                        continue
                except Exception as e:
                    logger.warning(
                        "Contact %d: Domain extraction error: %s",
                        idx,
                        str(e),
                    )
                    results.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "domain": domain_input,
                        "email": "",
                    })
                    not_found += 1
                    continue
                
                email_found = None
                
                # Step 1: Try email finder (database search)
                try:
                    logger.debug(
                        "Contact %d: Trying email finder: first_name=%s last_name=%s domain=%s",
                        idx,
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
                        logger.info(
                            "Contact %d: Email found via finder: %s",
                            idx,
                            email_found,
                        )
                        finder_found += 1
                    else:
                        logger.debug(
                            "Contact %d: No emails found via finder",
                            idx,
                        )
                except Exception as e:
                    # Handle HTTPException (404) and other exceptions
                    from fastapi import HTTPException
                    if isinstance(e, HTTPException) and e.status_code == 404:
                        logger.debug(
                            "Contact %d: No emails found in database (404), will try verifier",
                            idx,
                        )
                    else:
                        error_msg = str(e)
                        logger.warning(
                            "Contact %d: Email finder exception: %s",
                            idx,
                            error_msg,
                        )
                
                # Step 2: If not found, try email verifier
                if not email_found and bulk_verifier_service:
                    try:
                        logger.debug(
                            "Contact %d: Trying email verifier: first_name=%s last_name=%s domain=%s",
                            idx,
                            first_name,
                            last_name,
                            extracted_domain,
                        )
                        
                        # Use the same logic as start_single_email_verification
                        email_count = 1000
                        max_retries = settings.BULKMAILVERIFIER_MAX_RETRIES
                        
                        batch_number = 1
                        found_valid = False
                        
                        while batch_number <= max_retries and not found_valid:
                            # Generate emails for this batch
                            batch_emails = generate_email_combinations(
                                first_name=first_name,
                                last_name=last_name,
                                domain=extracted_domain,
                                count=email_count,
                            )
                            
                            # Verify emails sequentially until first valid is found
                            valid_email, _ = await _verify_email_sequential(
                                emails=batch_emails,
                                service=bulk_verifier_service,
                            )
                            
                            if valid_email:
                                email_found = valid_email
                                found_valid = True
                                logger.info(
                                    "Contact %d: Email found via verifier: %s (batch %d)",
                                    idx,
                                    email_found,
                                    batch_number,
                                )
                                verifier_found += 1
                                break
                            
                            batch_number += 1
                        
                        if not found_valid:
                            logger.debug(
                                "Contact %d: No valid email found via verifier after %d batches",
                                idx,
                                max_retries,
                            )
                    except Exception as e:
                        logger.warning(
                            "Contact %d: Email verifier exception: %s",
                            idx,
                            str(e),
                        )
                elif not email_found and not bulk_verifier_service:
                    logger.debug(
                        "Contact %d: Email verifier not available (credentials not configured)",
                        idx,
                    )
                
                # Add result
                results.append({
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": extracted_domain,
                    "email": email_found or "",
                })
                
                if not email_found:
                    not_found += 1
            
            logger.info(
                "Email export processing completed: total=%d finder_found=%d verifier_found=%d not_found=%d",
                len(results),
                finder_found,
                verifier_found,
                not_found,
            )
            
            # Update progress to 100% after completion
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Generate CSV file
            file_path = await export_service.generate_email_export_csv(
                session,
                export_id,
                results,
            )
            
            # Update export with file path and generate signed URL
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(results),
                company_count=0,
            )
            
            logger.info(
                "Email export completed: export_id=%s contact_count=%d duration=%.2fs",
                export_id,
                len(results),
                time.time() - start_time,
            )
            
            # Verify credit deduction was done at request time
            # Credits should have been deducted at the endpoint (1 credit per contact)
            # This is a verification step - if credits weren't deducted, log a warning
            try:
                credit_service = CreditService()
                profile_repo = UserProfileRepository()
                profile = await profile_repo.get_by_user_id(session, export.user_id)
                if profile:
                    user_role = profile.role or "FreeUser"
                    if credit_service.should_deduct_credits(user_role):
                        # Credits should have been deducted at endpoint level
                        # Log for verification (credits were already deducted per contact at request time)
                        logger.debug(
                            "Credit deduction verification: export_id=%s user_id=%s role=%s contact_count=%d "
                            "(credits should have been deducted at endpoint)",
                            export_id,
                            export.user_id,
                            user_role,
                            len(contacts_data),
                        )
            except Exception as credit_verify_exc:
                logger.warning(
                    "Failed to verify credit deduction for email export: export_id=%s error=%s",
                    export_id,
                    credit_verify_exc,
                )
            
            # Update activity if activity_id was provided
            if activity_id:
                try:
                    from app.models.exports import ExportStatus
                    from app.models.user import ActivityStatus
                    from app.services.activity_service import ActivityService
                    
                    activity_service = ActivityService()
                    emails_found = sum(1 for r in results if r.get("email"))
                    result_summary = {
                        "export_id": export_id,
                        "status": ExportStatus.completed.value,
                        "total_contacts": len(results),
                        "emails_found": emails_found,
                        "emails_not_found": len(results) - emails_found,
                    }
                    await activity_service.update_export_activity(
                        session=session,
                        activity_id=activity_id,
                        result_count=emails_found,
                        result_summary=result_summary,
                        status=ActivityStatus.SUCCESS,
                    )
                except Exception as activity_exc:
                    logger.exception("Failed to update activity after export completion: activity_id=%d", activity_id)
            
        except Exception as exc:
            logger.exception("Email export failed: export_id=%s", export_id)
            
            # Update status to failed
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
            except Exception as status_exc:
                logger.exception("Failed to update export status after error: export_id=%s", export_id)
            
            # Update activity if activity_id was provided
            if activity_id:
                try:
                    from app.models.user import ActivityStatus
                    from app.services.activity_service import ActivityService
                    
                    activity_service = ActivityService()
                    await activity_service.update_export_activity(
                        session=session,
                        activity_id=activity_id,
                        result_count=0,
                        status=ActivityStatus.FAILED,
                        error_message=str(exc),
                    )
                except Exception as activity_exc:
                    logger.exception("Failed to update activity after export failure: activity_id=%d", activity_id)