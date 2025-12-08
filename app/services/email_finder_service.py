"""Service layer for email finder operations."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.email_finder import EmailFinderRepository
from app.schemas.email import SimpleEmailFinderResponse, SimpleEmailResult
from app.utils.domain import extract_domain_from_url


class EmailFinderService:
    """Business logic for email finder operations."""

    def __init__(
        self,
        email_finder_repo: Optional[EmailFinderRepository] = None,
    ) -> None:
        """Initialize the service with repository dependency."""
        self.email_finder_repo = email_finder_repo or EmailFinderRepository()
        if self.email_finder_repo is None:
            raise ValueError("EmailFinderRepository cannot be None")

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
        # Find emails by contact name and company domain
        # Normalize and validate first name
        first_name_normalized = first_name.strip() if first_name else None
        if not first_name_normalized:
            # First name validation failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="first_name is required and cannot be empty",
            )
        
        # Normalize and validate last name
        last_name_normalized = last_name.strip() if last_name else None
        if not last_name_normalized:
            # Last name validation failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="last_name is required and cannot be empty",
            )
        
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
        extracted_domain = extract_domain_from_url(domain_input)
        if not extracted_domain:
            # Domain extraction failed
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract valid domain from: {domain_input}",
            )
        
        
        # OPTIMIZATION: Skip redundant check_companies_exist_by_domain() call
        # The find_emails_by_name_and_domain() method will check for companies and return empty list if none found
        # This eliminates duplicate work (saves ~38s per request)
        # Initiate contact search (optimized: no redundant company check)
        
        # Query repository for matching (uuid, email) pairs
        # enable_diagnostics=True when we need detailed error messages (only if no results)
        if self.email_finder_repo is None:
            # EmailFinderRepository is None
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email finder service is not properly initialized",
            )
        
        if not hasattr(self.email_finder_repo, 'find_emails_by_name_and_domain'):
            # EmailFinderRepository missing required method
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email finder repository is not properly configured",
            )
        
        email_pairs = await self.email_finder_repo.find_emails_by_name_and_domain(
            session=session,
            first_name=first_name_normalized,
            last_name=last_name_normalized,
            domain=extracted_domain,
            enable_diagnostics=True,  # Enable diagnostics to get detailed error info if no results
        )
        
        
        if not email_pairs:
            # No contacts found matching criteria
            
            # Build error message (diagnostics already logged by repository if enabled)
            error_detail = f"No contacts found with name '{first_name_normalized} {last_name_normalized}' for companies with domain: {extracted_domain}"
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail,
            )
        
        # Transform (uuid, email) pairs to SimpleEmailResult objects
        # Transform (uuid, email) pairs to response format
        
        email_results: list[SimpleEmailResult] = []
        transformed_count = 0
        skipped_count = 0
        
        for uuid_val, email_val in email_pairs:
            
            if uuid_val and email_val:
                email_results.append(
                    SimpleEmailResult(
                        uuid=uuid_val,
                        email=email_val,
                    )
                )
                transformed_count += 1
            else:
                # Skipping invalid pair (missing uuid or email)
                skipped_count += 1
        
        
        # Sample transformed results
        if email_results:
            sample_count = min(3, len(email_results))
            for i, result in enumerate(email_results[:sample_count]):
                pass
        
        
        return SimpleEmailFinderResponse(
            emails=email_results,
            total=len(email_results),
        )

