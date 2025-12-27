"""Utility functions for domain extraction from URLs."""

from urllib.parse import urlparse

from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_domain_from_url(url: str | None) -> str | None:
    """
    Extract normalized domain from a URL string.
    
    Handles various URL formats:
    - Full URLs: "https://example.com", "http://www.example.com"
    - Domain-only: "example.com"
    - URLs with paths: "https://example.com/path"
    
    Args:
        url: URL string to extract domain from, or None
        
    Returns:
        Normalized domain in lowercase (e.g., "example.com"), or None if input is None/empty
        
    Examples:
        >>> extract_domain_from_url("https://www.example.com")
        'example.com'
        >>> extract_domain_from_url("http://example.com/path")
        'example.com'
        >>> extract_domain_from_url("example.com")
        'example.com'
        >>> extract_domain_from_url(None)
        None
        >>> extract_domain_from_url("")
        None
    """
    if not url or not url.strip():
        return None
    
    original_url = url
    url = url.strip()
    
    # If URL doesn't have a scheme, add one temporarily for parsing
    if not url.startswith(("http://", "https://", "ftp://")):
        url = "https://" + url
    
    try:
        parsed = urlparse(url)
        
        # Get domain from netloc (hostname) or path if netloc is empty
        domain = parsed.netloc or parsed.path.split("/")[0]
        
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        
        # Remove 'www.' prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Return lowercase normalized domain
        normalized = domain.lower() if domain else None
        return normalized
    except Exception as e:
        # If parsing fails, try to extract domain from the original string
        # Remove common prefixes
        domain = original_url.lower().strip()
        
        if domain.startswith(("http://", "https://", "ftp://")):
            domain = domain.split("://", 1)[1]
        if "/" in domain:
            domain = domain.split("/")[0]
        if ":" in domain:
            domain = domain.split(":")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        
        final_domain = domain if domain else None
        return final_domain

