"""
Company Name Cleaning and Validation Utilities

This module provides functions to clean, validate, and normalize company names.
It handles encoding issues, removes invalid patterns, and preserves legitimate
company name formats including international characters.
"""

import re
from typing import Optional

from app.utils.logger import get_logger
from app.utils.text_normalization import (
    contains_letters,
    fix_encoding_issues,
    normalize_unicode,
    normalize_whitespace,
    remove_emojis,
    remove_wrapping_quotes,
)

logger = get_logger(__name__)

# Configuration constants
MIN_COMPANY_NAME_LENGTH = 2
ALLOW_SINGLE_LETTER = False
ALLOW_NUMBERS_ONLY = False
REMOVE_EMOJIS = True
FIX_ENCODING = True

# Placeholder patterns that indicate invalid names
PLACEHOLDER_PATTERNS = [
    r'^_+$',  # Only underscores
    r'^\.+$',  # Only dots
    r'^,+$',  # Only commas
    r'^\-+$',  # Only hyphens
    r'^=+$',  # Only equals
    r'^\*+$',  # Only asterisks
    r'^#+$',  # Only hash
    r'^/+$',  # Only slashes
    r'^\\+$',  # Only backslashes
    r'^\?+$',  # Only question marks
    r'^!+$',  # Only exclamation marks
    r'^~+$',  # Only tildes
]

# Patterns that indicate encoding corruption
ENCODING_CORRUPTION_PATTERNS = [
    r'^\?+$',  # Only question marks (common encoding replacement)
    r'^\uFFFD+$',  # Replacement character
    r'^\?+\s+\?+$',  # Question marks with spaces
]




def is_placeholder_pattern(text: str) -> bool:
    """
    Check if text matches placeholder patterns (like "___", "...", etc.).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a placeholder pattern
    """
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


def has_encoding_corruption(text: str) -> bool:
    """
    Check if text shows signs of encoding corruption.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to have encoding corruption
    """
    for pattern in ENCODING_CORRUPTION_PATTERNS:
        if re.match(pattern, text):
            return True
    
    # Check for replacement characters
    if '' in text:
        return True
    
    return False




def is_valid_company_name(name: Optional[str]) -> bool:
    """
    Validate if a company name is valid.
    
    Validation rules:
    - Must not be None or empty
    - Must meet minimum length requirement
    - Must contain at least one letter (unless ALLOW_NUMBERS_ONLY is True)
    - Cannot be only special characters
    - Cannot be a placeholder pattern
    - Cannot show encoding corruption
    
    Args:
        name: Company name to validate
        
    Returns:
        True if name is valid, False otherwise
    """
    if name is None:
        return False
    
    # Convert to string if not already
    if not isinstance(name, str):
        name = str(name)
    
    # Strip whitespace for validation
    name = name.strip()
    
    # Empty after stripping
    if not name:
        return False
    
    # Check minimum length
    if len(name) < MIN_COMPANY_NAME_LENGTH:
        if not ALLOW_SINGLE_LETTER or len(name) < 1:
            return False
    
    # Check for placeholder patterns
    if is_placeholder_pattern(name):
        return False
    
    # Check for encoding corruption
    if FIX_ENCODING and has_encoding_corruption(name):
        return False
    
    # Must contain at least one letter (unless numbers only is allowed)
    if not ALLOW_NUMBERS_ONLY:
        if not contains_letters(name):
            return False
    
    # Check if it's only special characters (after removing spaces)
    name_no_spaces = name.replace(' ', '')
    if name_no_spaces:
        # Count alphanumeric characters (including international characters)
        # Use Unicode letter and number categories
        alnum_count = len(re.findall(r'[a-zA-Z0-9\u0080-\uFFFF]', name_no_spaces))
        if alnum_count == 0:
            return False
    
    return True


def clean_company_name(name: Optional[str]) -> Optional[str]:
    """
    Clean and validate a company name.
    
    Cleaning steps:
    1. Handle None/empty input
    2. Convert to string
    3. Strip whitespace
    4. Remove wrapping quotes
    5. Normalize whitespace
    6. Fix encoding issues
    7. Remove emojis
    8. Normalize Unicode
    9. Validate result
    
    Args:
        name: Company name to clean
        
    Returns:
        Cleaned company name, or None if invalid
    """
    # Handle None input
    if name is None:
        return None
    
    # Convert to string if not already
    if not isinstance(name, str):
        name = str(name)
    
    # Strip whitespace
    name = name.strip()
    
    # Empty after stripping
    if not name:
        return None
    
    # Remove wrapping quotes
    name = remove_wrapping_quotes(name)
    
    # Normalize whitespace
    name = normalize_whitespace(name)
    
    # Empty after cleaning
    if not name:
        return None
    
    # Fix encoding issues
    if FIX_ENCODING:
        name = fix_encoding_issues(name)
        if not name:
            return None
    
    # Remove emojis
    if REMOVE_EMOJIS:
        name = remove_emojis(name)
        name = normalize_whitespace(name)  # Re-normalize after emoji removal
        if not name:
            return None
    
    # Normalize Unicode
    name = normalize_unicode(name)
    name = normalize_whitespace(name)  # Re-normalize after Unicode normalization
    if not name:
        return None
    
    # Validate the cleaned name
    if not is_valid_company_name(name):
        return None
    
    return name

