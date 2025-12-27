"""Service layer for email finder operations."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.connectra_client import ConnectraClient
from app.core.vql.structures import PopulateConfig, VQLCondition, VQLFilter, VQLOperator, VQLQuery
from app.repositories.email_finder import EmailFinderRepository
from app.schemas.email import SimpleEmailFinderResponse, SimpleEmailResult
from app.utils.domain import extract_domain_from_url
from app.utils.logger import get_logger, log_error, log_external_api_call

logger = get_logger(__name__)


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
        start_time = time.time()
        logger.info(
            "Email finder request",
            extra={
                "context": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain,
                    "website": website,
                }
            }
        )
        
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
        
        # Use VQL through ConnectraClient instead of direct database queries
        try:
            # Build VQL query to find contacts by name and company domain
            vql_query = VQLQuery(
                filters=VQLFilter(
                    and_=[
                        VQLCondition(
                            field="first_name",
                            operator=VQLOperator.CONTAINS,
                            value=first_name_normalized
                        ),
                        VQLCondition(
                            field="last_name",
                            operator=VQLOperator.CONTAINS,
                            value=last_name_normalized
                        ),
                        VQLCondition(
                            field="email",
                            operator=VQLOperator.EXISTS,
                            value=True
                        ),
                        VQLCondition(
                            field="company.normalized_domain",
                            operator=VQLOperator.EQ,
                            value=extracted_domain
                        ),
                    ]
                ),
                select_columns=["uuid", "email"],
                company_config=PopulateConfig(
                    populate=True,
                    select_columns=["normalized_domain"]
                ),
                limit=100,  # Reduced from 1000 to avoid API limit errors
                offset=0
            )
            
            # Query via ConnectraClient
            vql_start = time.time()
            async with ConnectraClient() as client:
                response = await client.search_contacts(vql_query)
            vql_duration_ms = (time.time() - vql_start) * 1000
            
            log_external_api_call(
                service_name="Connectra",
                method="POST",
                url="/contacts",
                status_code=200,
                duration_ms=vql_duration_ms,
                request_data={"first_name": first_name_normalized, "last_name": last_name_normalized, "domain": extracted_domain},
                response_data={"result_count": len(response.get("data", []))},
                logger_name="app.services.email_finder",
            )
            
            # Extract contacts from response
            contacts_data = response.get("data", [])
            
            if not contacts_data:
                # No contacts found matching criteria
                error_detail = f"No contacts found with name '{first_name_normalized} {last_name_normalized}' for companies with domain: {extracted_domain}"
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_detail,
                )
            
            # Transform response to SimpleEmailResult objects
            email_results: list[SimpleEmailResult] = []
            for item in contacts_data:
                uuid_val = item.get("uuid")
                email_val = item.get("email")
                
                if uuid_val and email_val:
                    email_results.append(
                        SimpleEmailResult(
                            uuid=uuid_val,
                            email=email_val,
                        )
                    )
            
            if not email_results:
                # No valid email results found
                error_detail = f"No contacts with valid emails found for name '{first_name_normalized} {last_name_normalized}' and domain: {extracted_domain}"
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_detail,
                )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Email finder completed",
                extra={
                    "context": {
                        "first_name": first_name_normalized,
                        "last_name": last_name_normalized,
                        "domain": extracted_domain,
                        "result_count": len(email_results),
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            
            return SimpleEmailFinderResponse(
                emails=email_results,
                total=len(email_results),
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (like 404)
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(
                "Email finder returned no results",
                extra={
                    "context": {
                        "first_name": first_name_normalized,
                        "last_name": last_name_normalized,
                        "domain": extracted_domain,
                    },
                    "performance": {"duration_ms": duration_ms}
                }
            )
            raise
        except Exception as exc:
            # Log error and fall back to repository method if VQL fails
            log_error(
                "VQL email finder failed, falling back to repository",
                exc,
                "app.services.email_finder",
                context={
                    "first_name": first_name_normalized,
                    "last_name": last_name_normalized,
                    "domain": extracted_domain,
                }
            )
            
            # Fallback to repository method for backward compatibility
            if self.email_finder_repo is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Email finder service is not properly initialized",
                ) from exc
            
            if not hasattr(self.email_finder_repo, 'find_emails_by_name_and_domain'):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Email finder repository is not properly configured",
                ) from exc
            
            try:
                email_pairs = await self.email_finder_repo.find_emails_by_name_and_domain(
                    session=session,
                    first_name=first_name_normalized,
                    last_name=last_name_normalized,
                    domain=extracted_domain,
                    enable_diagnostics=True,
                )
                
                if not email_pairs:
                    error_detail = f"No contacts found with name '{first_name_normalized} {last_name_normalized}' for companies with domain: {extracted_domain}"
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=error_detail,
                    )
                
                email_results: list[SimpleEmailResult] = []
                for uuid_val, email_val in email_pairs:
                    if uuid_val and email_val:
                        email_results.append(
                            SimpleEmailResult(
                                uuid=uuid_val,
                                email=email_val,
                            )
                        )
                
                return SimpleEmailFinderResponse(
                    emails=email_results,
                    total=len(email_results),
                )
            except HTTPException:
                raise
            except Exception as fallback_exc:
                duration_ms = (time.time() - start_time) * 1000
                log_error(
                    "Repository fallback also failed",
                    fallback_exc,
                    "app.services.email_finder",
                    context={
                        "first_name": first_name_normalized,
                        "last_name": last_name_normalized,
                        "domain": extracted_domain,
                        "duration_ms": duration_ms,
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Email finder service temporarily unavailable",
                ) from fallback_exc

