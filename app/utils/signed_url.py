"""Utilities for generating and verifying signed URLs for file downloads."""

from datetime import datetime
from typing import Optional

from jose import jwt

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def generate_signed_url(export_id: str, user_id: str, expires_at: datetime) -> str:
    """
    Generate a JWT-based signed URL with expiration.
    
    Args:
        export_id: The export ID
        user_id: The user ID who owns the export
        expires_at: When the URL should expire
        
    Returns:
        A signed URL token string
    """
    payload = {
        "export_id": export_id,
        "user_id": user_id,
        "exp": expires_at,
        "type": "export_download",
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return token


def verify_signed_url(token: str) -> Optional[dict]:
    """
    Verify and decode a signed URL token.
    
    Args:
        token: The JWT token from the signed URL
        
    Returns:
        Dictionary with export_id and user_id if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != "export_download":
            return None
            
        return {
            "export_id": payload.get("export_id"),
            "user_id": payload.get("user_id"),
        }
    except Exception:
        return None

