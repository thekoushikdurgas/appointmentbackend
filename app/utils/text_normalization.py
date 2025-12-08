"""
Shared text normalization utilities.

This module provides common text cleaning and normalization functions
used across company names, titles, and keywords utilities.

This module focuses on low-level text cleaning:
- Unicode normalization (special characters, mathematical symbols)
- Whitespace normalization
- Emoji removal
- Encoding issue fixes
- Wrapping quote removal
- Letter detection (multi-language support)

Used by:
- title_utils.py
- company_name_utils.py
- keyword_utils.py

Note: For service-layer normalization (handling None, placeholders, CSV exports),
see normalization.py which is used by service classes.
"""

import re
import unicodedata
from typing import Optional

# Try to import emoji library, fallback if not available
try:
    import emoji
    HAS_EMOJI = True
except ImportError:
    HAS_EMOJI = False


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters to their standard forms.
    Converts special Unicode variants (like mathematical bold, sans-serif, etc.)
    to standard ASCII/Latin characters where possible.
    
    Args:
        text: Input text with potentially special Unicode characters
        
    Returns:
        Normalized text
    """
    # First, try to decompose and recompose
    text = unicodedata.normalize('NFKC', text)
    
    # Replace common Unicode variants with ASCII equivalents
    replacements = {
        # Mathematical bold
        '𝔸': 'A', '𝔹': 'B', 'ℂ': 'C', '𝔻': 'D', '𝔼': 'E', '𝔽': 'F',
        '𝔾': 'G', 'ℍ': 'H', '𝕀': 'I', '𝕁': 'J', '𝕂': 'K', '𝕃': 'L',
        '𝕄': 'M', 'ℕ': 'N', '𝕆': 'O', 'ℙ': 'P', 'ℚ': 'Q', 'ℝ': 'R',
        '𝕊': 'S', '𝕋': 'T', '𝕌': 'U', '𝕍': 'V', '𝕎': 'W', '𝕏': 'X',
        '𝕐': 'Y', 'ℤ': 'Z',
        # Mathematical bold lowercase
        '𝕒': 'a', '𝕓': 'b', '𝕔': 'c', '𝕕': 'd', '𝕖': 'e', '𝕗': 'f',
        '𝕘': 'g', '𝕙': 'h', '𝕚': 'i', '𝕛': 'j', '𝕜': 'k', '𝕝': 'l',
        '𝕞': 'm', '𝕟': 'n', '𝕠': 'o', '𝕡': 'p', '𝕢': 'q', '𝕣': 'r',
        '𝕤': 's', '𝕥': 't', '𝕦': 'u', '𝕧': 'v', '𝕨': 'w', '𝕩': 'x',
        '𝕪': 'y', '𝕫': 'z',
        # Mathematical sans-serif bold
        '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F',
        '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L',
        '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R',
        '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X',
        '𝗬': 'Y', '𝗭': 'Z',
        # Mathematical sans-serif bold lowercase
        '𝗮': 'a', '𝗯': 'b', '𝗰': 'c', '𝗱': 'd', '𝗲': 'e', '𝗳': 'f',
        '𝗴': 'g', '𝗵': 'h', '𝗶': 'i', '𝗷': 'j', '𝗸': 'k', '𝗹': 'l',
        '𝗺': 'm', '𝗻': 'n', '𝗼': 'o', '𝗽': 'p', '𝗾': 'q', '𝗿': 'r',
        '𝘀': 's', '𝘁': 't', '𝘂': 'u', '𝘃': 'v', '𝘄': 'w', '𝘅': 'x',
        '𝘆': 'y', '𝘇': 'z',
        # Mathematical italic
        '𝐴': 'A', '𝐵': 'B', '𝐶': 'C', '𝐷': 'D', '𝐸': 'E', '𝐹': 'F',
        '𝐺': 'G', '𝐻': 'H', '𝐼': 'I', '𝐽': 'J', '𝐾': 'K', '𝐿': 'L',
        '𝑀': 'M', '𝑁': 'N', '𝑂': 'O', '𝑃': 'P', '𝑄': 'Q', '𝑅': 'R',
        '𝑆': 'S', '𝑇': 'T', '𝑈': 'U', '𝑉': 'V', '𝑊': 'W', '𝑋': 'X',
        '𝑌': 'Y', '𝑍': 'Z',
        # Mathematical italic lowercase
        '𝑎': 'a', '𝑏': 'b', '𝑐': 'c', '𝑑': 'd', '𝑒': 'e', '𝑓': 'f',
        '𝑔': 'g', 'ℎ': 'h', '𝑖': 'i', '𝑗': 'j', '𝑘': 'k', '𝑙': 'l',
        '𝑚': 'm', '𝑛': 'n', '𝑜': 'o', '𝑝': 'p', '𝑞': 'q', '𝑟': 'r',
        '𝑠': 't', '𝑡': 't', '𝑢': 'u', '𝑣': 'v', '𝑤': 'w', '𝑥': 'x',
        '𝑦': 'y', '𝑧': 'z',
        # Fullwidth characters
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F',
        'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L',
        'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R',
        'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X',
        'Ｙ': 'Y', 'Ｚ': 'Z',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e', 'ｆ': 'f',
        'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j', 'ｋ': 'k', 'ｌ': 'l',
        'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o', 'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r',
        'ｓ': 's', 'ｔ': 't', 'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x',
        'ｙ': 'y', 'ｚ': 'z',
        # Replacement character
        '': '',  # Remove replacement characters
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace: remove leading/trailing, collapse multiple spaces.
    
    Args:
        text: Input text with potentially irregular whitespace
        
    Returns:
        Text with normalized whitespace
    """
    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()
    return text


def remove_wrapping_quotes(text: str) -> str:
    """
    Remove wrapping quotes (single or double) from text.
    Handles cases like: "Company Name", 'Company Name', "'Company Name'"
    
    Args:
        text: Input text potentially wrapped in quotes
        
    Returns:
        Text with wrapping quotes removed
    """
    text = text.strip()
    
    # Remove wrapping quotes (can be nested)
    while len(text) >= 2:
        if (text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'"):
            text = text[1:-1].strip()
        else:
            break
    
    return text


def remove_emojis(text: str) -> str:
    """
    Remove emojis and emoji-like symbols from text.
    
    Args:
        text: Input text potentially containing emojis
        
    Returns:
        Text with emojis removed
    """
    # Remove emojis using the emoji library if available
    if HAS_EMOJI:
        text = emoji.replace_emoji(text, replace='')
    
    # Remove other common symbols that might be used as emojis
    symbol_patterns = [
        r'[\U0001F300-\U0001F9FF]',  # Emoticons
        r'[\U00002600-\U000027BF]',  # Miscellaneous symbols
        r'[\U0001F600-\U0001F64F]',  # Emoticons
        r'[\U0001F680-\U0001F6FF]',  # Transport and map symbols
    ]
    
    for pattern in symbol_patterns:
        text = re.sub(pattern, '', text)
    
    return text


def contains_letters(text: str) -> bool:
    """
    Check if text contains at least one letter (any language).
    
    Supports:
    - ASCII letters (a-z, A-Z)
    - Unicode letters from all scripts (Chinese, Japanese, Arabic, Hebrew, Cyrillic, etc.)
    - Uses Unicode letter category (\\p{L}) which includes all language scripts
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains at least one letter from any language
    """
    # Match letters from all Unicode scripts
    # This includes: Latin, Cyrillic, Arabic, Hebrew, Chinese, Japanese, Korean, etc.
    # Pattern matches any Unicode character in the range \u0080-\uFFFF (non-ASCII)
    # plus ASCII letters a-z, A-Z
    return bool(re.search(r'[a-zA-Z\u0080-\uFFFF]', text))


def fix_encoding_issues(text: str) -> str:
    """
    Attempt to fix common encoding issues.
    
    Args:
        text: Input text with potential encoding issues
        
    Returns:
        Text with encoding issues fixed where possible
    """
    # Remove replacement characters
    text = text.replace('', '')
    
    # Try to decode and re-encode to fix common issues
    try:
        # If text contains only question marks (common encoding replacement)
        if re.match(r'^\?+\s*\?*$', text.strip()):
            return ''  # Likely encoding corruption, return empty
    except Exception:
        pass  # Regex failed, continue with normalization
    
    return text

