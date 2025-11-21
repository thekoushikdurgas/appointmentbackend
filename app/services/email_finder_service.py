"""Service layer for email finder operations."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.email_finder import EmailFinderRepository
from app.schemas.email import SimpleEmailFinderResponse, SimpleEmailResult
from app.utils.domain import extract_domain_from_url

logger = get_logger(__name__)


class EmailFinderService:
    """Business logic for email finder operations."""

    def __init__(
        self,
        email_finder_repo: Optional[EmailFinderRepository] = None,
    ) -> None:
        """Initialize the service with repository dependency."""
        self.logger = get_logger(__name__)
        self.email_finder_repo = email_finder_repo or EmailFinderRepository()
        self.logger.debug("EmailFinderService initialized")

    async def find_emails(
        self,
        session: AsyncSession,
        first_name: str,
        last_name: str,
        domain: Optional[str] = None,
        website: Optional[str] = None,
    ) -> SimpleEmailFinderResponse:
        """
        Find emails by contact name and company domain.
        
        Args:
            session: Database session
            first_name: Contact first name (required)
            last_name: Contact last name (required)
            domain: Company domain or website URL (optional, can use website instead)
            website: Company website URL (optional, alias for domain)
            
        Returns:
            SimpleEmailFinderResponse with list of (uuid, email) pairs
        """
        self.logger.info(
            "Finding emails: first_name=%s last_name=%s domain=%s website=%s",
            first_name,
            last_name,
            domain,
            website,
        )
        
        # Normalize and validate first name
        first_name_normalized = first_name.strip() if first_name else None
        if not first_name_normalized:
            self.logger.warning("first_name validation failed: input=%s", first_name)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        self.logger.debug("Normalized first_name: input=%s normalized=%s", first_name, first_name_normalized)
        
        # Normalize and validate last name
        last_name_normalized = last_name.strip() if last_name else None
        if not last_name_normalized:
            self.logger.warning("last_name validation failed: input=%s", last_name)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        self.logger.debug("Normalized last_name: input=%s normalized=%s", last_name, last_name_normalized)
        
        # Extract domain from website or domain parameter
        domain_input = domain or website
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either domain or website parameter is required",
            )
        
        # Normalize domain input
        domain_input = domain_input.strip()
        if not domain_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain or website cannot be empty",
            )
        
        # Extract normalized domain from URL or domain string
        self.logger.debug("Starting domain extraction process: input=%s", domain_input)
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            self.logger.error(
                "Domain extraction failed: could not extract valid domain from input=%s",
                domain_input,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        
        self.logger.info(
            "Domain extraction completed: input=%s extracted=%s",
            domain_input,
            extracted_domain,
        )
        
        # OPTIMIZATION: Skip redundant check_companies_exist_by_domain() call
        # The find_emails_by_name_and_domain() method will check for companies and return empty list if none found
        # This eliminates duplicate work (saves ~38s per request)
        self.logger.debug(
            "Initiating contact search: first_name=%s last_name=%s domain=%s (optimized: no redundant company check)",
            first_name_normalized,
            last_name_normalized,
            extracted_domain,
        )
        
        # Query repository for matching (uuid, email) pairs
        # enable_diagnostics=True when we need detailed error messages (only if no results)
        email_pairs = await self.email_finder_repo.find_emails_by_name_and_domain(
            session=session,
            first_name=first_name_normalized,
            last_name=last_name_normalized,
            domain=extracted_domain,
            enable_diagnostics=True,  # Enable diagnostics to get detailed error info if no results
        )
        
        self.logger.info(
            "Contact search completed: found=%d (uuid, email) pairs matching criteria (first_name=%s, last_name=%s, domain=%s)",
            len(email_pairs),
            first_name_normalized,
            last_name_normalized,
            extracted_domain,
        )
        
        if not email_pairs:
            self.logger.warning(
                "No contacts found with name '%s %s' for companies with domain: %s",
                first_name_normalized,
                last_name_normalized,
                extracted_domain,
            )
            
            # Build error message (diagnostics already logged by repository if enabled)
            error_detail = f"No contacts found with name '{first_name_normalized} {last_name_normalized}' for companies with domain: {extracted_domain}"
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail,
            )
        
        # Transform (uuid, email) pairs to SimpleEmailResult objects
        self.logger.info(
            "Transforming (uuid, email) pairs to response format: processing %d pairs",
            len(email_pairs),
        )
        
        email_results: list[SimpleEmailResult] = []
        transformed_count = 0
        skipped_count = 0
        
        for uuid_val, email_val in email_pairs:
            # Extract and log field information
            self.logger.debug(
                "Processing pair: uuid=%s, email=%s",
                uuid_val,
                email_val,
            )
            
            if uuid_val and email_val:
                email_results.append(
                    SimpleEmailResult(
                        uuid=uuid_val,
                        email=email_val,
                    )
                )
                transformed_count += 1
            else:
                self.logger.warning(
                    "Skipping invalid pair: uuid=%s, email=%s (missing uuid or email)",
                    uuid_val,
                    email_val,
                )
                skipped_count += 1
        
        # Log field extraction summary
        self.logger.info(
            "Field extraction and transformation summary: total_pairs=%d, transformed=%d, skipped=%d",
            len(email_pairs),
            transformed_count,
            skipped_count,
        )
        
        # Log sample results for debugging
        if email_results:
            sample_count = min(3, len(email_results))
            self.logger.debug("Sample transformed results (first %d):", sample_count)
            for i, result in enumerate(email_results[:sample_count]):
                self.logger.debug(
                    "  Result %d: uuid=%s, email=%s",
                    i + 1,
                    result.uuid,
                    result.email,
                )
        
        self.logger.info(
            "Email finder completed: total_results=%d (uuid, email) pairs successfully transformed",
            len(email_results),
        )
        
        return SimpleEmailFinderResponse(
            emails=email_results,
            total=len(email_results),
        )

