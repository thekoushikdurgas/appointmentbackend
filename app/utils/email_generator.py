"""Utility functions for generating email combinations using probability-based formats."""

from typing import Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_name_variations(first_name: str, last_name: str) -> Dict[str, str]:
    """
    Extract various name variations for email generation.
    
    Args:
        first_name: Contact first name (will be lowercased)
        last_name: Contact last name (will be lowercased)
        
    Returns:
        Dictionary with name variations:
        - fn: full first name (lowercase)
        - ln: full last name (lowercase)
        - f_initial: first initial
        - l_initial: last initial
        - fi: first 2 chars of first name
        - ka: first 2 chars (alternative, same as fi for 2-char names)
        - first_truncated: first 2-3 chars (fi, kau, etc.)
        - las: last 3 chars of last name
        - sah: last 3 chars of last name (alternative)
        - last_truncated: last 3-4 chars (las, sah, sahaa, etc.)
    """
    # Generate name variations from first_name and last_name
    fn = first_name.lower().strip()
    ln = last_name.lower().strip()
    
    f_initial = fn[0] if fn else ""
    l_initial = ln[0] if ln else ""
    
    # First name truncations (2-3 chars)
    fi = fn[:2] if len(fn) >= 2 else fn
    kau = fn[:3] if len(fn) >= 3 else fn
    first_truncated = fi  # Use 2 chars as default
    
    # Last name truncations (3-4 chars)
    las = ln[:3] if len(ln) >= 3 else ln
    sah = ln[:3] if len(ln) >= 3 else ln
    sahaa = ln[:4] if len(ln) >= 4 else ln
    last_truncated = las  # Use 3 chars as default
    
    variations = {
        "fn": fn,
        "ln": ln,
        "f_initial": f_initial,
        "l_initial": l_initial,
        "fi": fi,
        "ka": fi,  # Same as fi for 2 chars
        "kau": kau,
        "first_truncated": first_truncated,
        "las": las,
        "sah": sah,
        "sahaa": sahaa,
        "last_truncated": last_truncated,
    }
    # Name variations generated: fn, ln, f_initial, l_initial, fi, kau, las, sahaa
    return variations


def _generate_tier1_patterns(vars: Dict[str, str]) -> List[str]:
    """
    Generate Tier 1 - Most Common Email Formats (60-70% coverage).
    
    Patterns:
    1. first.last
    2. firstlast
    3. first
    4. f.last
    5. flast
    6. first.l
    7. first_last
    8. first_l
    9. first-last
    10. first-l
    """
    patterns = [
        f"{vars['fn']}.{vars['ln']}",      # first.last
        f"{vars['fn']}{vars['ln']}",       # firstlast
        vars['fn'],                         # first
        f"{vars['f_initial']}.{vars['ln']}",  # f.last
        f"{vars['f_initial']}{vars['ln']}",   # flast
        f"{vars['fn']}.{vars['l_initial']}",  # first.l
        f"{vars['fn']}_{vars['ln']}",       # first_last
        f"{vars['fn']}_{vars['l_initial']}", # first_l
        f"{vars['fn']}-{vars['ln']}",       # first-last
        f"{vars['fn']}-{vars['l_initial']}", # first-l
    ]
    # Generated Tier1 patterns (most common email formats)
    return patterns


def _generate_tier2_patterns(vars: Dict[str, str]) -> List[str]:
    """
    Generate Tier 2 - Moderately Common Email Formats (20-25% coverage).
    
    Patterns:
    1. f.l
    2. fl
    3. last.first
    4. lastfirst
    5. last.f
    6. l.first
    7. l.f
    8. first.las
    9. fi.last
    10. fi.las
    11. firstl
    12. flast1
    13. first1
    14. first.last1
    15. f.last1
    """
    # Get additional truncations for tier2
    kaus = vars['fn'][:4] if len(vars['fn']) >= 4 else vars['fn']  # first 4 chars (e.g., "kaus")
    
    patterns = [
        f"{vars['f_initial']}.{vars['l_initial']}",  # f.l
        f"{vars['f_initial']}{vars['l_initial']}",   # fl
        f"{vars['ln']}.{vars['fn']}",                # last.first
        f"{vars['ln']}{vars['fn']}",                 # lastfirst
        f"{vars['ln']}.{vars['f_initial']}",         # last.f
        f"{vars['l_initial']}.{vars['fn']}",         # l.first
        f"{vars['l_initial']}.{vars['f_initial']}",  # l.f
        f"{vars['fn']}.{vars['las']}",               # first.las
        f"{vars['fi']}.{vars['ln']}",                # fi.last
        f"{vars['fi']}.{vars['las']}",              # fi.las
        f"{vars['fn']}{vars['l_initial']}",         # firstl
        f"{vars['f_initial']}{vars['ln']}1",        # flast1 (literal "1")
        f"{vars['fn']}1",                           # first1 (literal "1")
        f"{vars['fn']}.{vars['ln']}1",              # first.last1 (literal "1")
        f"{vars['f_initial']}.{vars['ln']}1",       # f.last1 (literal "1")
        # Additional variations from example
        f"{kaus}.{vars['ln']}",                     # kaus.last (e.g., kaus.saha)
        f"{vars['kau']}.{vars['ln']}",              # kau.last (e.g., kau.saha)
    ]
    # Generated Tier2 patterns (moderately common email formats)
    return patterns


def _generate_tier3_patterns(vars: Dict[str, str]) -> List[str]:
    """
    Generate Tier 3 - Rare Legacy Email Formats (15% additional coverage).
    
    Patterns from the comprehensive list, matching the exact examples provided.
    """
    patterns = [
        # Reversed with separators
        f"{vars['ln']}_{vars['fn']}",                # last_first (e.g., saha_kaushik)
        f"{vars['ln']}-{vars['fn']}",                # last-first (e.g., saha-kaushik)
        # Truncated combinations
        f"{vars['fn']}{vars['las']}",                 # firstlas (e.g., kaushiksah)
        f"{vars['kau']}.{vars['ln']}",               # kau.last (e.g., kau.shik - but this should be kau.saha)
        f"{vars['kau']}.{vars['sah']}",              # kau.sah (e.g., kau.saha)
        # Initial combinations with separators
        f"{vars['f_initial']}_{vars['ln']}",         # f_last (e.g., k_saha)
        f"{vars['l_initial']}_{vars['fn']}",         # l_first (e.g., s_kaushik)
        f"{vars['l_initial']}-{vars['fn']}",        # l-first (e.g., s-kaushik)
        # Truncated with numbers (literal "1" or "99" as shown in example)
        f"{vars['fn']}.{vars['las']}99",             # first.las99 (e.g., kaushik.sah99)
        f"{vars['f_initial']}.{vars['las']}",        # f.las (e.g., k.sah)
        f"{vars['f_initial']}{vars['las']}",         # flas (e.g., ksah)
        # Reversed truncated
        f"{vars['ln']}.{vars['fi']}",                # last.fi (e.g., saha.ka)
        f"{vars['ln']}_{vars['fi']}",                # last_fi (e.g., saha_ka)
        f"{vars['l_initial']}.{vars['fi']}",        # l.fi (e.g., s.ka)
        # Additional variations from example
        f"{vars['fn']}_{vars['las']}",               # first_las (e.g., kaushik_sah)
        f"{vars['fn']}_{vars['sahaa']}",            # first_sahaa (e.g., kaushik_sahaa)
        f"{vars['f_initial']}_{vars['sahaa']}",     # f_sahaa (e.g., k_sahaa)
        f"{vars['fi']}.{vars['l_initial']}",        # fi.l (e.g., ka.s)
        f"{vars['f_initial']}.{vars['sahaa']}",      # f.sahaa (e.g., k.sahaa)
        f"{vars['f_initial']}{vars['sahaa']}",      # fsahaa (e.g., ksahaa)
        f"{vars['sah']}.{vars['fn']}",               # sah.first (e.g., sah.kaushik)
        # Additional truncation variations
        f"{vars['fi']}.{vars['l_initial']}",        # fi.l (already above, but keeping for completeness)
        f"{vars['kau']}.{vars['sah']}",              # kau.sah (already above)
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    duplicates_removed = 0
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
        else:
            duplicates_removed += 1
    
    return unique_patterns


def generate_email_combinations(
    first_name: str, last_name: str, domain: str, count: int = 1000
) -> List[str]:
    """
    Generate email combinations using probability-based format patterns.
    
    Generates emails in priority order (most common first) using structured
    format patterns organized into three tiers:
    - Tier 1: Most Common (60-70% coverage) - 10 patterns
    - Tier 2: Moderately Common (20-25% coverage) - 15 patterns
    - Tier 3: Rare Legacy (15% additional coverage) - remaining patterns
    
    Args:
        first_name: Contact first name (will be lowercased)
        last_name: Contact last name (will be lowercased)
        domain: Email domain (e.g., "example.com")
        count: Number of unique emails to generate (default: 1000)
        
    Returns:
        List of unique email addresses in probability order (most common first)
    """
    # Starting email generation for first_name, last_name, domain with requested count
    
    # Normalize domain
    domain = domain.lower().strip()
    
    # Get name variations (fn, ln, f_initial, l_initial)
    vars = _get_name_variations(first_name, last_name)
    
    # Validate inputs - return empty list if first_name or last_name is empty
    if not vars['fn'] or not vars['ln']:
        return []
    
    # Generate patterns in priority order (Tier1, Tier2, Tier3)
    tier1_patterns = _generate_tier1_patterns(vars)
    tier2_patterns = _generate_tier2_patterns(vars)
    tier3_patterns = _generate_tier3_patterns(vars)
    
    total_patterns = len(tier1_patterns) + len(tier2_patterns) + len(tier3_patterns)
    # Pattern generation completed for all tiers
    
    # Combine all patterns in priority order
    all_patterns = tier1_patterns + tier2_patterns + tier3_patterns
    
    # Generate emails from patterns
    emails = []
    seen = set()
    validation_failures = 0
    
    # First pass: use all unique patterns
    for pattern in all_patterns:
        if pattern and pattern not in seen:
            email = f"{pattern}@{domain}"
            # Validate email length (RFC 5321: local part max 64 chars)
            if len(pattern) <= 64:
                emails.append(email)
                seen.add(pattern)
            else:
                validation_failures += 1
                # Pattern validation failed - exceeds 64 char limit (RFC 5321)
    
    # Return top N emails maintaining priority order
    return emails[:count]
