"""Repository for email finder queries."""

from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.base import AsyncRepository
from app.utils.batch_lookup import (
    batch_fetch_companies_by_uuids,
    batch_fetch_company_metadata_by_uuids,
    batch_fetch_contact_metadata_by_uuids,
)
from app.utils.logger import get_logger, log_database_query, log_database_error

logger = get_logger(__name__)


class EmailFinderRepository(AsyncRepository):
    """Repository for finding emails by contact name and company domain."""

    def __init__(self):
        """Initialize the repository."""
        # We don't extend a specific model, so we pass Contact as base
        super().__init__(Contact)

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        """Normalize domain for comparison (lowercase, no www)."""
        normalized = domain.lower().strip()
        if normalized.startswith("www."):
            normalized = normalized[4:]
        return normalized

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
        normalized_domain = self._normalize_domain(domain)
        
        # Strategy 1: Check normalized_domain column
        normalized_domain_subq = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        
        # Strategy 2: Extract domain from website column and match
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
        
        # Compiling SQL query for debugging
        try:
            _compiled = combined_subq.compile(compile_kwargs={"literal_binds": False})
        except Exception:
            # Error handling: SQL could not be compiled
            pass
        
        start_time = time.time()
        try:
            # Execute query to get count and UUIDs
            result = await session.execute(combined_subq)
            rows = result.scalars().all()
            company_uuids = list(rows)
            count = len(company_uuids)
            exists = count > 0
            
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table="companies_metadata",
                filters={"domain": normalized_domain},
                result_count=count,
                duration_ms=duration_ms,
                logger_name="app.repositories.email_finder",
            )
            
            # Check which strategy found results (only if companies exist)
            if not exists:
                # No companies found with domain using either normalized_domain column or website extraction
                return False
            
            # Check normalized_domain strategy
            normalized_start = time.time()
            normalized_result = await session.execute(normalized_domain_subq)
            normalized_uuids = list(normalized_result.scalars().all())
            normalized_count = len(normalized_uuids)
            normalized_duration = (time.time() - normalized_start) * 1000
            
            # Check website extraction strategy
            website_start = time.time()
            website_result = await session.execute(website_subq)
            website_uuids = list(website_result.scalars().all())
            website_count = len(website_uuids)
            website_duration = (time.time() - website_start) * 1000
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table="companies_metadata",
                error=exc,
                duration_ms=duration_ms,
                context={"domain": normalized_domain, "method": "check_companies_exist_by_domain"}
            )
            raise
        
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
        normalized_domain = self._normalize_domain(domain)
        first_name_normalized = first_name.strip()
        last_name_normalized = last_name.strip()
        # Normalized parameters: domain, first name, and last name
        
        # Step 1: Get company UUIDs from companies_metadata
        company_meta_uuids = await self._get_company_uuids_by_domain(session, normalized_domain)
        if not company_meta_uuids:
            # Step 1 - no company UUIDs found in companies_metadata for domain
            return []
        
        # Step 2: Validate company UUIDs exist in companies table
        step2_uuids = await self._validate_company_uuids(session, company_meta_uuids)
        if not step2_uuids:
            # Step 2 - no company UUIDs found in companies table
            return []
        
        # Step 3: Find contacts using cached company UUIDs
        email_results = await self._find_contacts_by_names(
            session, step2_uuids, first_name_normalized, last_name_normalized
        )
        
        # OPTIMIZATION: Only run diagnostics if no results found AND diagnostics enabled
        if len(email_results) == 0 and enable_diagnostics:
            # Step 3 - no results found, running diagnostic queries
            diagnostics = await self._run_diagnostic_queries(
                session=session,
                company_uuids=step2_uuids,
                first_name=first_name_normalized,
                last_name=last_name_normalized,
            )
        elif len(email_results) == 0:
            # No (uuid, email) pairs found, enable diagnostics for detailed breakdown
            pass
        
        return email_results
    
    async def _get_company_uuids_by_domain(
        self, session: AsyncSession, normalized_domain: str
    ) -> list[str]:
        """
        Get company UUIDs from companies_metadata using dual strategy.
        
        Returns:
            List of company metadata UUIDs
        """
        # Strategy 1: Check normalized_domain column (FAST - uses index)
        normalized_domain_stmt = select(CompanyMetadata.uuid).where(
            CompanyMetadata.normalized_domain == normalized_domain,
            CompanyMetadata.normalized_domain.isnot(None)
        )
        normalized_result = await session.execute(normalized_domain_stmt)
        normalized_uuids = list(normalized_result.scalars().all())
        
        # Strategy 2: Only if normalized_domain found nothing, try website extraction (SLOW)
        website_uuids = []
        if not normalized_uuids:
            # Trying slow website extraction which may take 20+ seconds
            website_domain_expression = self._extract_domain_from_website_sql(
                CompanyMetadata.website, normalized_domain
            )
            website_stmt = select(CompanyMetadata.uuid).where(
                and_(
                    CompanyMetadata.website.isnot(None),
                    func.trim(CompanyMetadata.website) != "",
                    website_domain_expression == normalized_domain
                )
            ).limit(1000)
            website_result = await session.execute(website_stmt)
            website_uuids = list(website_result.scalars().all())
        
        return list(set(normalized_uuids + website_uuids))

    async def _validate_company_uuids(
        self, session: AsyncSession, company_meta_uuids: list[str]
    ) -> list[str]:
        """Validate company UUIDs exist in companies table."""
        company_stmt = select(Company.uuid).where(Company.uuid.in_(company_meta_uuids))
        result = await session.execute(company_stmt)
        return list(result.scalars().all())

    async def _find_contacts_by_names(
        self,
        session: AsyncSession,
        company_uuids: list[str],
        first_name: str,
        last_name: str,
    ) -> list[tuple[str, str]]:
        """Find contacts by company UUIDs and names."""
        stmt: Select = (
            select(Contact.uuid, Contact.email, Contact.first_name, Contact.last_name, Contact.company_id)
            .where(
                and_(
                    Contact.company_id.in_(company_uuids),
                    Contact.first_name.isnot(None),
                    Contact.first_name.ilike(f"%{first_name}%"),
                    Contact.last_name.isnot(None),
                    Contact.last_name.ilike(f"%{last_name}%"),
                    Contact.email.isnot(None),
                    func.trim(Contact.email) != "",
                )
            )
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        email_results = []
        for row in rows:
            uuid_val, email_val, _, _, _ = row
            if uuid_val and email_val and email_val.strip():
                email_results.append((uuid_val, email_val.strip()))
        
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
        
        # OPTIMIZATION: Single query with conditional aggregation instead of 5 separate queries
        # Construct case statements using explicit value parameter to avoid Function.__init__() error
        first_name_condition = and_(
            Contact.first_name.isnot(None),
            Contact.first_name.ilike(f"%{first_name}%"),
        )
        last_name_condition = and_(
            Contact.last_name.isnot(None),
            Contact.last_name.ilike(f"%{last_name}%"),
        )
        both_names_condition = and_(
            Contact.first_name.isnot(None),
            Contact.first_name.ilike(f"%{first_name}%"),
            Contact.last_name.isnot(None),
            Contact.last_name.ilike(f"%{last_name}%"),
        )
        email_condition = and_(
            Contact.email.isnot(None),
            func.trim(Contact.email) != "",
        )
        
        # Use case().else_() method instead of else_= parameter to avoid Function.__init__() error
        diagnostic_stmt = select(
            func.count(Contact.uuid).label("total_contacts"),
            func.sum(
                case(
                    (first_name_condition, 1),
                ).else_(0)
            ).label("first_name_count"),
            func.sum(
                case(
                    (last_name_condition, 1),
                ).else_(0)
            ).label("last_name_count"),
            func.sum(
                case(
                    (both_names_condition, 1),
                ).else_(0)
            ).label("both_names_count"),
            func.sum(
                case(
                    (email_condition, 1),
                ).else_(0)
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
            return []
        
        # Email addresses list (first 10 if more than 10)
        if len(emails) > 10:
            # Additional emails beyond the first 10
            pass
        
        # Fetch contacts only (no joins)
        stmt: Select = select(Contact).where(Contact.email.in_(emails))
        
        # Compiling SQL query for debugging
        try:
            _compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        except Exception:
            # Error handling: SQL could not be compiled
            pass
        
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
        
        # Field extraction statistics: extracted counts for uuid, email, first_name, last_name, and company_id
        
        # Sample extracted values for debugging
        if sample_records:
            for i, record in enumerate(sample_records):
                pass
        
        if len(rows) != len(emails):
            missing_count = len(emails) - len(rows)
            # Email count mismatch - identifying which emails were not found
            found_emails = {row[0].email.lower() if row[0].email else None for row in rows if row[0].email}
            missing_emails = [email for email in emails if email.lower() not in found_emails]
            if missing_emails:
                # Missing emails list (first 10 if more than 10)
                if len(missing_emails) > 10:
                    # Additional missing emails beyond the first 10
                    pass
        
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
        
        normalized_domain = self._normalize_domain(domain)
        
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
            # Warning condition: Diagnostic - no companies found with normalized_domain
            if website_count > 0:
                # Warning condition: Diagnostic - found companies with domain in website field, normalized_domain column may not be populated
                pass
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
        
        return diagnostics

