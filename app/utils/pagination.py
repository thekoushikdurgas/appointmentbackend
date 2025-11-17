"""Utilities for building pagination and cursor navigation links."""

from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from app.core.logging import get_logger

logger = get_logger(__name__)


def build_pagination_link(base_url: str, *, limit: int, offset: int) -> str:
    """Return a URL with updated limit/offset query parameters."""
    logger.debug(
        "Entering build_pagination_link base_url=%s limit=%d offset=%d",
        base_url,
        limit,
        offset,
    )
    url = urlparse(base_url)
    query = dict(parse_qsl(url.query))
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    result = urlunparse(new_url)
    logger.debug("Exiting build_pagination_link result=%s", result)
    return result


def build_cursor_link(base_url: str, cursor: str) -> str:
    """Return a URL that encodes the supplied cursor token and removes offset pagination."""
    logger.debug("Entering build_cursor_link base_url=%s cursor=%s", base_url, cursor)
    url = urlparse(base_url)
    query = dict(parse_qsl(url.query))
    query["cursor"] = cursor
    query.pop("offset", None)
    query.pop("limit", None)
    new_query = urlencode(query)
    new_url = url._replace(query=new_query)
    result = urlunparse(new_url)
    logger.debug("Exiting build_cursor_link result=%s", result)
    return result

