"""
Title Cleaning and Validation Utilities

This module provides functions to clean, validate, and normalize contact titles.
Titles have different validation rules than company names - they can be shorter
and more varied, but should still filter out invalid patterns.
"""

import re
from typing import Optional

from app.utils.logger import get_logger
from app.utils.text_normalization import (
    contains_letters,
    normalize_unicode,
    normalize_whitespace,
    remove_emojis,
    remove_wrapping_quotes,
)

logger = get_logger(__name__)

# Configuration constants
MIN_TITLE_LENGTH = 1  # Titles can be very short (even single word)
ALLOW_NUMBERS_ONLY = False  # Titles that are only numbers are usually invalid
REMOVE_EMOJIS = True
FIX_ENCODING = True
NORMALIZE_UNICODE = True

# Placeholder patterns that indicate invalid titles
TITLE_PLACEHOLDER_PATTERNS = [
    r'^_+$',  # Only underscores
    r'^\.+$',  # Only dots
    r'^,+$',  # Only commas
    r'^\-+$',  # Only hyphens
    r'^=+$',  # Only equals
    r'^\*+$',  # Only asterisks
    r'^#+$',  # Only hash
    r'^/+$',  # Only slashes
    r'^\\+$',  # Only backslashes
    r'^!+$',  # Only exclamation marks
    r'^~+$',  # Only tildes
    r'^0+$',  # Only zeros
    r'^00+$',  # Multiple zeros
    r'^000+$',  # Many zeros
]

# Patterns that indicate encoding corruption
TITLE_ENCODING_CORRUPTION_PATTERNS = [
    r'^\?+$',  # Only question marks (common encoding replacement)
    r'^\uFFFD+$',  # Replacement character
    r'^\?+\s+\?+$',  # Question marks with spaces
    r'^\\_\(.+\)_/',  # Escaped ASCII art patterns like "\\_(ツ)_/"
    r'^¯\\_\(.+\)_/¯',  # ASCII art patterns like "¯\\_(ツ)_/¯"
]

# ASCII art patterns that should be removed
ASCII_ART_PATTERNS = [
    r'^¯\\_\(.+\)_/¯',  # "¯\\_(ツ)_/¯"
    r'^\\_\(.+\)_/',  # "\\_(ツ)_/"
    r'^ᕕ\(.+\)ᕗ',  # "ᕕ( ᐛ )ᕗ"
    r'^∈\(.+\)∋',  # "∈(ﾟ◎ﾟ)∋✨🌏🔗"
]




def remove_ascii_art(text: str) -> str:
    """
    Remove ASCII art patterns from text.
    
    Args:
        text: Input text potentially containing ASCII art
        
    Returns:
        Text with ASCII art removed
    """
    # Check if entire text matches ASCII art patterns
    for pattern in ASCII_ART_PATTERNS:
        if re.match(pattern, text):
            return ''  # Entire text is ASCII art, remove it
    
    # If text contains ASCII art but also has other content, be more careful
    # Only remove if it's clearly just ASCII art
    if re.match(r'^[¯_\\/()ツᕕᕗ∈∋\s]+$', text):
        return ''  # Only ASCII art characters and whitespace
    
    return text




def is_title_placeholder_pattern(text: str) -> bool:
    """
    Check if text matches placeholder patterns (like "___", "...", "000", etc.).
    
    Args:
        text: Text to check
        
    Returns:
        True if text matches a placeholder pattern
    """
    for pattern in TITLE_PLACEHOLDER_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


def has_title_encoding_corruption(text: str) -> bool:
    """
    Check if text shows signs of encoding corruption.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to have encoding corruption
    """
    if not FIX_ENCODING:
        return False
    
    for pattern in TITLE_ENCODING_CORRUPTION_PATTERNS:
        if re.match(pattern, text):
            return True
    
    # Check for replacement characters
    if '' in text:
        return True
    
    return False




def is_valid_title(title: Optional[str]) -> bool:
    """
    Validate if a title is valid.
    
    Validation rules:
    - Must not be None or empty
    - Must meet minimum length requirement
    - Must contain at least one letter (unless ALLOW_NUMBERS_ONLY is True)
    - Cannot be only special characters
    - Cannot be a placeholder pattern
    - Cannot show encoding corruption
    
    Args:
        title: Title to validate
        
    Returns:
        True if title is valid, False otherwise
    """
    if title is None:
        return False
    
    # Convert to string if not already
    if not isinstance(title, str):
        title = str(title)
    
    # Strip whitespace for validation
    title = title.strip()
    
    # Empty after stripping
    if not title:
        return False
    
    # Check minimum length
    if len(title) < MIN_TITLE_LENGTH:
        return False
    
    # Check for placeholder patterns
    if is_title_placeholder_pattern(title):
        return False
    
    # Check for encoding corruption
    if has_title_encoding_corruption(title):
        return False
    
    # Must contain at least one letter (unless numbers only is allowed)
    if not ALLOW_NUMBERS_ONLY:
        if not contains_letters(title):
            return False
    
    # Check if it's only special characters (after removing spaces)
    title_no_spaces = title.replace(' ', '')
    if title_no_spaces:
        # Count alphanumeric characters (including international characters)
        alnum_count = len(re.findall(r'[a-zA-Z0-9\u0080-\uFFFF]', title_no_spaces))
        if alnum_count == 0:
            return False
    
    return True


def clean_title(title: Optional[str]) -> Optional[str]:
    """
    Clean and validate a contact title.
    
    Cleaning steps:
    1. Handle None/empty input
    2. Convert to string
    3. Strip whitespace
    4. Remove wrapping quotes
    5. Remove ASCII art patterns
    6. Normalize whitespace
    7. Fix encoding issues
    8. Remove emojis
    9. Normalize Unicode
    10. Validate result
    
    Args:
        title: Title to clean
        
    Returns:
        Cleaned title, or None if invalid
    """
    # Handle None input
    if title is None:
        return None
    
    # Convert to string if not already
    if not isinstance(title, str):
        title = str(title)
    
    # Strip whitespace
    title = title.strip()
    
    # Empty after stripping
    if not title:
        return None
    
    # Remove wrapping quotes
    title = remove_wrapping_quotes(title)
    
    # Remove ASCII art patterns
    title = remove_ascii_art(title)
    title = normalize_whitespace(title)  # Re-normalize after ASCII art removal
    
    # Empty after cleaning
    if not title:
        return None
    
    # Normalize whitespace
    title = normalize_whitespace(title)
    
    # Empty after cleaning
    if not title:
        return None
    
    # Fix encoding issues - remove replacement characters
    if FIX_ENCODING:
        title = title.replace('', '')
        if not title:
            return None
    
    # Remove emojis
    if REMOVE_EMOJIS:
        title = remove_emojis(title)
        title = normalize_whitespace(title)  # Re-normalize after emoji removal
        if not title:
            return None
    
    # Normalize Unicode
    if NORMALIZE_UNICODE:
        title = normalize_unicode(title)
        title = normalize_whitespace(title)  # Re-normalize after Unicode normalization
        if not title:
            return None
    
    # Validate the cleaned title
    if not is_valid_title(title):
        return None
    
    return title

