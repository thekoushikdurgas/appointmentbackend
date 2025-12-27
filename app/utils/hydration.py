"""Hydration utilities for converting ORM entities to response schemas.

This module provides common helpers for safely accessing attributes from
SQLAlchemy ORM objects and Row objects, which is needed when hydrating
entities into response schemas.

Used by:
- contacts_service.py (_hydrate_contact)
- companies_service.py (_hydrate_company)
- Other services that need to hydrate ORM entities
"""

from __future__ import annotations

from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get attribute from object or SQLAlchemy Row.
    
    SQLAlchemy may return Row objects instead of ORM instances when
    selecting multiple entities. This function handles both cases.
    
    Args:
        obj: Object to get attribute from (ORM instance or Row object)
        attr: Attribute name to access
        default: Default value if attribute not found
    
    Returns:
        Attribute value or default
    
    Example:
        # Works with ORM instances
        name = safe_getattr(contact, "first_name", "Unknown")
        
        # Works with Row objects from select(Contact, Company)
        name = safe_getattr(row, "first_name", "Unknown")
    """
    if obj is None:
        return default
    
    # First, try to detect if it's a SQLAlchemy Row object
    # Row objects have _mapping or _fields attributes
    is_row = (
        hasattr(obj, '_mapping') or 
        hasattr(obj, '_fields') or
        (hasattr(obj, '__class__') and 'Row' in str(type(obj)))
    )
    
    if is_row:
        # It's a Row object - try key access first
        try:
            # Try accessing as a key (Row objects support key access)
            return obj[attr]
        except (KeyError, IndexError, AttributeError, TypeError):
            # If key access fails, try to access via entity name
            # For select(Contact, Company), we might access as Contact.departments
            try:
                # Try accessing via the Contact entity
                if hasattr(obj, 'Contact'):
                    return getattr(obj.Contact, attr, default)
            except (AttributeError, TypeError):
                pass
            return default
    
    # For ORM instances, try attribute access
    # Use getattr with default to avoid raising AttributeError
    # But also catch any exceptions from SQLAlchemy C extensions
    try:
        # Check if attribute exists first
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            return value
        return default
    except AttributeError:
        # AttributeError from SQLAlchemy C extension - try key access
        if hasattr(obj, '__getitem__'):
            try:
                return obj[attr]
            except (KeyError, IndexError, TypeError):
                return default
        return default
    except Exception:
        # Catch any other exceptions (including from SQLAlchemy C extensions)
        return default


def join_sequence(values: Optional[list[str]], separator: str = ", ") -> Optional[str]:
    """
    Join a sequence of strings with a separator, returning None if empty.
    
    Useful for converting list fields (like industries, keywords) into
    comma-separated strings for display.
    
    Args:
        values: List of strings to join
        separator: Separator string (default: ", ")
    
    Returns:
        Joined string or None if values is empty/None
    
    Example:
        industries = ["Tech", "Software"]
        industry_str = join_sequence(industries)  # "Tech, Software"
        empty_str = join_sequence([])  # None
    """
    if not values:
        return None
    return separator.join(values) if values else None

