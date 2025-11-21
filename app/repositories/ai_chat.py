"""Repository providing AI chat-specific query utilities."""

from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from sqlalchemy import func

from app.core.logging import get_logger
from app.models.ai_chat import AIChat
from app.repositories.base import AsyncRepository
from app.schemas.filters import AIChatFilterParams

logger = get_logger(__name__)


class AIChatRepository(AsyncRepository[AIChat]):
    """Data access helpers for AI chat queries."""

    def __init__(self) -> None:
        """Initialize the repository for the AIChat model."""
        logger.debug("Entering AIChatRepository.__init__")
        super().__init__(AIChat)
        logger.debug("Exiting AIChatRepository.__init__")

    async def get_by_id(self, session: AsyncSession, chat_id: str) -> Optional[AIChat]:
        """Retrieve a chat by its ID (UUID string)."""
        logger.debug("Getting chat by ID: id=%s", chat_id)
        stmt: Select[tuple[AIChat]] = select(self.model).where(self.model.id == chat_id)
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        logger.debug("Chat %sfound for id=%s", "" if chat else "not ", chat_id)
        return chat

    async def get_by_id_and_user_id(
        self, session: AsyncSession, chat_id: str, user_id: str
    ) -> Optional[AIChat]:
        """Retrieve a chat by ID and user ID (for ownership verification)."""
        logger.debug("Getting chat by ID and user_id: id=%s user_id=%s", chat_id, user_id)
        stmt: Select[tuple[AIChat]] = select(self.model).where(
            self.model.id == chat_id, self.model.user_id == user_id
        )
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
        logger.debug(
            "Chat %sfound for id=%s user_id=%s", "" if chat else "not ", chat_id, user_id
        )
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
        logger.debug(
            "Listing chats for user: user_id=%s limit=%d offset=%d ordering=%s filters=%s",
            user_id,
            limit,
            offset,
            ordering,
            filters.model_dump(exclude_none=True) if filters else None,
        )
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
                logger.warning("Invalid ordering field: %s, using default", resolved_ordering)
                stmt = stmt.order_by(self.model.created_at.desc())
        else:
            if hasattr(self.model, resolved_ordering):
                stmt = stmt.order_by(getattr(self.model, resolved_ordering).asc())
            else:
                logger.warning("Invalid ordering field: %s, using default", resolved_ordering)
                stmt = stmt.order_by(self.model.created_at.desc())

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        chats = list(result.scalars().all())
        logger.debug("Found %d chats for user_id=%s", len(chats), user_id)
        return chats

    async def count_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
        filters: Optional[AIChatFilterParams] = None,
    ) -> int:
        """Count total chats for a user with optional filters."""
        logger.debug(
            "Counting chats for user: user_id=%s filters=%s",
            user_id,
            filters.model_dump(exclude_none=True) if filters else None,
        )
        stmt: Select[tuple[int]] = (
            select(func.count(self.model.id)).where(self.model.user_id == user_id)
        )
        
        # Apply filters if provided
        if filters:
            stmt = self._apply_filters(stmt, filters)
        
        result = await session.execute(stmt)
        count = result.scalar_one() or 0
        logger.debug("Found %d total chats for user_id=%s", count, user_id)
        return count
    
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
        logger.debug("Creating chat: user_id=%s", user_id)
        chat = AIChat(
            user_id=user_id,
            title=title or "",
            messages=messages or [],
        )
        session.add(chat)
        await session.flush()
        await session.refresh(chat)
        logger.debug("Created chat: id=%s user_id=%s", chat.id, chat.user_id)
        return chat

    async def update_chat(
        self,
        session: AsyncSession,
        chat: AIChat,
        **kwargs
    ) -> AIChat:
        """Update chat fields."""
        logger.debug("Updating chat: id=%s fields=%s", chat.id, list(kwargs.keys()))
        for key, value in kwargs.items():
            if value is not None:
                setattr(chat, key, value)
        await session.flush()
        await session.refresh(chat)
        logger.debug("Updated chat: id=%s", chat.id)
        return chat

    async def delete_chat(self, session: AsyncSession, chat: AIChat) -> None:
        """Delete a chat."""
        logger.debug("Deleting chat: id=%s", chat.id)
        await session.delete(chat)
        await session.flush()
        logger.debug("Deleted chat: id=%s", chat.id)

