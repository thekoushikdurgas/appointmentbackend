"""Celery task definitions and helpers for batched contact imports."""

from __future__ import annotations

import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, log_function_call
from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus
from app.services.import_service import ImportService
from app.tasks.celery_app import celery_app


settings = get_settings()
import_service = ImportService()
logger = get_logger(__name__)


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _parse_int(value: Optional[str]) -> Optional[int]:
    """Parse a numeric string into an integer, tolerating commas and empty values."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value.replace(",", "")))
    except ValueError:
        return None


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _parse_list(value: Optional[str]) -> List[str]:
    """Split a comma-delimited string into a list of trimmed items."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@log_function_call(logger=logger, log_arguments=True, log_result=True)
def _parse_text(value: Optional[str]) -> Optional[str]:
    """Return a stripped string or None when blank."""
    if value is None:
        return None
    value = value.strip()
    return value or None


@log_function_call(logger=logger, log_arguments=False, log_result=True)
def _company_uuid(row: Dict[str, str]) -> str:
    """Generate a deterministic UUID for a company row."""
    key = f"{row.get('company','')}{row.get('company_linkedin_url','')}{row.get('company_name_for_emails','')}"
    return str(uuid5(NAMESPACE_URL, key))


@log_function_call(logger=logger, log_arguments=False, log_result=True)
def _contact_uuid(row: Dict[str, str], company_uuid: str) -> str:
    """Generate a deterministic UUID for a contact row scoped to a company."""
    key = f"{row.get('first_name','')}{row.get('last_name','')}{row.get('email','')}{company_uuid}"
    return str(uuid5(NAMESPACE_URL, key))


@log_function_call(logger=logger)
async def _upsert_company(session: AsyncSession, row: Dict[str, str], now: datetime) -> str:
    """Insert or update a company and metadata, returning the company UUID."""
    uuid = _company_uuid(row)
    industries = _parse_list(row.get("industry"))
    keywords = _parse_list(row.get("keywords"))
    technologies = _parse_list(row.get("technologies"))

    text_search = " ".join(
        filter(
            None,
            [
                row.get("company_address"),
                row.get("company_city"),
                row.get("company_state"),
                row.get("company_country"),
            ],
        )
    )

    stmt = insert(Company).values(
        uuid=uuid,
        name=_parse_text(row.get("company")),
        employees_count=_parse_int(row.get("employees")),
        industries=industries or None,
        keywords=keywords or None,
        address=_parse_text(row.get("company_address")),
        annual_revenue=_parse_int(row.get("annual_revenue")),
        total_funding=_parse_int(row.get("total_funding")),
        technologies=technologies or None,
        text_search=text_search,
        created_at=now,
        updated_at=now,
    )
    update_values = {
        "name": stmt.excluded.name,
        "employees_count": stmt.excluded.employees_count,
        "industries": stmt.excluded.industries,
        "keywords": stmt.excluded.keywords,
        "address": stmt.excluded.address,
        "annual_revenue": stmt.excluded.annual_revenue,
        "total_funding": stmt.excluded.total_funding,
        "technologies": stmt.excluded.technologies,
        "text_search": stmt.excluded.text_search,
        "updated_at": stmt.excluded.updated_at,
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=[Company.uuid],
        set_=update_values,
    )
    await session.execute(stmt)

    meta_stmt = insert(CompanyMetadata).values(
        uuid=uuid,
        linkedin_url=_parse_text(row.get("company_linkedin_url")),
        facebook_url=_parse_text(row.get("facebook_url")),
        twitter_url=_parse_text(row.get("twitter_url")),
        website=_parse_text(row.get("website")),
        company_name_for_emails=_parse_text(row.get("company_name_for_emails")),
        phone_number=_parse_text(row.get("company_phone")),
        latest_funding=_parse_text(row.get("latest_funding")),
        latest_funding_amount=_parse_int(row.get("latest_funding_amount")),
        last_raised_at=_parse_text(row.get("last_raised_at")),
        city=_parse_text(row.get("company_city")),
        state=_parse_text(row.get("company_state")),
        country=_parse_text(row.get("company_country")),
    )
    meta_update = {
        "linkedin_url": meta_stmt.excluded.linkedin_url,
        "facebook_url": meta_stmt.excluded.facebook_url,
        "twitter_url": meta_stmt.excluded.twitter_url,
        "website": meta_stmt.excluded.website,
        "company_name_for_emails": meta_stmt.excluded.company_name_for_emails,
        "phone_number": meta_stmt.excluded.phone_number,
        "latest_funding": meta_stmt.excluded.latest_funding,
        "latest_funding_amount": meta_stmt.excluded.latest_funding_amount,
        "last_raised_at": meta_stmt.excluded.last_raised_at,
        "city": meta_stmt.excluded.city,
        "state": meta_stmt.excluded.state,
        "country": meta_stmt.excluded.country,
    }
    meta_stmt = meta_stmt.on_conflict_do_update(
        index_elements=[CompanyMetadata.uuid],
        set_=meta_update,
    )
    await session.execute(meta_stmt)
    logger.debug("Upserted company: uuid=%s", uuid)
    return uuid


@log_function_call(logger=logger)
async def _upsert_contact(
    session: AsyncSession,
    row: Dict[str, str],
    company_uuid: str,
    now: datetime,
) -> None:
    """Insert or update a contact and corresponding metadata."""
    contact_uuid = _contact_uuid(row, company_uuid)
    departments = _parse_list(row.get("departments"))

    contact_stmt = insert(Contact).values(
        uuid=contact_uuid,
        first_name=_parse_text(row.get("first_name")),
        last_name=_parse_text(row.get("last_name")),
        company_id=company_uuid,
        email=_parse_text(row.get("email")),
        title=_parse_text(row.get("title")),
        departments=departments or None,
        mobile_phone=_parse_text(row.get("mobile_phone")),
        email_status=_parse_text(row.get("email_status")),
        text_search=_parse_text(row.get("text_search")),
        created_at=now,
        updated_at=now,
        seniority=_parse_text(row.get("seniority")) or "_",
    )
    contact_update = {
        "first_name": contact_stmt.excluded.first_name,
        "last_name": contact_stmt.excluded.last_name,
        "email": contact_stmt.excluded.email,
        "title": contact_stmt.excluded.title,
        "departments": contact_stmt.excluded.departments,
        "mobile_phone": contact_stmt.excluded.mobile_phone,
        "email_status": contact_stmt.excluded.email_status,
        "text_search": contact_stmt.excluded.text_search,
        "updated_at": now,
        "seniority": contact_stmt.excluded.seniority,
    }
    contact_stmt = contact_stmt.on_conflict_do_update(
        index_elements=[Contact.uuid],
        set_=contact_update,
    )
    await session.execute(contact_stmt)

    contact_meta_stmt = insert(ContactMetadata).values(
        uuid=contact_uuid,
        linkedin_url=_parse_text(row.get("person_linkedin_url")),
        facebook_url=_parse_text(row.get("facebook_url")),
        twitter_url=_parse_text(row.get("twitter_url")),
        website=_parse_text(row.get("website")),
        work_direct_phone=_parse_text(row.get("work_direct_phone")),
        home_phone=_parse_text(row.get("home_phone")),
        city=_parse_text(row.get("city")),
        state=_parse_text(row.get("state")),
        country=_parse_text(row.get("country")),
        other_phone=_parse_text(row.get("other_phone")),
        stage=_parse_text(row.get("stage")),
    )
    contact_meta_update = {
        "linkedin_url": contact_meta_stmt.excluded.linkedin_url,
        "facebook_url": contact_meta_stmt.excluded.facebook_url,
        "twitter_url": contact_meta_stmt.excluded.twitter_url,
        "website": contact_meta_stmt.excluded.website,
        "work_direct_phone": contact_meta_stmt.excluded.work_direct_phone,
        "home_phone": contact_meta_stmt.excluded.home_phone,
        "city": contact_meta_stmt.excluded.city,
        "state": contact_meta_stmt.excluded.state,
        "country": contact_meta_stmt.excluded.country,
        "other_phone": contact_meta_stmt.excluded.other_phone,
        "stage": contact_meta_stmt.excluded.stage,
    }
    contact_meta_stmt = contact_meta_stmt.on_conflict_do_update(
        index_elements=[ContactMetadata.uuid],
        set_=contact_meta_update,
    )
    await session.execute(contact_meta_stmt)
    logger.debug("Upserted contact: uuid=%s company_uuid=%s", contact_uuid, company_uuid)


@log_function_call(logger=logger, log_arguments=True)
async def _process_csv(job_id: str, file_path: str) -> None:
    """Read a CSV, enqueue upserts, and update import job progress metrics."""
    logger.info("Starting contacts import processing: job_id=%s file_path=%s", job_id, file_path)
    async with AsyncSessionLocal() as session:
        job: Optional[ContactImportJob] = await import_service.job_repository.get_by_job_id(session, job_id)
        if not job:
            logger.warning("Import job not found during processing: job_id=%s", job_id)
            return

        await import_service.set_status(session, job_id, status=ImportJobStatus.processing, message="Processing CSV")

        errors: List[ContactImportError] = []
        processed = 0
        error_total = 0
        now = datetime.now(timezone.utc)
        batch_processed = 0

        try:
            with open(file_path, newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row_number, row in enumerate(reader, start=1):
                    try:
                        company_uuid = await _upsert_company(session, row, now)
                        await _upsert_contact(session, row, company_uuid, now)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Failed to process row: job_id=%s row_number=%d", job_id, row_number)
                        error = ContactImportError(
                            job_id=job.id,
                            row_number=row_number,
                            error_message=str(exc)[:500],
                            payload=json.dumps(row),
                        )
                        errors.append(error)
                    processed += 1
                    batch_processed += 1

                    if batch_processed >= 200:
                        error_batch = len(errors)
                        await session.commit()
                        if errors:
                            await import_service.add_errors(session, job.id, errors)
                            error_total += error_batch
                            errors.clear()
                        logger.debug(
                            "Committed batch progress: job_id=%s processed=%d errors=%d",
                            job_id,
                            processed,
                            error_total,
                        )
                        await import_service.increment_progress(
                            session,
                            job_id,
                            processed_delta=batch_processed,
                            error_delta=error_batch,
                        )
                        batch_processed = 0

            await session.commit()
            final_error_batch = 0
            if errors:
                final_error_batch = len(errors)
                await import_service.add_errors(session, job.id, errors)
                error_total += final_error_batch
                errors.clear()
            if batch_processed:
                await import_service.increment_progress(
                    session,
                    job_id,
                    processed_delta=batch_processed,
                    error_delta=final_error_batch,
                )
            await import_service.set_status(
                session,
                job_id,
                status=ImportJobStatus.completed,
                processed_rows=processed,
                error_count=error_total,
                total_rows=processed,
                message=f"Processed {processed} rows",
            )
            logger.info(
                "Completed contacts import: job_id=%s processed=%d errors=%d",
                job_id,
                processed,
                error_total,
            )
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            await import_service.set_status(
                session,
                job_id,
                status=ImportJobStatus.failed,
                total_rows=processed,
                message=f"Failed with error: {exc}",
            )
            logger.exception("Contacts import failed: job_id=%s processed=%d", job_id, processed)
            raise
        finally:
            await session.commit()
            logger.debug("Finished import job cleanup: job_id=%s", job_id)


@celery_app.task(name="contacts.process_import")
def process_contacts_import(job_id: str, file_path: str) -> None:
    """Celery entrypoint for processing contacts imports."""
    logger.info("Celery task started: job_id=%s file_path=%s", job_id, file_path)
    asyncio.run(_process_csv(job_id, file_path))
    logger.info("Celery task finished: job_id=%s", job_id)

