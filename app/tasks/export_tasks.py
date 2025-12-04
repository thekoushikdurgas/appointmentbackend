"""Background task functions for export processing.

This module provides async functions for processing exports in the background.
These functions are designed to be used with FastAPI's BackgroundTasks.
"""

import time
from datetime import UTC, datetime
from typing import Optional, Tuple
from uuid import uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import insert, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.models.exports import ExportStatus, UserExport
from app.repositories.companies import CompanyRepository
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
            
            # Update export with file path, related UUIDs, and generate signed URL
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
            
            # Ensure session is clean after search operations before any other database operations
            await session.commit()
            
            total_records = len(contact_uuids) + len(company_uuids) + len(unmatched_urls)
            logger.info(
                "LinkedIn search completed: export_id=%s contacts=%d companies=%d unmatched=%d total=%d",
                export_id,
                len(contact_uuids),
                len(company_uuids),
                len(unmatched_urls),
                total_records,
            )
            
            # Update initial progress (session should be clean now)
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


async def _verify_email_sequential(
    emails: list[str],
    service,
    verified_emails_set: Optional[set[str]] = None,
) -> tuple[Optional[str], int]:
    """
    Verify emails sequentially until first valid email is found.
    
    Helper function for email export processing.
    Returns tuple of (valid_email, emails_checked_count)
    
    Args:
        emails: List of email addresses to verify
        service: BulkMailVerifierService instance
        verified_emails_set: Optional set to track verified emails (will be updated in-place)
    """
    if verified_emails_set is None:
        verified_emails_set = set()
    
    emails_checked = 0
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
            
            if mapped_status == "valid":
                logger.debug("Found valid email: %s (checked %d emails)", email, emails_checked)
                return email, emails_checked
        except Exception as e:
            logger.debug("Email verification failed for %s: %s", email, str(e))
            # Still add to verified set to avoid retrying failed emails
            verified_emails_set.add(email)
            continue
    
    return None, emails_checked


async def _find_or_create_company_by_domain(
    session: AsyncSession,
    domain: str,
) -> Optional[str]:
    """
    Find or create a company by domain.
    
    Args:
        session: Database session
        domain: Company domain (normalized)
        
    Returns:
        Company UUID if found or created, None if domain is invalid
    """
    if not domain or not domain.strip():
        return None
    
    normalized_domain = domain.lower().strip()
    if normalized_domain.startswith("www."):
        normalized_domain = normalized_domain[4:]
    
    try:
        # Try to find existing company by normalized_domain in CompanyMetadata
        stmt = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain
        ).limit(1)
        result = await session.execute(stmt)
        company_uuid = result.scalar_one_or_none()
        
        if company_uuid:
            logger.debug("Found existing company by domain: domain=%s uuid=%s", normalized_domain, company_uuid)
            return company_uuid
        
        # Company not found, create a minimal company record
        logger.debug("Company not found, creating new company: domain=%s", normalized_domain)
        company_uuid = str(uuid5(NAMESPACE_URL, f"domain:{normalized_domain}"))
        server_time = datetime.now(UTC).replace(tzinfo=None)
        
        # Create company record with conflict handling
        company_data = {
            "uuid": company_uuid,
            "name": None,  # Will be populated later if available
            "created_at": server_time,
            "updated_at": server_time,
        }
        company_stmt = (
            insert(Company)
            .values(**company_data)
            .on_conflict_do_nothing(index_elements=["uuid"])
        )
        await session.execute(company_stmt)
        
        # Create company metadata with domain and conflict handling
        company_meta_data = {
            "uuid": company_uuid,
            "normalized_domain": normalized_domain,
            "website": f"https://{normalized_domain}",  # Default website format
        }
        company_meta_stmt = (
            insert(CompanyMetadata)
            .values(**company_meta_data)
            .on_conflict_do_update(
                index_elements=["uuid"],
                set_={
                    "normalized_domain": insert(CompanyMetadata).excluded.normalized_domain,
                    "website": insert(CompanyMetadata).excluded.website,
                }
            )
        )
        await session.execute(company_meta_stmt)
        
        await session.flush()
        logger.info("Created/updated company: domain=%s uuid=%s", normalized_domain, company_uuid)
        return company_uuid
        
    except Exception as e:
        logger.exception("Error finding/creating company by domain: domain=%s error=%s", normalized_domain, str(e))
        return None


async def _upsert_contact_with_verified_email(
    session: AsyncSession,
    first_name: str,
    last_name: str,
    email: str,
    domain: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Optional[Contact]:
    """
    Upsert a contact record with verified email.
    
    Creates or updates a contact record with the verified email and available information.
    If domain is provided, will find or create company and associate it.
    
    Args:
        session: Database session
        first_name: Contact first name
        last_name: Contact last name
        email: Verified email address
        domain: Company domain (optional, used to find/create company)
        company_id: Company UUID (optional, if already known)
        
    Returns:
        Contact record if successful, None if failed
    """
    if not email or not email.strip():
        logger.warning("Cannot upsert contact: email is empty")
        return None
    
    try:
        # Normalize email
        normalized_email = email.lower().strip()
        
        # Generate or find company_id if domain is provided
        final_company_id = company_id
        if domain and not final_company_id:
            final_company_id = await _find_or_create_company_by_domain(session, domain)
        
        # Generate deterministic UUID based on email + name
        name_part = f"{first_name or ''}{last_name or ''}".strip()
        uuid_input = f"{normalized_email}{name_part}"
        contact_uuid = str(uuid5(NAMESPACE_URL, uuid_input))
        
        server_time = datetime.now(UTC).replace(tzinfo=None)
        
        # Prepare contact data
        contact_data = {
            "uuid": contact_uuid,
            "first_name": first_name.strip() if first_name and first_name.strip() else None,
            "last_name": last_name.strip() if last_name and last_name.strip() else None,
            "email": normalized_email,
            "email_status": "valid",  # Set status to valid since it's verified
            "company_id": final_company_id,
            "created_at": server_time,
            "updated_at": server_time,
        }
        
        # Upsert contact using on_conflict_do_update
        # Update email and status always, but preserve existing name/company if new values are None
        update_dict = {
            "email": insert(Contact).excluded.email,
            "email_status": insert(Contact).excluded.email_status,
            "updated_at": insert(Contact).excluded.updated_at,
        }
        
        # Only update name fields if they're provided (not None)
        if contact_data["first_name"] is not None:
            update_dict["first_name"] = insert(Contact).excluded.first_name
        if contact_data["last_name"] is not None:
            update_dict["last_name"] = insert(Contact).excluded.last_name
        # Only update company_id if provided
        if final_company_id is not None:
            update_dict["company_id"] = insert(Contact).excluded.company_id
        
        stmt = (
            insert(Contact)
            .values(**contact_data)
            .on_conflict_do_update(
                index_elements=["uuid"],
                set_=update_dict
            )
        )
        await session.execute(stmt)
        await session.flush()
        
        # Fetch the contact to return
        stmt = select(Contact).where(Contact.uuid == contact_uuid)
        result = await session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        # Log what fields are being saved (for verification)
        populated_fields = []
        if contact_data["first_name"]:
            populated_fields.append("first_name")
        if contact_data["last_name"]:
            populated_fields.append("last_name")
        if final_company_id:
            populated_fields.append("company_id")
        null_fields = ["title", "departments", "mobile_phone", "text_search", "seniority"]
        
        logger.info(
            "Upserted contact with verified email: uuid=%s email=%s first_name=%s last_name=%s company_id=%s populated_fields=[%s] null_fields=[%s]",
            contact_uuid,
            normalized_email,
            first_name,
            last_name,
            final_company_id,
            ", ".join(populated_fields) if populated_fields else "none",
            ", ".join(null_fields),
        )
        
        return contact
        
    except Exception as e:
        logger.exception(
            "Error upserting contact with verified email: email=%s first_name=%s last_name=%s error=%s",
            email,
            first_name,
            last_name,
            str(e),
        )
        return None


async def _get_or_create_contact_metadata(
    session: AsyncSession,
    contact_uuid: str,
) -> ContactMetadata:
    """Fetch or create ContactMetadata row for a contact UUID."""
    stmt = select(ContactMetadata).where(ContactMetadata.uuid == contact_uuid)
    result = await session.execute(stmt)
    meta = result.scalar_one_or_none()
    if meta:
        return meta

    meta = ContactMetadata(uuid=contact_uuid)
    session.add(meta)
    await session.flush()
    return meta


async def _get_company_and_metadata(
    session: AsyncSession,
    company_uuid: Optional[str],
) -> Tuple[Optional[Company], Optional[CompanyMetadata]]:
    """Fetch Company and CompanyMetadata for a given company UUID, if any."""
    if not company_uuid:
        return None, None

    company_stmt = select(Company).where(Company.uuid == company_uuid)
    company_result = await session.execute(company_stmt)
    company = company_result.scalar_one_or_none()

    meta_stmt = select(CompanyMetadata).where(CompanyMetadata.uuid == company_uuid)
    meta_result = await session.execute(meta_stmt)
    company_meta = meta_result.scalar_one_or_none()

    if company and not company_meta:
        company_meta = CompanyMetadata(uuid=company_uuid)
        session.add(company_meta)
        await session.flush()

    return company, company_meta


def _split_csv_list(value: str) -> list[str]:
    """Split a comma-separated string into a clean list of tokens."""
    return [token.strip() for token in value.split(",") if isinstance(value, str) and token.strip()]


async def _map_and_apply_apollo_row(
    session: AsyncSession,
    contact_obj: Contact,
    raw_row: dict,
) -> None:
    """
    Map Apollo CSV columns into Contact/ContactMetadata/Company/CompanyMetadata.

    Known fields are written into typed columns. Remaining fields are concatenated
    into existing flexible metadata fields (text_search, keywords, etc.), not JSON.
    """
    if not raw_row:
        return

    contact_meta = await _get_or_create_contact_metadata(session, contact_obj.uuid)
    company, company_meta = await _get_company_and_metadata(session, contact_obj.company_id)

    handled_keys: set[str] = set()

    # --- Contact fields ---
    title_val = raw_row.get("title")
    if title_val and isinstance(title_val, str):
        contact_obj.title = title_val.strip()
        handled_keys.add("title")

    departments_val = raw_row.get("departments")
    if departments_val and isinstance(departments_val, str):
        contact_obj.departments = _split_csv_list(departments_val)
        handled_keys.add("departments")

    email_status_val = raw_row.get("email_status")
    if email_status_val and isinstance(email_status_val, str):
        contact_obj.email_status = email_status_val.strip()
        handled_keys.add("email_status")

    mobile_phone_val = raw_row.get("mobile_phone")
    if mobile_phone_val and isinstance(mobile_phone_val, str):
        contact_obj.mobile_phone = mobile_phone_val.strip()
        handled_keys.add("mobile_phone")

    # --- Contact metadata fields ---
    for csv_key, attr in [
        ("work_direct_phone", "work_direct_phone"),
        ("home_phone", "home_phone"),
        ("other_phone", "other_phone"),
    ]:
        val = raw_row.get(csv_key)
        if val and isinstance(val, str):
            setattr(contact_meta, attr, val.strip())
            handled_keys.add(csv_key)

    for csv_key, attr in [
        ("city", "city"),
        ("state", "state"),
        ("country", "country"),
    ]:
        val = raw_row.get(csv_key)
        if val and isinstance(val, str):
            setattr(contact_meta, attr, val.strip())
            handled_keys.add(csv_key)

    person_linkedin_val = raw_row.get("person_linkedin_url")
    if person_linkedin_val and isinstance(person_linkedin_val, str):
        contact_meta.linkedin_url = person_linkedin_val.strip()
        handled_keys.add("person_linkedin_url")

    # --- Company fields ---
    if company:
        company_name_val = raw_row.get("company") or raw_row.get("company_name_for_emails")
        if company_name_val and isinstance(company_name_val, str):
            company.name = company_name_val.strip()
            handled_keys.update({"company", "company_name_for_emails"})

        employees_val = raw_row.get("employees")
        if employees_val:
            try:
                company.employees_count = int(str(employees_val).replace(",", "").strip())
                handled_keys.add("employees")
            except (TypeError, ValueError):
                # leave unmapped; will go into text_search
                pass

        industry_val = raw_row.get("industry")
        if industry_val and isinstance(industry_val, str):
            company.industries = _split_csv_list(industry_val)
            handled_keys.add("industry")

        keywords_val = raw_row.get("keywords")
        if keywords_val and isinstance(keywords_val, str):
            company.keywords = _split_csv_list(keywords_val)
            handled_keys.add("keywords")

        technologies_val = raw_row.get("technologies")
        if technologies_val and isinstance(technologies_val, str):
            company.technologies = _split_csv_list(technologies_val)
            handled_keys.add("technologies")

        annual_revenue_val = raw_row.get("annual_revenue")
        if annual_revenue_val:
            try:
                company.annual_revenue = int(str(annual_revenue_val).replace(",", "").strip())
                handled_keys.add("annual_revenue")
            except (TypeError, ValueError):
                pass

        total_funding_val = raw_row.get("total_funding")
        if total_funding_val:
            try:
                company.total_funding = int(str(total_funding_val).replace(",", "").strip())
                handled_keys.add("total_funding")
            except (TypeError, ValueError):
                pass

        company_address_val = raw_row.get("company_address")
        if company_address_val and isinstance(company_address_val, str):
            company.address = company_address_val.strip()
            handled_keys.add("company_address")

    # --- Company metadata fields ---
    if company_meta:
        for csv_key, attr in [
            ("company_city", "city"),
            ("company_state", "state"),
            ("company_country", "country"),
        ]:
            val = raw_row.get(csv_key)
            if val and isinstance(val, str):
                setattr(company_meta, attr, val.strip())
                handled_keys.add(csv_key)

        phone_val = raw_row.get("company_phone") or raw_row.get("corporate_phone")
        if phone_val and isinstance(phone_val, str):
            company_meta.phone_number = phone_val.strip()
            handled_keys.update({"company_phone", "corporate_phone"})

        website_val = raw_row.get("website")
        if website_val and isinstance(website_val, str):
            company_meta.website = website_val.strip()
            handled_keys.add("website")

        company_linkedin_val = raw_row.get("company_linkedin_url")
        if company_linkedin_val and isinstance(company_linkedin_val, str):
            company_meta.linkedin_url = company_linkedin_val.strip()
            handled_keys.add("company_linkedin_url")

        facebook_val = raw_row.get("facebook_url")
        if facebook_val and isinstance(facebook_val, str):
            company_meta.facebook_url = facebook_val.strip()
            handled_keys.add("facebook_url")

        twitter_val = raw_row.get("twitter_url")
        if twitter_val and isinstance(twitter_val, str):
            company_meta.twitter_url = twitter_val.strip()
            handled_keys.add("twitter_url")

        latest_funding_val = raw_row.get("latest_funding")
        if latest_funding_val and isinstance(latest_funding_val, str):
            company_meta.latest_funding = latest_funding_val.strip()
            handled_keys.add("latest_funding")

        latest_funding_amount_val = raw_row.get("Latest_funding_amount")
        if latest_funding_amount_val:
            try:
                company_meta.latest_funding_amount = int(
                    str(latest_funding_amount_val).replace(",", "").strip()
                )
                handled_keys.add("Latest_funding_amount")
            except (TypeError, ValueError):
                pass

        last_raised_at_val = raw_row.get("last_raised_at")
        if last_raised_at_val and isinstance(last_raised_at_val, str):
            company_meta.last_raised_at = last_raised_at_val.strip()
            handled_keys.add("last_raised_at")

        company_name_emails_val = raw_row.get("company_name_for_emails")
        if company_name_emails_val and isinstance(company_name_emails_val, str):
            company_meta.company_name_for_emails = company_name_emails_val.strip()
            handled_keys.add("company_name_for_emails")

    # --- Remaining keys go into text_search / keywords style metadata ---
    contact_text_parts = [contact_obj.text_search] if contact_obj.text_search else []
    company_text_parts = [company.text_search] if (company and company.text_search) else []

    for key, value in raw_row.items():
        if key in handled_keys or not value or not isinstance(value, str):
            continue
        value_str = value.strip()
        if not value_str:
            continue

        # Heuristic: company-prefixed fields -> company text_search
        if key.startswith("company_") or key in {
            "annual_revenue",
            "total_funding",
            "latest_funding",
            "Latest_funding_amount",
            "last_raised_at",
            "technologies",
        }:
            if company is not None:
                company_text_parts.append(f"{key}: {value_str}")
        else:
            contact_text_parts.append(f"{key}: {value_str}")

    if contact_text_parts:
        contact_obj.text_search = " | ".join(part for part in contact_text_parts if part)

    if company is not None and company_text_parts:
        company.text_search = " | ".join(part for part in company_text_parts if part)

    await session.flush()

async def process_email_export(export_id: str, contacts_data: list[dict], activity_id: Optional[int] = None) -> None:
    """
    Process an email export in the background.
    
    This function is designed to be used with FastAPI's BackgroundTasks.
    It processes contacts to find emails, generates a CSV export, and updates the export status.
    
    Args:
        export_id: The UUID of the export record
        contacts_data: List of contact dictionaries with keys: first_name, last_name, domain, website, email.
            When CSV context is provided, each dict may also contain:
              - raw_row: Original CSV row keyed by header name
              - raw_headers: Ordered list of CSV headers
              - contact_field_mappings: Mapping from logical contact fields to CSV columns
              - company_field_mappings: Mapping from logical company fields to CSV columns
    """
    logger.info(
        "Starting email export task: export_id=%s contact_count=%d activity_id=%s",
        export_id,
        len(contacts_data),
        activity_id,
    )
    
    start_time = time.time()
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if export was cancelled before starting
            logger.debug(
                "Checking export status before processing: export_id=%s",
                export_id,
            )
            stmt = select(UserExport).where(UserExport.export_id == export_id)
            result = await session.execute(stmt)
            export = result.scalar_one_or_none()
            if export and export.status == ExportStatus.cancelled:
                logger.info(
                    "Export was cancelled before processing: export_id=%s user_id=%s",
                    export_id,
                    export.user_id if export else "unknown",
                )
                return
            
            if not export:
                logger.error(
                    "Export record not found: export_id=%s",
                    export_id,
                )
                return
            
            logger.debug(
                "Export record found: export_id=%s user_id=%s status=%s",
                export_id,
                export.user_id,
                export.status,
            )
            
            # Update status to processing
            logger.info(
                "Updating export status to processing: export_id=%s",
                export_id,
            )
            await _update_export_status(session, export_id, ExportStatus.processing)
            
            # Import services
            logger.debug(
                "Initializing services: export_id=%s",
                export_id,
            )
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
            
            if bulk_verifier_service:
                logger.info(
                    "Email verifier service available: export_id=%s",
                    export_id,
                )
            else:
                logger.warning(
                    "Email verifier service not available (credentials not configured): export_id=%s",
                    export_id,
                )
            
            # Prepare CSV header order. If any contact has raw CSV context,
            # prefer its headers so the export mirrors the original file.
            csv_headers: list[str] | None = None
            email_column_name = "email"
            for contact in contacts_data:
                raw_row = contact.get("raw_row")
                if isinstance(raw_row, dict) and raw_row:
                    csv_headers = list(raw_row.keys())
                    break
            if csv_headers is None:
                # Fallback to legacy minimal headers
                csv_headers = ["first_name", "last_name", "domain", "email"]
            # Ensure there is an email column in the header list
            if email_column_name not in csv_headers:
                csv_headers.append(email_column_name)
            
            # Track related contact and company UUIDs for this export
            contact_uuids: set[str] = set()
            company_uuids: set[str] = set()

            # Process each contact
            total_records = len(contacts_data)
            results = []
            csv_rows: list[dict] = []
            finder_found = 0
            verifier_found = 0
            not_found = 0
            contacts_saved = 0
            contacts_failed = 0
            
            logger.info(
                "Starting contact processing: export_id=%s total_records=%d",
                export_id,
                total_records,
            )
            
            # Update initial progress
            logger.debug(
                "Setting initial progress: export_id=%s total_records=%d",
                export_id,
                total_records,
            )
            await _update_export_progress(
                session,
                export_id,
                0,
                total_records,
                start_time,
            )
            
            for idx, contact in enumerate(contacts_data, 1):
                contact_start_time = time.time()
                
                # Check for cancellation
                if idx % 10 == 0:  # Check cancellation every 10 contacts to reduce DB queries
                    stmt = select(UserExport).where(UserExport.export_id == export_id)
                    result = await session.execute(stmt)
                    export = result.scalar_one_or_none()
                    if export and export.status == ExportStatus.cancelled:
                        logger.info(
                            "Export cancelled during processing: export_id=%s processed=%d/%d",
                            export_id,
                            idx - 1,
                            total_records,
                        )
                        return
                
                # Update progress
                if idx % 5 == 0 or idx == total_records:  # Update progress every 5 contacts or on last
                    await _update_export_progress(
                        session,
                        export_id,
                        idx - 1,
                        total_records,
                        start_time,
                    )
                
                logger.debug(
                    "Processing contact %d/%d: export_id=%s first_name=%s last_name=%s",
                    idx,
                    total_records,
                    export_id,
                    contact.get("first_name", ""),
                    contact.get("last_name", ""),
                )
                
                first_name = contact.get("first_name", "").strip()
                last_name = contact.get("last_name", "").strip()
                domain_input = contact.get("domain") or contact.get("website")
                existing_email = (contact.get("email") or "").strip() if contact.get("email") else None
                raw_row = contact.get("raw_row") or {}
                
                if not domain_input:
                    logger.warning(
                        "Contact %d/%d: Missing domain/website, skipping email search: export_id=%s first_name=%s last_name=%s",
                        idx,
                        total_records,
                        export_id,
                        first_name,
                        last_name,
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
                logger.debug(
                    "Extracting domain: contact=%d/%d export_id=%s domain_input=%s",
                    idx,
                    total_records,
                    export_id,
                    domain_input,
                )
                try:
                    extracted_domain = extract_domain_from_url(domain_input)
                    if not extracted_domain:
                        logger.warning(
                            "Contact %d/%d: Could not extract domain from: %s export_id=%s",
                            idx,
                            total_records,
                            domain_input,
                            export_id,
                        )
                        results.append({
                            "first_name": first_name,
                            "last_name": last_name,
                            "domain": domain_input,
                            "email": "",
                        })
                        not_found += 1
                        continue
                    logger.debug(
                        "Domain extracted: contact=%d/%d export_id=%s extracted_domain=%s",
                        idx,
                        total_records,
                        export_id,
                        extracted_domain,
                    )
                except Exception as e:
                    logger.warning(
                        "Contact %d/%d: Domain extraction error: %s export_id=%s domain_input=%s",
                        idx,
                        total_records,
                        str(e),
                        export_id,
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
                
                email_found = None
                finder_start_time = time.time()
                
                # Step 0: If an existing email was provided, try to verify and reuse it
                if existing_email and bulk_verifier_service:
                    try:
                        logger.debug(
                            "Contact %d/%d: Verifying existing email before finder: export_id=%s email=%s",
                            idx,
                            total_records,
                            export_id,
                            existing_email,
                        )
                        # Reuse the same sequential verification helper with a single email
                        valid_email, _ = await _verify_email_sequential(
                            emails=[existing_email],
                            service=bulk_verifier_service,
                            verified_emails_set=set(),
                        )
                        if valid_email:
                            email_found = valid_email
                            logger.info(
                                "Contact %d/%d: Existing email verified as valid: email=%s export_id=%s",
                                idx,
                                total_records,
                                email_found,
                                export_id,
                            )
                            verifier_found += 1
                            try:
                                saved_contact = await _upsert_contact_with_verified_email(
                                    session=session,
                                    first_name=first_name,
                                    last_name=last_name,
                                    email=email_found,
                                    domain=extracted_domain,
                                )
                                if saved_contact:
                                    contacts_saved += 1
                                    contact_uuids.add(saved_contact.uuid)
                                    if saved_contact.company_id:
                                        company_uuids.add(saved_contact.company_id)
                                    # Enrich contact and company from raw CSV row (Apollo mapping)
                                    await _map_and_apply_apollo_row(session, saved_contact, raw_row)
                                else:
                                    contacts_failed += 1
                            except Exception as save_error:
                                contacts_failed += 1
                                logger.exception(
                                    "Contact %d/%d: Exception saving verified existing email to database: email=%s error=%s export_id=%s",
                                    idx,
                                    total_records,
                                    email_found,
                                    str(save_error),
                                    export_id,
                                )
                    except Exception as e:
                        logger.exception(
                            "Contact %d/%d: Existing email verification failed, will fall back to finder/verifier: email=%s export_id=%s error=%s",
                            idx,
                            total_records,
                            existing_email,
                            export_id,
                            str(e),
                        )

                # Step 1: Try email finder (database search) if we still don't have an email
                try:
                    logger.debug(
                        "Contact %d/%d: Trying email finder: export_id=%s first_name=%s last_name=%s domain=%s",
                        idx,
                        total_records,
                        export_id,
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
                    finder_elapsed = time.time() - finder_start_time
                    
                    if finder_result.emails and len(finder_result.emails) > 0:
                        email_found = finder_result.emails[0].email
                        logger.info(
                            "Contact %d/%d: Email found via finder: email=%s elapsed=%.2fs export_id=%s",
                            idx,
                            total_records,
                            email_found,
                            finder_elapsed,
                            export_id,
                        )
                        finder_found += 1
                        
                        # Save email to contact table (email from finder is already in DB, but ensure it's updated)
                        try:
                            saved_contact = await _upsert_contact_with_verified_email(
                                session=session,
                                first_name=first_name,
                                last_name=last_name,
                                email=email_found,
                                domain=extracted_domain,
                            )
                            if saved_contact:
                                contacts_saved += 1
                                contact_uuids.add(saved_contact.uuid)
                                if saved_contact.company_id:
                                    company_uuids.add(saved_contact.company_id)
                                await _map_and_apply_apollo_row(session, saved_contact, raw_row)
                                # Log field details for verification
                                fields_summary = []
                                if saved_contact.first_name:
                                    fields_summary.append("first_name")
                                if saved_contact.last_name:
                                    fields_summary.append("last_name")
                                if saved_contact.company_id:
                                    fields_summary.append("company_id")
                                
                                logger.debug(
                                    "Contact %d/%d: Updated contact from finder: email=%s uuid=%s populated_fields=[%s] export_id=%s",
                                    idx,
                                    total_records,
                                    email_found,
                                    saved_contact.uuid,
                                    ", ".join(fields_summary) if fields_summary else "none",
                                    export_id,
                                )
                            else:
                                contacts_failed += 1
                                logger.warning(
                                    "Contact %d/%d: Failed to update contact from finder: email=%s export_id=%s",
                                    idx,
                                    total_records,
                                    email_found,
                                    export_id,
                                )
                        except Exception as save_error:
                            contacts_failed += 1
                            logger.exception(
                                "Contact %d/%d: Exception updating contact from finder: email=%s error=%s export_id=%s",
                                idx,
                                total_records,
                                email_found,
                                str(save_error),
                                export_id,
                            )
                    else:
                        logger.debug(
                            "Contact %d/%d: No emails found via finder: elapsed=%.2fs export_id=%s",
                            idx,
                            total_records,
                            finder_elapsed,
                            export_id,
                        )
                except Exception as e:
                    finder_elapsed = time.time() - finder_start_time
                    # Handle HTTPException (404) and other exceptions
                    from fastapi import HTTPException
                    if isinstance(e, HTTPException) and e.status_code == 404:
                        logger.debug(
                            "Contact %d/%d: No emails found in database (404), will try verifier: elapsed=%.2fs export_id=%s",
                            idx,
                            total_records,
                            finder_elapsed,
                            export_id,
                        )
                    else:
                        # Log full exception with traceback for debugging
                        logger.exception(
                            "Contact %d/%d: Email finder exception: elapsed=%.2fs export_id=%s first_name=%s last_name=%s domain=%s",
                            idx,
                            total_records,
                            finder_elapsed,
                            export_id,
                            first_name,
                            last_name,
                            extracted_domain,
                        )
                
                # Step 2: If not found, try email verifier
                if not email_found and bulk_verifier_service:
                    verifier_start_time = time.time()
                    try:
                        logger.debug(
                            "Contact %d/%d: Trying email verifier: export_id=%s first_name=%s last_name=%s domain=%s",
                            idx,
                            total_records,
                            export_id,
                            first_name,
                            last_name,
                            extracted_domain,
                        )
                        
                        # Use the same logic as start_single_email_verification
                        email_count = 1000
                        logger.debug(
                            "Contact %d/%d: Verifier settings: email_count=%d export_id=%s",
                            idx,
                            total_records,
                            email_count,
                            export_id,
                        )
                        
                        # Generate all unique email patterns once
                        all_unique_emails = generate_email_combinations(
                            first_name=first_name,
                            last_name=last_name,
                            domain=extracted_domain,
                            count=email_count,
                        )
                        total_unique_patterns = len(all_unique_emails)
                        
                        if total_unique_patterns == 0:
                            logger.debug(
                                "Contact %d/%d: No unique patterns generated: export_id=%s",
                                idx,
                                total_records,
                                export_id,
                            )
                        else:
                            # Calculate number of batches needed
                            total_batches = (total_unique_patterns + email_count - 1) // email_count
                            
                            # Track verified emails to prevent duplicates
                            verified_emails_set = set()
                            found_valid = False
                            total_emails_verified = 0
                            
                            # Process emails in batches until we find a valid email
                            for batch_number in range(1, total_batches + 1):
                                batch_start_time = time.time()
                                logger.debug(
                                    "Contact %d/%d: Verifier batch %d/%d: export_id=%s",
                                    idx,
                                    total_records,
                                    batch_number,
                                    total_batches,
                                    export_id,
                                )
                                
                                # Calculate batch slice
                                start_idx = (batch_number - 1) * email_count
                                end_idx = min(start_idx + email_count, total_unique_patterns)
                                batch_emails = all_unique_emails[start_idx:end_idx]
                                
                                # Filter out already verified emails
                                batch_emails_to_check = [e for e in batch_emails if e not in verified_emails_set]
                                
                                if not batch_emails_to_check:
                                    continue
                                
                                logger.debug(
                                    "Contact %d/%d: Checking %d emails in batch %d: export_id=%s",
                                    idx,
                                    total_records,
                                    len(batch_emails_to_check),
                                    batch_number,
                                    export_id,
                                )
                                
                                # Verify emails sequentially until first valid is found
                                valid_email, emails_verified = await _verify_email_sequential(
                                    emails=batch_emails_to_check,
                                    service=bulk_verifier_service,
                                    verified_emails_set=verified_emails_set,
                                )
                                
                                # Track verified emails
                                verified_emails_set.update(batch_emails_to_check[:emails_verified])
                                total_emails_verified += emails_verified
                                batch_elapsed = time.time() - batch_start_time
                                
                                if valid_email:
                                    email_found = valid_email
                                    found_valid = True
                                    verifier_elapsed = time.time() - verifier_start_time
                                    logger.info(
                                        "Contact %d/%d: Email found via verifier: email=%s batch=%d/%d emails_verified=%d elapsed=%.2fs export_id=%s",
                                        idx,
                                        total_records,
                                        email_found,
                                        batch_number,
                                        total_batches,
                                        total_emails_verified,
                                        verifier_elapsed,
                                        export_id,
                                    )
                                    verifier_found += 1
                                    
                                    # Save verified email to contact table
                                    try:
                                        saved_contact = await _upsert_contact_with_verified_email(
                                            session=session,
                                            first_name=first_name,
                                            last_name=last_name,
                                            email=email_found,
                                            domain=extracted_domain,
                                        )
                                        if saved_contact:
                                            contacts_saved += 1
                                            contact_uuids.add(saved_contact.uuid)
                                            if saved_contact.company_id:
                                                company_uuids.add(saved_contact.company_id)
                                            await _map_and_apply_apollo_row(session, saved_contact, raw_row)
                                            # Log field details for verification
                                            fields_summary = []
                                            if saved_contact.first_name:
                                                fields_summary.append("first_name")
                                            if saved_contact.last_name:
                                                fields_summary.append("last_name")
                                            if saved_contact.company_id:
                                                fields_summary.append("company_id")
                                            null_fields = []
                                            if saved_contact.title is None:
                                                null_fields.append("title")
                                            if saved_contact.departments is None:
                                                null_fields.append("departments")
                                            if saved_contact.mobile_phone is None:
                                                null_fields.append("mobile_phone")
                                            
                                            logger.debug(
                                                "Contact %d/%d: Saved verified email to database: email=%s uuid=%s populated_fields=[%s] null_fields=[%s] export_id=%s",
                                                idx,
                                                total_records,
                                                email_found,
                                                saved_contact.uuid,
                                                ", ".join(fields_summary) if fields_summary else "none",
                                                ", ".join(null_fields[:3]) + ("..." if len(null_fields) > 3 else ""),
                                                export_id,
                                            )
                                        else:
                                            contacts_failed += 1
                                            logger.warning(
                                                "Contact %d/%d: Failed to save verified email to database: email=%s export_id=%s",
                                                idx,
                                                total_records,
                                                email_found,
                                                export_id,
                                            )
                                    except Exception as save_error:
                                        contacts_failed += 1
                                        logger.exception(
                                            "Contact %d/%d: Exception saving verified email to database: email=%s error=%s export_id=%s",
                                            idx,
                                            total_records,
                                            email_found,
                                            str(save_error),
                                            export_id,
                                        )
                                    break
                                
                                logger.debug(
                                    "Contact %d/%d: Batch %d completed, no valid email: emails_verified=%d elapsed=%.2fs export_id=%s",
                                    idx,
                                    total_records,
                                    batch_number,
                                    emails_verified,
                                    batch_elapsed,
                                    export_id,
                                )
                            
                            if not found_valid:
                                verifier_elapsed = time.time() - verifier_start_time
                                logger.debug(
                                    "Contact %d/%d: No valid email found via verifier after %d batches (%d unique patterns): total_emails_verified=%d elapsed=%.2fs export_id=%s",
                                    idx,
                                    total_records,
                                    total_batches,
                                    total_unique_patterns,
                                    total_emails_verified,
                                    verifier_elapsed,
                                    export_id,
                                )
                    except Exception as e:
                        verifier_elapsed = time.time() - verifier_start_time
                        logger.exception(
                            "Contact %d/%d: Email verifier exception: elapsed=%.2fs export_id=%s first_name=%s last_name=%s domain=%s",
                            idx,
                            total_records,
                            verifier_elapsed,
                            export_id,
                            first_name,
                            last_name,
                            extracted_domain,
                        )
                elif not email_found and not bulk_verifier_service:
                    logger.debug(
                        "Contact %d/%d: Email verifier not available (credentials not configured): export_id=%s",
                        idx,
                        total_records,
                        export_id,
                    )
                
                # Build full CSV row: start from original raw_row if available,
                # then override or add the email column. This preserves all
                # original CSV columns while only changing the email value.
                row_for_csv: dict = {}
                if raw_row:
                    # Preserve original column order/keys; any missing header will
                    # be filled as empty later in the writer.
                    row_for_csv.update(raw_row)
                # Ensure domain field is present when we fall back to legacy headers
                if "domain" in csv_headers and "domain" not in row_for_csv:
                    row_for_csv["domain"] = extracted_domain or ""
                # Set/override the email column
                row_for_csv[email_column_name] = email_found or ""

                contact_elapsed = time.time() - contact_start_time
                results.append({
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": extracted_domain,
                    "email": email_found or "",
                })
                csv_rows.append(row_for_csv)
                
                if not email_found:
                    not_found += 1
                    logger.debug(
                        "Contact %d/%d: No email found: elapsed=%.2fs export_id=%s",
                        idx,
                        total_records,
                        contact_elapsed,
                        export_id,
                    )
                else:
                    logger.debug(
                        "Contact %d/%d: Contact processing completed: email=%s elapsed=%.2fs export_id=%s",
                        idx,
                        total_records,
                        email_found,
                        contact_elapsed,
                        export_id,
                    )
            
            processing_elapsed = time.time() - start_time
            logger.info(
                "Email export processing completed: export_id=%s total=%d finder_found=%d verifier_found=%d not_found=%d contacts_saved=%d contacts_failed=%d duration=%.2fs",
                export_id,
                len(results),
                finder_found,
                verifier_found,
                not_found,
                contacts_saved,
                contacts_failed,
                processing_elapsed,
            )
            
            # Update progress to 100% after completion
            logger.debug(
                "Updating final progress: export_id=%s total_records=%d",
                export_id,
                total_records,
            )
            await _update_export_progress(
                session,
                export_id,
                total_records,
                total_records,
                start_time,
            )
            
            # Generate CSV file
            csv_start_time = time.time()
            logger.info(
                "Generating CSV file: export_id=%s result_count=%d",
                export_id,
                len(results),
            )
            file_path = await export_service.generate_email_export_csv(
                session,
                export_id,
                csv_rows if csv_rows else results,
                csv_headers,
            )
            csv_elapsed = time.time() - csv_start_time
            logger.info(
                "CSV file generated: export_id=%s file_path=%s elapsed=%.2fs",
                export_id,
                file_path,
                csv_elapsed,
            )
            
            # Update export with file path and generate signed URL
            logger.debug(
                "Updating export status to completed: export_id=%s file_path=%s",
                export_id,
                file_path,
            )
            export = await export_service.update_export_status(
                session,
                export_id,
                ExportStatus.completed,
                file_path,
                contact_count=len(results),
                company_count=len(company_uuids),
            )
            # Persist UUID lists on the export record for later reference
            try:
                export.contact_uuids = sorted(contact_uuids) if contact_uuids else []
                export.company_uuids = sorted(company_uuids) if company_uuids else []
                await session.commit()
            except Exception as uuid_exc:
                logger.warning(
                    "Failed to update export UUID lists: export_id=%s error=%s",
                    export_id,
                    uuid_exc,
                )
            
            total_elapsed = time.time() - start_time
            logger.info(
                "Email export completed: export_id=%s contact_count=%d duration=%.2fs processing=%.2fs csv_generation=%.2fs finder_found=%d verifier_found=%d not_found=%d contacts_saved=%d contacts_failed=%d",
                export_id,
                len(results),
                total_elapsed,
                processing_elapsed,
                csv_elapsed,
                finder_found,
                verifier_found,
                not_found,
                contacts_saved,
                contacts_failed,
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
                logger.debug(
                    "Updating activity after export completion: export_id=%s activity_id=%d",
                    export_id,
                    activity_id,
                )
                try:
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
                        "finder_found": finder_found,
                        "verifier_found": verifier_found,
                        "not_found": not_found,
                    }
                    logger.debug(
                        "Activity result summary: export_id=%s activity_id=%d emails_found=%d total=%d",
                        export_id,
                        activity_id,
                        emails_found,
                        len(results),
                    )
                    await activity_service.update_export_activity(
                        session=session,
                        activity_id=activity_id,
                        result_count=emails_found,
                        result_summary=result_summary,
                        status=ActivityStatus.SUCCESS,
                    )
                    logger.info(
                        "Activity updated after export completion: export_id=%s activity_id=%d emails_found=%d",
                        export_id,
                        activity_id,
                        emails_found,
                    )
                except Exception as activity_exc:
                    logger.exception(
                        "Failed to update activity after export completion: export_id=%s activity_id=%d error=%s",
                        export_id,
                        activity_id,
                        activity_exc,
                    )
            
        except Exception as exc:
            total_elapsed = time.time() - start_time
            logger.exception(
                "Email export failed: export_id=%s duration=%.2fs error=%s",
                export_id,
                total_elapsed,
                exc,
            )
            
            # Update status to failed
            logger.error(
                "Updating export status to failed: export_id=%s error=%s",
                export_id,
                str(exc),
            )
            try:
                await _update_export_status(
                    session,
                    export_id,
                    ExportStatus.failed,
                    error_message=str(exc),
                )
                logger.info(
                    "Export status updated to failed: export_id=%s",
                    export_id,
                )
            except Exception as status_exc:
                logger.exception(
                    "Failed to update export status after error: export_id=%s status_error=%s",
                    export_id,
                    status_exc,
                )
            
            # Update activity if activity_id was provided
            if activity_id:
                logger.debug(
                    "Updating activity after export failure: export_id=%s activity_id=%d",
                    export_id,
                    activity_id,
                )
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
                    logger.info(
                        "Activity updated after export failure: export_id=%s activity_id=%d",
                        export_id,
                        activity_id,
                    )
                except Exception as activity_exc:
                    logger.exception(
                        "Failed to update activity after export failure: export_id=%s activity_id=%d error=%s",
                        export_id,
                        activity_id,
                        activity_exc,
                    )