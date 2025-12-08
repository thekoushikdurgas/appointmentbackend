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

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class AsyncRepository(Generic[ModelType]):
    """Generic async repository for SQLAlchemy ORM models.
    
    All models use UUID as the primary identifier. Use get_by_uuid() to retrieve entities.
    """

    def __init__(self, model: Type[ModelType]):
        """Store the SQLAlchemy model class for subsequent queries."""
        self.model = model

    async def get_by_uuid(self, session: AsyncSession, uuid: str) -> Optional[ModelType]:
        """Retrieve a record by its UUID column."""
        if not hasattr(self.model, "uuid"):
            raise AttributeError(f"{self.model.__name__} has no attribute 'uuid'")
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.uuid == uuid)
        result = await session.execute(stmt)
        entity = result.scalar_one_or_none()
        return entity

