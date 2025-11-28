"""Pydantic schemas for email finder operations."""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.companies import CompanyDB, CompanyMetadataOut
from app.schemas.contacts import ContactDB
from app.schemas.metadata import ContactMetadataOut


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


class EmailVerifierRequest(BaseModel):
    """Request schema for email verifier endpoint."""

    first_name: str = Field(..., description="Contact first name")
    last_name: str = Field(..., description="Contact last name")
    domain: Optional[str] = Field(None, description="Company domain or website URL (can use website parameter instead)")
    website: Optional[str] = Field(None, description="Company website URL (alias for domain parameter)")
    email_count: Optional[int] = Field(
        1000,
        description="Number of random email combinations to generate per batch (default: 1000, minimum: 1, no upper limit)",
        ge=1,
    )
    max_retries: Optional[int] = Field(
        None,
        description="Maximum number of batches to process if no valid emails found (default: from config, minimum: 1, no upper limit). If not provided, uses BULKMAILVERIFIER_MAX_RETRIES from settings.",
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

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: Optional[int]) -> Optional[int]:
        """Validate max_retries is at least 1."""
        if v is None:
            return None  # Will use default from config
        if v < 1:
            raise ValueError("max_retries must be at least 1")
        return v

    model_config = ConfigDict(from_attributes=True)


class EmailVerifierResponse(BaseModel):
    """Response schema for email verifier endpoint."""

    valid_emails: list[str] = Field(
        default_factory=list,
        description="List of verified valid email addresses",
    )
    total_valid: int = Field(0, description="Total number of valid emails found")
    generated_emails: list[str] = Field(
        default_factory=list,
        description="List of all generated email addresses (for reference)",
    )
    total_generated: int = Field(0, description="Total number of emails generated")
    total_batches_processed: int = Field(0, description="Total number of batches processed")

    model_config = ConfigDict(from_attributes=True)


class EmailVerificationStatus(str, Enum):
    """Enumeration of email verification statuses."""

    VALID = "valid"
    INVALID = "invalid"
    CATCHALL = "catchall"
    UNKNOWN = "unknown"


class VerifiedEmailResult(BaseModel):
    """Result for a single verified email with its status."""

    email: str = Field(..., description="Email address that was verified")
    status: EmailVerificationStatus = Field(..., description="Verification status of the email")

    model_config = ConfigDict(from_attributes=True)


class BulkEmailVerifierRequest(BaseModel):
    """Request schema for bulk email verifier endpoint."""

    emails: list[str] = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="List of email addresses to verify (minimum: 1, maximum: 10000)",
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

    model_config = ConfigDict(from_attributes=True)


class SingleEmailVerifierRequest(BaseModel):
    """Request schema for single email verifier endpoint."""

    email: EmailStr = Field(..., description="Email address to verify")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class SingleEmailVerifierResponse(BaseModel):
    """Response schema for single email verifier endpoint."""

    result: VerifiedEmailResult = Field(..., description="Verification result for the email")

    model_config = ConfigDict(from_attributes=True)


class SingleEmailVerifierFindResponse(BaseModel):
    """Response schema for single email verifier find endpoint."""

    valid_email: Optional[str] = Field(
        None,
        description="The single valid email address found, or None if no valid email was found",
    )

    model_config = ConfigDict(from_attributes=True)


class CreditsResponse(BaseModel):
    """Response schema for check credits endpoint."""

    credits: Optional[Union[int, str]] = Field(None, description="Credits information (may be text or number)")
    raw_response: Optional[str] = Field(None, description="Raw response from API if not JSON")
    # Allow additional fields since the actual response format may vary
    model_config = ConfigDict(extra="allow", from_attributes=True)
    
    @field_validator("credits", mode="before")
    @classmethod
    def normalize_credits(cls, v):
        """Convert credits to string if it's an integer, for consistent output format."""
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v


class EmailListInfo(BaseModel):
    """Schema for individual email list information."""

    slug: str = Field(..., description="Unique identifier for the list")
    status: str = Field(..., description="Verification status (Completed, Verifying, etc.)")
    total_emails: int = Field(..., description="Total number of emails in the list")
    total_verified: int = Field(..., description="Number of verified emails")
    retry: int = Field(0, description="Retry count")
    valid_emails: int = Field(0, description="Number of valid emails")
    invalid_emails: int = Field(0, description="Number of invalid emails")
    catchall_emails: int = Field(0, description="Number of catchall emails")
    unknown_emails: int = Field(0, description="Number of unknown emails")

    model_config = ConfigDict(from_attributes=True)


class AllListsResponse(BaseModel):
    """Response schema for get all lists endpoint."""

    lists: list[EmailListInfo] = Field(
        default_factory=list,
        description="List of all uploaded email lists",
    )

    model_config = ConfigDict(from_attributes=True)

