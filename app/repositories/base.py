"""Shared base repository implementation for async SQLAlchemy access.

All models in this codebase use UUID as the primary identifier.
Use get_by_uuid() to retrieve entities by their UUID.

Migration Note:
- The deprecated get() method (by integer ID) has been removed.
- All repositories should use get_by_uuid() instead.
- If you need to query by integer ID, use direct SQLAlchemy queries.
"""

from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.logging import get_logger

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


logger = get_logger(__name__)


class AsyncRepository(Generic[ModelType]):
    """Generic async repository for SQLAlchemy ORM models.
    
    All models use UUID as the primary identifier. Use get_by_uuid() to retrieve entities.
    """

    def __init__(self, model: Type[ModelType]):
        """Store the SQLAlchemy model class for subsequent queries."""
        logger.debug("Initializing AsyncRepository model=%s", model.__name__)
        self.model = model
        logger.debug("Initialized AsyncRepository model=%s", self.model.__name__)

    async def get_by_uuid(self, session: AsyncSession, uuid: str) -> Optional[ModelType]:
        """Retrieve a record by its UUID column."""
        logger.debug(
            "Entering AsyncRepository.get_by_uuid model=%s uuid=%s",
            self.model.__name__,
            uuid,
        )
        if not hasattr(self.model, "uuid"):
            logger.error("Model %s does not expose a uuid attribute", self.model.__name__)
            raise AttributeError(f"{self.model.__name__} has no attribute 'uuid'")
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.uuid == uuid)
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        logger.debug(
            "Exiting AsyncRepository.get_by_uuid model=%s found=%s",
            self.model.__name__,
            entity is not None,
        )
        return entity

