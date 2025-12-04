"""
Shared normalization utilities for service layer.

This module provides common text normalization functions used across
contacts, companies, and LinkedIn services to eliminate code duplication.

This module focuses on service-layer normalization:
- Handling None/empty values
- Removing placeholder values
- Cleaning wrapping quotes from CSV exports
- Phone number prefix normalization
- Sequence normalization for lists/arrays

Used by:
- contacts_service.py
- companies_service.py
- linkedin_service.py

Note: For Unicode/text cleaning (emojis, encoding issues, etc.), see
text_normalization.py which is used by utility modules like title_utils.py,
company_name_utils.py, and keyword_utils.py.
"""

from typing import Any, Iterable, Optional

# Placeholder value used in the system
PLACEHOLDER_VALUE = "_"


def normalize_text(value: Any, *, allow_placeholder: bool = False) -> Optional[str]:
    """
    Coerce raw string-like values to cleaned text or None.
    
    This function handles:
    - None values
    - Empty strings
    - Placeholder values (unless allow_placeholder=True)
    - Wrapping quotes from CSV exports (e.g., "'+123", '"value"')
    - Phone number prefixes like "'+"
    
    Args:
        value: Raw value to normalize (can be any type)
        allow_placeholder: If True, allow PLACEHOLDER_VALUE to pass through
        
    Returns:
        Normalized text string or None if value is empty/invalid
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not allow_placeholder and text == PLACEHOLDER_VALUE:
        return None

    # Remove wrapping quotes that leak from CSV exports (e.g., "'+123", '"value"').
    while len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
        if not text:
            return None
        if not allow_placeholder and text == PLACEHOLDER_VALUE:
            return None

    if text.startswith("'+") and len(text) > 2:
        text = text[1:].strip()

    if not text:
        return None
    if not allow_placeholder and text == PLACEHOLDER_VALUE:
        return None
    return text


def normalize_sequence(values: Optional[Iterable[Any]], *, allow_placeholder: bool = False) -> list[str]:
    """
    Clean an iterable of values, returning only meaningful text tokens.
    
    This function processes a sequence of values, normalizing each one
    and filtering out empty/invalid values.
    
    Args:
        values: Iterable of values to normalize
        allow_placeholder: If True, allow PLACEHOLDER_VALUE to pass through
        
    Returns:
        List of normalized text strings (empty list if no valid values)
    """
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        normalized = normalize_text(value, allow_placeholder=allow_placeholder)
        if normalized:
            cleaned.append(normalized)
    return cleaned


def coalesce_text(*values: Any, allow_placeholder: bool = False) -> Optional[str]:
    """
    Return the first non-empty normalized text value from the provided options.
    
    This function is useful for selecting the first valid value from multiple
    potential sources (e.g., primary vs. secondary email, name fields, etc.).
    
    Args:
        *values: Variable number of values to check
        allow_placeholder: If True, allow PLACEHOLDER_VALUE to pass through
        
    Returns:
        First normalized non-empty text value, or None if all are empty/invalid
    """
    for value in values:
        normalized = normalize_text(value, allow_placeholder=allow_placeholder)
        if normalized is not None:
            return normalized
    return None

