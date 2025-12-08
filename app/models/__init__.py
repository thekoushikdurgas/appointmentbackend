"""Expose SQLAlchemy models for metadata generation."""

from app.db.base import Base  # noqa: F401

# Import models for metadata discovery.
from . import ai_chat  # noqa: F401
from . import billing  # noqa: F401
from . import companies  # noqa: F401
from . import contacts  # noqa: F401
from . import email_patterns  # noqa: F401
from . import exports  # noqa: F401
from . import imports  # noqa: F401
from . import token_blacklist  # noqa: F401
from . import user  # noqa: F401
from . import user_scraping  # noqa: F401

