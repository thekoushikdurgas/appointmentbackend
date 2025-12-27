"""Utility functions for transforming Sales Navigator data to database format."""

import re
from typing import Optional, Tuple
from uuid import NAMESPACE_URL, uuid5

from app.utils.logger import get_logger
from app.utils.normalization import PLACEHOLDER_VALUE, normalize_text

logger = get_logger(__name__)


def parse_name(name: Optional[str]) -> Tuple[str, str]:
    """
    Parse full name into first_name and last_name.
    
    Args:
        name: Full name string
        
    Returns:
        Tuple of (first_name, last_name)
    """
    if not name:
        return PLACEHOLDER_VALUE, PLACEHOLDER_VALUE
    
    name_parts = name.strip().split()
    if len(name_parts) == 0:
        return PLACEHOLDER_VALUE, PLACEHOLDER_VALUE
    elif len(name_parts) == 1:
        return name_parts[0], PLACEHOLDER_VALUE
    else:
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])
        return first_name, last_name


def parse_location(location: Optional[str]) -> Tuple[str, str, str]:
    """
    Parse location string into city, state, country.
    
    Args:
        location: Location string (e.g., "New York, New York, United States")
        
    Returns:
        Tuple of (city, state, country)
    """
    if not location:
        return PLACEHOLDER_VALUE, PLACEHOLDER_VALUE, PLACEHOLDER_VALUE
    
    parts = [p.strip() for p in location.split(',')]
    
    if len(parts) >= 3:
        # Format: "City, State, Country"
        return parts[0], parts[1], parts[-1]
    elif len(parts) == 2:
        # Format: "City, Country" or "State, Country"
        return parts[0], PLACEHOLDER_VALUE, parts[1]
    elif len(parts) == 1:
        # Just country or city
        return parts[0], PLACEHOLDER_VALUE, PLACEHOLDER_VALUE
    else:
        return PLACEHOLDER_VALUE, PLACEHOLDER_VALUE, PLACEHOLDER_VALUE


def infer_seniority(title: Optional[str]) -> str:
    """
    Infer seniority level from job title.
    
    Args:
        title: Job title string
        
    Returns:
        Seniority level (executive, director, manager, senior_ic, entry, or "_")
    """
    if not title:
        return PLACEHOLDER_VALUE
    
    title_lower = title.lower()
    
    # C-level executives
    if any(term in title_lower for term in ['ceo', 'cto', 'cfo', 'coo', 'founder', 'founding', 'president']):
        return "executive"
    
    # Directors
    if 'director' in title_lower or 'vp' in title_lower or 'vice president' in title_lower:
        return "director"
    
    # Managers
    if 'manager' in title_lower or 'lead' in title_lower or 'head' in title_lower:
        return "manager"
    
    # Senior individual contributors
    if 'senior' in title_lower or 'sr.' in title_lower or 'principal' in title_lower:
        return "senior_ic"
    
    # Entry level
    if any(term in title_lower for term in ['junior', 'jr.', 'intern', 'entry', 'associate']):
        return "entry"
    
    return PLACEHOLDER_VALUE


def extract_departments_from_title_about(title: Optional[str], about: Optional[str]) -> list[str]:
    """
    Extract department names from title and about fields.
    
    Args:
        title: Job title
        about: About/bio text
        
    Returns:
        List of department names
    """
    departments = []
    text = f"{title or ''} {about or ''}".lower()
    
    department_keywords = {
        'engineering': ['engineer', 'engineering', 'developer', 'programmer', 'software', 'tech'],
        'sales': ['sales', 'account executive', 'business development', 'bd'],
        'marketing': ['marketing', 'growth', 'demand gen', 'brand'],
        'product': ['product', 'pm', 'product manager'],
        'operations': ['operations', 'ops', 'operational'],
        'finance': ['finance', 'financial', 'accounting', 'cfo'],
        'hr': ['hr', 'human resources', 'talent', 'recruiting'],
        'legal': ['legal', 'counsel', 'attorney', 'law'],
    }
    
    for dept, keywords in department_keywords.items():
        if any(keyword in text for keyword in keywords):
            departments.append(dept.capitalize())
    
    return departments if departments else []


def convert_sales_nav_url_to_linkedin(profile_url: Optional[str]) -> str:
    """
    Convert Sales Navigator profile URL to standard LinkedIn URL.
    
    Note: Sales Navigator URLs contain lead_id which cannot be directly converted
    to public LinkedIn profile URLs. This function attempts to extract what it can
    but may return the original URL or placeholder.
    
    Args:
        profile_url: Sales Navigator profile URL
        
    Returns:
        Standard LinkedIn profile URL or "_" if conversion not possible
    """
    if not profile_url:
        return PLACEHOLDER_VALUE
    
    # Try to extract lead_id from Sales Navigator URL
    # Format: https://www.linkedin.com/sales/lead/{LEAD_ID},{SEARCH_TYPE},{SEARCH_ID}
    match = re.search(r'/sales/lead/([^,]+),', profile_url)
    if match:
        lead_id = match.group(1)
        # Note: We can't directly convert lead_id to public profile URL
        # Return placeholder - the system will use the Sales Navigator URL as fallback
        return PLACEHOLDER_VALUE
    
    # If it's already a standard LinkedIn URL, return it
    if 'linkedin.com/in/' in profile_url or 'linkedin.com/pub/' in profile_url:
        return profile_url
    
    return PLACEHOLDER_VALUE


def generate_contact_uuid(linkedin_url: str, email: Optional[str] = None) -> str:
    """
    Generate deterministic UUID5 for contact.
    
    Args:
        linkedin_url: LinkedIn profile URL (standard or Sales Navigator)
        email: Optional email address
        
    Returns:
        UUID5 string
    """
    # Normalize linkedin_url
    linkedin_url = normalize_text(linkedin_url, allow_placeholder=True) or PLACEHOLDER_VALUE
    
    # If email is provided, use linkedin_url + email
    if email:
        email = normalize_text(email, allow_placeholder=True) or ""
        hash_str = linkedin_url + email
    else:
        # Use only linkedin_url if email is missing
        hash_str = linkedin_url
    
    return str(uuid5(NAMESPACE_URL, hash_str))


def generate_company_uuid(company_name: str, company_url: Optional[str] = None) -> str:
    """
    Generate deterministic UUID5 for company.
    
    Args:
        company_name: Company name
        company_url: Optional company LinkedIn URL
        
    Returns:
        UUID5 string
    """
    # Normalize company name
    company_name = normalize_text(company_name, allow_placeholder=True) or PLACEHOLDER_VALUE
    
    # Normalize company URL
    company_url = normalize_text(company_url, allow_placeholder=True) or PLACEHOLDER_VALUE
    
    hash_str = company_name + company_url
    
    return str(uuid5(NAMESPACE_URL, hash_str))

