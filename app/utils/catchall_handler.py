"""Utilities for handling catchall email statuses with IcyPeas fallback."""

from __future__ import annotations

from typing import Optional, Tuple

from app.schemas.email import EmailVerificationStatus
from app.services.icypeas_service import IcyPeasService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def handle_catchall_email(
    first_name: str,
    last_name: str,
    domain: str,
    catchall_email: str,
    catchall_status: EmailVerificationStatus,
) -> Tuple[str, EmailVerificationStatus, Optional[str]]:
    """Handle catchall emails by attempting an IcyPeas lookup.

    Args:
        first_name: Contact first name
        last_name: Contact last name
        domain: Email domain
        catchall_email: Original catchall email from Truelist
        catchall_status: CATCHALL status from Truelist

    Returns:
        Tuple of (email, status, certainty)
        - If IcyPeas succeeds: (icypeas_email, VALID, certainty)
        - If IcyPeas fails: (catchall_email, CATCHALL, None)
    """
    # Fast path: if IcyPeas not configured, just return original catchall
    try:
        service = IcyPeasService()
    except Exception:
        return catchall_email, catchall_status, None

    try:
        result = await service.search_email(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            max_attempts=5,
            poll_interval=0.3,  # Optimized: exponential backoff
        )
    except Exception:
        # Any error from IcyPeas: fall back to original catchall
        return catchall_email, catchall_status, None

    if not result:
        return catchall_email, catchall_status, None

    email = result.get("email") or catchall_email
    certainty = result.get("certainty")

    # Consider any certainty value as acceptable (ultra_sure, sure, probable)
    return email, EmailVerificationStatus.VALID, certainty
