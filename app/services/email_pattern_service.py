"""Service layer for email pattern operations."""

import csv
import io
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional
from uuid import uuid5, NAMESPACE_URL

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contacts import Contact
from app.models.email_patterns import EmailPattern
from app.repositories.email_patterns import EmailPatternRepository
from app.repositories.companies import CompanyRepository
from app.models.companies import Company
from app.schemas.email_patterns import (
    EmailPatternAnalyzeResponse,
    EmailPatternBulkCreate,
    EmailPatternCreate,
    EmailPatternImportResponse,
    EmailPatternResponse,
    EmailPatternUpdate,
    PatternAnalysisResult,
)
from app.utils.email_generator import _get_name_variations

class EmailPatternService:
    """Business logic for email pattern operations."""

    def __init__(
        self,
        email_pattern_repo: Optional[EmailPatternRepository] = None,
        company_repo: Optional[CompanyRepository] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        self.email_pattern_repo = email_pattern_repo or EmailPatternRepository()
        self.company_repo = company_repo or CompanyRepository()

    async def create_pattern(
        self,
        session: AsyncSession,
        pattern_data: EmailPatternCreate,
        upsert: bool = False,
    ) -> EmailPatternResponse:
        """Create a new email pattern or update existing if upsert=True."""
        # Creating email pattern: company_uuid=%s pattern_format=%s upsert=%s

        # Check if pattern already exists
        if pattern_data.pattern_format:
            existing = await self.email_pattern_repo.get_by_pattern_format(
                session,
                pattern_data.company_uuid,
                pattern_data.pattern_format,
            )
            if existing:
                if upsert:
                    # Atomically increment contact_count by 1, preserve other fields
                    # Use atomic database update to prevent race conditions
                    updated_pattern = await self.email_pattern_repo.increment_contact_count(
                        session,
                        existing.uuid,
                        increment=1,
                    )
                    if updated_pattern:
                        # Update timestamp (atomic increment doesn't update updated_at)
                        updated_pattern.updated_at = datetime.now()
                        await session.commit()
                        await session.refresh(updated_pattern)
                        
                        # Updated existing email pattern (upsert): uuid=%s company_uuid=%s contact_count=%d
                        
                        return EmailPatternResponse.model_validate(updated_pattern)
                    else:
                        # Pattern was deleted between check and update (rare race condition)
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Pattern was deleted during update",
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Pattern '{pattern_data.pattern_format}' already exists for this company",
                    )

        # Create new pattern
        pattern = EmailPattern(
            uuid=pattern_data.uuid or str(uuid.uuid4()),
            company_uuid=pattern_data.company_uuid,
            pattern_format=pattern_data.pattern_format,
            pattern_string=pattern_data.pattern_string,
            contact_count=pattern_data.contact_count,
            is_auto_extracted=pattern_data.is_auto_extracted,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        session.add(pattern)
        await session.commit()
        await session.refresh(pattern)

        # Created email pattern: uuid=%s company_uuid=%s

        return EmailPatternResponse.model_validate(pattern)

    async def get_patterns_by_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> list[EmailPatternResponse]:
        """Get all patterns for a company."""
        # Getting patterns for company: company_uuid=%s

        patterns = await self.email_pattern_repo.get_by_company_uuid(session, company_uuid)

        return [EmailPatternResponse.model_validate(p) for p in patterns]

    async def update_pattern(
        self,
        session: AsyncSession,
        pattern_uuid: str,
        pattern_data: EmailPatternUpdate,
    ) -> EmailPatternResponse:
        """Update an existing email pattern."""
        # Updating email pattern: pattern_uuid=%s

        pattern = await self.email_pattern_repo.get_by_uuid(session, pattern_uuid)
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pattern with UUID '{pattern_uuid}' not found",
            )

        # Update fields
        if pattern_data.pattern_format is not None:
            pattern.pattern_format = pattern_data.pattern_format
        if pattern_data.pattern_string is not None:
            pattern.pattern_string = pattern_data.pattern_string
        if pattern_data.contact_count is not None:
            pattern.contact_count = pattern_data.contact_count
        if pattern_data.is_auto_extracted is not None:
            pattern.is_auto_extracted = pattern_data.is_auto_extracted

        pattern.updated_at = datetime.now()

        await session.commit()
        await session.refresh(pattern)

        # Updated email pattern: pattern_uuid=%s

        return EmailPatternResponse.model_validate(pattern)

    async def delete_pattern(
        self,
        session: AsyncSession,
        pattern_uuid: str,
    ) -> None:
        """Delete an email pattern."""
        # Deleting email pattern: pattern_uuid=%s

        pattern = await self.email_pattern_repo.get_by_uuid(session, pattern_uuid)
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pattern with UUID '{pattern_uuid}' not found",
            )

        await session.delete(pattern)
        await session.commit()

        # Deleted email pattern: pattern_uuid=%s

    def extract_pattern_from_email(
        self,
        email: str,
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> Optional[tuple[str, str]]:
        """
        Extract pattern format and pattern string from an email address.
        
        Args:
            email: Email address (e.g., "john.doe@example.com")
            first_name: Contact first name
            last_name: Contact last name
            
        Returns:
            Tuple of (pattern_format, pattern_string) or None if pattern cannot be determined
        """
        if not email or "@" not in email:
            return None

        local_part = email.split("@")[0].lower()

        if not first_name or not last_name:
            # If we don't have names, we can't determine the pattern
            return None

        # Get name variations
        name_vars = _get_name_variations(first_name, last_name)

        # Try to match against known patterns
        # Check Tier 1 patterns first (most common)
        patterns_to_check = [
            # first.last
            (f"{name_vars['fn']}.{name_vars['ln']}", "first.last"),
            # firstlast
            (f"{name_vars['fn']}{name_vars['ln']}", "firstlast"),
            # first
            (name_vars["fn"], "first"),
            # f.last
            (f"{name_vars['f_initial']}.{name_vars['ln']}", "f.last"),
            # flast
            (f"{name_vars['f_initial']}{name_vars['ln']}", "flast"),
            # first.l
            (f"{name_vars['fn']}.{name_vars['l_initial']}", "first.l"),
            # first_last
            (f"{name_vars['fn']}_{name_vars['ln']}", "first_last"),
            # first_l
            (f"{name_vars['fn']}_{name_vars['l_initial']}", "first_l"),
            # first-last
            (f"{name_vars['fn']}-{name_vars['ln']}", "first-last"),
            # first-l
            (f"{name_vars['fn']}-{name_vars['l_initial']}", "first-l"),
        ]

        # Check Tier 2 patterns
        patterns_to_check.extend([
            # f.l
            (f"{name_vars['f_initial']}.{name_vars['l_initial']}", "f.l"),
            # fl
            (f"{name_vars['f_initial']}{name_vars['l_initial']}", "fl"),
            # last.first
            (f"{name_vars['ln']}.{name_vars['fn']}", "last.first"),
            # lastfirst
            (f"{name_vars['ln']}{name_vars['fn']}", "lastfirst"),
            # last.f
            (f"{name_vars['ln']}.{name_vars['f_initial']}", "last.f"),
            # l.first
            (f"{name_vars['l_initial']}.{name_vars['fn']}", "l.first"),
            # l.f
            (f"{name_vars['l_initial']}.{name_vars['f_initial']}", "l.f"),
            # first.las
            (f"{name_vars['fn']}.{name_vars['las']}", "first.las"),
            # fi.last
            (f"{name_vars['fi']}.{name_vars['ln']}", "fi.last"),
            # fi.las
            (f"{name_vars['fi']}.{name_vars['las']}", "fi.las"),
        ])

        # Check if local part matches any pattern
        for pattern_string, pattern_format in patterns_to_check:
            if local_part == pattern_string:
                return (pattern_format, pattern_string)

        # Check for numeric suffixes (e.g., "john.doe2", "johndoe123")
        # This handles emails with numbers that don't match standard patterns
        import re
        numeric_match = re.match(r'^(.+?)(\d+)$', local_part)
        if numeric_match:
            base_local = numeric_match.group(1)
            numeric_suffix = numeric_match.group(2)
            
            # Try matching base_local against known patterns
            for pattern_string, pattern_format in patterns_to_check:
                if base_local == pattern_string:
                    # Found match with numeric suffix
                    # Return pattern format with numeric indicator and full local part
                    # Pattern format stays the same, pattern_string includes the number
                    return (pattern_format, local_part)  # Return full local_part including number

        # If no exact match, return None
        return None

    async def analyze_company_emails(
        self,
        session: AsyncSession,
        company_uuid: str,
        force_reanalyze: bool = False,
    ) -> EmailPatternAnalyzeResponse:
        """
        Analyze all contacts' emails for a company and extract patterns.
        
        Args:
            session: Database session
            company_uuid: Company UUID to analyze
            force_reanalyze: If True, reanalyze even if patterns already exist
            
        Returns:
            EmailPatternAnalyzeResponse with analysis results
        """
        # Starting email pattern analysis: company_uuid=%s force_reanalyze=%s
        # (company_uuid, force_reanalyze)

        # Check if patterns already exist
        existing_patterns = await self.email_pattern_repo.get_by_company_uuid(session, company_uuid)
        if existing_patterns and not force_reanalyze:
            # Patterns already exist for company: company_uuid=%s count=%d
            # (company_uuid, len(existing_patterns))
            # Return existing patterns
            patterns = [EmailPatternResponse.model_validate(p) for p in existing_patterns]
            return EmailPatternAnalyzeResponse(
                company_uuid=company_uuid,
                patterns_found=len(patterns),
                contacts_analyzed=sum(p.contact_count for p in existing_patterns),
                patterns=[
                    PatternAnalysisResult(
                        pattern_format=p.pattern_format or "",
                        pattern_string=p.pattern_string or "",
                        contact_count=p.contact_count,
                        sample_emails=[],
                    )
                    for p in patterns
                ],
                created=0,
                updated=0,
            )

        # Query all contacts for this company that have emails
        stmt = (
            select(Contact)
            .where(Contact.company_id == company_uuid)
            .where(Contact.email.isnot(None))
            .where(Contact.email != "")
        )

        result = await session.execute(stmt)
        contacts = result.scalars().all()

        # Found contacts with emails: company_uuid=%s count=%d
        # (company_uuid, len(contacts))

        # Group patterns by format
        pattern_groups: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "sample_emails": []}
        )

        analyzed_count = 0
        for contact in contacts:
            if not contact.email or not contact.first_name or not contact.last_name:
                continue

            pattern_result = self.extract_pattern_from_email(
                contact.email,
                contact.first_name,
                contact.last_name,
            )

            if pattern_result:
                pattern_format, pattern_string = pattern_result
                key = f"{pattern_format}:{pattern_string}"
                pattern_groups[key]["count"] += 1
                pattern_groups[key]["pattern_format"] = pattern_format
                pattern_groups[key]["pattern_string"] = pattern_string
                # Store sample emails (max 5 per pattern)
                if len(pattern_groups[key]["sample_emails"]) < 5:
                    pattern_groups[key]["sample_emails"].append(contact.email)
                analyzed_count += 1

        # Pattern extraction completed: company_uuid=%s patterns_found=%d contacts_analyzed=%d

        # Create or update patterns in database
        created_count = 0
        updated_count = 0
        pattern_results = []

        for key, pattern_data in pattern_groups.items():
            pattern_format = pattern_data["pattern_format"]
            pattern_string = pattern_data["pattern_string"]
            contact_count = pattern_data["count"]

            # Check if pattern already exists
            existing = await self.email_pattern_repo.get_by_pattern_format(
                session,
                company_uuid,
                pattern_format,
            )

            if existing:
                # Update existing pattern
                existing.contact_count = contact_count
                existing.pattern_string = pattern_string
                existing.updated_at = datetime.now()
                updated_count += 1
                pattern_results.append(
                    PatternAnalysisResult(
                        pattern_format=pattern_format,
                        pattern_string=pattern_string,
                        contact_count=contact_count,
                        sample_emails=pattern_data["sample_emails"],
                    )
                )
            else:
                # Create new pattern
                new_pattern = EmailPattern(
                    uuid=str(uuid.uuid4()),
                    company_uuid=company_uuid,
                    pattern_format=pattern_format,
                    pattern_string=pattern_string,
                    contact_count=contact_count,
                    is_auto_extracted=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(new_pattern)
                created_count += 1
                pattern_results.append(
                    PatternAnalysisResult(
                        pattern_format=pattern_format,
                        pattern_string=pattern_string,
                        contact_count=contact_count,
                        sample_emails=pattern_data["sample_emails"],
                    )
                )

        await session.commit()

        # Pattern analysis completed: company_uuid=%s created=%d updated=%d
        # (company_uuid, created_count, updated_count)

        return EmailPatternAnalyzeResponse(
            company_uuid=company_uuid,
            patterns_found=len(pattern_groups),
            contacts_analyzed=analyzed_count,
            patterns=pattern_results,
            created=created_count,
            updated=updated_count,
        )

    async def import_patterns_from_csv(
        self,
        session: AsyncSession,
        csv_content: str,
    ) -> EmailPatternImportResponse:
        """
        Import email patterns from CSV content.
        
        Supports two CSV formats:
        1. Direct pattern format: company_uuid, pattern_format, pattern_string, contact_count, is_auto_extracted
        2. Contact data format: company/company_linkedin_url/company_name_for_emails, first_name, last_name, email
           (patterns will be extracted automatically)
        
        Args:
            session: Database session
            csv_content: CSV file content as string
            
        Returns:
            EmailPatternImportResponse with import statistics
        """
        # Starting CSV import for email patterns
        
        total_rows = 0
        created = 0
        updated = 0
        errors = 0
        error_details = []
        
        # Dictionary to group patterns by (company_uuid, pattern_format)
        pattern_groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "pattern_string": None,
                "contact_count": 0,
                "is_auto_extracted": False,
            }
        )
        
        try:
            # Parse CSV content
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            # First pass: Parse CSV and group patterns
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
                total_rows += 1
                try:
                    # Try to get company_uuid directly, or generate it from company fields
                    company_uuid = row.get('company_uuid', '').strip()
                    
                    # If company_uuid is missing, generate it from company fields
                    if not company_uuid:
                        # Get company identifying fields
                        raw_company_name = row.get('company', '').strip() or "_"
                        linkedin_url = row.get('company_linkedin_url', '').strip() or "_"
                        company_name_for_emails = row.get('company_name_for_emails', '').strip() or "_"
                        
                        # Generate deterministic company_uuid using same logic as bulk_service
                        hash_str = raw_company_name + linkedin_url + company_name_for_emails
                        company_uuid = str(uuid5(NAMESPACE_URL, hash_str))
                    
                    # Check if pattern_format is provided directly in CSV
                    pattern_format = row.get('pattern_format', '').strip()
                    pattern_string = row.get('pattern_string', '').strip() or None
                    is_auto_extracted = False
                    
                    # If pattern_format is not provided, try to extract it from contact data
                    if not pattern_format:
                        # Extract pattern from email, first_name, last_name
                        first_name = row.get('first_name', '').strip()
                        last_name = row.get('last_name', '').strip()
                        email = row.get('email', '').strip()
                        
                        if email and first_name and last_name:
                            # Try to extract pattern
                            pattern_result = self.extract_pattern_from_email(email, first_name, last_name)
                            if pattern_result:
                                pattern_format, extracted_pattern_string = pattern_result
                                # Use extracted pattern_string if not provided
                                if not pattern_string:
                                    pattern_string = extracted_pattern_string
                                is_auto_extracted = True
                            else:
                                # Pattern could not be extracted, skip this row
                                error_msg = f"Row {row_num}: Could not extract pattern from email '{email}'"
                                error_details.append(error_msg)
                                errors += 1
                                continue
                        else:
                            # Missing required fields for pattern extraction
                            error_msg = f"Row {row_num}: Missing required fields for pattern extraction (need email, first_name, last_name or pattern_format)"
                            error_details.append(error_msg)
                            errors += 1
                            continue
                    else:
                        # Pattern format provided in CSV, check if is_auto_extracted is specified
                        is_auto_str = str(row.get('is_auto_extracted', '')).strip().lower()
                        if is_auto_str in ('true', '1', 'yes', 'y'):
                            is_auto_extracted = True
                    
                    # Group patterns by (company_uuid, pattern_format) and count contacts
                    pattern_key = (company_uuid, pattern_format)
                    
                    # Parse contact_count from CSV (default: 1 per row)
                    contact_count = 1
                    contact_count_str = row.get('contact_count', '').strip()
                    if contact_count_str:
                        try:
                            contact_count = int(float(contact_count_str))
                            if contact_count < 0:
                                contact_count = 0
                        except (ValueError, TypeError):
                            contact_count = 1
                    
                    # Increment contact count for this pattern
                    pattern_groups[pattern_key]["contact_count"] += contact_count
                    
                    # Store pattern_string from first occurrence (or provided value)
                    if pattern_string and not pattern_groups[pattern_key]["pattern_string"]:
                        pattern_groups[pattern_key]["pattern_string"] = pattern_string
                    
                    # Set is_auto_extracted if any row has it as True
                    if is_auto_extracted:
                        pattern_groups[pattern_key]["is_auto_extracted"] = True
                    
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    error_details.append(error_msg)
                    errors += 1
                    # Error processing CSV row %d: %s
                    continue
            
            # Second pass: Create/update email pattern records from grouped patterns
            for (company_uuid, pattern_format), pattern_data in pattern_groups.items():
                try:
                    # Generate deterministic pattern UUID
                    pattern_hash = company_uuid + pattern_format
                    pattern_uuid = str(uuid5(NAMESPACE_URL, pattern_hash))
                    
                    # Check if pattern exists
                    existing = await self.email_pattern_repo.get_by_pattern_format(
                        session,
                        company_uuid,
                        pattern_format,
                    )
                    
                    if existing:
                        # Atomically increment contact_count by batch count, preserve other fields
                        # Use atomic database update to prevent race conditions
                        increment_amount = pattern_data["contact_count"]
                        updated_pattern = await self.email_pattern_repo.increment_contact_count(
                            session,
                            existing.uuid,
                            increment=increment_amount,
                        )
                        if updated_pattern:
                            # Update timestamp (atomic increment doesn't update updated_at)
                            updated_pattern.updated_at = datetime.now()
                            await session.commit()
                            await session.refresh(updated_pattern)
                        updated += 1
                    else:
                        # Create new pattern
                        pattern = EmailPattern(
                            uuid=pattern_uuid,
                            company_uuid=company_uuid,
                            pattern_format=pattern_format,
                            pattern_string=pattern_data["pattern_string"],
                            contact_count=pattern_data["contact_count"],
                            is_auto_extracted=pattern_data["is_auto_extracted"],
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )
                        session.add(pattern)
                        created += 1
                    
                except Exception as e:
                    error_msg = f"Error creating pattern for company_uuid={company_uuid}, pattern_format={pattern_format}: {str(e)}"
                    error_details.append(error_msg)
                    errors += 1
                    # Error creating pattern record: %s
                    continue
            
            # Commit all changes
            await session.commit()
            
            # CSV import completed: total_rows=%d created=%d updated=%d errors=%d
            # (total_rows, created, updated, errors)
            
            return EmailPatternImportResponse(
                total_rows=total_rows,
                created=created,
                updated=updated,
                errors=errors,
                error_details=error_details[:10] if len(error_details) > 10 else error_details,  # Limit to first 10 errors
            )
            
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import patterns from CSV: {str(e)}",
            )

    async def import_patterns_bulk(
        self,
        session: AsyncSession,
        patterns_data: list[EmailPatternCreate],
    ) -> EmailPatternImportResponse:
        """
        Import email patterns from JSON array.
        
        Patterns are grouped by (company_uuid, pattern_format) and contact_count is aggregated.
        Uses deterministic UUID generation for pattern_uuid.
        
        Args:
            session: Database session
            patterns_data: List of EmailPatternCreate objects
            
        Returns:
            EmailPatternImportResponse with import statistics
        """
        # Starting bulk import for email patterns: count=%d
        
        total_rows = len(patterns_data)
        created = 0
        updated = 0
        errors = 0
        error_details = []
        
        # Dictionary to group patterns by (company_uuid, pattern_format)
        pattern_groups: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "pattern_string": None,
                "contact_count": 0,
                "is_auto_extracted": False,
            }
        )
        
        try:
            # First pass: Group patterns by (company_uuid, pattern_format)
            for idx, pattern_data in enumerate(patterns_data, start=1):
                try:
                    # Validate required fields
                    if not pattern_data.company_uuid:
                        error_msg = f"Pattern {idx}: Missing required field 'company_uuid'"
                        error_details.append(error_msg)
                        errors += 1
                        continue
                    
                    if not pattern_data.pattern_format:
                        error_msg = f"Pattern {idx}: Missing required field 'pattern_format'"
                        error_details.append(error_msg)
                        errors += 1
                        continue
                    
                    # Group patterns by (company_uuid, pattern_format)
                    pattern_key = (pattern_data.company_uuid, pattern_data.pattern_format)
                    
                    # Aggregate contact_count
                    pattern_groups[pattern_key]["contact_count"] += pattern_data.contact_count
                    
                    # Store pattern_string from first occurrence (or provided value)
                    if pattern_data.pattern_string and not pattern_groups[pattern_key]["pattern_string"]:
                        pattern_groups[pattern_key]["pattern_string"] = pattern_data.pattern_string
                    
                    # Set is_auto_extracted if any pattern has it as True
                    if pattern_data.is_auto_extracted:
                        pattern_groups[pattern_key]["is_auto_extracted"] = True
                    
                except Exception as e:
                    error_msg = f"Pattern {idx}: {str(e)}"
                    error_details.append(error_msg)
                    errors += 1
                    # Error processing pattern %d: %s
                    continue
            
            # Second pass: Create/update email pattern records from grouped patterns
            for (company_uuid, pattern_format), pattern_data in pattern_groups.items():
                try:
                    # Generate deterministic pattern UUID
                    pattern_hash = company_uuid + pattern_format
                    pattern_uuid = str(uuid5(NAMESPACE_URL, pattern_hash))
                    
                    # Check if pattern exists
                    existing = await self.email_pattern_repo.get_by_pattern_format(
                        session,
                        company_uuid,
                        pattern_format,
                    )
                    
                    if existing:
                        # Atomically increment contact_count by batch count, preserve other fields
                        # Use atomic database update to prevent race conditions
                        increment_amount = pattern_data["contact_count"]
                        updated_pattern = await self.email_pattern_repo.increment_contact_count(
                            session,
                            existing.uuid,
                            increment=increment_amount,
                        )
                        if updated_pattern:
                            # Update timestamp (atomic increment doesn't update updated_at)
                            updated_pattern.updated_at = datetime.now()
                            await session.commit()
                            await session.refresh(updated_pattern)
                        updated += 1
                    else:
                        # Create new pattern
                        pattern = EmailPattern(
                            uuid=pattern_uuid,
                            company_uuid=company_uuid,
                            pattern_format=pattern_format,
                            pattern_string=pattern_data["pattern_string"],
                            contact_count=pattern_data["contact_count"],
                            is_auto_extracted=pattern_data["is_auto_extracted"],
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )
                        session.add(pattern)
                        created += 1
                    
                except Exception as e:
                    error_msg = f"Error creating pattern for company_uuid={company_uuid}, pattern_format={pattern_format}: {str(e)}"
                    error_details.append(error_msg)
                    errors += 1
                    # Error creating pattern record: %s
                    continue
            
            # Commit all changes
            await session.commit()
            
            # Bulk import completed: total_rows=%d created=%d updated=%d errors=%d
            # (total_rows, created, updated, errors)
            
            return EmailPatternImportResponse(
                total_rows=total_rows,
                created=created,
                updated=updated,
                errors=errors,
                error_details=error_details[:10] if len(error_details) > 10 else error_details,  # Limit to first 10 errors
            )
            
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import patterns in bulk: {str(e)}",
            )

    async def get_patterns_by_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> Optional[dict]:
        """
        Get email patterns for a contact by looking up the contact's company.
        
        Simplified: Uses sequential queries instead of JOIN for better performance.
        
        Args:
            session: Database session
            contact_uuid: Contact UUID
            
        Returns:
            Dictionary with pattern information or None if contact/company not found
        """
        # Getting patterns for contact: contact_uuid=%s
        
        # Simplified: Get contact first (no JOIN)
        stmt = select(Contact).where(Contact.uuid == contact_uuid)
        result = await session.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            return None
        
        company_uuid = contact.company_id
        if not company_uuid:
            return {
                "contact_uuid": contact_uuid,
                "company_uuid": None,
                "pattern_format": None,
                "pattern_string": None,
                "contact_count": None,
                "is_auto_extracted": None,
                "patterns": [],
            }
        
        # Get patterns for company using repository (no JOIN, simple query)
        patterns = await self.email_pattern_repo.get_by_company_uuid(session, company_uuid)
        if not company_uuid:
            return {
                "contact_uuid": contact_uuid,
                "company_uuid": None,
                "pattern_format": None,
                "pattern_string": None,
                "contact_count": None,
                "is_auto_extracted": None,
                "patterns": [],
            }
        
        # Build hash map for O(1) pattern format lookups (optimization for companies with many patterns)
        patterns_dict = {p.pattern_format: p for p in patterns if p.pattern_format}
        
        # Try to extract pattern from contact's email if available
        pattern_format = None
        pattern_string = None
        if contact.email and contact.first_name and contact.last_name:
            pattern_result = self.extract_pattern_from_email(
                contact.email,
                contact.first_name,
                contact.last_name,
            )
            if pattern_result:
                pattern_format, pattern_string = pattern_result
        
        # Find matching pattern in database using hash map lookup (O(1) instead of O(m))
        matching_pattern = None
        if pattern_format:
            matching_pattern = patterns_dict.get(pattern_format)
        
        result = {
            "contact_uuid": contact_uuid,
            "company_uuid": company_uuid,
            "pattern_format": matching_pattern.pattern_format if matching_pattern else pattern_format,
            "pattern_string": matching_pattern.pattern_string if matching_pattern else pattern_string,
            "contact_count": matching_pattern.contact_count if matching_pattern else None,
            "is_auto_extracted": matching_pattern.is_auto_extracted if matching_pattern else None,
            "patterns": [
                {
                    "pattern_format": p.pattern_format,
                    "pattern_string": p.pattern_string,
                    "contact_count": p.contact_count,
                    "is_auto_extracted": p.is_auto_extracted,
                }
                for p in patterns
            ],
        }
        return result

    async def get_patterns_by_contacts_batch(
        self,
        session: AsyncSession,
        contact_uuids: list[str],
    ) -> list[dict]:
        """
        Get email patterns for multiple contacts using batch queries.
        
        Optimized version that uses batch database queries instead of sequential lookups.
        Reduces database queries from 2n to ~2-3 queries total.
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs to get patterns for
            
        Returns:
            List of dictionaries with pattern information (same format as get_patterns_by_contact)
            Contacts not found will have None values but still be included in results
        """
        # Getting patterns for contacts batch: count=%d
        
        if not contact_uuids:
            return []
        
        # Batch fetch all contacts in one query (optimized: select only needed fields)
        # Select only fields we need: uuid, company_id, email, first_name, last_name
        contacts_stmt = (
            select(
                Contact.uuid,
                Contact.company_id,
                Contact.email,
                Contact.first_name,
                Contact.last_name
            )
            .where(Contact.uuid.in_(contact_uuids))
        )
        contacts_result = await session.execute(contacts_stmt)
        contacts_rows = contacts_result.all()
        
        # Convert rows to Contact-like objects for compatibility
        from types import SimpleNamespace
        contacts = [
            SimpleNamespace(
                uuid=row[0],
                company_id=row[1],
                email=row[2],
                first_name=row[3],
                last_name=row[4]
            )
            for row in contacts_rows
        ]
        
        # Build contact lookup dictionary
        contacts_dict = {c.uuid: c for c in contacts}
        
        # Group contacts by company_uuid to batch fetch patterns
        company_uuids = {c.company_id for c in contacts if c.company_id}
        
        # Batch fetch all patterns for all companies in one query
        patterns_by_company: dict[str, list[EmailPattern]] = {}
        all_patterns = []
        if company_uuids:
            patterns_stmt = (
                select(EmailPattern)
                .where(EmailPattern.company_uuid.in_(company_uuids))
                .order_by(EmailPattern.contact_count.desc(), EmailPattern.created_at.desc())
            )
            patterns_result = await session.execute(patterns_stmt)
            all_patterns = patterns_result.scalars().all()
            
            # Group patterns by company_uuid
            for pattern in all_patterns:
                if pattern.company_uuid not in patterns_by_company:
                    patterns_by_company[pattern.company_uuid] = []
                patterns_by_company[pattern.company_uuid].append(pattern)
        
        # Pre-build patterns_dict and patterns_list for each company (optimization)
        patterns_dict_by_company: dict[str, dict[str, EmailPattern]] = {}
        patterns_list_by_company: dict[str, list[dict]] = {}
        for company_uuid, patterns in patterns_by_company.items():
            patterns_dict_by_company[company_uuid] = {p.pattern_format: p for p in patterns if p.pattern_format}
            patterns_list_by_company[company_uuid] = [
                {
                    "pattern_format": p.pattern_format,
                    "pattern_string": p.pattern_string,
                    "contact_count": p.contact_count,
                    "is_auto_extracted": p.is_auto_extracted,
                }
                for p in patterns
            ]
        
        # Process each contact and build response
        results = []
        for contact_uuid in contact_uuids:
            contact = contacts_dict.get(contact_uuid)
            
            if not contact:
                # Contact not found
                results.append({
                    "contact_uuid": contact_uuid,
                    "company_uuid": None,
                    "pattern_format": None,
                    "pattern_string": None,
                    "contact_count": None,
                    "is_auto_extracted": None,
                    "patterns": [],
                })
                continue
            
            company_uuid = contact.company_id
            if not company_uuid:
                # Contact has no company
                results.append({
                    "contact_uuid": contact_uuid,
                    "company_uuid": None,
                    "pattern_format": None,
                    "pattern_string": None,
                    "contact_count": None,
                    "is_auto_extracted": None,
                    "patterns": [],
                })
                continue
            
            # Validate company exists (handle orphaned contacts in batch)
            # Note: We batch-fetched patterns, so if company_uuid is in patterns_by_company,
            # the company exists. If not, it might be orphaned or have no patterns.
            # For batch processing, we'll assume company exists if we have patterns for it,
            # otherwise treat as orphaned or no patterns.
            
            # Get pre-built patterns_dict and patterns_list for this company (optimization)
            patterns_dict = patterns_dict_by_company.get(company_uuid, {})
            patterns_list = patterns_list_by_company.get(company_uuid, [])
            
            # Try to extract pattern from contact's email if available
            pattern_format = None
            pattern_string = None
            if contact.email and contact.first_name and contact.last_name:
                pattern_result = self.extract_pattern_from_email(
                    contact.email,
                    contact.first_name,
                    contact.last_name,
                )
                if pattern_result:
                    pattern_format, pattern_string = pattern_result
            
            # Find matching pattern in database using hash map lookup (O(1))
            matching_pattern = None
            if pattern_format:
                matching_pattern = patterns_dict.get(pattern_format)
            
            results.append({
                "contact_uuid": contact_uuid,
                "company_uuid": company_uuid,
                "pattern_format": matching_pattern.pattern_format if matching_pattern else pattern_format,
                "pattern_string": matching_pattern.pattern_string if matching_pattern else pattern_string,
                "contact_count": matching_pattern.contact_count if matching_pattern else None,
                "is_auto_extracted": matching_pattern.is_auto_extracted if matching_pattern else None,
                "patterns": patterns_list,  # Use pre-built list instead of list comprehension
            })
        
        # Batch pattern lookup completed: requested=%d processed=%d
        return results

