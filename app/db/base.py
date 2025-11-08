from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


# Ensure models are imported when this module is loaded.
try:  # pragma: no cover
    import app.models  # noqa: F401
except ModuleNotFoundError:
    pass

