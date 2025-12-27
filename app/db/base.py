"""SQLAlchemy declarative base import and auto-discovery hooks."""

from sqlalchemy.orm import DeclarativeBase

from app.utils.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


# Ensure models are imported when this module is loaded.
try:  # pragma: no cover
    import app.models  # noqa: F401
except ModuleNotFoundError:
    pass

