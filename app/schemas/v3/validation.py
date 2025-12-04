"""Validation schemas for v3 API."""

from typing import List

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """A validation issue found in a field."""

    field: str = Field(..., description="Field name with issue")
    issue: str = Field(..., description="Description of the issue")
    severity: str = Field(..., description="Issue severity: 'error' or 'warning'")


class ContactValidationResult(BaseModel):
    """Validation result for a contact."""

    contact_uuid: str = Field(..., description="Contact UUID")
    is_valid: bool = Field(..., description="Whether contact data is valid")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of validation issues")
    fields_validated: List[str] = Field(default_factory=list, description="List of fields that were validated")


class CompanyValidationResult(BaseModel):
    """Validation result for a company."""

    company_uuid: str = Field(..., description="Company UUID")
    is_valid: bool = Field(..., description="Whether company data is valid")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of validation issues")
    fields_validated: List[str] = Field(default_factory=list, description="List of fields that were validated")


class ValidationResponse(BaseModel):
    """Response for single contact/company validation."""

    validation: ContactValidationResult | CompanyValidationResult


class ValidationBatchRequest(BaseModel):
    """Request for batch validation."""

    uuids: List[str] = Field(..., description="List of UUIDs to validate", min_length=1)


class ValidationBatchResponse(BaseModel):
    """Response for batch validation."""

    total: int = Field(..., description="Total number of records processed")
    validations: List[ContactValidationResult | CompanyValidationResult] = Field(
        ..., description="Validation results for each record"
    )

