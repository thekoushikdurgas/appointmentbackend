"""
Keyword Cleaning and Validation Utilities

This module provides functions to clean, validate, and normalize keywords.
Keywords have different validation rules than company names - they can be shorter
and more varied, but should still filter out invalid patterns.
"""

import re
from typing import List, Optional

from app.utils.logger import get_logger
from app.utils.text_normalization import (
    contains_letters,
    normalize_whitespace,
    remove_wrapping_quotes,
)

logger = get_logger(__name__)

# Configuration constants
MIN_KEYWORD_LENGTH = 1  # Keywords can be shorter than company names
ALLOW_NUMBERS_ONLY = False  # Keywords that are only numbers are usually invalid
REMOVE_ENCODING_CORRUPTION = True

# Placeholder patterns that indicate invalid keywords
KEYWORD_PLACEHOLDER_PATTERNS = [
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
    r'^0+$',  # Only zeros
    r'^00+$',  # Multiple zeros
]

# Patterns that indicate encoding corruption
KEYWORD_ENCODING_CORRUPTION_PATTERNS = [
    r'^\?+$',  # Only question marks (common encoding replacement)
    r'^\uFFFD+$',  # Replacement character
    r'^\?+\s+\?+$',  # Question marks with spaces
]


def is_keyword_placeholder_pattern(text: str) -> bool:
    """
    Check if text matches placeholder patterns (like "___", "...", "000", etc.).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a placeholder pattern
    """
    for pattern in KEYWORD_PLACEHOLDER_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


def has_keyword_encoding_corruption(text: str) -> bool:
    """
    Check if text shows signs of encoding corruption.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to have encoding corruption
    """
    if not REMOVE_ENCODING_CORRUPTION:
        return False
    
    for pattern in KEYWORD_ENCODING_CORRUPTION_PATTERNS:
        if re.match(pattern, text):
            return True
    
    # Check for replacement characters
    if '' in text:
        return True
    
    return False






def is_valid_keyword(keyword: Optional[str]) -> bool:
    """
    Validate if a keyword is valid.
    
    Validation rules:
    - Must not be None or empty
    - Must meet minimum length requirement
    - Must contain at least one letter (unless ALLOW_NUMBERS_ONLY is True)
    - Cannot be only special characters
    - Cannot be a placeholder pattern
    - Cannot show encoding corruption
    
    Args:
        keyword: Keyword to validate
        
    Returns:
        True if keyword is valid, False otherwise
    """
    if keyword is None:
        return False
    
    # Convert to string if not already
    if not isinstance(keyword, str):
        keyword = str(keyword)
    
    # Strip whitespace for validation
    keyword = keyword.strip()
    
    # Empty after stripping
    if not keyword:
        return False
    
    # Check minimum length
    if len(keyword) < MIN_KEYWORD_LENGTH:
        return False
    
    # Check for placeholder patterns
    if is_keyword_placeholder_pattern(keyword):
        return False
    
    # Check for encoding corruption
    if has_keyword_encoding_corruption(keyword):
        return False
    
    # Must contain at least one letter (unless numbers only is allowed)
    if not ALLOW_NUMBERS_ONLY:
        if not contains_letters(keyword):
            return False
    
    # Check if it's only special characters (after removing spaces)
    keyword_no_spaces = keyword.replace(' ', '')
    if keyword_no_spaces:
        # Count alphanumeric characters (including international characters)
        alnum_count = len(re.findall(r'[a-zA-Z0-9\u0080-\uFFFF]', keyword_no_spaces))
        if alnum_count == 0:
            return False
    
    return True


def clean_keyword(keyword: Optional[str]) -> Optional[str]:
    """
    Clean and validate a keyword.
    
    Cleaning steps:
    1. Handle None/empty input
    2. Convert to string
    3. Strip whitespace
    4. Remove wrapping quotes
    5. Normalize whitespace
    6. Fix encoding issues
    7. Validate result
    
    Args:
        keyword: Keyword to clean
        
    Returns:
        Cleaned keyword, or None if invalid
    """
    # Handle None input
    if keyword is None:
        return None
    
    # Convert to string if not already
    if not isinstance(keyword, str):
        keyword = str(keyword)
    
    # Strip whitespace
    keyword = keyword.strip()
    
    # Empty after stripping
    if not keyword:
        return None
    
    # Remove wrapping quotes
    keyword = remove_wrapping_quotes(keyword)
    
    # Normalize whitespace
    keyword = normalize_whitespace(keyword)
    
    # Empty after cleaning
    if not keyword:
        return None
    
    # Fix encoding issues - remove replacement characters
    if REMOVE_ENCODING_CORRUPTION:
        keyword = keyword.replace('', '')
        if not keyword:
            return None
    
    # Validate the cleaned keyword
    if not is_valid_keyword(keyword):
        return None
    
    return keyword


def clean_keyword_array(keywords: Optional[List[str]]) -> Optional[List[str]]:
    """
    Clean an array of keywords by cleaning each element.
    
    Args:
        keywords: List of keywords to clean
        
    Returns:
        Cleaned list or None if all elements are None/empty
    """
    if keywords is None:
        return None
    
    if not isinstance(keywords, list):
        return None
    
    cleaned_list = []
    for keyword in keywords:
        cleaned_keyword = clean_keyword(keyword)
        if cleaned_keyword is not None:
            cleaned_list.append(cleaned_keyword)
    
    # Return None if list is empty after cleaning
    if len(cleaned_list) == 0:
        return None
    
    return cleaned_list

