"""Cursor token encoding helpers used for pagination."""

import base64

from app.core.logging import get_logger

logger = get_logger(__name__)


def encode_offset_cursor(offset: int) -> str:
    """Encode an integer offset into a URL-safe cursor token."""
    logger.debug("Entering encode_offset_cursor offset=%d", offset)
    token = f"o={offset}"
    encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")
    logger.debug("Exiting encode_offset_cursor result=%s", encoded)
    return encoded


def decode_offset_cursor(token: str) -> int:
    """Decode a cursor token into an integer offset."""
    logger.debug("Entering decode_offset_cursor token=%s", token)
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        if not decoded.startswith("o="):
            raise ValueError("Invalid cursor payload")
        value = int(decoded.split("=", 1)[1])
        logger.debug("Exiting decode_offset_cursor result=%d", value)
        return value
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to decode cursor token: token=%s error=%s", token, exc)
        raise ValueError("Invalid cursor value") from exc

