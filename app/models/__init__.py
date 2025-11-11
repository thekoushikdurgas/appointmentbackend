"""Expose SQLAlchemy models for metadata generation."""

from app.db.base import Base  # noqa: F401

# Import models for metadata discovery.
from . import ai_chat  # noqa: F401
from . import companies  # noqa: F401
from . import contacts  # noqa: F401
from . import departments  # noqa: F401
from . import imports  # noqa: F401
from . import user  # noqa: F401

