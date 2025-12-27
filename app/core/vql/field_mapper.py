"""Field mapping from VQL field names to SQLAlchemy model attributes."""

from typing import Dict, Optional, Tuple

from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase

from app.models.companies import Company, CompanyMetadata
from app.models.contacts import Contact, ContactMetadata
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FieldMapper:
    """Maps VQL field names to SQLAlchemy model columns and determines table relationships."""

    # Contact table fields
    CONTACT_FIELDS: Dict[str, str] = {
        "id": "uuid",
        "uuid": "uuid",
        "first_name": "first_name",
        "last_name": "last_name",
        "title": "title",
        "email": "email",
        "company_id": "company_id",
        "seniority": "seniority",
        "departments": "departments",
        "mobile_phone": "mobile_phone",
        "email_status": "email_status",
        "status": "status",
        "text_search": "text_search",
        "contact_location": "text_search",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }

    # ContactMetadata fields
    CONTACT_METADATA_FIELDS: Dict[str, str] = {
        "person_linkedin_url": "linkedin_url",
        "linkedin_url": "linkedin_url",
        "linkedin_sales_url": "linkedin_sales_url",
        "facebook_url": "facebook_url",
        "twitter_url": "twitter_url",
        "website": "website",
        "work_direct_phone": "work_direct_phone",
        "home_phone": "home_phone",
        "other_phone": "other_phone",
        "city": "city",
        "state": "state",
        "country": "country",
        "stage": "stage",
    }

    # Company table fields
    COMPANY_FIELDS: Dict[str, str] = {
        "id": "uuid",
        "uuid": "uuid",
        "name": "name",
        "employees_count": "employees_count",
        "employees": "employees_count",
        "industries": "industries",
        "industry": "industries",
        "keywords": "keywords",
        "technologies": "technologies",
        "address": "address",
        "annual_revenue": "annual_revenue",
        "total_funding": "total_funding",
        "text_search": "text_search",
        "company_location": "text_search",
        "company_text_search": "text_search",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }

    # CompanyMetadata fields
    COMPANY_METADATA_FIELDS: Dict[str, str] = {
        "domain": "website",  # Domain extracted from website
        "website": "website",
        "normalized_domain": "normalized_domain",
        "company_name_for_emails": "company_name_for_emails",
        "phone_number": "phone_number",
        "corporate_phone": "phone_number",
        "company_phone": "phone_number",
        "latest_funding": "latest_funding",
        "latest_funding_amount": "latest_funding_amount",
        "last_raised_at": "last_raised_at",
        "company_linkedin_url": "linkedin_url",
        "linkedin_url": "linkedin_url",
        "linkedin_sales_url": "linkedin_sales_url",
        "facebook_url": "facebook_url",
        "twitter_url": "twitter_url",
        "company_city": "city",
        "city": "city",
        "company_state": "state",
        "state": "state",
        "company_country": "country",
        "country": "country",
    }

    @classmethod
    def map_contact_field(
        cls, field_name: str
    ) -> Tuple[Optional[Column], Optional[str]]:
        """
        Map a VQL field name to a Contact or ContactMetadata column.

        Returns:
            Tuple of (Column object, table_name) or (None, None) if not found
        """
        # Check Contact table
        if field_name in cls.CONTACT_FIELDS:
            attr_name = cls.CONTACT_FIELDS[field_name]
            if hasattr(Contact, attr_name):
                return (getattr(Contact, attr_name), "contacts")

        # Check ContactMetadata table
        if field_name in cls.CONTACT_METADATA_FIELDS:
            attr_name = cls.CONTACT_METADATA_FIELDS[field_name]
            if hasattr(ContactMetadata, attr_name):
                return (getattr(ContactMetadata, attr_name), "contacts_metadata")

        return (None, None)

    @classmethod
    def map_company_field(
        cls, field_name: str
    ) -> Tuple[Optional[Column], Optional[str]]:
        """
        Map a VQL field name to a Company or CompanyMetadata column.

        Returns:
            Tuple of (Column object, table_name) or (None, None) if not found
        """
        # Check Company table
        if field_name in cls.COMPANY_FIELDS:
            attr_name = cls.COMPANY_FIELDS[field_name]
            if hasattr(Company, attr_name):
                return (getattr(Company, attr_name), "companies")

        # Check CompanyMetadata table
        if field_name in cls.COMPANY_METADATA_FIELDS:
            attr_name = cls.COMPANY_METADATA_FIELDS[field_name]
            if hasattr(CompanyMetadata, attr_name):
                return (getattr(CompanyMetadata, attr_name), "companies_metadata")

        return (None, None)

    @classmethod
    def get_field_type(cls, field_name: str, entity_type: str = "contact") -> str:
        """
        Determine the field type (string, integer, array, etc.) for operator handling.

        Args:
            field_name: VQL field name
            entity_type: "contact" or "company"

        Returns:
            Field type string: "string", "integer", "array", "datetime", etc.
        """
        if entity_type == "contact":
            column, _ = cls.map_contact_field(field_name)
        else:
            column, _ = cls.map_company_field(field_name)

        if column is None:
            return "string"  # Default

        # Check for array fields
        array_fields = ["departments", "industries", "keywords", "technologies"]
        if field_name in array_fields or any(
            field_name in getattr(cls, f"{entity_type.upper()}_FIELDS", {})
            for _ in array_fields
        ):
            return "array"

        # Check column type
        column_type = str(column.type)
        if "BigInteger" in column_type or "Integer" in column_type:
            return "integer"
        elif "DateTime" in column_type:
            return "datetime"
        elif "Text" in column_type or "String" in column_type:
            return "string"
        else:
            return "string"  # Default

    @classmethod
    def is_valid_field(cls, field_name: str, entity_type: str = "contact") -> bool:
        """Check if a field name is valid for the given entity type."""
        if entity_type == "contact":
            column, _ = cls.map_contact_field(field_name)
        else:
            column, _ = cls.map_company_field(field_name)
        return column is not None

