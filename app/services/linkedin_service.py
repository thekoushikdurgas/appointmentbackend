"""Service layer for LinkedIn URL-based CRUD operations."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.clients.connectra_client import ConnectraClient
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.linkedin import LinkedInRepository
from app.repositories.user import UserProfileRepository
from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.linkedin import (
    CompanyWithRelations,
    ContactWithRelations,
    LinkedInSearchResponse,
)
from app.schemas.metadata import ContactMetadataOut
from app.services.credit_service import CreditService
from app.services.vql_transformer import VQLTransformer
from app.utils.normalization import PLACEHOLDER_VALUE, normalize_text

settings = get_settings()

# Performance optimization constants
MAX_LINKEDIN_SEARCH_RESULTS = 1000  # Maximum results per search to prevent memory issues
LINKEDIN_UUID_BATCH_SIZE = 1000  # PostgreSQL IN clause limit


class LinkedInService:
    """Business logic for LinkedIn URL-based operations."""

    def __init__(
        self,
        linkedin_repo: Optional[LinkedInRepository] = None,
        credit_service: Optional[CreditService] = None,
        profile_repo: Optional[UserProfileRepository] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        self.linkedin_repo = linkedin_repo or LinkedInRepository()
        self.credit_service = credit_service or CreditService()
        self.profile_repo = profile_repo or UserProfileRepository()

    async def search_by_url(
        self, linkedin_url: str, user_id: Optional[str] = None, use_parallel: bool = False
    ) -> LinkedInSearchResponse:
        """
        Search for contacts and companies by LinkedIn URL using optimized sequential queries.
        
        Creates its own database session internally and handles credit deduction.
        
        Optimizations:
        - Parallel execution of contact and company searches
        - Sequential queries with batch fetching (no JOINs)
        - UUID batching for large lists
        - Result size limits
        - Batch fetching of company contacts (eliminates N+1 problem)
        
        Args:
            linkedin_url: LinkedIn URL to search for
            user_id: Optional user ID for credit deduction (FreeUser/ProUser only)
            use_parallel: Whether to execute searches in parallel (default: True)
        
        Returns all matches from both ContactMetadata and CompanyMetadata.
        """
        # Create internal session for database operations
        async with AsyncSessionLocal() as session:
            # Use Connectra for LinkedIn search
            try:
                async with ConnectraClient() as client:
                    transformer = VQLTransformer()
                    
                    # Search contacts and companies via Connectra
                    contacts_response = await client.search_by_linkedin_url(linkedin_url, "contact")
                    companies_response = await client.search_by_linkedin_url(linkedin_url, "company")
                    
                    # Transform responses
                    contacts_list = transformer.transform_contact_response(contacts_response)
                    companies_list = transformer.transform_company_response(companies_response)
                    
                    # Convert ContactListItem to ContactWithRelations
                    contact_relations = []
                    for contact_item in contacts_list:
                        # Extract contact data
                        departments_list = None
                        if contact_item.departments:
                            departments_list = [d.strip() for d in contact_item.departments.split(",") if d.strip()]
                        
                        contact_db = ContactDB(
                            uuid=contact_item.uuid,
                            first_name=contact_item.first_name,
                            last_name=contact_item.last_name,
                            email=contact_item.email,
                            title=contact_item.title,
                            departments=departments_list,
                            mobile_phone=contact_item.mobile_phone,
                            email_status=contact_item.email_status,
                            seniority=contact_item.seniority,
                            created_at=contact_item.created_at,
                            updated_at=contact_item.updated_at,
                        )
                        
                        # Extract metadata
                        contact_metadata = None
                        if contact_item.person_linkedin_url or contact_item.work_direct_phone or contact_item.city:
                            contact_metadata = ContactMetadataOut(
                                uuid=contact_item.uuid,
                                linkedin_url=contact_item.person_linkedin_url,
                                website=contact_item.website,
                                work_direct_phone=contact_item.work_direct_phone,
                                home_phone=contact_item.home_phone,
                                other_phone=contact_item.other_phone,
                                city=contact_item.city,
                                state=contact_item.state,
                                country=contact_item.country,
                                stage=contact_item.stage,
                                facebook_url=contact_item.facebook_url,
                                twitter_url=contact_item.twitter_url,
                            )
                        
                        # Extract company data if available
                        company_db = None
                        company_metadata = None
                        if contact_item.company:
                            industries_list = [contact_item.industry] if contact_item.industry else None
                            keywords_list = None
                            if contact_item.keywords:
                                keywords_list = [k.strip() for k in contact_item.keywords.split(",") if k.strip()]
                            technologies_list = None
                            if contact_item.technologies:
                                technologies_list = [t.strip() for t in contact_item.technologies.split(",") if t.strip()]
                            
                            company_db = CompanyDB(
                                uuid="",  # Company UUID not available in ContactListItem
                                name=contact_item.company,
                                employees_count=contact_item.employees,
                                industries=industries_list,
                                keywords=keywords_list,
                                address=contact_item.company_address,
                                annual_revenue=contact_item.annual_revenue,
                                total_funding=contact_item.total_funding,
                                technologies=technologies_list,
                                created_at=None,
                                updated_at=None,
                            )
                            
                            company_metadata = CompanyMetadataOut(
                                uuid="",
                                linkedin_url=contact_item.company_linkedin_url,
                                website=contact_item.website,
                                city=contact_item.company_city,
                                state=contact_item.company_state,
                                country=contact_item.company_country,
                                phone_number=contact_item.company_phone,
                            )
                        
                        contact_relations.append(ContactWithRelations(
                            contact=contact_db,
                            metadata=contact_metadata,
                            company=company_db,
                            company_metadata=company_metadata,
                        ))
                    
                    # Convert CompanyListItem to CompanyWithRelations
                    company_relations = []
                    for company_item in companies_list:
                        industries_list = None
                        if company_item.industry:
                            industries_list = [company_item.industry]
                        elif hasattr(company_item, 'industries') and company_item.industries:
                            industries_list = company_item.industries
                        
                        company_db = CompanyDB(
                            uuid=company_item.uuid,
                            name=company_item.name,
                            employees_count=company_item.employees_count,
                            industries=industries_list,
                            keywords=company_item.keywords,
                            annual_revenue=company_item.annual_revenue,
                            total_funding=company_item.total_funding,
                            technologies=company_item.technologies,
                            created_at=None,
                            updated_at=None,
                        )
                        
                        company_metadata = None
                        if hasattr(company_item, 'metadata') and company_item.metadata:
                            company_metadata = company_item.metadata
                        else:
                            # Create metadata from company_item fields
                            company_metadata = CompanyMetadataOut(
                                uuid=company_item.uuid,
                                linkedin_url=company_item.linkedin_url,
                                website=company_item.website,
                                city=company_item.city,
                                state=company_item.state,
                                country=company_item.country,
                                phone_number=getattr(company_item, 'phone_number', None),
                            )
                        
                        company_relations.append(CompanyWithRelations(
                            company=company_db,
                            metadata=company_metadata,
                            contacts=[],  # Contacts not populated in company search
                        ))
                    
                    return LinkedInSearchResponse(
                        contacts=contact_relations,
                        companies=company_relations,
                        total_contacts=len(contact_relations),
                        total_companies=len(company_relations),
                    )
            except Exception as exc:
                logger.error(f"Connectra LinkedIn search failed: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="LinkedIn search service temporarily unavailable"
                ) from exc

    async def search_by_multiple_urls(
        self, session: AsyncSession, linkedin_urls: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Search for contacts and companies by multiple LinkedIn URLs.
        
        Processes URLs in parallel for better performance. Collects all unique
        contact and company UUIDs, and tracks which URLs didn't match anything.
        
        Args:
            session: Database session
            linkedin_urls: List of LinkedIn URLs to search for
            
        Returns:
            Tuple of (contact_uuids, company_uuids, unmatched_urls)
        """
        if not linkedin_urls:
            return [], [], []
        
        # Normalize URLs
        normalized_urls = [url.strip() for url in linkedin_urls if url and url.strip()]
        if not normalized_urls:
            return [], [], []
        
        # Search all URLs sequentially to avoid concurrent session operations
        async def search_single_url(url: str) -> tuple[str, LinkedInSearchResponse]:
            """Search a single URL and return the URL with results."""
            try:
                # Use sequential execution (use_parallel=False) to avoid concurrent session operations
                # Flush any pending operations to ensure session is ready
                await session.flush()
                result = await self.search_by_url(url, use_parallel=False)
                # Flush after search to ensure session is ready for next operation
                await session.flush()
                return url, result
            except Exception as exc:
                # Rollback on error to ensure session is clean
                try:
                    await session.rollback()
                except Exception:
                    # If rollback fails, session might be in invalid state
                    # Log but continue - the next operation will handle it
                    pass
                # Return empty result for failed searches
                return url, LinkedInSearchResponse(contacts=[], companies=[], total_contacts=0, total_companies=0)
        
        # Execute all searches sequentially to avoid concurrent session operations
        # Ensure session is ready before starting
        await session.flush()
        search_results = []
        for url in normalized_urls:
            result = await search_single_url(url)
            search_results.append(result)
        
        # Collect unique UUIDs and track unmatched URLs
        contact_uuids_set: set[str] = set()
        company_uuids_set: set[str] = set()
        unmatched_urls: list[str] = []
        
        for url, result in search_results:
            found_contact = False
            found_company = False
            
            # Collect contact UUIDs
            for contact_rel in result.contacts:
                if contact_rel.contact and contact_rel.contact.uuid:
                    contact_uuids_set.add(contact_rel.contact.uuid)
                    found_contact = True
            
            # Collect company UUIDs
            for company_rel in result.companies:
                if company_rel.company and company_rel.company.uuid:
                    company_uuids_set.add(company_rel.company.uuid)
                    found_company = True
                
                # Also collect contact UUIDs from company relations
                for contact_rel in company_rel.contacts:
                    if contact_rel.contact and contact_rel.contact.uuid:
                        contact_uuids_set.add(contact_rel.contact.uuid)
                        found_contact = True
            
            # Track unmatched URLs
            if not found_contact and not found_company:
                unmatched_urls.append(url)
        
        contact_uuids = list(contact_uuids_set)
        company_uuids = list(company_uuids_set)
        
        return contact_uuids, company_uuids, unmatched_urls

