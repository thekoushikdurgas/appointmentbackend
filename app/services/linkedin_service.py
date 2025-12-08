"""Service layer for LinkedIn URL-based CRUD operations."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.companies import CompanyRepository
from app.repositories.contacts import ContactRepository
from app.repositories.linkedin import LinkedInRepository
from app.repositories.user import UserProfileRepository
from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.linkedin import (
    CompanyWithRelations,
    ContactWithRelations,
    LinkedInSearchResponse,
    LinkedInUpsertResponse,
)
from app.schemas.metadata import ContactMetadataOut
from app.services.credit_service import CreditService
from app.utils.normalization import PLACEHOLDER_VALUE, normalize_text

# Performance optimization constants
MAX_LINKEDIN_SEARCH_RESULTS = 1000  # Maximum results per search to prevent memory issues
LINKEDIN_UUID_BATCH_SIZE = 1000  # PostgreSQL IN clause limit


class LinkedInService:
    """Business logic for LinkedIn URL-based operations."""

    def __init__(
        self,
        linkedin_repo: Optional[LinkedInRepository] = None,
        contact_repo: Optional[ContactRepository] = None,
        company_repo: Optional[CompanyRepository] = None,
        credit_service: Optional[CreditService] = None,
        profile_repo: Optional[UserProfileRepository] = None,
    ) -> None:
        """Initialize the service with repository dependencies."""
        self.linkedin_repo = linkedin_repo or LinkedInRepository()
        self.contact_repo = contact_repo or ContactRepository()
        self.company_repo = company_repo or CompanyRepository()
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
        #region agent log
        import json
        log_path = "d:\\code\\ayan\\contact360\\.cursor\\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_service_entry", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:79", "message": "service_entry", "data": {"linkedin_url": linkedin_url, "user_id": user_id, "use_parallel": use_parallel}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1,H2"}) + "\n")
        except: pass
        #endregion agent log
        # Create internal session for database operations
        #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_session_create", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:80", "message": "before_session_create", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
        except: pass
        #endregion agent log
        async with AsyncSessionLocal() as session:
            #region agent log
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_session_created", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:81", "message": "session_created", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
            except: pass
            #endregion agent log
            try:
                start_time = time.time()
                
                # ========================================================================
                # Parallel execution: Search contacts and companies simultaneously
                # ========================================================================
                async def search_contacts() -> tuple[list[ContactWithRelations], dict[str, Company], dict[str, CompanyMetadata]]:
                    """Search for contacts by LinkedIn URL using sequential queries."""
                    step_start = time.time()
                    
                    # Step 1: Find contact metadata by LinkedIn URL
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_contact_query", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:92", "message": "before_contact_query", "data": {"linkedin_url": linkedin_url}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H2"}) + "\n")
                    except: pass
                    #endregion agent log
                    contact_metadata_list = await self.linkedin_repo.find_contacts_metadata_by_linkedin_url(
                        session, linkedin_url
                    )
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_contact_query", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:95", "message": "after_contact_query", "data": {"result_count": len(contact_metadata_list)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H2"}) + "\n")
                    except: pass
                    #endregion agent log
                    
                    # Apply result limit
                    if len(contact_metadata_list) > MAX_LINKEDIN_SEARCH_RESULTS:
                        contact_metadata_list = contact_metadata_list[:MAX_LINKEDIN_SEARCH_RESULTS]
                    
                    step_time = time.time() - step_start
                    
                    if not contact_metadata_list:
                        return [], {}, {}
                    
                    step_start = time.time()
                    # Step 2: Extract contact UUIDs and batch fetch contacts
                    contact_uuids = [cm.uuid for cm in contact_metadata_list]
                    contacts_dict = await self.linkedin_repo.find_contacts_by_uuids(
                        session, contact_uuids, batch_size=LINKEDIN_UUID_BATCH_SIZE
                    )
                    step_time = time.time() - step_start
                    
                    step_start = time.time()
                    # Step 3: Extract company UUIDs and batch fetch companies
                    company_uuids_from_contacts = [
                        contact.company_id
                        for contact in contacts_dict.values()
                        if contact.company_id
                    ]
                    # Remove duplicates
                    company_uuids_from_contacts = list(set(company_uuids_from_contacts))
                    
                    if company_uuids_from_contacts:
                        companies_dict = await self.linkedin_repo.find_companies_by_uuids(
                            session, company_uuids_from_contacts, batch_size=LINKEDIN_UUID_BATCH_SIZE
                        )
                        step_time = time.time() - step_start
                        
                        step_start = time.time()
                        # Step 4: Batch fetch company metadata
                        company_metadata_dict = await self.linkedin_repo.find_companies_metadata_by_uuids(
                            session, company_uuids_from_contacts, batch_size=LINKEDIN_UUID_BATCH_SIZE
                        )
                        step_time = time.time() - step_start
                    else:
                        companies_dict = {}
                        company_metadata_dict = {}
                    
                    step_start = time.time()
                    # Step 5: Merge contact data
                    contacts: list[ContactWithRelations] = []
                    for contact_meta in contact_metadata_list:
                        contact = contacts_dict.get(contact_meta.uuid)
                        if not contact:
                            # Skip if contact doesn't exist (orphaned metadata)
                            continue
                        
                        # Get company and company metadata if contact has company_id
                        company = companies_dict.get(contact.company_id) if contact.company_id else None
                        company_meta = (
                            company_metadata_dict.get(company.uuid) if company else None
                        )
                        
                        # Build ContactWithRelations
                        contact_data = ContactDB.model_validate(contact)
                        metadata_data = ContactMetadataOut.model_validate(contact_meta)
                        company_data = CompanyDB.model_validate(company) if company else None
                        company_meta_data = (
                            CompanyMetadataOut.model_validate(company_meta) if company_meta else None
                        )
                        
                        contacts.append(
                            ContactWithRelations(
                                contact=contact_data,
                                metadata=metadata_data,
                                company=company_data,
                                company_metadata=company_meta_data,
                            )
                        )
                    step_time = time.time() - step_start
                    
                    return contacts, companies_dict, company_metadata_dict
                
                async def search_companies() -> list[CompanyWithRelations]:
                    """Search for companies by LinkedIn URL using sequential queries."""
                    step_start = time.time()
                    
                    # Step 1: Find company metadata by LinkedIn URL
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_company_query", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:179", "message": "before_company_query", "data": {"linkedin_url": linkedin_url}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H2"}) + "\n")
                    except: pass
                    #endregion agent log
                    company_metadata_list = await self.linkedin_repo.find_companies_metadata_by_linkedin_url(
                        session, linkedin_url
                    )
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_company_query", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:182", "message": "after_company_query", "data": {"result_count": len(company_metadata_list)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H2"}) + "\n")
                    except: pass
                    #endregion agent log
                    
                    # Apply result limit
                    if len(company_metadata_list) > MAX_LINKEDIN_SEARCH_RESULTS:
                        company_metadata_list = company_metadata_list[:MAX_LINKEDIN_SEARCH_RESULTS]
                    
                    step_time = time.time() - step_start
                    
                    if not company_metadata_list:
                        return []
                    
                    step_start = time.time()
                    # Step 2: Extract company UUIDs and batch fetch companies
                    company_uuids = [cm.uuid for cm in company_metadata_list]
                    companies_dict = await self.linkedin_repo.find_companies_by_uuids(
                        session, company_uuids, batch_size=LINKEDIN_UUID_BATCH_SIZE
                    )
                    step_time = time.time() - step_start
                    
                    step_start = time.time()
                    # Step 3: Batch fetch company contacts (eliminates N+1 problem)
                    contacts_by_company = await self.linkedin_repo.find_contacts_by_company_uuids(
                        session, company_uuids
                    )
                    step_time = time.time() - step_start
                    total_contacts = sum(len(contacts) for contacts in contacts_by_company.values())
                    
                    step_start = time.time()
                    # Step 4: Merge company data
                    companies: list[CompanyWithRelations] = []
                    for company_meta in company_metadata_list:
                        company = companies_dict.get(company_meta.uuid)
                        if not company:
                            # Skip if company doesn't exist (orphaned metadata)
                            continue
                        
                        company_data = CompanyDB.model_validate(company)
                        company_meta_data = CompanyMetadataOut.model_validate(company_meta)
                        
                        # Get contacts for this company (from batch fetch)
                        company_contacts_rows = contacts_by_company.get(company.uuid, [])
                        company_contacts: list[ContactWithRelations] = []
                        for contact, contact_meta in company_contacts_rows:
                            contact_data = ContactDB.model_validate(contact)
                            metadata_data = (
                                ContactMetadataOut.model_validate(contact_meta) if contact_meta else None
                            )
                            
                            company_contacts.append(
                                ContactWithRelations(
                                    contact=contact_data,
                                    metadata=metadata_data,
                                    company=company_data,
                                    company_metadata=company_meta_data,
                                )
                            )
                        
                        companies.append(
                            CompanyWithRelations(
                                company=company_data,
                                metadata=company_meta_data,
                                contacts=company_contacts,
                            )
                        )
                    step_time = time.time() - step_start
                    
                    return companies
                
                # Execute contact and company searches (parallel or sequential based on use_parallel flag)
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_execution_mode", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:293", "message": "execution_mode", "data": {"use_parallel": use_parallel}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H5"}) + "\n")
                except: pass
                #endregion agent log
                if use_parallel:
                    parallel_start = time.time()
                    (contacts_result, companies_dict_from_contacts, company_metadata_dict_from_contacts), companies = await asyncio.gather(
                        search_contacts(),
                        search_companies(),
                    )
                    contacts = contacts_result
                    parallel_time = time.time() - parallel_start
                else:
                    # Sequential execution to avoid concurrent session operations
                    sequential_start = time.time()
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_sequential_contacts", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:305", "message": "before_sequential_contacts", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H5"}) + "\n")
                    except: pass
                    #endregion agent log
                    contacts_result, companies_dict_from_contacts, company_metadata_dict_from_contacts = await search_contacts()
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_sequential_contacts", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:306", "message": "after_sequential_contacts", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H5"}) + "\n")
                    except: pass
                    #endregion agent log
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_sequential_companies", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:307", "message": "before_sequential_companies", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H5"}) + "\n")
                    except: pass
                    #endregion agent log
                    companies = await search_companies()
                    contacts = contacts_result
                    sequential_time = time.time() - sequential_start
                
                total_time = time.time() - start_time
                
                # Build response
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_build_response", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:336", "message": "before_build_response", "data": {"contacts_count": len(contacts), "companies_count": len(companies)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
                except: pass
                #endregion agent log
                response = LinkedInSearchResponse(
                    contacts=contacts,
                    companies=companies,
                    total_contacts=len(contacts),
                    total_companies=len(companies),
                )
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_response_built", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:343", "message": "response_built", "data": {"total_contacts": response.total_contacts, "total_companies": response.total_companies, "contacts_len": len(response.contacts), "companies_len": len(response.companies)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
                except: pass
                #endregion agent log
                
                # Deduct credits for FreeUser and ProUser (after successful search)
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_credit_deduction", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:277", "message": "before_credit_deduction", "data": {"user_id": user_id}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                except: pass
                #endregion agent log
                if user_id:
                    try:
                        #region agent log
                        try:
                            with open(log_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_profile_lookup", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:279", "message": "before_profile_lookup", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                        except: pass
                        #endregion agent log
                        profile = await self.profile_repo.get_by_user_id(session, user_id)
                        #region agent log
                        try:
                            with open(log_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_profile_lookup", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:280", "message": "after_profile_lookup", "data": {"profile_found": profile is not None, "role": profile.role if profile else None}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                        except: pass
                        #endregion agent log
                        if profile:
                            user_role = profile.role or "FreeUser"
                            if self.credit_service.should_deduct_credits(user_role):
                                #region agent log
                                try:
                                    with open(log_path, "a", encoding="utf-8") as f:
                                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_deduct_credits", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:283", "message": "before_deduct_credits", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                                except: pass
                                #endregion agent log
                                await self.credit_service.deduct_credits(session, user_id, amount=1)
                                #region agent log
                                try:
                                    with open(log_path, "a", encoding="utf-8") as f:
                                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_deduct_credits", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:284", "message": "after_deduct_credits", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                                except: pass
                                #endregion agent log
                    except Exception as credit_exc:
                        #region agent log
                        try:
                            with open(log_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_credit_exception", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:285", "message": "credit_exception", "data": {"exception_type": type(credit_exc).__name__, "exception_msg": str(credit_exc)[:500]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H3"}) + "\n")
                        except: pass
                        #endregion agent log
                        # Credit deduction failed but search continues
                        # Rollback any pending changes from credit deduction
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                
                # Commit transaction on success
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_commit", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:293", "message": "before_commit", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H4"}) + "\n")
                except: pass
                #endregion agent log
                await session.commit()
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_commit", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:294", "message": "after_commit", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H4"}) + "\n")
                except: pass
                #endregion agent log
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_return_response", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:422", "message": "before_return_response", "data": {"response_type": type(response).__name__, "total_contacts": response.total_contacts, "total_companies": response.total_companies}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
                except Exception as log_exc:
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_log_error_return", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:422", "message": "log_error_return", "data": {"error": str(log_exc)}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1"}) + "\n")
                    except: pass
                #endregion agent log
                return response
                
            except Exception as exc:
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_service_exception", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:296", "message": "service_exception", "data": {"exception_type": type(exc).__name__, "exception_msg": str(exc)[:500], "exception_repr": repr(exc)[:500]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H1,H2,H3,H4,H5,H6"}) + "\n")
                except: pass
                #endregion agent log
                # Rollback transaction on error
                #region agent log
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_before_rollback", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:298", "message": "before_rollback", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H4"}) + "\n")
                except: pass
                #endregion agent log
                try:
                    await session.rollback()
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_after_rollback", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:300", "message": "after_rollback", "data": {}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H4"}) + "\n")
                    except: pass
                    #endregion agent log
                except Exception as rollback_exc:
                    #region agent log
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"id": f"log_{int(time.time() * 1000)}_rollback_exception", "timestamp": int(time.time() * 1000), "location": "linkedin_service.py:302", "message": "rollback_exception", "data": {"exception_type": type(rollback_exc).__name__, "exception_msg": str(rollback_exc)[:500]}, "sessionId": "debug-session", "runId": "run1", "hypothesisId": "H4"}) + "\n")
                    except: pass
                    #endregion agent log
                    pass
                raise

    async def upsert_by_url(
        self,
        session: AsyncSession,
        linkedin_url: str,
        contact_data: Optional[dict] = None,
        company_data: Optional[dict] = None,
        contact_metadata: Optional[dict] = None,
        company_metadata: Optional[dict] = None,
    ) -> LinkedInUpsertResponse:
        """
        Create or update records based on LinkedIn URL.
        
        If a contact or company with the LinkedIn URL exists, update it.
        Otherwise, create new records.
        """
        created = False
        updated = False
        contacts: list[ContactWithRelations] = []
        companies: list[CompanyWithRelations] = []
        
        # Normalize LinkedIn URL
        normalized_url = normalize_text(linkedin_url)
        if not normalized_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LinkedIn URL cannot be empty",
            )
        
        # Check if this is a person LinkedIn URL (in ContactMetadata)
        contact_match = await self.linkedin_repo.find_contact_by_exact_linkedin_url(
            session, normalized_url
        )
        
        # Check if this is a company LinkedIn URL (in CompanyMetadata)
        company_match = await self.linkedin_repo.find_company_by_exact_linkedin_url(
            session, normalized_url
        )
        
        # Handle contact upsert
        if contact_match or contact_data or contact_metadata:
            contact, contact_meta, company, company_meta = contact_match if contact_match else (None, None, None, None)
            
            if contact:
                # Update existing contact
                updated = True
                
                if contact_data:
                    # Update contact fields
                    for key, value in contact_data.items():
                        if hasattr(contact, key):
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(contact, key, normalized)
                    contact.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    await session.flush()
                
                # Update or create contact metadata
                if contact_metadata or normalized_url:
                    if contact_meta:
                        # Update existing metadata
                        if contact_metadata:
                            for key, value in contact_metadata.items():
                                if hasattr(contact_meta, key):
                                    normalized = normalize_text(value) if isinstance(value, str) else value
                                    setattr(contact_meta, key, normalized)
                        # Always update linkedin_url
                        contact_meta.linkedin_url = normalized_url
                        await session.flush()
                    else:
                        # Create new metadata
                        contact_meta = ContactMetadata(
                            uuid=contact.uuid,
                            linkedin_url=normalized_url,
                        )
                        if contact_metadata:
                            for key, value in contact_metadata.items():
                                if hasattr(contact_meta, key):
                                    normalized = normalize_text(value) if isinstance(value, str) else value
                                    setattr(contact_meta, key, normalized)
                        session.add(contact_meta)
                        await session.flush()
            else:
                # Create new contact
                created = True
                
                contact_uuid = contact_data.get("uuid") if contact_data else None
                normalized_uuid = normalize_text(contact_uuid, allow_placeholder=False)
                contact_uuid = normalized_uuid or uuid4().hex
                
                now = datetime.now(UTC).replace(tzinfo=None)
                contact = Contact(
                    uuid=contact_uuid,
                    created_at=now,
                    updated_at=now,
                    seniority=PLACEHOLDER_VALUE,
                )
                
                if contact_data:
                    for key, value in contact_data.items():
                        if hasattr(contact, key) and key != "uuid":
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(contact, key, normalized)
                
                session.add(contact)
                await session.flush()
                
                # Create contact metadata
                contact_meta = ContactMetadata(
                    uuid=contact.uuid,
                    linkedin_url=normalized_url,
                )
                if contact_metadata:
                    for key, value in contact_metadata.items():
                        if hasattr(contact_meta, key):
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(contact_meta, key, normalized)
                session.add(contact_meta)
                await session.flush()
            
            # Refresh to get related company if exists
            if contact.company_id:
                company = await self.company_repo.get_by_uuid(session, contact.company_id)
                if company:
                    company_meta_result = await session.execute(
                        select(CompanyMetadata).where(CompanyMetadata.uuid == company.uuid)
                    )
                    company_meta = company_meta_result.scalar_one_or_none()
            
            # Build response
            contact_data_out = ContactDB.model_validate(contact)
            metadata_data_out = (
                ContactMetadataOut.model_validate(contact_meta) if contact_meta else None
            )
            company_data_out = CompanyDB.model_validate(company) if company else None
            company_meta_data_out = (
                CompanyMetadataOut.model_validate(company_meta) if company_meta else None
            )
            
            contacts.append(
                ContactWithRelations(
                    contact=contact_data_out,
                    metadata=metadata_data_out,
                    company=company_data_out,
                    company_metadata=company_meta_data_out,
                )
            )
        
        # Handle company upsert
        if company_match or company_data or company_metadata:
            company, company_meta = company_match if company_match else (None, None)
            
            if company:
                # Update existing company
                updated = True
                
                if company_data:
                    # Update company fields
                    for key, value in company_data.items():
                        if hasattr(company, key):
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(company, key, normalized)
                    company.updated_at = datetime.now(UTC).replace(tzinfo=None)
                    await session.flush()
                
                # Update or create company metadata
                if company_metadata or normalized_url:
                    if company_meta:
                        # Update existing metadata
                        if company_metadata:
                            for key, value in company_metadata.items():
                                if hasattr(company_meta, key):
                                    normalized = normalize_text(value) if isinstance(value, str) else value
                                    setattr(company_meta, key, normalized)
                        # Always update linkedin_url
                        company_meta.linkedin_url = normalized_url
                        await session.flush()
                    else:
                        # Create new metadata
                        company_meta = CompanyMetadata(
                            uuid=company.uuid,
                            linkedin_url=normalized_url,
                        )
                        if company_metadata:
                            for key, value in company_metadata.items():
                                if hasattr(company_meta, key):
                                    normalized = normalize_text(value) if isinstance(value, str) else value
                                    setattr(company_meta, key, normalized)
                        session.add(company_meta)
                        await session.flush()
            else:
                # Create new company
                created = True
                
                company_uuid = company_data.get("uuid") if company_data else None
                normalized_uuid = normalize_text(company_uuid, allow_placeholder=False)
                company_uuid = normalized_uuid or uuid4().hex
                
                now = datetime.now(UTC).replace(tzinfo=None)
                company = Company(
                    uuid=company_uuid,
                    created_at=now,
                    updated_at=now,
                )
                
                if company_data:
                    for key, value in company_data.items():
                        if hasattr(company, key) and key != "uuid":
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(company, key, normalized)
                
                session.add(company)
                await session.flush()
                
                # Create company metadata
                company_meta = CompanyMetadata(
                    uuid=company.uuid,
                    linkedin_url=normalized_url,
                )
                if company_metadata:
                    for key, value in company_metadata.items():
                        if hasattr(company_meta, key):
                            normalized = normalize_text(value) if isinstance(value, str) else value
                            setattr(company_meta, key, normalized)
                session.add(company_meta)
                await session.flush()
            
            # Get company contacts
            company_contacts_rows = await self.linkedin_repo.get_company_contacts(
                session, company.uuid
            )
            
            company_contacts: list[ContactWithRelations] = []
            for contact, contact_meta in company_contacts_rows:
                contact_data_out = ContactDB.model_validate(contact)
                metadata_data_out = (
                    ContactMetadataOut.model_validate(contact_meta) if contact_meta else None
                )
                
                company_contacts.append(
                    ContactWithRelations(
                        contact=contact_data_out,
                        metadata=metadata_data_out,
                        company=CompanyDB.model_validate(company),
                        company_metadata=CompanyMetadataOut.model_validate(company_meta) if company_meta else None,
                    )
                )
            
            # Build response
            company_data_out = CompanyDB.model_validate(company)
            company_meta_data_out = (
                CompanyMetadataOut.model_validate(company_meta) if company_meta else None
            )
            
            companies.append(
                CompanyWithRelations(
                    company=company_data_out,
                    metadata=company_meta_data_out,
                    contacts=company_contacts,
                )
            )
        
        await session.commit()
        
        return LinkedInUpsertResponse(
            created=created,
            updated=updated,
            contacts=contacts,
            companies=companies,
        )

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
                result = await self.search_by_url(session, url, use_parallel=False)
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

