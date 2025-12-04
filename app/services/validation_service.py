"""Service for validating contact and company data."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.companies import Company
from app.models.contacts import Contact
from app.utils.company_name_utils import is_valid_company_name
from app.utils.keyword_utils import is_valid_keyword
from app.utils.title_utils import is_valid_title

logger = get_logger(__name__)


class ValidationService:
    """Service for validating data quality."""

    def __init__(self):
        """Initialize validation service."""
        # Use validation utilities from app.utils
        self.is_valid_company_name = is_valid_company_name
        self.is_valid_keyword = is_valid_keyword
        self.is_valid_title = is_valid_title

    async def validate_contact(
        self,
        session: AsyncSession,
        contact_uuid: str,
    ) -> Optional[dict]:
        """
        Validate a single contact.
        
        Args:
            session: Database session
            contact_uuid: Contact UUID
            
        Returns:
            Dictionary with validation results or None if contact not found
        """
        try:
            # Get contact
            result = await session.execute(
                select(Contact).where(Contact.uuid == contact_uuid)
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                return None
            
            issues = []
            fields_validated = []
            is_valid = True
            
            # Validate title
            fields_validated.append("title")
            if contact.title:
                if not self.is_valid_title(contact.title):
                    issues.append({
                        "field": "title",
                        "issue": "Title is invalid",
                        "severity": "error",
                    })
                    is_valid = False
            else:
                issues.append({
                    "field": "title",
                    "issue": "Title is missing",
                    "severity": "warning",
                })
            
            # Validate first_name
            fields_validated.append("first_name")
            if not contact.first_name or not contact.first_name.strip():
                issues.append({
                    "field": "first_name",
                    "issue": "First name is missing",
                    "severity": "warning",
                })
            
            # Validate last_name
            fields_validated.append("last_name")
            if not contact.last_name or not contact.last_name.strip():
                issues.append({
                    "field": "last_name",
                    "issue": "Last name is missing",
                    "severity": "warning",
                })
            
            # Validate email
            fields_validated.append("email")
            if contact.email:
                if "@" not in contact.email:
                    issues.append({
                        "field": "email",
                        "issue": "Email format is invalid",
                        "severity": "error",
                    })
                    is_valid = False
            else:
                issues.append({
                    "field": "email",
                    "issue": "Email is missing",
                    "severity": "warning",
                })
            
            # Validate departments (keywords)
            if contact.departments:
                fields_validated.append("departments")
                for idx, dept in enumerate(contact.departments):
                    if not self.is_valid_keyword(dept):
                        issues.append({
                            "field": f"departments[{idx}]",
                            "issue": f"Invalid department keyword: '{dept}'",
                            "severity": "error",
                        })
                        is_valid = False
            
            return {
                "contact_uuid": contact_uuid,
                "is_valid": is_valid,
                "issues": issues,
                "fields_validated": fields_validated,
            }
        except Exception as e:
            logger.exception("Error validating contact: uuid=%s", contact_uuid)
            raise

    async def validate_company(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Optional[dict]:
        """
        Validate a single company.
        
        Args:
            session: Database session
            company_uuid: Company UUID
            
        Returns:
            Dictionary with validation results or None if company not found
        """
        try:
            # Get company
            result = await session.execute(
                select(Company).where(Company.uuid == company_uuid)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                return None
            
            issues = []
            fields_validated = []
            is_valid = True
            
            # Validate company name
            fields_validated.append("name")
            if company.name:
                if not self.is_valid_company_name(company.name):
                    issues.append({
                        "field": "name",
                        "issue": "Company name is invalid",
                        "severity": "error",
                    })
                    is_valid = False
            else:
                issues.append({
                    "field": "name",
                    "issue": "Company name is missing",
                    "severity": "error",
                })
                is_valid = False
            
            # Validate keywords
            if company.keywords:
                fields_validated.append("keywords")
                for idx, keyword in enumerate(company.keywords):
                    if not self.is_valid_keyword(keyword):
                        issues.append({
                            "field": f"keywords[{idx}]",
                            "issue": f"Invalid keyword: '{keyword}'",
                            "severity": "error",
                        })
                        is_valid = False
            
            # Validate industries
            if company.industries:
                fields_validated.append("industries")
                for idx, industry in enumerate(company.industries):
                    if not industry or not industry.strip():
                        issues.append({
                            "field": f"industries[{idx}]",
                            "issue": "Empty industry value",
                            "severity": "warning",
                        })
            
            return {
                "company_uuid": company_uuid,
                "is_valid": is_valid,
                "issues": issues,
                "fields_validated": fields_validated,
            }
        except Exception as e:
            logger.exception("Error validating company: uuid=%s", company_uuid)
            raise

    async def validate_contacts_batch(
        self,
        session: AsyncSession,
        contact_uuids: list[str],
    ) -> list[dict]:
        """
        Validate a batch of contacts.
        
        Args:
            session: Database session
            contact_uuids: List of contact UUIDs
            
        Returns:
            List of validation results
        """
        results = []
        for uuid in contact_uuids:
            result = await self.validate_contact(session, uuid)
            if result:
                results.append(result)
            else:
                # Contact not found - include with error
                results.append({
                    "contact_uuid": uuid,
                    "is_valid": False,
                    "issues": [{
                        "field": "contact",
                        "issue": "Contact not found",
                        "severity": "error",
                    }],
                    "fields_validated": [],
                })
        return results

    async def validate_companies_batch(
        self,
        session: AsyncSession,
        company_uuids: list[str],
    ) -> list[dict]:
        """
        Validate a batch of companies.
        
        Args:
            session: Database session
            company_uuids: List of company UUIDs
            
        Returns:
            List of validation results
        """
        results = []
        for uuid in company_uuids:
            result = await self.validate_company(session, uuid)
            if result:
                results.append(result)
            else:
                # Company not found - include with error
                results.append({
                    "company_uuid": uuid,
                    "is_valid": False,
                    "issues": [{
                        "field": "company",
                        "issue": "Company not found",
                        "severity": "error",
                    }],
                    "fields_validated": [],
                })
        return results

