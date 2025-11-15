"""Service layer for AI chat conversation management."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.ai_chat import AIChatRepository
from app.schemas.ai_chat import (
    AIChatCreate,
    AIChatListItem,
    AIChatResponse,
    AIChatUpdate,
    Message,
    PaginatedAIChatResponse,
)
from app.utils.pagination import build_pagination_link

logger = get_logger(__name__)


class AIChatService:
    """Business logic for AI chat conversation management."""

    def __init__(self, repository: Optional[AIChatRepository] = None) -> None:
        """Initialize the service with repository dependency."""
        logger.debug("Entering AIChatService.__init__")
        self.repository = repository or AIChatRepository()
        logger.debug("Exiting AIChatService.__init__")

    def _validate_messages(self, messages: Optional[list[Message]]) -> None:
        """Validate message format."""
        if messages is None:
            return

        if not isinstance(messages, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"messages": ["Messages must be a list"]}
            )

        for msg in messages:
            # Messages can be Pydantic models or dicts
            if isinstance(msg, Message):
                # Pydantic model - validation already done by schema
                continue
            elif isinstance(msg, dict):
                # Dict - validate structure
                if "sender" not in msg or "text" not in msg:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"messages": ["Each message must have 'sender' and 'text' fields"]}
                    )
                if msg["sender"] not in ("user", "ai"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"messages": ["Sender must be 'user' or 'ai'"]}
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"messages": ["Each message must be a dictionary"]}
                )

    def _convert_messages_to_dict(self, messages: Optional[list[Message]]) -> list[dict]:
        """Convert Pydantic Message objects to dictionaries for JSON storage."""
        if not messages:
            return []
        return [msg.model_dump() for msg in messages]

    async def create_chat(
        self,
        session: AsyncSession,
        user_id: str,
        chat_data: AIChatCreate,
    ) -> AIChatResponse:
        """Create a new AI chat conversation."""
        logger.debug("Creating chat: user_id=%s", user_id)

        # Validate messages if provided
        if chat_data.messages:
            self._validate_messages(chat_data.messages)

        # Convert messages to dict for storage
        messages_dict = self._convert_messages_to_dict(chat_data.messages)

        # Create chat
        chat = await self.repository.create_chat(
            session,
            user_id=user_id,
            title=chat_data.title or "",
            messages=messages_dict,
        )

        # logger.info("Chat created: id=%s user_id=%s", chat.id, chat.user_id)
        return AIChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title or "",
            messages=chat.messages or [],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def get_chat(
        self,
        session: AsyncSession,
        chat_id: str,
        user_id: str,
    ) -> AIChatResponse:
        """Get a specific chat with ownership verification."""
        logger.debug("Getting chat: id=%s user_id=%s", chat_id, user_id)

        chat = await self.repository.get_by_id_and_user_id(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_id(session, chat_id)
            if existing_chat:
                logger.warning("Access denied: chat belongs to different user: id=%s", chat_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this chat."
                )
            logger.warning("Chat not found: id=%s", chat_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )

        logger.debug("Chat retrieved: id=%s", chat_id)
        return AIChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title or "",
            messages=chat.messages or [],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def list_chats(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        limit: int = 25,
        offset: int = 0,
        ordering: str = "-created_at",
        request_url: str,
    ) -> PaginatedAIChatResponse:
        """List user's chats with pagination and ordering."""
        logger.debug(
            "Listing chats: user_id=%s limit=%d offset=%d ordering=%s",
            user_id,
            limit,
            offset,
            ordering,
        )

        # Validate and clamp limit
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 25

        # Get chats and count
        chats = await self.repository.list_by_user_id(
            session,
            user_id,
            limit=limit,
            offset=offset,
            ordering=ordering,
        )
        total_count = await self.repository.count_by_user_id(session, user_id)

        # Build pagination links
        next_link = None
        if offset + limit < total_count:
            next_link = build_pagination_link(
                request_url,
                limit=limit,
                offset=offset + limit,
            )

        previous_link = None
        if offset > 0:
            previous_link = build_pagination_link(
                request_url,
                limit=limit,
                offset=max(0, offset - limit),
            )

        # Convert to list items
        results = [
            AIChatListItem(
                id=chat.id,
                title=chat.title or "",
                created_at=chat.created_at,
                updated_at=chat.updated_at,
            )
            for chat in chats
        ]

        # logger.info(
        #     "Listed chats: user_id=%s returned=%d total=%d",
        #     user_id,
        #     len(results),
        #     total_count,
        # )

        return PaginatedAIChatResponse(
            count=total_count,
            next=next_link,
            previous=previous_link,
            results=results,
        )

    async def update_chat(
        self,
        session: AsyncSession,
        chat_id: str,
        user_id: str,
        update_data: AIChatUpdate,
    ) -> AIChatResponse:
        """Update a chat with ownership verification."""
        logger.debug("Updating chat: id=%s user_id=%s", chat_id, user_id)

        # Get chat with ownership check
        chat = await self.repository.get_by_id_and_user_id(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_id(session, chat_id)
            if existing_chat:
                logger.warning("Update denied: chat belongs to different user: id=%s", chat_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to update this chat."
                )
            logger.warning("Chat not found: id=%s", chat_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )

        # Validate messages if provided
        if update_data.messages is not None:
            self._validate_messages(update_data.messages)

        # Prepare update dict (only non-None fields)
        update_dict = {}
        if update_data.title is not None:
            update_dict["title"] = update_data.title
        if update_data.messages is not None:
            update_dict["messages"] = self._convert_messages_to_dict(update_data.messages)

        # Update chat
        if update_dict:
            await self.repository.update_chat(session, chat, **update_dict)
            await session.refresh(chat)

        # logger.info("Chat updated: id=%s", chat_id)
        return AIChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title or "",
            messages=chat.messages or [],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def delete_chat(
        self,
        session: AsyncSession,
        chat_id: str,
        user_id: str,
    ) -> None:
        """Delete a chat with ownership verification."""
        logger.debug("Deleting chat: id=%s user_id=%s", chat_id, user_id)

        # Get chat with ownership check
        chat = await self.repository.get_by_id_and_user_id(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_id(session, chat_id)
            if existing_chat:
                logger.warning("Delete denied: chat belongs to different user: id=%s", chat_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to delete this chat."
                )
            logger.warning("Chat not found: id=%s", chat_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )

        # Delete chat
        await self.repository.delete_chat(session, chat)
        # logger.info("Chat deleted: id=%s", chat_id)

