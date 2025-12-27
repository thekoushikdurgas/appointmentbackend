"""Pydantic schemas for email finder operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailResult(BaseModel):
    """Email result with full contact and company context."""

    email: str = Field(..., description="Email address from Contact.email")
    contact: ContactDB
    metadata: Optional[ContactMetadataOut] = None
    company: Optional[CompanyDB] = None
    company_metadata: Optional[CompanyMetadataOut] = None

    model_config = ConfigDict(from_attributes=True)


class EmailFinderResponse(BaseModel):
    """Response schema for email finder search results."""

    emails: list[EmailResult] = Field(default_factory=list, description="List of found emails with context")
    total: int = Field(0, description="Total number of emails found")


class SimpleEmailResult(BaseModel):
    """Simple email result with only uuid and email."""

    uuid: str = Field(..., description="Contact UUID")
    email: str = Field(..., description="Email address from Contact.email")

    model_config = ConfigDict(from_attributes=True)


class SimpleEmailFinderResponse(BaseModel):
    """Simple response schema for email finder search results."""

    emails: list[SimpleEmailResult] = Field(default_factory=list, description="List of found emails with uuid and email")
    total: int = Field(0, description="Total number of emails found")


class EmailProvider(str, Enum):
    BULKMAILVERIFIER = "bulkmailverifier"
    TRUELIST = "truelist"


class EmailVerifierRequest(BaseModel):
    """Request schema for email verifier endpoint."""

    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    domain: Optional[str] = Field(None, description="Company domain or website URL (can use website parameter instead)")
    website: Optional[str] = Field(None, description="Company website URL (alias for domain parameter)")
    provider: EmailProvider = Field(..., description="Email verification provider to use")
    email_count: Optional[int] = Field(
        1000,
        description="Number of random email combinations to generate per batch (default: 1000, minimum: 1, no upper limit). All unique patterns will be checked once, processed in batches of this size.",
        ge=1,
    )

    @field_validator("email_count")
    @classmethod
    def validate_email_count(cls, v: Optional[int]) -> int:
        """Validate email_count is at least 1."""
        if v is None:
            return 1000
        if v < 1:
            raise ValueError("email_count must be at least 1")
        return v

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EmailVerificationStatus(str, Enum):
    """Enumeration of email verification statuses."""

    VALID = "valid"
    INVALID = "invalid"
    CATCHALL = "catchall"
    UNKNOWN = "unknown"


class EmailVerifierResponse(BaseModel):
    """Response schema for email verifier endpoint."""

    valid_emails: list[str] = Field(
        default_factory=list,
        description="List of verified valid email addresses",
    )
    total_valid: int = Field(0, description="Total number of valid emails found")
    # First email found with status (valid, catchall, or risky)
    first_email: Optional[str] = Field(
        None,
        description="First email found with status valid, catchall, or risky",
    )
    first_email_status: Optional["EmailVerificationStatus"] = Field(
        None,
        description="Status of the first email found (valid, catchall, or unknown for risky)",
    )
    generated_emails: list[str] = Field(
        default_factory=list,
        description="List of all generated email addresses (for reference)",
    )
    total_generated: int = Field(0, description="Total number of emails generated")
    total_batches_processed: int = Field(0, description="Total number of batches processed")

    model_config = ConfigDict(from_attributes=True)


class VerifiedEmailResult(BaseModel):
    """Result for a single verified email with its status."""

    email: str = Field(..., description="Email address that was verified")
    status: EmailVerificationStatus = Field(..., description="Verification status of the email")
    # Truelist-specific fields (optional, only present when using Truelist provider)
    email_state: Optional[str] = Field(None, description="Truelist email_state (e.g., 'ok', 'risky', 'invalid')")
    email_sub_state: Optional[str] = Field(None, description="Truelist email_sub_state (e.g., 'accept_all', 'disposable', 'role')")
    domain: Optional[str] = Field(None, description="Domain extracted from email (Truelist)")
    canonical: Optional[str] = Field(None, description="Canonical email format (Truelist)")
    mx_record: Optional[str] = Field(None, description="MX record information (Truelist)")
    verified_at: Optional[str] = Field(None, description="Timestamp when email was verified (Truelist)")
    did_you_mean: Optional[str] = Field(None, description="Suggested email correction (Truelist)")

    # IcyPeas-specific fields (optional)
    certainty: Optional[str] = Field(
        None,
        description="IcyPeas certainty level (ultra_sure, sure, probable)",
    )
    mx_provider: Optional[str] = Field(
        None,
        description="MX provider from IcyPeas results",
    )
    fallback_source: Optional[str] = Field(
        None,
        description="Fallback source used (e.g., 'icypeas', 'truelist_catchall')",
    )

    model_config = ConfigDict(from_attributes=True)


class BulkEmailVerifierRequest(BaseModel):
    """Request schema for bulk email verifier endpoint."""

    provider: EmailProvider = Field(..., description="Email verification provider to use")
    emails: list[str] = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="List of email addresses to verify (minimum: 1, maximum: 10000)",
    )

    # Optional column mapping metadata from the original CSV file
    mapping: Optional[dict] = Field(
        default=None,
        description=(
            "Optional mapping metadata describing how the original CSV columns "
            "map to the normalized email field."
        ),
    )

    # Extended CSV context and field mappings
    raw_headers: Optional[list[str]] = Field(
        default=None,
        description="Optional ordered list of all CSV headers from the original file.",
    )
    rows: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Optional raw rows from the CSV, keyed by header name. "
            "If provided, len(rows) must equal len(emails) or emails will be extracted from rows."
        ),
    )
    email_column: Optional[str] = Field(
        default=None,
        description=(
            "Explicit column name containing email addresses. "
            "If not provided, will auto-detect from raw_headers."
        ),
    )

    @field_validator("emails")
    @classmethod
    def validate_emails(cls, v: list[str]) -> list[str]:
        """Validate email list is not empty and contains valid email formats."""
        if not v:
            raise ValueError("emails list cannot be empty")
        if len(v) > 10000:
            raise ValueError("emails list cannot exceed 10000 emails")
        # Basic email format validation
        for email in v:
            if not email or not isinstance(email, str):
                raise ValueError(f"Invalid email in list: {email}")
            email = email.strip()
            if not email or "@" not in email:
                raise ValueError(f"Invalid email format: {email}")
        return [email.strip().lower() for email in v if email.strip()]

    @model_validator(mode="after")
    def validate_csv_context(self) -> "BulkEmailVerifierRequest":
        """Validate consistency between emails, rows, and headers."""
        if self.rows is not None and self.raw_headers is not None:
            header_set = set(self.raw_headers)
            # Ensure all row keys are known headers
            for row in self.rows:
                unknown_keys = set(row.keys()) - header_set
                if unknown_keys:
                    raise ValueError(
                        f"rows contain keys not present in raw_headers: {sorted(unknown_keys)}"
                    )

            # Validate email_column if provided
            if self.email_column is not None and self.email_column not in header_set:
                raise ValueError(
                    f"email_column '{self.email_column}' not found in raw_headers"
                )

        return self

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SingleEmailVerifierRequest(BaseModel):
    """Request schema for single email verifier endpoint."""

    email: EmailStr = Field(..., description="Email address to verify")
    provider: EmailProvider = Field(..., description="Email verification provider to use")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class BulkEmailVerifierResponse(BaseModel):
    """Response schema for bulk email verifier endpoint."""

    results: list[VerifiedEmailResult] = Field(
        default_factory=list,
        description="List of verification results for each email",
    )
    total: int = Field(0, description="Total number of emails verified")
    valid_count: int = Field(0, description="Number of valid emails")
    invalid_count: int = Field(0, description="Number of invalid emails")
    catchall_count: int = Field(0, description="Number of catchall emails")
    unknown_count: int = Field(0, description="Number of unknown emails")
    download_url: Optional[str] = Field(
        default=None,
        description="Signed URL for downloading CSV file with verification results. Only present when CSV context provided.",
    )
    export_id: Optional[str] = Field(
        default=None,
        description="Export ID for tracking CSV file. Only present when CSV context provided.",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the download URL expires. Only present when CSV context provided.",
    )

    model_config = ConfigDict(from_attributes=True)


class SingleEmailVerifierResponse(BaseModel):
    """Response schema for single email verifier endpoint."""

    result: VerifiedEmailResult = Field(..., description="Verification result for the email")

    model_config = ConfigDict(from_attributes=True)


class SingleEmailVerifierFindResponse(BaseModel):
    """Response schema for single email verifier find endpoint."""

    valid_email: Optional[str] = Field(
        None,
        description="The first email address found (valid, catchall, or risky), or None if none found",
    )
    status: Optional["EmailVerificationStatus"] = Field(
        None,
        description="Status of the first email found (valid, catchall, or unknown for risky)",
    )

    model_config = ConfigDict(from_attributes=True)


class EmailExportContact(BaseModel):
    """Schema for a single contact in email export request."""

    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    domain: Optional[str] = Field(None, description="Company domain or website URL (can use website parameter instead)")
    website: Optional[str] = Field(None, description="Company website URL (alias for domain parameter)")
    email: Optional[str] = Field(
        None,
        description="Optional existing email from the source data. "
        "When provided, the system will attempt to verify and reuse it before generating new emails.",
    )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate and normalize name fields."""
        if not v or not isinstance(v, str):
            raise ValueError("Name fields must be non-empty strings")
        return v.strip()

    @field_validator("domain", "website")
    @classmethod
    def validate_domain_or_website(cls, v: Optional[str]) -> Optional[str]:
        """Normalize domain/website fields."""
        return v.strip() if v and isinstance(v, str) else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email field (trim whitespace)."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("email must be a string when provided")
        return v.strip() or None

    @model_validator(mode="after")
    def validate_domain_or_website_provided(self):
        """Validate that at least domain or website is provided."""
        if not self.domain and not self.website:
            raise ValueError("Either domain or website must be provided")
        return self

    model_config = ConfigDict(from_attributes=True)


class EmailExportRequest(BaseModel):
    """Request schema for email export endpoint."""

    contacts: list[EmailExportContact] = Field(
        ...,
        min_length=1,
        description="List of contacts to export (minimum: 1)",
    )

    # Optional column mapping metadata from the original CSV file
    mapping: Optional[dict] = Field(
        default=None,
        description=(
            "Optional mapping metadata describing how the original CSV columns "
            "map to the normalized contact fields (first_name, last_name, domain, website, email)."
        ),
    )

    # Extended CSV context and field mappings
    raw_headers: Optional[list[str]] = Field(
        default=None,
        description="Optional ordered list of all CSV headers from the original file.",
    )
    rows: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Optional raw rows from the CSV, keyed by header name. "
            "If provided, len(rows) must equal len(contacts)."
        ),
    )
    contact_field_mappings: Optional[dict[str, Optional[str]]] = Field(
        default=None,
        description=(
            "Optional mapping from logical contact fields (e.g. title, departments, mobile_phone) "
            "to CSV column names."
        ),
    )
    company_field_mappings: Optional[dict[str, Optional[str]]] = Field(
        default=None,
        description=(
            "Optional mapping from logical company fields (e.g. company_name, employees_count, "
            "industry, keywords) to CSV column names."
        ),
    )

    @field_validator("contacts")
    @classmethod
    def validate_contacts(cls, v: list[EmailExportContact]) -> list[EmailExportContact]:
        """Validate contacts list is not empty."""
        if not v:
            raise ValueError("contacts list cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_csv_context(self) -> "EmailExportRequest":
        """Validate consistency between contacts, rows, and headers."""
        if self.rows is not None and len(self.rows) != len(self.contacts):
            raise ValueError("rows length must match contacts length when provided")

        if self.raw_headers is not None:
            header_set = set(self.raw_headers)
            # Ensure all row keys are known headers
            if self.rows is not None:
                for row in self.rows:
                    unknown_keys = set(row.keys()) - header_set
                    if unknown_keys:
                        raise ValueError(
                            f"rows contain keys not present in raw_headers: {sorted(unknown_keys)}"
                        )

            # Ensure field mapping values reference known headers
            for mapping in (self.contact_field_mappings, self.company_field_mappings):
                if mapping:
                    invalid = {
                        col_name
                        for col_name in mapping.values()
                        if col_name is not None and col_name not in header_set
                    }
                    if invalid:
                        raise ValueError(
                            f"field mappings reference columns not present in raw_headers: {sorted(invalid)}"
                        )

        return self

    model_config = ConfigDict(from_attributes=True)


class SingleEmailRequest(BaseModel):
    """Request schema for single email endpoint."""

    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    domain: Optional[str] = Field(None, description="Company domain or website URL (can use website parameter instead)")
    website: Optional[str] = Field(None, description="Company website URL (alias for domain parameter)")
    provider: EmailProvider = Field(..., description="Email verification provider to use")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate and normalize name fields (trim + lowercase)."""
        if not v or not isinstance(v, str):
            raise ValueError("Name fields must be non-empty strings")
        return v.strip().lower()

    @field_validator("domain", "website")
    @classmethod
    def validate_domain_or_website(cls, v: Optional[str]) -> Optional[str]:
        """Normalize domain/website fields (trim + lowercase)."""
        return v.strip().lower() if v and isinstance(v, str) else None

    @model_validator(mode="after")
    def validate_domain_or_website_provided(self):
        """Validate that at least domain or website is provided."""
        if not self.domain and not self.website:
            raise ValueError("Either domain or website must be provided")
        return self

    model_config = ConfigDict(from_attributes=True)


class SingleEmailResponse(BaseModel):
    """Response schema for single email endpoint."""

    email: Optional[str] = Field(
        None,
        description="The email address found, or None if no email was found",
    )
    source: Optional[str] = Field(
        None,
        description="Source of the email: 'finder' (database), 'verifier' (email verification), 'cache', 'pattern_fallback', or None if not found",
    )
    status: Optional[EmailVerificationStatus] = Field(
        None,
        description="Verification status of the email when found via verifier (valid, catchall, or unknown for risky). Only present when source is 'verifier'.",
    )

    # IcyPeas-specific fields (optional)
    certainty: Optional[str] = Field(
        None,
        description="Email certainty level when found via IcyPeas (ultra_sure, sure, probable)",
    )

    model_config = ConfigDict(from_attributes=True)

