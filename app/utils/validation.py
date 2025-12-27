"""Validation utility functions for input validation with helpful error messages."""

import uuid
from typing import Optional


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID format.
    
    Args:
        value: String to validate as UUID
        
    Returns:
        True if value is a valid UUID format, False otherwise
    """
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_email_format(email: str) -> str:
    """Validate email format with helpful error.
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValueError: If email format is invalid
    """
    if "@" not in email:
        raise ValueError("Email must contain @ symbol")
    if "." not in email.split("@")[1]:
        raise ValueError("Email domain must contain a dot (e.g., example.com)")
    return email


def validate_string_length(
    value: str, 
    min_length: Optional[int] = None, 
    max_length: Optional[int] = None,
    field_name: str = "field"
) -> str:
    """Validate string length with helpful messages.
    
    Args:
        value: String value to validate
        min_length: Minimum required length
        max_length: Maximum allowed length
        field_name: Name of the field being validated (for error messages)
        
    Returns:
        Validated string value
        
    Raises:
        ValueError: If string length validation fails
    """
    if min_length is not None and len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")
    return value


def validate_integer_range(
    value: int,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    field_name: str = "field"
) -> int:
    """Validate integer is within a range with helpful messages.
    
    Args:
        value: Integer value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Name of the field being validated (for error messages)
        
    Returns:
        Validated integer value
        
    Raises:
        ValueError: If integer is outside the allowed range
    """
    if min_value is not None and value < min_value:
        raise ValueError(f"{field_name} must be at least {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name} must not exceed {max_value}")
    return value


def validate_enum_value(
    value: str,
    allowed_values: list[str],
    field_name: str = "field"
) -> str:
    """Validate that a value is one of the allowed enum values.
    
    Args:
        value: Value to validate
        allowed_values: List of allowed values
        field_name: Name of the field being validated (for error messages)
        
    Returns:
        Validated value
        
    Raises:
        ValueError: If value is not in allowed_values
    """
    if value not in allowed_values:
        allowed_str = ", ".join(allowed_values)
        raise ValueError(f"{field_name} must be one of: {allowed_str}")
    return value
