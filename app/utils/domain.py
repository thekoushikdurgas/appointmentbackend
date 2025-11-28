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
    logger.info("Domain extraction: Starting extraction from input=%s", url)
    
    if not url or not url.strip():
        logger.warning("Domain extraction: Input is None or empty, returning None")
        return None
    
    original_url = url
    url = url.strip()
    logger.debug("Domain extraction: After strip: %s", url)
    
    # If URL doesn't have a scheme, add one temporarily for parsing
    if not url.startswith(("http://", "https://", "ftp://")):
        url = "https://" + url
        logger.debug("Domain extraction: Added https:// scheme: %s", url)
    
    try:
        parsed = urlparse(url)
        logger.debug("Domain extraction: Parsed netloc=%s path=%s", parsed.netloc, parsed.path)
        
        # Get domain from netloc (hostname) or path if netloc is empty
        domain = parsed.netloc or parsed.path.split("/")[0]
        logger.debug("Domain extraction: Extracted domain (before normalization)=%s", domain)
        
        # Remove port if present
        if ":" in domain:
            domain_before_port = domain
            domain = domain.split(":")[0]
            logger.debug("Domain extraction: Removed port: before=%s after=%s", domain_before_port, domain)
        
        # Remove 'www.' prefix
        if domain.startswith("www."):
            domain_before_www = domain
            domain = domain[4:]
            logger.debug("Domain extraction: Removed www. prefix: before=%s after=%s", domain_before_www, domain)
        
        # Return lowercase normalized domain
        normalized = domain.lower() if domain else None
        logger.info("Domain extraction: Successfully extracted domain: input=%s output=%s", original_url, normalized)
        return normalized
    except Exception as e:
        logger.warning(
            "Domain extraction: URL parsing failed, trying fallback method: error=%s type=%s input=%s",
            str(e),
            type(e).__name__,
            original_url,
        )
        # If parsing fails, try to extract domain from the original string
        # Remove common prefixes
        domain = original_url.lower().strip()
        logger.debug("Domain extraction: Fallback method starting with=%s", domain)
        
        if domain.startswith(("http://", "https://", "ftp://")):
            domain_before = domain
            domain = domain.split("://", 1)[1]
            logger.debug("Domain extraction: Fallback removed protocol: before=%s after=%s", domain_before, domain)
        if "/" in domain:
            domain_before = domain
            domain = domain.split("/")[0]
            logger.debug("Domain extraction: Fallback removed path: before=%s after=%s", domain_before, domain)
        if ":" in domain:
            domain_before = domain
            domain = domain.split(":")[0]
            logger.debug("Domain extraction: Fallback removed port: before=%s after=%s", domain_before, domain)
        if domain.startswith("www."):
            domain_before = domain
            domain = domain[4:]
            logger.debug("Domain extraction: Fallback removed www.: before=%s after=%s", domain_before, domain)
        
        final_domain = domain if domain else None
        if final_domain:
            logger.warning(
                "Domain extraction: Fallback method succeeded: input=%s output=%s (primary parsing failed)",
                original_url,
                final_domain,
            )
        else:
            logger.error(
                "Domain extraction: Fallback method failed to extract domain: input=%s",
                original_url,
            )
        return final_domain

