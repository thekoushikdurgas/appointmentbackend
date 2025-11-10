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


def _parse_offset(candidate: str) -> int:
    """Extract an integer offset from a decoded cursor payload."""
    if candidate is None:
        raise ValueError("Missing cursor candidate")

    text = candidate.strip()
    if not text:
        raise ValueError("Empty cursor candidate")

    if text.startswith("o="):
        text = text.split("=", 1)[1].strip()

    value = int(text)
    if value < 0:
        raise ValueError("Offset cannot be negative")
    return value


def decode_offset_cursor(token: str) -> int:
    """Decode a cursor token into an integer offset.

    Supports the current `o=<offset>` encoding as well as legacy tokens that
    were either base64-encoded plain integers or raw integer strings.
    """
    logger.debug("Entering decode_offset_cursor token=%s", token)
    errors: list[str] = []

    candidates: list[str] = []
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        candidates.append(decoded)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"base64:{exc}")

    candidates.append(token)

    for candidate in candidates:
        try:
            value = _parse_offset(candidate)
            logger.debug(
                "Exiting decode_offset_cursor result=%d candidate=%s",
                value,
                candidate,
            )
            return value
        except Exception as exc:  # noqa: BLE001
            errors.append(f"candidate:{candidate!r} error:{exc}")

    logger.warning(
        "Failed to decode cursor token: token=%s attempts=%s",
        token,
        "; ".join(errors),
    )
    raise ValueError("Invalid cursor value")

