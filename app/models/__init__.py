from app.db.base import Base  # noqa: F401

# Import models so Alembic can detect them.
from . import companies  # noqa: F401
from . import contacts  # noqa: F401
from . import departments  # noqa: F401
from . import imports  # noqa: F401

