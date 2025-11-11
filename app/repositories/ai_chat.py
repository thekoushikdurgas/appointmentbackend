"""Repository providing AI chat-specific query utilities."""

from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ai_chat import AIChat
from app.repositories.base import AsyncRepository

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
        *,
        limit: int = 25,
        offset: int = 0,
        ordering: str = "-created_at",
    ) -> list[AIChat]:
        """List chats for a user with pagination and ordering."""
        logger.debug(
            "Listing chats for user: user_id=%s limit=%d offset=%d ordering=%s",
            user_id,
            limit,
            offset,
            ordering,
        )
        stmt: Select[tuple[AIChat]] = select(self.model).where(self.model.user_id == user_id)

        # Apply ordering
        if ordering.startswith("-"):
            order_field = ordering[1:]
            if hasattr(self.model, order_field):
                stmt = stmt.order_by(getattr(self.model, order_field).desc())
            else:
                logger.warning("Invalid ordering field: %s, using default", ordering)
                stmt = stmt.order_by(self.model.created_at.desc())
        else:
            if hasattr(self.model, ordering):
                stmt = stmt.order_by(getattr(self.model, ordering).asc())
            else:
                logger.warning("Invalid ordering field: %s, using default", ordering)
                stmt = stmt.order_by(self.model.created_at.desc())

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await session.execute(stmt)
        chats = list(result.scalars().all())
        logger.debug("Found %d chats for user_id=%s", len(chats), user_id)
        return chats

    async def count_by_user_id(self, session: AsyncSession, user_id: str) -> int:
        """Count total chats for a user."""
        logger.debug("Counting chats for user: user_id=%s", user_id)
        stmt: Select[tuple[int]] = (
            select(func.count(self.model.id)).where(self.model.user_id == user_id)
        )
        result = await session.execute(stmt)
        count = result.scalar_one() or 0
        logger.debug("Found %d total chats for user_id=%s", count, user_id)
        return count

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

