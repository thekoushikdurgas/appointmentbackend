"""Service layer for bulk data insert operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid5, NAMESPACE_URL

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.repositories.linkedin import LinkedInRepository
from app.schemas.bulk import BulkInsertError, BulkInsertResponse
from app.utils.company_name_utils import clean_company_name
from app.utils.keyword_utils import clean_keyword_array
from app.utils.normalization import PLACEHOLDER_VALUE
from app.utils.title_utils import clean_title


def _get_value(data: Dict[str, Any], key: str, default: str = PLACEHOLDER_VALUE) -> str:
    """Get value from data dict with default placeholder."""
    value = data.get(key)
    if value is None or value == "":
        return default
    return str(value)


def _get_int_value(data: Dict[str, Any], key: str, default: int = 0) -> int:
    """Get integer value from data dict with default."""
    value = data.get(key)
    if value is None or value == "":
        return default
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def _split_comma_list(value: Optional[str]) -> List[str]:
    """Split comma-separated string into list of trimmed strings."""
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _has_contact_fields(data: Dict[str, Any]) -> bool:
    """Check if data contains contact fields."""
    contact_fields = ["first_name", "last_name", "email", "person_linkedin_url"]
    return any(data.get(field) for field in contact_fields)


def _has_company_fields(data: Dict[str, Any]) -> bool:
    """Check if data contains company fields."""
    company_fields = ["company", "company_linkedin_url", "company_name_for_emails"]
    return any(data.get(field) for field in company_fields)


class BulkService:
    """Business logic for bulk data insert operations."""

    def __init__(self, linkedin_repo: Optional[LinkedInRepository] = None):
        """Initialize the service with repository dependencies."""
        self.linkedin_repo = linkedin_repo or LinkedInRepository()

    async def bulk_insert(
        self,
        session: AsyncSession,
        data_list: List[Dict[str, Any]],
    ) -> BulkInsertResponse:
        """
        Process and insert bulk data (contacts and companies).
        
        Args:
            session: Database session
            data_list: List of raw data dictionaries
            
        Returns:
            BulkInsertResponse with summary statistics
        """
        contacts_inserted = 0
        contacts_updated = 0
        contacts_skipped = 0
        companies_inserted = 0
        companies_updated = 0
        companies_skipped = 0
        errors: List[BulkInsertError] = []
        
        # Separate data by type
        contact_data_list: List[Dict[str, Any]] = []
        company_data_list: List[Dict[str, Any]] = []
        
        for idx, data in enumerate(data_list):
            has_contact = _has_contact_fields(data)
            has_company = _has_company_fields(data)
            
            if has_contact:
                contact_data_list.append(data)
            if has_company:
                company_data_list.append(data)
            
            if not has_contact and not has_company:
                errors.append(
                    BulkInsertError(
                        index=idx,
                        error="Record contains neither contact nor company fields",
                        record_type=None,
                    )
                )
        
        # Process companies first (contacts may reference them)
        if company_data_list:
            company_result = await self._upsert_companies(session, company_data_list)
            companies_inserted = company_result["inserted"]
            companies_updated = company_result["updated"]
            companies_skipped = company_result["skipped"]
            errors.extend(company_result["errors"])
        
        # Process contacts
        if contact_data_list:
            contact_result = await self._upsert_contacts(session, contact_data_list)
            contacts_inserted = contact_result["inserted"]
            contacts_updated = contact_result["updated"]
            contacts_skipped = contact_result["skipped"]
            errors.extend(contact_result["errors"])
        
        # Commit transaction
        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise
        
        return BulkInsertResponse(
            contacts_inserted=contacts_inserted,
            contacts_updated=contacts_updated,
            contacts_skipped=contacts_skipped,
            companies_inserted=companies_inserted,
            companies_updated=companies_updated,
            companies_skipped=companies_skipped,
            total_processed=len(data_list),
            errors=errors if errors else None,
        )

    async def _upsert_companies(
        self,
        session: AsyncSession,
        data_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Upsert company data into database (insert or update by LinkedIn URL)."""
        company_lst: List[Dict[str, Any]] = []
        meta_lst: List[Dict[str, Any]] = []
        server_time = datetime.now(UTC).replace(tzinfo=None)
        errors: List[BulkInsertError] = []
        existing_company_uuids: Dict[str, str] = {}  # linkedin_url -> uuid mapping
        
        # First pass: build data structures and check for existing companies by LinkedIn URL
        for idx, data in enumerate(data_list):
            try:
                linkedin_url_raw = data.get("company_linkedin_url")
                linkedin_url = _get_value(data, "company_linkedin_url")
                
                # Check if company exists by LinkedIn URL (normalize first)
                if linkedin_url and linkedin_url != PLACEHOLDER_VALUE:
                    normalized_url = linkedin_url.strip()
                    if normalized_url:
                        company_match = await self.linkedin_repo.find_company_by_exact_linkedin_url(
                            session, normalized_url
                        )
                        if company_match:
                            company, company_meta = company_match
                            existing_company_uuids[normalized_url] = company.uuid
                
                # Get raw company name and clean it
                raw_company_name = data.get("company")
                company_name = clean_company_name(raw_company_name) if raw_company_name else None
                
                # Use existing UUID if found, otherwise generate new one
                uuid_company_name = raw_company_name if raw_company_name else PLACEHOLDER_VALUE
                company_name_for_emails = _get_value(data, "company_name_for_emails")
                
                # Use existing UUID if found, otherwise generate new one
                normalized_linkedin_url = linkedin_url.strip() if linkedin_url and linkedin_url != PLACEHOLDER_VALUE else ""
                if normalized_linkedin_url and normalized_linkedin_url in existing_company_uuids:
                    company_uuid = existing_company_uuids[normalized_linkedin_url]
                else:
                    hash_str = uuid_company_name + linkedin_url + company_name_for_emails
                    company_uuid = str(uuid5(NAMESPACE_URL, hash_str))
                
                # Process industries
                industry_str = _get_value(data, "industry", default="")
                industry_list = _split_comma_list(industry_str)
                
                # Process keywords with cleaning
                keywords_str = _get_value(data, "keywords", default="")
                raw_keywords = _split_comma_list(keywords_str)
                keywords_list = clean_keyword_array(raw_keywords) or []
                
                # Process technologies
                technologies_str = _get_value(data, "technologies", default="")
                technologies_list = _split_comma_list(technologies_str)
                
                # Build company record
                company_address = _get_value(data, "company_address")
                company_city = _get_value(data, "company_city")
                company_state = _get_value(data, "company_state")
                company_country = _get_value(data, "company_country")
                
                company = {
                    "uuid": company_uuid,
                    "name": company_name,
                    "employees_count": _get_int_value(data, "employees"),
                    "industries": industry_list if industry_list else None,
                    "keywords": keywords_list if keywords_list else None,
                    "address": company_address if company_address != PLACEHOLDER_VALUE else None,
                    "annual_revenue": _get_int_value(data, "annual_revenue"),
                    "total_funding": _get_int_value(data, "total_funding"),
                    "technologies": technologies_list if technologies_list else None,
                    "text_search": f"{company_address} {company_city} {company_state} {company_country}".strip()
                    if any([company_address, company_city, company_state, company_country])
                    else None,
                    "created_at": server_time,
                    "updated_at": server_time,
                }
                company_lst.append(company)
                
                # Build company metadata
                company_metadata = {
                    "uuid": company_uuid,
                    "linkedin_url": linkedin_url if linkedin_url != PLACEHOLDER_VALUE else None,
                    "facebook_url": _get_value(data, "facebook_url") if _get_value(data, "facebook_url") != PLACEHOLDER_VALUE else None,
                    "twitter_url": _get_value(data, "twitter_url") if _get_value(data, "twitter_url") != PLACEHOLDER_VALUE else None,
                    "website": _get_value(data, "website") if _get_value(data, "website") != PLACEHOLDER_VALUE else None,
                    "company_name_for_emails": company_name_for_emails if company_name_for_emails != PLACEHOLDER_VALUE else None,
                    "phone_number": _get_value(data, "company_phone") if _get_value(data, "company_phone") != PLACEHOLDER_VALUE else None,
                    "latest_funding": _get_value(data, "latest_funding") if _get_value(data, "latest_funding") != PLACEHOLDER_VALUE else None,
                    "latest_funding_amount": _get_int_value(data, "Latest_funding_amount"),
                    "last_raised_at": _get_value(data, "last_raised_at") if _get_value(data, "last_raised_at") != PLACEHOLDER_VALUE else None,
                    "city": company_city if company_city != PLACEHOLDER_VALUE else None,
                    "state": company_state if company_state != PLACEHOLDER_VALUE else None,
                    "country": company_country if company_country != PLACEHOLDER_VALUE else None,
                }
                meta_lst.append(company_metadata)
            except Exception as e:
                error_msg = str(e)
                errors.append(
                    BulkInsertError(
                        index=idx,
                        error=error_msg,
                        record_type="company",
                    )
                )
                continue
        
        inserted = 0
        updated = 0
        skipped = 0
        
        try:
            if company_lst:
                # Use on_conflict_do_update to update existing records
                stmt: Insert = (
                    insert(Company)
                    .on_conflict_do_update(
                        index_elements=["uuid"],
                        set_={
                            "name": insert(Company).excluded.name,
                            "employees_count": insert(Company).excluded.employees_count,
                            "industries": insert(Company).excluded.industries,
                            "keywords": insert(Company).excluded.keywords,
                            "address": insert(Company).excluded.address,
                            "annual_revenue": insert(Company).excluded.annual_revenue,
                            "total_funding": insert(Company).excluded.total_funding,
                            "technologies": insert(Company).excluded.technologies,
                            "text_search": insert(Company).excluded.text_search,
                            "updated_at": insert(Company).excluded.updated_at,
                        }
                    )
                )
                await session.execute(stmt, company_lst)
                
                # Count inserted vs updated by checking which UUIDs existed
                existing_uuids_set = set(existing_company_uuids.values())
                for company in company_lst:
                    if company["uuid"] in existing_uuids_set:
                        updated += 1
                    else:
                        inserted += 1
            
            if meta_lst:
                # Use on_conflict_do_update to update existing metadata
                stmt = (
                    insert(CompanyMetadata)
                    .on_conflict_do_update(
                        index_elements=["uuid"],
                        set_={
                            "linkedin_url": insert(CompanyMetadata).excluded.linkedin_url,
                            "facebook_url": insert(CompanyMetadata).excluded.facebook_url,
                            "twitter_url": insert(CompanyMetadata).excluded.twitter_url,
                            "website": insert(CompanyMetadata).excluded.website,
                            "company_name_for_emails": insert(CompanyMetadata).excluded.company_name_for_emails,
                            "phone_number": insert(CompanyMetadata).excluded.phone_number,
                            "latest_funding": insert(CompanyMetadata).excluded.latest_funding,
                            "latest_funding_amount": insert(CompanyMetadata).excluded.latest_funding_amount,
                            "last_raised_at": insert(CompanyMetadata).excluded.last_raised_at,
                            "city": insert(CompanyMetadata).excluded.city,
                            "state": insert(CompanyMetadata).excluded.state,
                            "country": insert(CompanyMetadata).excluded.country,
                        }
                    )
                )
                await session.execute(stmt, meta_lst)
        except Exception as e:
            for idx in range(len(data_list)):
                errors.append(
                    BulkInsertError(
                        index=idx,
                        error=f"Database upsert error: {str(e)}",
                        record_type="company",
                    )
                )
        
        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    async def _upsert_contacts(
        self,
        session: AsyncSession,
        data_list: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Upsert contact data into database (insert or update by LinkedIn URL)."""
        contact_lst: List[Dict[str, Any]] = []
        meta_lst: List[Dict[str, Any]] = []
        server_time = datetime.now(UTC).replace(tzinfo=None)
        errors: List[BulkInsertError] = []
        existing_contact_uuids: Dict[str, str] = {}  # linkedin_url -> uuid mapping
        
        # First pass: build data structures and check for existing contacts by LinkedIn URL
        for idx, data in enumerate(data_list):
            try:
                person_linkedin_url_raw = data.get("person_linkedin_url")
                person_linkedin_url = _get_value(data, "person_linkedin_url")
                
                # Check if contact exists by LinkedIn URL (normalize first)
                if person_linkedin_url and person_linkedin_url != PLACEHOLDER_VALUE:
                    normalized_url = person_linkedin_url.strip()
                    if normalized_url:
                        contact_match = await self.linkedin_repo.find_contact_by_exact_linkedin_url(
                            session, normalized_url
                        )
                        if contact_match:
                            contact, contact_meta, company, company_meta = contact_match
                            existing_contact_uuids[normalized_url] = contact.uuid
                
                # Generate company UUID (same logic as company insert)
                company_name = _get_value(data, "company")
                linkedin_url = _get_value(data, "company_linkedin_url")
                company_name_for_emails = _get_value(data, "company_name_for_emails")
                
                hash_str = company_name + linkedin_url + company_name_for_emails
                company_uuid = str(uuid5(NAMESPACE_URL, hash_str))
                
                # Process departments
                departments_str = _get_value(data, "departments", default="")
                departments = _split_comma_list(departments_str)
                
                # Use existing UUID if found, otherwise generate new one
                email = _get_value(data, "email")
                normalized_person_linkedin_url = person_linkedin_url.strip() if person_linkedin_url and person_linkedin_url != PLACEHOLDER_VALUE else ""
                if normalized_person_linkedin_url and normalized_person_linkedin_url in existing_contact_uuids:
                    data_uuid = existing_contact_uuids[normalized_person_linkedin_url]
                else:
                    data_uuid = str(uuid5(NAMESPACE_URL, person_linkedin_url + email))
                
                # Clean title
                raw_title = data.get("title")
                cleaned_title = clean_title(raw_title) if raw_title else None
                
                # Build contact record
                city = _get_value(data, "city")
                state = _get_value(data, "state")
                country = _get_value(data, "country")
                
                contact = {
                    "uuid": data_uuid,
                    "first_name": _get_value(data, "first_name") if _get_value(data, "first_name") != PLACEHOLDER_VALUE else None,
                    "last_name": _get_value(data, "last_name") if _get_value(data, "last_name") != PLACEHOLDER_VALUE else None,
                    "company_id": company_uuid,
                    "email": _get_value(data, "email") if _get_value(data, "email") != PLACEHOLDER_VALUE else None,
                    "title": cleaned_title,
                    "departments": departments if departments else None,
                    "mobile_phone": _get_value(data, "mobile_phone") if _get_value(data, "mobile_phone") != PLACEHOLDER_VALUE else None,
                    "email_status": _get_value(data, "email_status") if _get_value(data, "email_status") != PLACEHOLDER_VALUE else None,
                    "text_search": f"{city} {state} {country}".strip() if any([city, state, country]) else None,
                    "seniority": _get_value(data, "seniority", default=PLACEHOLDER_VALUE),
                    "created_at": server_time,
                    "updated_at": server_time,
                }
                contact_lst.append(contact)
                
                # Build contact metadata
                contact_metadata = {
                    "uuid": data_uuid,
                    "linkedin_url": person_linkedin_url if person_linkedin_url != PLACEHOLDER_VALUE else None,
                    "facebook_url": None,  # Not in raw data format
                    "twitter_url": None,  # Not in raw data format
                    "website": _get_value(data, "website") if _get_value(data, "website") != PLACEHOLDER_VALUE else None,
                    "work_direct_phone": _get_value(data, "work_direct_phone") if _get_value(data, "work_direct_phone") != PLACEHOLDER_VALUE else None,
                    "home_phone": _get_value(data, "home_phone") if _get_value(data, "home_phone") != PLACEHOLDER_VALUE else None,
                    "city": city if city != PLACEHOLDER_VALUE else None,
                    "state": state if state != PLACEHOLDER_VALUE else None,
                    "country": country if country != PLACEHOLDER_VALUE else None,
                    "other_phone": _get_value(data, "other_phone") if _get_value(data, "other_phone") != PLACEHOLDER_VALUE else None,
                    "stage": _get_value(data, "stage") if _get_value(data, "stage") != PLACEHOLDER_VALUE else None,
                }
                meta_lst.append(contact_metadata)
            except Exception as e:
                error_msg = str(e)
                errors.append(
                    BulkInsertError(
                        index=idx,
                        error=error_msg,
                        record_type="contact",
                    )
                )
                continue
        
        inserted = 0
        updated = 0
        skipped = 0
        
        try:
            if contact_lst:
                # Use on_conflict_do_update to update existing records
                stmt: Insert = (
                    insert(Contact)
                    .on_conflict_do_update(
                        index_elements=["uuid"],
                        set_={
                            "first_name": insert(Contact).excluded.first_name,
                            "last_name": insert(Contact).excluded.last_name,
                            "company_id": insert(Contact).excluded.company_id,
                            "email": insert(Contact).excluded.email,
                            "title": insert(Contact).excluded.title,
                            "departments": insert(Contact).excluded.departments,
                            "mobile_phone": insert(Contact).excluded.mobile_phone,
                            "email_status": insert(Contact).excluded.email_status,
                            "text_search": insert(Contact).excluded.text_search,
                            "seniority": insert(Contact).excluded.seniority,
                            "updated_at": insert(Contact).excluded.updated_at,
                        }
                    )
                )
                await session.execute(stmt, contact_lst)
                
                # Count inserted vs updated by checking which UUIDs existed
                existing_uuids_set = set(existing_contact_uuids.values())
                for contact in contact_lst:
                    if contact["uuid"] in existing_uuids_set:
                        updated += 1
                    else:
                        inserted += 1
            
            if meta_lst:
                # Use on_conflict_do_update to update existing metadata
                stmt = (
                    insert(ContactMetadata)
                    .on_conflict_do_update(
                        index_elements=["uuid"],
                        set_={
                            "linkedin_url": insert(ContactMetadata).excluded.linkedin_url,
                            "facebook_url": insert(ContactMetadata).excluded.facebook_url,
                            "twitter_url": insert(ContactMetadata).excluded.twitter_url,
                            "website": insert(ContactMetadata).excluded.website,
                            "work_direct_phone": insert(ContactMetadata).excluded.work_direct_phone,
                            "home_phone": insert(ContactMetadata).excluded.home_phone,
                            "other_phone": insert(ContactMetadata).excluded.other_phone,
                            "city": insert(ContactMetadata).excluded.city,
                            "state": insert(ContactMetadata).excluded.state,
                            "country": insert(ContactMetadata).excluded.country,
                            "stage": insert(ContactMetadata).excluded.stage,
                        }
                    )
                )
                await session.execute(stmt, meta_lst)
        except Exception as e:
            for idx in range(len(data_list)):
                errors.append(
                    BulkInsertError(
                        index=idx,
                        error=f"Database upsert error: {str(e)}",
                        record_type="contact",
                    )
                )
        
        return {
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

