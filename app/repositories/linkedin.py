"""Repository for LinkedIn URL-based queries."""

from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository

logger = get_logger(__name__)


class LinkedInRepository(AsyncRepository):
    """Repository for searching contacts and companies by LinkedIn URL."""

    def __init__(self):
        """Initialize the repository."""
        logger.debug("Entering LinkedInRepository.__init__")
        # We don't extend a specific model, so we pass None
        super().__init__(Contact)  # Use Contact as base, but we'll query multiple models
        logger.debug("Exiting LinkedInRepository.__init__")

    async def search_contacts_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[tuple[Contact, Optional[ContactMetadata], Optional[Company], Optional[CompanyMetadata]]]:
        """
        Search for contacts by LinkedIn URL in ContactMetadata.
        
        Returns tuples of (Contact, ContactMetadata, Company, CompanyMetadata).
        """
        logger.debug("Entering search_contacts_by_linkedin_url linkedin_url=%s", linkedin_url)
        
        # Create aliases for joins
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        company_alias = aliased(Company, name="company")
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")
        
        # Build query with all joins
        stmt: Select = (
            select(Contact, contact_meta_alias, company_alias, company_meta_alias)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
            .outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
            .where(
                and_(
                    contact_meta_alias.linkedin_url.isnot(None),
                    contact_meta_alias.linkedin_url != "_",
                    contact_meta_alias.linkedin_url.ilike(f"%{linkedin_url}%"),
                )
            )
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        logger.debug(
            "Exiting search_contacts_by_linkedin_url found=%d contacts",
            len(rows),
        )
        return rows

    async def search_companies_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[tuple[Company, Optional[CompanyMetadata]]]:
        """
        Search for companies by LinkedIn URL in CompanyMetadata.
        
        Returns tuples of (Company, CompanyMetadata).
        """
        logger.debug("Entering search_companies_by_linkedin_url linkedin_url=%s", linkedin_url)
        
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")
        
        # Build query with company metadata join
        stmt: Select = (
            select(Company, company_meta_alias)
            .outerjoin(company_meta_alias, Company.uuid == company_meta_alias.uuid)
            .where(
                and_(
                    company_meta_alias.linkedin_url.isnot(None),
                    company_meta_alias.linkedin_url.ilike(f"%{linkedin_url}%"),
                )
            )
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        logger.debug(
            "Exiting search_companies_by_linkedin_url found=%d companies",
            len(rows),
        )
        return rows

    async def find_contact_by_exact_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> Optional[tuple[Contact, Optional[ContactMetadata], Optional[Company], Optional[CompanyMetadata]]]:
        """
        Find a contact by exact LinkedIn URL match.
        
        Returns tuple of (Contact, ContactMetadata, Company, CompanyMetadata) or None.
        """
        logger.debug("Entering find_contact_by_exact_linkedin_url linkedin_url=%s", linkedin_url)
        
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        company_alias = aliased(Company, name="company")
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")
        
        stmt: Select = (
            select(Contact, contact_meta_alias, company_alias, company_meta_alias)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
            .outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
            .where(
                and_(
                    contact_meta_alias.linkedin_url.isnot(None),
                    contact_meta_alias.linkedin_url != "_",
                    contact_meta_alias.linkedin_url.ilike(linkedin_url),
                )
            )
            .limit(1)
        )
        
        result = await session.execute(stmt)
        row = result.first()
        
        logger.debug(
            "Exiting find_contact_by_exact_linkedin_url found=%s",
            row is not None,
        )
        return row

    async def find_company_by_exact_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> Optional[tuple[Company, Optional[CompanyMetadata]]]:
        """
        Find a company by exact LinkedIn URL match.
        
        Returns tuple of (Company, CompanyMetadata) or None.
        """
        logger.debug("Entering find_company_by_exact_linkedin_url linkedin_url=%s", linkedin_url)
        
        company_meta_alias = aliased(CompanyMetadata, name="company_metadata")
        
        stmt: Select = (
            select(Company, company_meta_alias)
            .outerjoin(company_meta_alias, Company.uuid == company_meta_alias.uuid)
            .where(
                and_(
                    company_meta_alias.linkedin_url.isnot(None),
                    company_meta_alias.linkedin_url.ilike(linkedin_url),
                )
            )
            .limit(1)
        )
        
        result = await session.execute(stmt)
        row = result.first()
        
        logger.debug(
            "Exiting find_company_by_exact_linkedin_url found=%s",
            row is not None,
        )
        return row

    async def get_company_contacts(
        self, session: AsyncSession, company_uuid: str
    ) -> list[tuple[Contact, Optional[ContactMetadata]]]:
        """
        Get all contacts for a company.
        
        Returns tuples of (Contact, ContactMetadata).
        """
        logger.debug("Entering get_company_contacts company_uuid=%s", company_uuid)
        
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        
        stmt: Select = (
            select(Contact, contact_meta_alias)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .where(Contact.company_id == company_uuid)
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        logger.debug(
            "Exiting get_company_contacts found=%d contacts",
            len(rows),
        )
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
        logger.debug("Entering find_contacts_metadata_by_linkedin_url linkedin_url=%s", linkedin_url)
        
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
                    logger.debug("Extracted username from URL: %s, using pattern: %s", username_part, search_pattern)
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
        
        logger.debug(
            "Exiting find_contacts_metadata_by_linkedin_url found=%d contact metadata records",
            len(contact_metadata_list),
        )
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
        logger.debug("Entering find_contacts_by_uuids count=%d batch_size=%d", len(contact_uuids), batch_size)
        
        if not contact_uuids:
            logger.debug("Exiting find_contacts_by_uuids: empty UUID list")
            return {}
        
        # If list is small enough, execute single query
        if len(contact_uuids) <= batch_size:
            stmt: Select = select(Contact).where(Contact.uuid.in_(contact_uuids))
            result = await session.execute(stmt)
            contacts = result.scalars().all()
            contacts_dict = {contact.uuid: contact for contact in contacts}
            logger.debug("Exiting find_contacts_by_uuids found=%d contacts (single batch)", len(contacts_dict))
            return contacts_dict
        
        # Split into batches and execute in parallel
        logger.debug("Splitting %d UUIDs into batches of %d", len(contact_uuids), batch_size)
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
        
        logger.debug(
            "Exiting find_contacts_by_uuids found=%d contacts (%d batches)",
            len(all_contacts),
            len(batches),
        )
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
        logger.debug("Entering find_companies_by_uuids count=%d batch_size=%d", len(company_uuids), batch_size)
        
        if not company_uuids:
            logger.debug("Exiting find_companies_by_uuids: empty UUID list")
            return {}
        
        # If list is small enough, execute single query
        if len(company_uuids) <= batch_size:
            stmt: Select = select(Company).where(Company.uuid.in_(company_uuids))
            result = await session.execute(stmt)
            companies = result.scalars().all()
            companies_dict = {company.uuid: company for company in companies}
            logger.debug("Exiting find_companies_by_uuids found=%d companies (single batch)", len(companies_dict))
            return companies_dict
        
        # Split into batches and execute in parallel
        logger.debug("Splitting %d UUIDs into batches of %d", len(company_uuids), batch_size)
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
        
        logger.debug(
            "Exiting find_companies_by_uuids found=%d companies (%d batches)",
            len(all_companies),
            len(batches),
        )
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
        logger.debug("Entering find_companies_metadata_by_uuids count=%d batch_size=%d", len(company_uuids), batch_size)
        
        if not company_uuids:
            logger.debug("Exiting find_companies_metadata_by_uuids: empty UUID list")
            return {}
        
        # If list is small enough, execute single query
        if len(company_uuids) <= batch_size:
            stmt: Select = select(CompanyMetadata).where(CompanyMetadata.uuid.in_(company_uuids))
            result = await session.execute(stmt)
            company_metadata_list = result.scalars().all()
            company_metadata_dict = {cm.uuid: cm for cm in company_metadata_list}
            logger.debug("Exiting find_companies_metadata_by_uuids found=%d records (single batch)", len(company_metadata_dict))
            return company_metadata_dict
        
        # Split into batches and execute in parallel
        logger.debug("Splitting %d UUIDs into batches of %d", len(company_uuids), batch_size)
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
        
        logger.debug(
            "Exiting find_companies_metadata_by_uuids found=%d records (%d batches)",
            len(all_metadata),
            len(batches),
        )
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
        logger.debug("Entering find_contacts_by_company_uuids count=%d", len(company_uuids))
        
        if not company_uuids:
            logger.debug("Exiting find_contacts_by_company_uuids: empty UUID list")
            return {}
        
        contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
        
        # Batch query: fetch all contacts for all companies in one query
        stmt: Select = (
            select(Contact, contact_meta_alias)
            .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
            .where(Contact.company_id.in_(company_uuids))
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # Group contacts by company_id
        contacts_by_company: dict[str, list[tuple[Contact, Optional[ContactMetadata]]]] = {}
        for contact, contact_meta in rows:
            company_uuid = contact.company_id
            if company_uuid:
                if company_uuid not in contacts_by_company:
                    contacts_by_company[company_uuid] = []
                contacts_by_company[company_uuid].append((contact, contact_meta))
        
        logger.debug(
            "Exiting find_contacts_by_company_uuids found contacts for %d companies (total contacts=%d)",
            len(contacts_by_company),
            len(rows),
        )
        return contacts_by_company

    async def find_companies_metadata_by_linkedin_url(
        self, session: AsyncSession, linkedin_url: str
    ) -> list[CompanyMetadata]:
        """
        Find company metadata records by LinkedIn URL.
        
        Step 1 of sequential query for companies: Query companies_metadata table only.
        Returns list of CompanyMetadata objects.
        """
        logger.debug("Entering find_companies_metadata_by_linkedin_url linkedin_url=%s", linkedin_url)
        
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
                    logger.debug("Extracted company identifier from URL: %s, using pattern: %s", company_part, search_pattern)
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
        
        logger.debug(
            "Exiting find_companies_metadata_by_linkedin_url found=%d company metadata records",
            len(company_metadata_list),
        )
        return list(company_metadata_list)

