"""Filter parameter schemas supporting contact metadata queries."""

import json
from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ContactFilterParams(BaseModel):
    """Full set of filterable fields accepted by the contacts endpoints."""

    model_config = ConfigDict(extra="ignore")

    first_name: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.first_name.",
    )
    last_name: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.last_name.",
    )
    title: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.title.",
    )
    seniority: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.seniority.",
    )
    department: Optional[str] = Field(
        default=None,
        alias="departments",
        description="Substring match against Contact.departments array (stored as comma-delimited text).",
    )
    email_status: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.email_status.",
    )
    email: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against Contact.email.",
    )
    company: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("company", "name"),
        description="Case-insensitive substring match against Company.name.",
    )
    company_name_for_emails: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring match against CompanyMetadata.company_name_for_emails.",
    )
    company_location: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("company_location", "company_text_search"),
        description="Company text-search column (Company.text_search) covering address, city, state, and country.",
    )
    contact_location: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("contact_location", "text_search"),
        description="Contact text-search column (Contact.text_search) covering person-level location metadata.",
    )
    employees_count: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("employees_count", "employees"),
        description="Exact match against Company.employees_count.",
        ge=0,
    )
    employees_min: Optional[int] = Field(
        default=None,
        description="Lower-bound filter applied to Company.employees_count.",
        ge=0,
    )
    employees_max: Optional[int] = Field(
        default=None,
        description="Upper-bound filter applied to Company.employees_count.",
        ge=0,
    )
    annual_revenue: Optional[int] = Field(
        default=None,
        description="Exact match against Company.annual_revenue (stored as integer dollars).",
        ge=0,
    )
    annual_revenue_min: Optional[int] = Field(
        default=None,
        description="Lower-bound filter applied to Company.annual_revenue.",
        ge=0,
    )
    annual_revenue_max: Optional[int] = Field(
        default=None,
        description="Upper-bound filter applied to Company.annual_revenue.",
        ge=0,
    )
    total_funding: Optional[int] = Field(
        default=None,
        description="Exact match against Company.total_funding.",
        ge=0,
    )
    total_funding_min: Optional[int] = Field(
        default=None,
        description="Lower-bound filter applied to Company.total_funding.",
        ge=0,
    )
    total_funding_max: Optional[int] = Field(
        default=None,
        description="Upper-bound filter applied to Company.total_funding.",
        ge=0,
    )
    technologies: Optional[str] = Field(
        default=None,
        description="Substring match within Company.technologies (stored as text array).",
    )
    keywords: Optional[str] = Field(
        default=None,
        description="Substring match within Company.keywords (stored as text array).",
    )
    industries: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("industries", "industry"),
        description="Substring match within Company.industries (stored as text array).",
    )
    search: Optional[str] = Field(
        default=None,
        description="General-purpose search term applied across contact and company text columns.",
    )
    ordering: Optional[str] = Field(
        default=None,
        description="Ordering key referencing exposed Contact/Company columns (see repository ordering_map).",
    )
    distinct: bool = Field(
        default=False,
        description="When true, request distinct contacts based on primary key.",
    )
    page_size: Optional[int] = Field(
        default=None,
        description="Explicit page size override (bounded by settings.MAX_PAGE_SIZE).",
        ge=1,
    )
    cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor token representing the next offset.",
    )
    exclude_company_ids: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose company UUID matches any provided value.",
    )
    exclude_titles: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose title matches any provided value (case-insensitive).",
    )
    exclude_company_locations: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose company location text matches any provided value (case-insensitive).",
    )
    exclude_contact_locations: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose contact location text matches any provided value (case-insensitive).",
    )
    exclude_seniorities: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose seniority matches any provided value (case-insensitive).",
    )
    exclude_departments: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose departments include any provided value (case-insensitive).",
    )
    exclude_technologies: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose company technologies include any provided value (case-insensitive).",
    )
    exclude_keywords: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose company keywords include any provided value (case-insensitive).",
    )
    exclude_industries: Optional[list[str]] = Field(
        default=None,
        description="Exclude contacts whose company industries include any provided value (case-insensitive).",
    )
    latest_funding_amount_min: Optional[int] = Field(
        default=None,
        description="Lower-bound filter applied to CompanyMetadata.latest_funding_amount.",
        ge=0,
    )
    latest_funding_amount_max: Optional[int] = Field(
        default=None,
        description="Upper-bound filter applied to CompanyMetadata.latest_funding_amount.",
        ge=0,
    )
    work_direct_phone: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.work_direct_phone.",
    )
    home_phone: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.home_phone.",
    )
    mobile_phone: Optional[str] = Field(
        default=None,
        description="Substring match against Contact.mobile_phone.",
    )
    corporate_phone: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.phone_number.",
    )
    other_phone: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.other_phone.",
    )
    city: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.city.",
    )
    state: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.state.",
    )
    country: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.country.",
    )
    company_address: Optional[str] = Field(
        default=None,
        description="Substring match against Company.text_search (address fields).",
    )
    company_city: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.city.",
    )
    company_state: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.state.",
    )
    company_country: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.country.",
    )
    company_phone: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.phone_number.",
    )
    person_linkedin_url: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.linkedin_url.",
    )
    website: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.website.",
    )
    company_linkedin_url: Optional[str] = Field(
        default=None,
        description="Substring match against CompanyMetadata.linkedin_url.",
    )
    facebook_url: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.facebook_url or CompanyMetadata.facebook_url.",
    )
    twitter_url: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.twitter_url or CompanyMetadata.twitter_url.",
    )
    stage: Optional[str] = Field(
        default=None,
        description="Substring match against ContactMetadata.stage.",
    )
    created_at_after: Optional[datetime] = Field(
        default=None,
        description="Filter contacts created after the provided ISO timestamp (inclusive).",
    )
    created_at_before: Optional[datetime] = Field(
        default=None,
        description="Filter contacts created before the provided ISO timestamp (inclusive).",
    )
    updated_at_after: Optional[datetime] = Field(
        default=None,
        description="Filter contacts updated after the provided ISO timestamp (inclusive).",
    )
    updated_at_before: Optional[datetime] = Field(
        default=None,
        description="Filter contacts updated before the provided ISO timestamp (inclusive).",
    )

    @staticmethod
    def _normalize_multi_value(raw, *, case_insensitive: bool = False) -> Optional[list[str]]:
        """Normalize heterogeneous inputs into a deduplicated list of non-empty strings."""
        def _coerce(value) -> list[str]:
            if value is None:
                return []
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return []
                if stripped.startswith("[") and stripped.endswith("]"):
                    try:
                        parsed = json.loads(stripped)
                        return _coerce(parsed)
                    except json.JSONDecodeError:
                        pass
                tokens: list[str] = []
                for fragment in stripped.split(","):
                    token = fragment.strip()
                    if token:
                        tokens.append(token)
                return tokens
            if isinstance(value, (list, tuple, set)):
                tokens: list[str] = []
                for item in value:
                    tokens.extend(_coerce(item))
                return tokens
            text = str(value).strip()
            return [text] if text else []

        tokens = _coerce(raw)
        if not tokens:
            return None
        deduped: dict[str, str] = {}
        for token in tokens:
            key = token.lower() if case_insensitive else token
            if key not in deduped:
                deduped[key] = token
        return list(deduped.values()) or None

    @field_validator("exclude_company_ids", mode="before")
    @classmethod
    def _normalize_exclude_company_ids(cls, value):
        """Normalize exclusion inputs into a clean list of company identifiers."""
        return cls._normalize_multi_value(value)

    @field_validator("exclude_titles", mode="before")
    @classmethod
    def _normalize_exclude_titles(cls, value):
        """Normalize exclusion inputs into a clean list of titles."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_company_locations", mode="before")
    @classmethod
    def _normalize_exclude_company_locations(cls, value):
        """Normalize exclusion inputs for company locations."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_contact_locations", mode="before")
    @classmethod
    def _normalize_exclude_contact_locations(cls, value):
        """Normalize exclusion inputs for contact locations."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_seniorities", mode="before")
    @classmethod
    def _normalize_exclude_seniorities(cls, value):
        """Normalize exclusion inputs for seniorities."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_departments", mode="before")
    @classmethod
    def _normalize_exclude_departments(cls, value):
        """Normalize exclusion inputs for departments."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_technologies", mode="before")
    @classmethod
    def _normalize_exclude_technologies(cls, value):
        """Normalize exclusion inputs for technologies."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_keywords", mode="before")
    @classmethod
    def _normalize_exclude_keywords(cls, value):
        """Normalize exclusion inputs for keywords."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @field_validator("exclude_industries", mode="before")
    @classmethod
    def _normalize_exclude_industries(cls, value):
        """Normalize exclusion inputs for industries."""
        return cls._normalize_multi_value(value, case_insensitive=True)

    @staticmethod
    def _coerce_bool(value, *, default: bool = False) -> bool:
        """Best-effort conversion of common truthy/falsey representations to bool."""
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off", ""}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    @field_validator("distinct", mode="before")
    @classmethod
    def _normalize_distinct(cls, value):
        """Coerce truthy/falsey query parameters into bool without raising."""
        return cls._coerce_bool(value, default=False)


# Mapping of filter field names to their associated storage column or behavior.
# This is used for documentation, validation, and to keep tests in sync with the contract.
CONTACT_FILTER_COLUMN_MAP: dict[str, str] = {
    "first_name": "Contact.first_name",
    "last_name": "Contact.last_name",
    "title": "Contact.title",
    "seniority": "Contact.seniority",
    "department": "Contact.departments",
    "email_status": "Contact.email_status",
    "email": "Contact.email",
    "company": "Company.name",
    "company_name_for_emails": "CompanyMetadata.company_name_for_emails",
    "company_location": "Company.text_search",
    "contact_location": "Contact.text_search",
    "employees_count": "Company.employees_count",
    "employees_min": "Company.employees_count (minimum)",
    "employees_max": "Company.employees_count (maximum)",
    "annual_revenue": "Company.annual_revenue",
    "annual_revenue_min": "Company.annual_revenue (minimum)",
    "annual_revenue_max": "Company.annual_revenue (maximum)",
    "total_funding": "Company.total_funding",
    "total_funding_min": "Company.total_funding (minimum)",
    "total_funding_max": "Company.total_funding (maximum)",
    "technologies": "Company.technologies",
    "keywords": "Company.keywords",
    "industries": "Company.industries",
    "search": "Multi-column search helper",
    "ordering": "Ordering key applied in repository ordering_map",
    "distinct": "Distinct contact flag",
    "page_size": "Explicit page size override",
    "cursor": "Cursor token override",
    "exclude_company_ids": "Contact.company_id (exclusion list)",
    "exclude_titles": "Contact.title (exclusion list)",
    "exclude_company_locations": "Company.text_search (exclusion list)",
    "exclude_contact_locations": "Contact.text_search (exclusion list)",
    "exclude_seniorities": "Contact.seniority (exclusion list)",
    "exclude_departments": "Contact.departments (exclusion list)",
    "exclude_technologies": "Company.technologies (exclusion list)",
    "exclude_keywords": "Company.keywords (exclusion list)",
    "exclude_industries": "Company.industries (exclusion list)",
    "latest_funding_amount_min": "CompanyMetadata.latest_funding_amount (minimum)",
    "latest_funding_amount_max": "CompanyMetadata.latest_funding_amount (maximum)",
    "work_direct_phone": "ContactMetadata.work_direct_phone",
    "home_phone": "ContactMetadata.home_phone",
    "mobile_phone": "Contact.mobile_phone",
    "corporate_phone": "CompanyMetadata.phone_number",
    "other_phone": "ContactMetadata.other_phone",
    "city": "ContactMetadata.city",
    "state": "ContactMetadata.state",
    "country": "ContactMetadata.country",
    "company_address": "Company.text_search",
    "company_city": "CompanyMetadata.city",
    "company_state": "CompanyMetadata.state",
    "company_country": "CompanyMetadata.country",
    "company_phone": "CompanyMetadata.phone_number",
    "person_linkedin_url": "ContactMetadata.linkedin_url",
    "website": "ContactMetadata.website",
    "company_linkedin_url": "CompanyMetadata.linkedin_url",
    "facebook_url": "ContactMetadata.facebook_url / CompanyMetadata.facebook_url",
    "twitter_url": "ContactMetadata.twitter_url / CompanyMetadata.twitter_url",
    "stage": "ContactMetadata.stage",
    "created_at_after": "Contact.created_at (minimum timestamp)",
    "created_at_before": "Contact.created_at (maximum timestamp)",
    "updated_at_after": "Contact.updated_at (minimum timestamp)",
    "updated_at_before": "Contact.updated_at (maximum timestamp)",
}


class AttributeListParams(BaseModel):
    """Filters for attribute list endpoints (departments, etc.)."""

    model_config = ConfigDict(extra="ignore")

    search: Optional[str] = None
    distinct: bool = False
    limit: int = 25
    offset: int = 0
    ordering: Optional[str] = None

    @field_validator("distinct", mode="before")
    @classmethod
    def _normalize_distinct(cls, value):
        """Avoid validation errors for unconventional truthy/falsey values."""
        return ContactFilterParams._coerce_bool(value, default=False)


class CountParams(BaseModel):
    """Parameters for count aggregation requests."""

    search: Optional[str] = None
    distinct: bool = False

