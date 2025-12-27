"""Service layer for AI chat conversation management."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ai_chat import AIChatRepository
from app.schemas.ai_chat import (
    AIChatCreate,
    AIChatListItem,
    AIChatResponse,
    AIChatUpdate,
    Message,
    PaginatedAIChatResponse,
)
from app.schemas.filters import AIChatFilterParams
from app.services.gemini_service import GeminiService
from app.utils.logger import get_logger
from app.utils.pagination import build_pagination_link

logger = get_logger(__name__)


class AIChatService:
    """Business logic for AI chat conversation management."""

    def __init__(
        self,
        repository: Optional[AIChatRepository] = None,
        gemini_service: Optional[GeminiService] = None,
    ) -> None:
        """Initialize the service with repository dependency."""
        self.repository = repository or AIChatRepository()
        self.gemini_service = gemini_service or GeminiService()

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

        return AIChatResponse(
            uuid=chat.uuid,
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
        chat = await self.repository.get_by_uuid_and_user_uuid(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_uuid(session, chat_id)
            if existing_chat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this chat."
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )

        return AIChatResponse(
            uuid=chat.uuid,
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
        filters: Optional[AIChatFilterParams] = None,
        *,
        limit: int = 25,
        offset: int = 0,
        ordering: str = "-created_at",
        request_url: str,
    ) -> PaginatedAIChatResponse:
        """List user's chats with pagination and ordering."""
        # Validate and clamp limit
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 25

        # Get chats and count
        chats = await self.repository.list_by_user_id(
            session,
            user_id,
            filters=filters,
            limit=limit,
            offset=offset,
            ordering=ordering,
        )
        total_count = await self.repository.count_by_user_id(session, user_id, filters=filters)

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
                uuid=chat.uuid,
                title=chat.title or "",
                created_at=chat.created_at,
                updated_at=chat.updated_at,
            )
            for chat in chats
        ]

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
        # Get chat with ownership check
        chat = await self.repository.get_by_uuid_and_user_uuid(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_uuid(session, chat_id)
            if existing_chat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to update this chat."
                )
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

        return AIChatResponse(
            uuid=chat.uuid,
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
        # Get chat with ownership check
        chat = await self.repository.get_by_uuid_and_user_uuid(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_uuid(session, chat_id)
            if existing_chat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to delete this chat."
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )

        # Delete chat
        await self.repository.delete_chat(session, chat)

    async def send_message(
        self,
        session: AsyncSession,
        chat_id: str,
        user_id: str,
        user_message: str,
        model_name: Optional[str] = None,
    ) -> AIChatResponse:
        """
        Send a user message and generate AI response using proper chat session management.
        
        Args:
            session: Database session
            chat_id: Chat ID
            user_id: User ID (for ownership verification)
            user_message: User's message text
            model_name: Optional model name override
            
        Returns:
            Updated chat with user message and AI response
        """
        # Get chat with ownership check
        chat = await self.repository.get_by_uuid_and_user_uuid(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_uuid(session, chat_id)
            if existing_chat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to send messages in this chat."
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )
        
        # Get current messages
        current_messages = chat.messages or []
        
        # Add user message
        user_msg = {"sender": "user", "text": user_message}
        updated_messages = current_messages + [user_msg]
        
        # Generate AI response using chat session with conversation_id
        try:
            ai_response_text = await self.gemini_service.generate_chat_response(
                user_message=user_message,
                chat_history=current_messages,
                conversation_id=chat_id,  # Use chat_id as conversation_id for session management
                model_name=model_name,
            )
            ai_msg = {"sender": "ai", "text": ai_response_text}
            updated_messages.append(ai_msg)
        except Exception as exc:
            # Add error message instead of failing completely
            ai_msg = {
                "sender": "ai",
                "text": "I apologize, but I'm having trouble processing your request right now. Please try again later."
            }
            updated_messages.append(ai_msg)
        
        # Update chat with new messages
        await self.repository.update_chat(session, chat, messages=updated_messages)
        await session.refresh(chat)
        
        return AIChatResponse(
            uuid=chat.uuid,
            user_id=chat.user_id,
            title=chat.title or "",
            messages=chat.messages or [],
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def send_message_stream(
        self,
        session: AsyncSession,
        chat_id: str,
        user_id: str,
        user_message: str,
        model_name: Optional[str] = None,
    ):
        """
        Send a user message and stream AI response chunks.
        
        Args:
            session: Database session
            chat_id: Chat ID
            user_id: User ID (for ownership verification)
            user_message: User's message text
            model_name: Optional model name override
            
        Yields:
            Chunks of AI response text
        """
        # Get chat with ownership check
        chat = await self.repository.get_by_uuid_and_user_uuid(session, chat_id, user_id)
        if not chat:
            # Check if chat exists but belongs to another user
            existing_chat = await self.repository.get_by_uuid(session, chat_id)
            if existing_chat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to send messages in this chat."
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found."
            )
        
        # Get current messages
        current_messages = chat.messages or []
        
        # Add user message to chat (we'll add AI response after streaming completes)
        user_msg = {"sender": "user", "text": user_message}
        updated_messages = current_messages + [user_msg]
        
        # Stream AI response
        ai_response_text = ""
        try:
            async for chunk in self.gemini_service.generate_chat_response_stream(
                user_message=user_message,
                chat_history=current_messages,
                conversation_id=chat_id,
                model_name=model_name,
            ):
                ai_response_text += chunk
                yield chunk
        except Exception as exc:
            error_msg = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            ai_response_text = error_msg
            yield error_msg
        
        # Update chat with complete conversation after streaming
        ai_msg = {"sender": "ai", "text": ai_response_text}
        updated_messages.append(ai_msg)
        await self.repository.update_chat(session, chat, messages=updated_messages)

