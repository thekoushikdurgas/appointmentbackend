"""Validation utilities for common data types."""

from uuid import UUID


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Validate if a string is a valid UUID format.
    
    Args:
        uuid_string: String to validate as UUID
        
    Returns:
        True if the string is a valid UUID format, False otherwise
        
    Example:
        >>> is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_valid_uuid("invalid-uuid")
        False
        >>> is_valid_uuid("")
        False
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

