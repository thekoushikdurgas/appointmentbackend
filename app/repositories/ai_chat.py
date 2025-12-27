"""Repository providing AI chat-specific query utilities."""

import time
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_chat import AIChat
from app.repositories.base import AsyncRepository
from app.schemas.filters import AIChatFilterParams
from app.utils.logger import get_logger, log_database_query, log_database_error

logger = get_logger(__name__)


class AIChatRepository(AsyncRepository[AIChat]):
    """Data access helpers for AI chat queries."""

    def __init__(self) -> None:
        """Initialize the repository for the AIChat model."""
        super().__init__(AIChat)

    async def get_by_uuid(self, session: AsyncSession, chat_uuid: str) -> Optional[AIChat]:
        """Retrieve a chat by its UUID."""
        stmt: Select[tuple[AIChat]] = select(self.model).where(self.model.uuid == chat_uuid)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        return chat

    async def get_by_uuid_and_user_uuid(
        self, session: AsyncSession, chat_uuid: str, user_uuid: str
    ) -> Optional[AIChat]:
        """Retrieve a chat by UUID and user UUID (for ownership verification)."""
        stmt: Select[tuple[AIChat]] = select(self.model).where(
            self.model.uuid == chat_uuid, self.model.user_id == user_uuid
        )
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        return chat

    async def list_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
        filters: Optional[AIChatFilterParams] = None,
        *,
        limit: int = 25,
        offset: int = 0,
        ordering: str = "-created_at",
    ) -> list[AIChat]:
        """List chats for a user with pagination and ordering."""
        start_time = time.time()
        try:
            stmt: Select[tuple[AIChat]] = select(self.model).where(self.model.user_id == user_id)

            # Apply filters if provided
            if filters:
                stmt = self._apply_filters(stmt, filters)

            # Apply ordering (use filter ordering if provided, otherwise use parameter)
            resolved_ordering = filters.ordering if filters and filters.ordering else ordering
            if resolved_ordering.startswith("-"):
                order_field = resolved_ordering[1:]
                if hasattr(self.model, order_field):
                    stmt = stmt.order_by(getattr(self.model, order_field).desc())
                else:
                    stmt = stmt.order_by(self.model.created_at.desc())
            else:
                if hasattr(self.model, resolved_ordering):
                    stmt = stmt.order_by(getattr(self.model, resolved_ordering).asc())
                else:
                    stmt = stmt.order_by(self.model.created_at.desc())

            # Apply pagination
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            chats = list(result.scalars().all())
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"user_id": user_id, "limit": limit, "offset": offset, "ordering": resolved_ordering},
                result_count=len(chats),
                duration_ms=duration_ms,
                logger_name="app.repositories.ai_chat",
            )
            
            return chats
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"user_id": user_id, "limit": limit, "offset": offset, "method": "list_by_user_id"}
            )
            raise

    async def count_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
        filters: Optional[AIChatFilterParams] = None,
    ) -> int:
        """Count total chats for a user with optional filters."""
        start_time = time.time()
        try:
            stmt: Select[tuple[int]] = (
                select(func.count(self.model.id)).where(self.model.user_id == user_id)
            )
            
            # Apply filters if provided
            if filters:
                stmt = self._apply_filters(stmt, filters)
            
            result = await session.execute(stmt)
            count = result.scalar_one() or 0
            duration_ms = (time.time() - start_time) * 1000
            
            log_database_query(
                query_type="SELECT",
                table=self.model.__tablename__,
                filters={"user_id": user_id, "operation": "count"},
                result_count=count,
                duration_ms=duration_ms,
                logger_name="app.repositories.ai_chat",
            )
            
            return count
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            log_database_error(
                operation="SELECT",
                table=self.model.__tablename__,
                error=exc,
                duration_ms=duration_ms,
                context={"user_id": user_id, "method": "count_by_user_id"}
            )
            raise
    
    def _apply_filters(
        self,
        stmt: Select,
        filters: AIChatFilterParams,
    ) -> Select:
        """Apply filter parameters to the given SQLAlchemy statement."""
        # Title filter (case-insensitive substring match)
        if filters.title:
            stmt = stmt.where(
                func.lower(self.model.title).contains(filters.title.lower())
            )
        
        # Search filter (applied to title and messages)
        if filters.search:
            search_term = filters.search.lower()
            stmt = stmt.where(
                func.lower(self.model.title).contains(search_term)
                # Note: messages is JSON, so we'd need JSONB search for full search
                # For now, just search in title
            )
        
        # Date range filters
        if filters.created_at_after:
            stmt = stmt.where(self.model.created_at >= filters.created_at_after)
        if filters.created_at_before:
            stmt = stmt.where(self.model.created_at <= filters.created_at_before)
        if filters.updated_at_after:
            stmt = stmt.where(self.model.updated_at >= filters.updated_at_after)
        if filters.updated_at_before:
            stmt = stmt.where(self.model.updated_at <= filters.updated_at_before)
        
        return stmt

    async def create_chat(
        self,
        session: AsyncSession,
        user_id: str,
        title: Optional[str] = None,
        messages: Optional[list[dict]] = None,
    ) -> AIChat:
        """Create a new chat."""
        chat = AIChat(
            user_id=user_id,
            title=title or "",
            messages=messages or [],
        )
        session.add(chat)
        await session.flush()
        await session.refresh(chat)
        return chat

    async def update_chat(
        self,
        session: AsyncSession,
        chat: AIChat,
        **kwargs
    ) -> AIChat:
        """Update chat fields."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(chat, key, value)
        await session.flush()
        await session.refresh(chat)
        return chat

    async def delete_chat(self, session: AsyncSession, chat: AIChat) -> None:
        """Delete a chat."""
        await session.delete(chat)
        await session.flush()

