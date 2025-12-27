"""Repository for LinkedIn URL-based queries."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from sqlalchemy import Select, and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_company_metadata_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
    fetch_company_by_uuid,
    fetch_company_metadata_by_uuid,
    fetch_contact_metadata_by_uuid,
)
from app.utils.logger import get_logger, log_database_query, log_database_error

logger = get_logger(__name__)


class LinkedInRepository(AsyncRepository):
    """Repository for searching contacts and companies by LinkedIn URL."""

    def __init__(self):
        """Initialize the repository."""
        # We don't extend a specific model, so we pass None
        super().__init__(Contact)  # Use Contact as base, but we'll query multiple models

    async def search_contacts_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[tuple[Contact, Optional[ContactMetadata], Optional[Company], Optional[CompanyMetadata]]]:
        """
        Search for contacts by LinkedIn URL in ContactMetadata.
        
        Returns tuples of (Contact, ContactMetadata, Company, CompanyMetadata).
        """
        start_time = time.time()
        try:
            # Use EXISTS subquery to filter contacts by LinkedIn URL in metadata
            stmt: Select = (
                select(Contact)
                .where(
                    exists(
                        select(1)
                        .select_from(ContactMetadata)
                        .where(
                            and_(
                                ContactMetadata.uuid == Contact.uuid,
                                ContactMetadata.linkedin_url.isnot(None),
                                ContactMetadata.linkedin_url != "_",
                                ContactMetadata.linkedin_url.ilike(f"%{linkedin_url}%"),
                            )
                        )
                    )
                )
            )
            
            result = await session.execute(stmt)
            contacts = result.scalars().all()
            
            # Extract foreign keys
            company_ids = {c.company_id for c in contacts if c.company_id}
            contact_uuids = {c.uuid for c in contacts}
            
            # Batch fetch related entities
            companies_dict = await batch_fetch_companies_by_uuids(session, company_ids)
            contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
            
            # Extract company UUIDs from fetched companies
            company_uuids = {c.uuid for c in companies_dict.values()}
            company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
            
            # Reconstruct tuples
            rows = []
            for contact in contacts:
                company = companies_dict.get(contact.company_id) if contact.company_id else None
                contact_meta = contact_meta_dict.get(contact.uuid)
                company_meta = company_meta_dict.get(company.uuid) if company else None
                rows.append((contact, contact_meta, company, company_meta))
            
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table="contacts",
                filters={"linkedin_url": linkedin_url[:100]},  # Truncate for logging
                result_count=len(rows),
                duration_ms=duration_ms,
                logger_name="app.repositories.linkedin",
            )
            
            return rows
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table="contacts",
                error=exc,
                duration_ms=duration_ms,
                context={"linkedin_url": linkedin_url[:100], "method": "search_contacts_by_linkedin_url"}
            )
            raise

    async def search_companies_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[tuple[Company, Optional[CompanyMetadata]]]:
        """
        Search for companies by LinkedIn URL in CompanyMetadata.
        
        Returns tuples of (Company, CompanyMetadata).
        """
        # Use EXISTS subquery to filter companies by LinkedIn URL in metadata
        
        stmt: Select = (
            select(Company)
            .where(
                exists(
                    select(1)
                    .select_from(CompanyMetadata)
                    .where(
                        and_(
                            CompanyMetadata.uuid == Company.uuid,
                            CompanyMetadata.linkedin_url.isnot(None),
                            CompanyMetadata.linkedin_url.ilike(f"%{linkedin_url}%"),
                        )
                    )
                )
            )
        )
        
        result = await session.execute(stmt)
        companies = result.scalars().all()
        
        company_uuids = {c.uuid for c in companies}
        company_meta_dict = await batch_fetch_company_metadata_by_uuids(session, company_uuids)
        
        # Reconstruct tuples
        rows = [(company, company_meta_dict.get(company.uuid)) for company in companies]
        
        return rows

    async def find_contact_by_exact_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> Optional[tuple[Contact, Optional[ContactMetadata], Optional[Company], Optional[CompanyMetadata]]]:
        """
        Find a contact by exact LinkedIn URL match.
        
        Returns tuple of (Contact, ContactMetadata, Company, CompanyMetadata) or None.
        """
        # Use EXISTS subquery to find contact by exact LinkedIn URL
        
        stmt: Select = (
            select(Contact)
            .where(
                exists(
                    select(1)
                    .select_from(ContactMetadata)
                    .where(
                        and_(
                            ContactMetadata.uuid == Contact.uuid,
                            ContactMetadata.linkedin_url.isnot(None),
                            ContactMetadata.linkedin_url != "_",
                            ContactMetadata.linkedin_url.ilike(linkedin_url),
                        )
                    )
                )
            )
            .limit(1)
        )
        
        result = await session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            return None
        
        company = await fetch_company_by_uuid(session, contact.company_id) if contact.company_id else None
        contact_meta = await fetch_contact_metadata_by_uuid(session, contact.uuid)
        company_meta = await fetch_company_metadata_by_uuid(session, company.uuid) if company else None
        
        row = (contact, contact_meta, company, company_meta)
        
        return row

    async def find_company_by_exact_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> Optional[tuple[Company, Optional[CompanyMetadata]]]:
        """
        Find a company by exact LinkedIn URL match.
        
        Returns tuple of (Company, CompanyMetadata) or None.
        """
        # Use EXISTS subquery to find company by exact LinkedIn URL
        
        stmt: Select = (
            select(Company)
            .where(
                exists(
                    select(1)
                    .select_from(CompanyMetadata)
                    .where(
                        and_(
                            CompanyMetadata.uuid == Company.uuid,
                            CompanyMetadata.linkedin_url.isnot(None),
                            CompanyMetadata.linkedin_url.ilike(linkedin_url),
                        )
                    )
                )
            )
            .limit(1)
        )
        
        result = await session.execute(stmt)
        company = result.scalar_one_or_none()
        
        if not company:
            return None
        
        company_meta = await fetch_company_metadata_by_uuid(session, company.uuid)
        
        row = (company, company_meta)
        
        return row

    async def get_company_contacts(
        self, session: AsyncSession, company_uuid: str
    ) -> list[tuple[Contact, Optional[ContactMetadata]]]:
        """
        Get all contacts for a company.
        
        Returns tuples of (Contact, ContactMetadata).
        """
        # Fetch contacts only (no joins)
        stmt: Select = select(Contact).where(Contact.company_id == company_uuid)
        
        result = await session.execute(stmt)
        contacts = result.scalars().all()
        
        contact_uuids = {c.uuid for c in contacts}
        contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
        
        # Reconstruct tuples
        rows = [(contact, contact_meta_dict.get(contact.uuid)) for contact in contacts]
        return rows

    async def find_contacts_metadata_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[ContactMetadata]:
        """
        Find contact metadata records by LinkedIn URL.
        
        Step 1 of sequential query: Query contacts_metadata table only.
        Returns list of ContactMetadata objects.
        
        Optimized for performance:
        - Uses GIN trigram index for ILIKE pattern matching
        - Extracts username from URL for more specific matching
        - Adds LIMIT to prevent excessive results
        """
        # Normalize and extract username from LinkedIn URL for better matching
        # LinkedIn URLs typically: https://www.linkedin.com/in/username or /in/username
        normalized_url = linkedin_url.strip()
        
        # Extract username part if it's a full URL
        # This helps with index usage by making the pattern more specific
        if "/in/" in normalized_url:
            # Extract the username part after /in/
            url_parts = normalized_url.split("/in/")
            if len(url_parts) > 1:
                username_part = url_parts[-1].split("?")[0].split("/")[0].strip()
                if username_part:
                    # Use the username part for more efficient matching
                    search_pattern = f"%{username_part}%"
                else:
                    search_pattern = f"%{normalized_url}%"
            else:
                search_pattern = f"%{normalized_url}%"
        else:
            # Use the full URL if no /in/ pattern found
            search_pattern = f"%{normalized_url}%"
        
        # Build query with optimized pattern matching
        # The GIN trigram index (idx_contacts_metadata_linkedin_url_gin) will be used
        # Adding LIMIT to prevent excessive results and improve performance
        stmt: Select = (
            select(ContactMetadata)
            .where(
                and_(
                    ContactMetadata.linkedin_url.isnot(None),
                    ContactMetadata.linkedin_url != "_",
                    ContactMetadata.linkedin_url.ilike(search_pattern),
                )
            )
            .limit(1000)  # Reasonable limit to prevent full table scans
        )
        
        result = await session.execute(stmt)
        contact_metadata_list = result.scalars().all()
        
        return list(contact_metadata_list)

    async def find_contacts_by_uuids(
        self, session: AsyncSession, contact_uuids: list[str], batch_size: int = 1000
    ) -> dict[str, Contact]:
        """
        Find contacts by UUID list with automatic batching for large lists.
        
        Step 2 of sequential query: Batch fetch contacts using UUID list.
        Automatically splits large lists into batches to prevent query failures.
        Returns dictionary keyed by UUID for fast lookup.
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs to fetch
            batch_size: Maximum UUIDs per batch (default: 1000, PostgreSQL limit)
        """
        if not contact_uuids:
            return {}
        
        # If list is small enough, execute single query
        if len(contact_uuids) <= batch_size:
            stmt: Select = select(Contact).where(Contact.uuid.in_(contact_uuids))
            result = await session.execute(stmt)
            contacts = result.scalars().all()
            contacts_dict = {contact.uuid: contact for contact in contacts}
            return contacts_dict
        
        # Split into batches and execute in parallel
        # Split into batches for parallel processing
        batches = [
            contact_uuids[i : i + batch_size] for i in range(0, len(contact_uuids), batch_size)
        ]
        
        # Execute batches in parallel
        async def fetch_batch(batch: list[str]) -> dict[str, Contact]:
            stmt: Select = select(Contact).where(Contact.uuid.in_(batch))
            result = await session.execute(stmt)
            contacts = result.scalars().all()
            return {contact.uuid: contact for contact in contacts}
        
        batch_tasks = [fetch_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Merge all batch results
        all_contacts = {}
        for batch_dict in batch_results:
            all_contacts.update(batch_dict)
        
        return all_contacts

    async def find_companies_by_uuids(
        self, session: AsyncSession, company_uuids: list[str], batch_size: int = 1000
    ) -> dict[str, Company]:
        """
        Find companies by UUID list with automatic batching for large lists.
        
        Step 3 of sequential query: Batch fetch companies using UUID list.
        Automatically splits large lists into batches to prevent query failures.
        Returns dictionary keyed by UUID for fast lookup.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs to fetch
            batch_size: Maximum UUIDs per batch (default: 1000, PostgreSQL limit)
        """
        if not company_uuids:
            return {}
        
        # If list is small enough, execute single query
        if len(company_uuids) <= batch_size:
            stmt: Select = select(Company).where(Company.uuid.in_(company_uuids))
            result = await session.execute(stmt)
            companies = result.scalars().all()
            companies_dict = {company.uuid: company for company in companies}
            return companies_dict
        
        # Split into batches and execute in parallel
        batches = [
            company_uuids[i : i + batch_size] for i in range(0, len(company_uuids), batch_size)
        ]
        
        # Execute batches in parallel
        async def fetch_batch(batch: list[str]) -> dict[str, Company]:
            stmt: Select = select(Company).where(Company.uuid.in_(batch))
            result = await session.execute(stmt)
            companies = result.scalars().all()
            return {company.uuid: company for company in companies}
        
        batch_tasks = [fetch_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Merge all batch results
        all_companies = {}
        for batch_dict in batch_results:
            all_companies.update(batch_dict)
        
        return all_companies

    async def find_companies_metadata_by_uuids(
        self, session: AsyncSession, company_uuids: list[str], batch_size: int = 1000
    ) -> dict[str, CompanyMetadata]:
        """
        Find company metadata records by UUID list with automatic batching for large lists.
        
        Step 4 of sequential query: Batch fetch company metadata using UUID list.
        Automatically splits large lists into batches to prevent query failures.
        Returns dictionary keyed by UUID for fast lookup.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs to fetch metadata for
            batch_size: Maximum UUIDs per batch (default: 1000, PostgreSQL limit)
        """
        if not company_uuids:
            return {}
        
        # If list is small enough, execute single query
        if len(company_uuids) <= batch_size:
            stmt: Select = select(CompanyMetadata).where(CompanyMetadata.uuid.in_(company_uuids))
            result = await session.execute(stmt)
            company_metadata_list = result.scalars().all()
            company_metadata_dict = {cm.uuid: cm for cm in company_metadata_list}
            return company_metadata_dict
        
        # Split into batches and execute in parallel
        batches = [
            company_uuids[i : i + batch_size] for i in range(0, len(company_uuids), batch_size)
        ]
        
        # Execute batches in parallel
        async def fetch_batch(batch: list[str]) -> dict[str, CompanyMetadata]:
            stmt: Select = select(CompanyMetadata).where(CompanyMetadata.uuid.in_(batch))
            result = await session.execute(stmt)
            company_metadata_list = result.scalars().all()
            return {cm.uuid: cm for cm in company_metadata_list}
        
        batch_tasks = [fetch_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Merge all batch results
        all_metadata = {}
        for batch_dict in batch_results:
            all_metadata.update(batch_dict)
        
        return all_metadata

    async def find_contacts_by_company_uuids(
        self, session: AsyncSession, company_uuids: list[str]
    ) -> dict[str, list[tuple[Contact, Optional[ContactMetadata]]]]:
        """
        Batch fetch contacts for multiple companies.
        
        Optimized to eliminate N+1 query problem: fetches all contacts for multiple
        companies in a single query instead of N separate queries.
        
        Returns dictionary keyed by company_uuid with list of (Contact, ContactMetadata) tuples.
        """
        if not company_uuids:
            return {}
        
        # Fetch contacts only (no joins)
        stmt: Select = select(Contact).where(Contact.company_id.in_(company_uuids))
        
        result = await session.execute(stmt)
        contacts = result.scalars().all()
        
        contact_uuids = {c.uuid for c in contacts}
        contact_meta_dict = await batch_fetch_contact_metadata_by_uuids(session, contact_uuids)
        
        # Group contacts by company_id and reconstruct tuples
        contacts_by_company: dict[str, list[tuple[Contact, Optional[ContactMetadata]]]] = {}
        for contact in contacts:
            company_uuid = contact.company_id
            if company_uuid:
                if company_uuid not in contacts_by_company:
                    contacts_by_company[company_uuid] = []
                contact_meta = contact_meta_dict.get(contact.uuid)
                contacts_by_company[company_uuid].append((contact, contact_meta))
        
        return contacts_by_company

    async def find_companies_metadata_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[CompanyMetadata]:
        """
        Find company metadata records by LinkedIn URL.
        
        Step 1 of sequential query for companies: Query companies_metadata table only.
        Returns list of CompanyMetadata objects.
        """
        # Normalize and extract company identifier from LinkedIn URL
        normalized_url = linkedin_url.strip()
        
        # Extract company identifier if it's a full URL
        # LinkedIn company URLs typically: https://www.linkedin.com/company/company-name
        if "/company/" in normalized_url:
            url_parts = normalized_url.split("/company/")
            if len(url_parts) > 1:
                company_part = url_parts[-1].split("?")[0].split("/")[0].strip()
                if company_part:
                    search_pattern = f"%{company_part}%"
                else:
                    search_pattern = f"%{normalized_url}%"
            else:
                search_pattern = f"%{normalized_url}%"
        else:
            search_pattern = f"%{normalized_url}%"
        
        stmt: Select = (
            select(CompanyMetadata)
            .where(
                and_(
                    CompanyMetadata.linkedin_url.isnot(None),
                    CompanyMetadata.linkedin_url.ilike(search_pattern),
                )
            )
            .limit(1000)  # Reasonable limit to prevent full table scans
        )
        
        result = await session.execute(stmt)
        company_metadata_list = result.scalars().all()
        
        return list(company_metadata_list)

