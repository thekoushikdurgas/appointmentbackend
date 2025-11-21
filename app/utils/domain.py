"""Utility functions for domain extraction from URLs."""

from urllib.parse import urlparse

from app.core.logging import get_logger

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
    logger.debug("Domain extraction: input=%s", url)
    
    if not url or not url.strip():
        logger.debug("Domain extraction: input is None or empty, returning None")
        return None
    
    original_url = url
    url = url.strip()
    logger.debug("Domain extraction: after strip=%s", url)
    
    # If URL doesn't have a scheme, add one temporarily for parsing
    if not url.startswith(("http://", "https://", "ftp://")):
        url = "https://" + url
        logger.debug("Domain extraction: added https:// scheme, url=%s", url)
    
    try:
        parsed = urlparse(url)
        logger.debug("Domain extraction: parsed netloc=%s path=%s", parsed.netloc, parsed.path)
        
        # Get domain from netloc (hostname) or path if netloc is empty
        domain = parsed.netloc or parsed.path.split("/")[0]
        logger.debug("Domain extraction: extracted domain (before normalization)=%s", domain)
        
        # Remove port if present
        if ":" in domain:
            domain_before_port = domain
            domain = domain.split(":")[0]
            logger.debug("Domain extraction: removed port, before=%s after=%s", domain_before_port, domain)
        
        # Remove 'www.' prefix
        if domain.startswith("www."):
            domain_before_www = domain
            domain = domain[4:]
            logger.debug("Domain extraction: removed www. prefix, before=%s after=%s", domain_before_www, domain)
        
        # Return lowercase normalized domain
        normalized = domain.lower() if domain else None
        logger.debug("Domain extraction: final normalized domain=%s (input=%s)", normalized, original_url)
        return normalized
    except Exception as e:
        logger.warning("Domain extraction: URL parsing failed, trying fallback method. Error: %s, input=%s", e, original_url)
        # If parsing fails, try to extract domain from the original string
        # Remove common prefixes
        domain = original_url.lower().strip()
        logger.debug("Domain extraction: fallback method, starting with=%s", domain)
        
        if domain.startswith(("http://", "https://", "ftp://")):
            domain = domain.split("://", 1)[1]
            logger.debug("Domain extraction: fallback removed protocol, domain=%s", domain)
        if "/" in domain:
            domain = domain.split("/")[0]
            logger.debug("Domain extraction: fallback removed path, domain=%s", domain)
        if ":" in domain:
            domain = domain.split(":")[0]
            logger.debug("Domain extraction: fallback removed port, domain=%s", domain)
        if domain.startswith("www."):
            domain = domain[4:]
            logger.debug("Domain extraction: fallback removed www., domain=%s", domain)
        
        final_domain = domain if domain else None
        logger.debug("Domain extraction: fallback final domain=%s (input=%s)", final_domain, original_url)
        return final_domain

