"""Shared base repository implementation for async SQLAlchemy access.

All models in this codebase use UUID as the primary identifier.
Use get_by_uuid() to retrieve entities by their UUID.

Migration Note:
- The deprecated get() method (by integer ID) has been removed.
- All repositories should use get_by_uuid() instead.
- If you need to query by integer ID, use direct SQLAlchemy queries.
"""

import time
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.utils.logger import get_logger, log_database_query, log_database_error

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
logger = get_logger(__name__)


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
            logger.error(
                f"Model {self.model.__name__} has no attribute 'uuid'",
                extra={"context": {"model": self.model.__name__}}
            )
            raise AttributeError(f"{self.model.__name__} has no attribute 'uuid'")
        
        start_time = time.time()
        try:
            stmt: Select[tuple[ModelType]] = select(self.model).where(self.model.uuid == uuid)
            result = await session.execute(stmt)
            entity = result.scalar_one_or_none()
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__ if hasattr(self.model, "__tablename__") else self.model.__name__,
                filters={"uuid": uuid},
                result_count=1 if entity else 0,
                duration_ms=duration_ms,
                logger_name=f"app.repositories.{self.model.__name__.lower()}",
            )
            
            return entity
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__ if hasattr(self.model, "__tablename__") else self.model.__name__,
                error=exc,
                duration_ms=duration_ms,
                context={
                    "model": self.model.__name__,
                    "uuid": uuid,
                    "method": "get_by_uuid",
                }
            )
            raise

