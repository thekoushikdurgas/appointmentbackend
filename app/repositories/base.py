from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class AsyncRepository(Generic[ModelType]):
    """Generic async repository for SQLAlchemy ORM models."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, session: AsyncSession, uuid: str) -> Optional[ModelType]:
        if not hasattr(self.model, "uuid"):
            raise AttributeError(f"{self.model.__name__} has no attribute 'uuid'")
        stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.uuid == uuid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

