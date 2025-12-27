"""Expose SQLAlchemy models for metadata generation."""

from app.db.base import Base  # noqa: F401

# Import models for metadata discovery.
from . import (
    ai_chat,  # noqa: F401
    billing,  # noqa: F401
    companies,  # noqa: F401
    contacts,  # noqa: F401
    email_patterns,  # noqa: F401
    exports,  # noqa: F401
    token_blacklist,  # noqa: F401
    user,  # noqa: F401
    user_scraping,  # noqa: F401
)

