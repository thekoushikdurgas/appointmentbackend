"""Async test data factories for seeding database state in integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from typing import Iterable, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.models.imports import ContactImportError, ContactImportJob, ImportJobStatus

_company_id_seq = count(1)
_company_metadata_id_seq = count(1)
_contact_id_seq = count(1)
_contact_metadata_id_seq = count(1)
_import_job_id_seq = count(1)
_import_error_id_seq = count(1)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create_company(
    session: AsyncSession,
    *,
    with_metadata: bool = True,
    metadata_overrides: Optional[dict] = None,
    **overrides,
) -> Company:
    """Seed a `Company` (and optional `CompanyMetadata`) row."""
    metadata_overrides = metadata_overrides or {}

    now = overrides.pop("created_at", None) or _utcnow()
    uuid = overrides.get("uuid") or uuid4().hex

    company = Company(
        id=overrides.pop("id", next(_company_id_seq)),
        uuid=uuid,
        name=overrides.pop("name", "Acme Corporation"),
        employees_count=overrides.pop("employees_count", 250),
        industries=overrides.pop("industries", ["Software"]),
        keywords=overrides.pop("keywords", ["SaaS"]),
        address=overrides.pop("address", "123 Main St"),
        annual_revenue=overrides.pop("annual_revenue", 1_000_000),
        total_funding=overrides.pop("total_funding", 5_000_000),
        technologies=overrides.pop("technologies", ["Python", "AWS"]),
        text_search=overrides.pop("text_search", "Austin TX"),
        created_at=now,
        updated_at=overrides.pop("updated_at", now),
        **overrides,
    )
    session.add(company)

    if with_metadata:
        metadata = CompanyMetadata(
            id=metadata_overrides.get("id", next(_company_metadata_id_seq)),
            uuid=uuid,
            linkedin_url=metadata_overrides.get("linkedin_url", "https://linkedin.com/company/acme"),
            facebook_url=metadata_overrides.get("facebook_url", "https://facebook.com/acme"),
            twitter_url=metadata_overrides.get("twitter_url", "https://twitter.com/acme"),
            website=metadata_overrides.get("website", "https://acme.example.com"),
            company_name_for_emails=metadata_overrides.get("company_name_for_emails", "AcmeCo"),
            phone_number=metadata_overrides.get("phone_number", "+1-555-0100"),
            latest_funding=metadata_overrides.get("latest_funding", "Series B"),
            latest_funding_amount=metadata_overrides.get("latest_funding_amount", 25_000_000),
            last_raised_at=metadata_overrides.get("last_raised_at", "2024-06-01"),
            city=metadata_overrides.get("city", "Austin"),
            state=metadata_overrides.get("state", "TX"),
            country=metadata_overrides.get("country", "USA"),
        )
        session.add(metadata)

    await session.flush()
    return company


async def create_contact(
    session: AsyncSession,
    *,
    company: Optional[Company] = None,
    with_metadata: bool = True,
    departments: Optional[Iterable[str]] = None,
    metadata_overrides: Optional[dict] = None,
    **overrides,
) -> Contact:
    """Seed a `Contact` row with optional metadata and associated company."""
    metadata_overrides = metadata_overrides or {}
    company_obj = company
    if company_obj is None:
        company_obj = await create_company(session)

    now = overrides.pop("created_at", None) or _utcnow()
    uuid = overrides.get("uuid") or uuid4().hex

    contact = Contact(
        id=overrides.pop("id", next(_contact_id_seq)),
        uuid=uuid,
        first_name=overrides.pop("first_name", "Jane"),
        last_name=overrides.pop("last_name", "Doe"),
        company_id=overrides.pop("company_id", company_obj.uuid),
        email=overrides.pop("email", "jane.doe@example.com"),
        title=overrides.pop("title", "Director of Sales"),
        departments=list(departments) if departments is not None else overrides.pop("departments", ["Sales"]),
        mobile_phone=overrides.pop("mobile_phone", "+1-555-0200"),
        email_status=overrides.pop("email_status", "valid"),
        text_search=overrides.pop("text_search", "Austin TX"),
        created_at=now,
        updated_at=overrides.pop("updated_at", now),
        seniority=overrides.pop("seniority", "Director"),
        **overrides,
    )

    session.add(contact)

    if with_metadata:
        metadata = ContactMetadata(
            id=metadata_overrides.get("id", next(_contact_metadata_id_seq)),
            uuid=uuid,
            linkedin_url=metadata_overrides.get("linkedin_url", "https://linkedin.com/in/janedoe"),
            facebook_url=metadata_overrides.get("facebook_url", None),
            twitter_url=metadata_overrides.get("twitter_url", None),
            website=metadata_overrides.get("website", "https://janedoe.example.com"),
            work_direct_phone=metadata_overrides.get("work_direct_phone", "+1-555-0201"),
            home_phone=metadata_overrides.get("home_phone", None),
            city=metadata_overrides.get("city", "Austin"),
            state=metadata_overrides.get("state", "TX"),
            country=metadata_overrides.get("country", "USA"),
            other_phone=metadata_overrides.get("other_phone", None),
            stage=metadata_overrides.get("stage", "prospect"),
        )
        session.add(metadata)

    await session.flush()
    return contact


async def create_import_job(
    session: AsyncSession,
    *,
    job_id: Optional[str] = None,
    status: ImportJobStatus = ImportJobStatus.pending,
    processed_rows: int = 0,
    error_count: int = 0,
    errors: Optional[list[dict]] = None,
    **overrides,
) -> ContactImportJob:
    """Seed an import job (and optional errors) for imports API tests."""
    now = _utcnow()
    job = ContactImportJob(
        id=overrides.pop("id", next(_import_job_id_seq)),
        job_id=job_id or uuid4().hex,
        file_name=overrides.pop("file_name", "contacts.csv"),
        file_path=overrides.pop("file_path", "/tmp/contacts.csv"),
        total_rows=overrides.pop("total_rows", 10),
        processed_rows=processed_rows,
        status=status,
        error_count=error_count,
        message=overrides.pop("message", None),
        created_at=overrides.pop("created_at", now),
        updated_at=overrides.pop("updated_at", now),
        completed_at=overrides.pop("completed_at", None),
        **overrides,
    )
    session.add(job)
    await session.flush()

    if errors:
        error_models = [
            ContactImportError(
                id=error.get("id", next(_import_error_id_seq)),
                job_id=job.id,
                row_number=error.get("row_number", idx + 1),
                error_message=error.get("error_message", "Invalid row"),
                payload=error.get("payload", '{"email": "invalid"}'),
                created_at=error.get("created_at", now),
            )
            for idx, error in enumerate(errors)
        ]
        session.add_all(error_models)
        await session.flush()
        job.error_count = len(error_models)

    return job

