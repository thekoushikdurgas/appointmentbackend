"""Repository for email finder queries."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Select, Text, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.logging import get_logger
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
)

logger = get_logger(__name__)


class EmailFinderRepository(AsyncRepository):
    """Repository for finding emails by contact name and company domain."""

    def __init__(self):
        """Initialize the repository."""
        logger.debug("Entering EmailFinderRepository.__init__")
        # We don't extend a specific model, so we pass Contact as base
        super().__init__(Contact)
        logger.debug("Exiting EmailFinderRepository.__init__")

    @staticmethod
    def _extract_domain_from_website_sql(website_column, normalized_domain: str):
        """
        Extract normalized domain from website column using SQL functions.
        
        Uses PostgreSQL-specific functions to extract domain from URLs:
        1. Remove protocol (http://, https://)
        2. Extract hostname (everything before first /)
        3. Remove port number
        4. Remove www. prefix
        5. Convert to lowercase
        
        Args:
            website_column: SQLAlchemy column reference (CompanyMetadata.website)
            normalized_domain: The normalized domain string to match against
            
        Returns:
            SQLAlchemy expression that extracts and normalizes domain from website column
        """
        # Step 1: Remove protocol (http://, https://)
        no_protocol = func.regexp_replace(
            func.coalesce(website_column, ""),
            r"^https?://",
            "",
            "i"
        )
        # Step 2: Extract hostname (everything before first /)
        hostname = func.split_part(no_protocol, "/", 1)
        # Step 3: Remove port number
        no_port = func.split_part(hostname, ":", 1)
        # Step 4: Remove www. prefix and convert to lowercase
        domain_expression = func.lower(
            func.regexp_replace(no_port, r"^www\.", "", "i")
        )
        return domain_expression

    async def check_companies_exist_by_domain(
        self,
        session: AsyncSession,
        domain: str,
    ) -> bool:
        """
        Check if any companies exist for the given domain.
        
        Searches companies_metadata table using dual strategy:
        1. Check normalized_domain column (existing)
        2. Extract domain from website column and match (new)
        
        Args:
            session: Database session
            domain: Company domain to check (normalized, case-insensitive)
            
        Returns:
            True if at least one company matches the domain via either strategy, False otherwise
        """
        logger.debug(
            "Checking if companies exist for domain: %s (using dual search strategy)",
            domain,
        )
        
        # Normalize domain for comparison (lowercase, no www)
        normalized_domain = domain.lower().strip()
        if normalized_domain.startswith("www."):
            normalized_domain = normalized_domain[4:]
            logger.debug("Removed www. prefix, normalized_domain=%s", normalized_domain)
        
        logger.debug("Using normalized_domain for search: %s", normalized_domain)
        
        # Strategy 1: Check normalized_domain column
        logger.debug("Strategy 1: Checking normalized_domain column")
        normalized_domain_subq = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        
        # Strategy 2: Extract domain from website column and match
        logger.debug("Strategy 2: Extracting domain from website column")
        website_domain_expression = self._extract_domain_from_website_sql(
            CompanyMetadata.website,
            normalized_domain
        )
        website_subq = select(CompanyMetadata.uuid).where(
            and_(
                CompanyMetadata.website.isnot(None),
                func.trim(CompanyMetadata.website) != "",
                website_domain_expression == normalized_domain
            )
        )
        
        # Combine both strategies with OR condition
        combined_subq = select(CompanyMetadata.uuid).where(
            or_(
                CompanyMetadata.uuid.in_(normalized_domain_subq),
                CompanyMetadata.uuid.in_(website_subq)
            )
        ).distinct()
        
        # Log the SQL query
        try:
            compiled = combined_subq.compile(compile_kwargs={"literal_binds": False})
            logger.debug("Companies exist query (combined strategy): %s", str(compiled))
        except Exception as e:
            logger.debug("Could not compile SQL for logging: %s", e)
        
        # Execute query to get count and UUIDs
        result = await session.execute(combined_subq)
        rows = result.scalars().all()
        company_uuids = list(rows)
        count = len(company_uuids)
        exists = count > 0
        
        # Check which strategy found results
        if exists:
            # Check normalized_domain strategy
            normalized_result = await session.execute(normalized_domain_subq)
            normalized_uuids = list(normalized_result.scalars().all())
            normalized_count = len(normalized_uuids)
            
            # Check website extraction strategy
            website_result = await session.execute(website_subq)
            website_uuids = list(website_result.scalars().all())
            website_count = len(website_uuids)
            
            logger.info(
                "Companies exist check for domain %s: found=%d companies (normalized_domain=%d, website_extraction=%d), exists=%s",
                normalized_domain,
                count,
                normalized_count,
                website_count,
                exists,
            )
            
            if normalized_count > 0:
                logger.debug(
                    "Strategy 1 (normalized_domain) found %d company UUIDs: %s",
                    normalized_count,
                    normalized_uuids[:10] if normalized_count > 10 else normalized_uuids,
                )
            if website_count > 0:
                logger.debug(
                    "Strategy 2 (website extraction) found %d company UUIDs: %s",
                    website_count,
                    website_uuids[:10] if website_count > 10 else website_uuids,
                )
            
            logger.debug(
                "Total unique company UUIDs found: %s",
                company_uuids[:10] if len(company_uuids) > 10 else company_uuids,
            )
            if len(company_uuids) > 10:
                logger.debug("... and %d more company UUIDs", len(company_uuids) - 10)
        else:
            logger.warning(
                "No companies found with domain=%s using either normalized_domain column or website extraction",
                normalized_domain,
            )
        
        return exists

    async def find_emails_by_name_and_domain(
        self,
        session: AsyncSession,
        first_name: str,
        last_name: str,
        domain: str,
        enable_diagnostics: bool = False,
    ) -> list[tuple[str, str]]:
        """
        Find email addresses by contact name and company domain using optimized approach.
        
        This method uses an optimized strategy:
        1. Find company UUIDs from companies_metadata (prioritize normalized_domain, fallback to website extraction)
        2. Validate company UUIDs exist in companies table
        3. Find contact emails using cached company UUIDs (no subquery re-execution)
        
        Args:
            session: Database session
            first_name: Contact first name (case-insensitive partial match)
            last_name: Contact last name (case-insensitive partial match)
            domain: Company domain to match (normalized, case-insensitive)
            enable_diagnostics: If True, run diagnostic queries (only when no results found)
            
        Returns:
            List of tuples (uuid, email) where uuid is contact UUID and email is email address
            
        Note:
            - Prioritizes normalized_domain column (indexed) over website extraction
            - Caches company UUIDs to avoid re-executing subqueries
            - Uses direct UUID list filtering instead of nested subqueries
            - Uses idx_companies_metadata_normalized_domain index
            - Uses idx_contacts_company_id and trigram indexes for name matching
        """
        logger.debug(
            "Entering find_emails_by_name_and_domain first_name=%s last_name=%s domain=%s",
            first_name,
            last_name,
            domain,
        )
        
        # Normalize domain for comparison (lowercase, no www)
        normalized_domain = domain.lower().strip()
        if normalized_domain.startswith("www."):
            normalized_domain = normalized_domain[4:]
            logger.debug("Removed www. prefix, normalized_domain=%s", normalized_domain)
        
        # Normalize names
        first_name_normalized = first_name.strip()
        last_name_normalized = last_name.strip()
        logger.debug(
            "Normalized parameters: domain=%s first_name=%s last_name=%s",
            normalized_domain,
            first_name_normalized,
            last_name_normalized,
        )
        
        # Step 1: Get company UUIDs from companies_metadata
        # OPTIMIZATION: Prioritize normalized_domain (indexed), only use website extraction as fallback
        logger.debug("Step 1: Finding company UUIDs from companies_metadata for domain=%s", normalized_domain)
        
        # Strategy 1: Check normalized_domain column (FAST - uses index)
        normalized_domain_stmt = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        
        normalized_result = await session.execute(normalized_domain_stmt)
        normalized_uuids = list(normalized_result.scalars().all())
        normalized_count = len(normalized_uuids)
        
        logger.debug("Step 1 Strategy 1 (normalized_domain): Found %d company UUIDs", normalized_count)
        
        # Strategy 2: Only if normalized_domain found nothing, try website extraction (SLOW - no index)
        website_uuids = []
        website_count = 0
        if normalized_count == 0:
            logger.debug("Step 1 Strategy 2: normalized_domain found nothing, trying website extraction")
            website_domain_expression = self._extract_domain_from_website_sql(
                CompanyMetadata.website,
                normalized_domain
            )
            website_stmt = select(CompanyMetadata.uuid).where(
                and_(
                    CompanyMetadata.website.isnot(None),
                    func.trim(CompanyMetadata.website) != "",
                    website_domain_expression == normalized_domain
                )
            )
            website_result = await session.execute(website_stmt)
            website_uuids = list(website_result.scalars().all())
            website_count = len(website_uuids)
            logger.debug("Step 1 Strategy 2 (website extraction): Found %d company UUIDs", website_count)
        
        # Combine results (usually just normalized_uuids, but include website_uuids if any)
        company_meta_uuids = list(set(normalized_uuids + website_uuids))
        step1_count = len(company_meta_uuids)
        
        logger.info(
            "Step 1 - Found %d company UUIDs from companies_metadata for domain=%s (normalized_domain=%d, website_extraction=%d)",
            step1_count,
            normalized_domain,
            normalized_count,
            website_count,
        )
        
        if step1_count == 0:
            logger.warning("Step 1 - No company UUIDs found in companies_metadata for domain=%s", normalized_domain)
            return []
        
        if step1_count > 10:
            logger.debug("Step 1 - Company UUIDs (first 10): %s ... and %d more", company_meta_uuids[:10], step1_count - 10)
        else:
            logger.debug("Step 1 - Company UUIDs: %s", company_meta_uuids)
        
        # Step 2: Validate company UUIDs exist in companies table
        # OPTIMIZATION: Use cached UUID list directly instead of subquery
        logger.debug("Step 2: Validating company UUIDs exist in companies table")
        company_stmt = select(Company.uuid).where(Company.uuid.in_(company_meta_uuids))
        
        step2_result = await session.execute(company_stmt)
        step2_uuids = list(step2_result.scalars().all())
        step2_count = len(step2_uuids)
        
        logger.info("Step 2 - Found %d company UUIDs from companies table", step2_count)
        
        if step2_count == 0:
            logger.warning("Step 2 - No company UUIDs found in companies table (mismatch with companies_metadata)")
            return []
        
        if step1_count != step2_count:
            logger.warning(
                "Step 1/2 mismatch: companies_metadata has %d UUIDs but companies table has %d UUIDs",
                step1_count,
                step2_count,
            )
        
        # Step 3: Find contacts using cached company UUIDs
        # OPTIMIZATION: Use direct UUID list instead of nested subquery
        logger.debug(
            "Step 3: Searching contacts with company_ids=%d first_name=%s last_name=%s",
            step2_count,
            first_name_normalized,
            last_name_normalized,
        )
        
        # Main query: Use cached UUIDs directly
        stmt: Select = (
            select(
                Contact.uuid,
                Contact.email,
                Contact.first_name,
                Contact.last_name,
                Contact.company_id
            )
            .where(
                and_(
                    # Filter by company_id using cached UUID list (uses idx_contacts_company_id)
                    Contact.company_id.in_(step2_uuids),
                    # Name matches (use trigram indexes)
                    Contact.first_name.isnot(None),
                    Contact.first_name.ilike(f"%{first_name_normalized}%"),
                    Contact.last_name.isnot(None),
                    Contact.last_name.ilike(f"%{last_name_normalized}%"),
                    # Email check
                    Contact.email.isnot(None),
                    func.trim(Contact.email) != "",
                )
            )
        )
        
        # Log Step 3 query
        try:
            compiled_step3 = stmt.compile(compile_kwargs={"literal_binds": False})
            logger.debug("Step 3 SQL query: %s", str(compiled_step3))
        except Exception as e:
            logger.debug("Could not compile Step 3 SQL for logging: %s", e)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # Extract email results
        email_results = []
        for row in rows:
            uuid_val, email_val, first_name_val, last_name_val, company_id_val = row
            if uuid_val and email_val and email_val.strip():
                email_results.append((uuid_val, email_val.strip()))
        
        logger.info(
            "Step 3 - Found %d contacts matching all criteria (company_id + first_name + last_name + email)",
            len(email_results),
        )
        
        # OPTIMIZATION: Only run diagnostics if no results found AND diagnostics enabled
        if len(email_results) == 0 and enable_diagnostics:
            logger.debug("Step 3 - No results found, running diagnostic queries")
            diagnostics = await self._run_diagnostic_queries(
                session=session,
                company_uuids=step2_uuids,
                first_name=first_name_normalized,
                last_name=last_name_normalized,
            )
            logger.warning(
                "No (uuid, email) pairs found. Diagnostic summary: total_contacts=%d first_name_matches=%d last_name_matches=%d both_names_matches=%d contacts_with_emails=%d",
                diagnostics.get("total_contacts", 0),
                diagnostics.get("first_name_count", 0),
                diagnostics.get("last_name_count", 0),
                diagnostics.get("both_names_count", 0),
                diagnostics.get("emails_count", 0),
            )
        elif len(email_results) == 0:
            logger.warning("No (uuid, email) pairs found. Enable diagnostics for detailed breakdown.")
        
        logger.debug(
            "Exiting find_emails_by_name_and_domain found=%d (uuid, email) pairs",
            len(email_results),
        )
        return email_results
    
    async def _run_diagnostic_queries(
        self,
        session: AsyncSession,
        company_uuids: list[str],
        first_name: str,
        last_name: str,
    ) -> dict:
        """
        Run diagnostic queries to understand why contacts weren't found.
        OPTIMIZATION: Combined into single query using conditional aggregation.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs to check
            first_name: Contact first name
            last_name: Contact last name
            
        Returns:
            Dictionary with diagnostic counts
        """
        logger.debug("Running combined diagnostic queries for %d company UUIDs", len(company_uuids))
        
        # OPTIMIZATION: Single query with conditional aggregation instead of 5 separate queries
        diagnostic_stmt = select(
            func.count(Contact.uuid).label("total_contacts"),
            func.sum(
                func.case(
                    (and_(
                        Contact.first_name.isnot(None),
                        Contact.first_name.ilike(f"%{first_name}%"),
                    ), 1),
                    else_=0
                )
            ).label("first_name_count"),
            func.sum(
                func.case(
                    (and_(
                        Contact.last_name.isnot(None),
                        Contact.last_name.ilike(f"%{last_name}%"),
                    ), 1),
                    else_=0
                )
            ).label("last_name_count"),
            func.sum(
                func.case(
                    (and_(
                        Contact.first_name.isnot(None),
                        Contact.first_name.ilike(f"%{first_name}%"),
                        Contact.last_name.isnot(None),
                        Contact.last_name.ilike(f"%{last_name}%"),
                    ), 1),
                    else_=0
                )
            ).label("both_names_count"),
            func.sum(
                func.case(
                    (and_(
                        Contact.email.isnot(None),
                        func.trim(Contact.email) != "",
                    ), 1),
                    else_=0
                )
            ).label("emails_count"),
        ).where(
            Contact.company_id.in_(company_uuids)
        )
        
        result = await session.execute(diagnostic_stmt)
        row = result.first()
        
        diagnostics = {
            "total_contacts": row.total_contacts or 0,
            "first_name_count": row.first_name_count or 0,
            "last_name_count": row.last_name_count or 0,
            "both_names_count": row.both_names_count or 0,
            "emails_count": row.emails_count or 0,
        }
        
        logger.debug("Diagnostic results: %s", diagnostics)
        return diagnostics

    async def get_contacts_by_emails(
        self,
        session: AsyncSession,
        emails: list[str],
    ) -> list[tuple[Contact, Optional[ContactMetadata], Optional[Company], Optional[CompanyMetadata]]]:
        """
        Fetch full contact, company, and metadata data for a list of email addresses.
        
        Args:
            session: Database session
            emails: List of email addresses to fetch data for
            
        Returns:
            List of tuples: (Contact, ContactMetadata, Company, CompanyMetadata)
        """
        if not emails:
            logger.debug("get_contacts_by_emails: Empty email list, returning empty list")
            return []
        
        logger.debug("Fetching full contact data for %d emails", len(emails))
        logger.debug("Email addresses: %s", emails[:10] if len(emails) > 10 else emails)
        if len(emails) > 10:
            logger.debug("... and %d more emails", len(emails) - 10)
        
        # Fetch contacts only (no joins)
        stmt: Select = select(Contact).where(Contact.email.in_(emails))
        
        # Log the SQL query
        try:
            compiled = stmt.compile(compile_kwargs={"literal_binds": False})
            logger.debug("get_contacts_by_emails SQL query: %s", str(compiled))
        except Exception as e:
            logger.debug("Could not compile SQL for logging: %s", e)
        
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
        
        logger.info("Fetched full data for %d contacts (requested %d emails)", len(rows), len(emails))
        
        # Extract and log field statistics
        uuids_extracted = 0
        emails_extracted = 0
        first_names_extracted = 0
        last_names_extracted = 0
        company_ids_extracted = 0
        
        # Sample values for debugging (first 3 records)
        sample_records = []
        
        for row in rows:
            contact, contact_meta, company, company_meta = row
            
            # Extract and count fields
            if contact and contact.uuid:
                uuids_extracted += 1
            if contact and contact.email and contact.email.strip():
                emails_extracted += 1
            if contact and contact.first_name:
                first_names_extracted += 1
            if contact and contact.last_name:
                last_names_extracted += 1
            if contact and contact.company_id:
                company_ids_extracted += 1
            
            # Collect sample records (first 3)
            if len(sample_records) < 3:
                sample_records.append({
                    "uuid": contact.uuid if contact else None,
                    "email": contact.email if contact else None,
                    "first_name": contact.first_name if contact else None,
                    "last_name": contact.last_name if contact else None,
                    "company_id": contact.company_id if contact else None,
                })
        
        # Log field extraction statistics
        logger.debug(
            "Field extraction from contacts: uuid=%d, email=%d, first_name=%d, last_name=%d, company_id=%d",
            uuids_extracted,
            emails_extracted,
            first_names_extracted,
            last_names_extracted,
            company_ids_extracted,
        )
        
        # Log sample extracted values
        if sample_records:
            logger.debug("Sample extracted contact fields (first %d records):", len(sample_records))
            for i, record in enumerate(sample_records):
                logger.debug(
                    "  Record %d: uuid=%s, email=%s, first_name=%s, last_name=%s, company_id=%s",
                    i + 1,
                    record["uuid"],
                    record["email"],
                    record["first_name"],
                    record["last_name"],
                    record["company_id"],
                )
        
        if len(rows) != len(emails):
            missing_count = len(emails) - len(rows)
            logger.warning(
                "Email count mismatch: requested %d emails but retrieved %d contacts (%d missing)",
                len(emails),
                len(rows),
                missing_count,
            )
            # Log which emails were not found
            found_emails = {row[0].email.lower() if row[0].email else None for row in rows if row[0].email}
            missing_emails = [email for email in emails if email.lower() not in found_emails]
            if missing_emails:
                logger.warning("Missing emails: %s", missing_emails[:10] if len(missing_emails) > 10 else missing_emails)
                if len(missing_emails) > 10:
                    logger.warning("... and %d more missing emails", len(missing_emails) - 10)
        
        logger.info(
            "Contact field extraction completed: %d contacts processed, %d emails extracted",
            len(rows),
            emails_extracted,
        )
        
        return rows

    async def diagnose_search_failure(
        self,
        session: AsyncSession,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        """
        Diagnostic method to help debug why a search failed.
        
        Checks various conditions to identify why contacts weren't found:
        - Domain existence in normalized_domain vs website field
        - Company UUIDs for the domain
        - Contact counts for those companies
        - Name matching breakdowns
        
        Args:
            session: Database session
            domain: Company domain to check
            first_name: Contact first name
            last_name: Contact last name
            
        Returns:
            Dictionary with diagnostic information
        """
        logger.debug("Running diagnostic for search failure: domain=%s first_name=%s last_name=%s", domain, first_name, last_name)
        
        normalized_domain = domain.lower().strip()
        if normalized_domain.startswith("www."):
            normalized_domain = normalized_domain[4:]
        
        first_name_normalized = first_name.strip()
        last_name_normalized = last_name.strip()
        
        diagnostics = {
            "domain": normalized_domain,
            "first_name": first_name_normalized,
            "last_name": last_name_normalized,
        }
        
        # Check normalized_domain column
        normalized_domain_count_stmt = select(func.count(CompanyMetadata.uuid)).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        normalized_result = await session.execute(normalized_domain_count_stmt)
        normalized_count = normalized_result.scalar() or 0
        diagnostics["companies_with_normalized_domain"] = normalized_count
        
        # Check website field (raw)
        website_count_stmt = select(func.count(CompanyMetadata.uuid)).where(
            CompanyMetadata.website.ilike(f"%{normalized_domain}%"),
            CompanyMetadata.website.isnot(None)
        )
        website_result = await session.execute(website_count_stmt)
        website_count = website_result.scalar() or 0
        diagnostics["companies_with_domain_in_website"] = website_count
        
        if normalized_count == 0:
            logger.warning("Diagnostic: No companies found with normalized_domain=%s", normalized_domain)
            if website_count > 0:
                logger.warning("Diagnostic: But found %d companies with domain in website field - normalized_domain column may not be populated", website_count)
            return diagnostics
        
        # Get company UUIDs
        company_meta_subq = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        company_subq = select(Company.uuid).where(
            Company.uuid.in_(company_meta_subq)
        )
        
        # Total contacts for these companies
        total_contacts_stmt = select(func.count(Contact.uuid)).where(
            Contact.company_id.in_(company_subq)
        )
        total_result = await session.execute(total_contacts_stmt)
        diagnostics["total_contacts_for_companies"] = total_result.scalar() or 0
        
        # Contacts with matching first_name
        first_name_stmt = select(func.count(Contact.uuid)).where(
            and_(
                Contact.company_id.in_(company_subq),
                Contact.first_name.isnot(None),
                Contact.first_name.ilike(f"%{first_name_normalized}%"),
            )
        )
        first_name_result = await session.execute(first_name_stmt)
        diagnostics["contacts_with_matching_first_name"] = first_name_result.scalar() or 0
        
        # Contacts with matching last_name
        last_name_stmt = select(func.count(Contact.uuid)).where(
            and_(
                Contact.company_id.in_(company_subq),
                Contact.last_name.isnot(None),
                Contact.last_name.ilike(f"%{last_name_normalized}%"),
            )
        )
        last_name_result = await session.execute(last_name_stmt)
        diagnostics["contacts_with_matching_last_name"] = last_name_result.scalar() or 0
        
        # Contacts with both names
        both_names_stmt = select(func.count(Contact.uuid)).where(
            and_(
                Contact.company_id.in_(company_subq),
                Contact.first_name.isnot(None),
                Contact.first_name.ilike(f"%{first_name_normalized}%"),
                Contact.last_name.isnot(None),
                Contact.last_name.ilike(f"%{last_name_normalized}%"),
            )
        )
        both_names_result = await session.execute(both_names_stmt)
        diagnostics["contacts_with_both_names"] = both_names_result.scalar() or 0
        
        # Contacts with emails
        emails_stmt = select(func.count(Contact.uuid)).where(
            and_(
                Contact.company_id.in_(company_subq),
                Contact.email.isnot(None),
                func.trim(Contact.email) != "",
            )
        )
        emails_result = await session.execute(emails_stmt)
        diagnostics["contacts_with_emails"] = emails_result.scalar() or 0
        
        logger.info("Diagnostic results: %s", diagnostics)
        return diagnostics

