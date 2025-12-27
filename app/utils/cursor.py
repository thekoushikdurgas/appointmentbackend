"""Cursor token encoding helpers used for pagination."""

import base64
import json
from typing import Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def encode_offset_cursor(offset: int) -> str:
    """Encode an integer offset into a URL-safe cursor token."""
    token = f"o={offset}"
    encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")
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
            return value
        except Exception as exc:  # noqa: BLE001
            errors.append(f"candidate:{candidate!r} error:{exc}")

    raise ValueError(
        f"Invalid cursor value. Cursor must be a base64-encoded offset token (e.g., from a previous pagination response) or a valid integer offset. Received: {token!r}"
    )


def encode_keyset_cursor(last_id: int, last_value: Optional[Any] = None) -> str:
    """
    Encode a keyset pagination cursor from last record ID and optional sort value.
    
    Args:
        last_id: Last record ID from previous page
        last_value: Optional last sort value (for multi-column sorting)
        
    Returns:
        Base64-encoded cursor token
    """
    cursor_data = {"id": last_id}
    if last_value is not None:
        cursor_data["value"] = last_value
    token = json.dumps(cursor_data)
    encoded = base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")
    return encoded


def decode_keyset_cursor(token: str) -> tuple[int, Optional[Any]]:
    """
    Decode a keyset pagination cursor.
    
    Args:
        token: Base64-encoded cursor token
        
    Returns:
        Tuple of (last_id, last_value)
    """
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        cursor_data = json.loads(decoded)
        last_id = cursor_data.get("id")
        last_value = cursor_data.get("value")
        if last_id is None:
            raise ValueError("Missing 'id' in keyset cursor")
        return int(last_id), last_value
    except Exception as exc:
        raise ValueError(f"Invalid keyset cursor token: {exc}") from exc

