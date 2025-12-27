"""AI Chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.middleware.rate_limit import rate_limit_by_user
from app.models.user import User
from app.schemas.ai_chat import (
    AIChatCreate,
    AIChatMessageRequest,
    AIChatResponse,
    AIChatUpdate,
    ChatStreamRequest,
    PaginatedAIChatResponse,
)
from app.schemas.filters import AIChatFilterParams
from app.services.ai_chat_service import AIChatService
from app.utils.logger import get_logger, log_api_error

logger = get_logger(__name__)
router = APIRouter(prefix="/ai-chats", tags=["AI Chat"])
service = AIChatService()


async def resolve_ai_chat_filters(request: Request) -> AIChatFilterParams:
    """Build AI chat filter parameters from query string."""
    query_params = request.query_params
    data = dict(query_params)
    try:
        return AIChatFilterParams.model_validate(data)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Invalid query parameters")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/", response_model=PaginatedAIChatResponse)
async def list_chats(
    request: Request,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    limit: int = Query(25, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    ordering: str = Query(
        "-created_at",
        description="Order by field. Prepend '-' for descending. Valid: created_at, updated_at, -created_at, -updated_at"
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedAIChatResponse:
    """
    Get a list of all AI chat conversations for the current user with pagination.
    
    Only returns chats owned by the authenticated user.
    Default ordering is by -created_at (newest first).
    """
    # List chats for authenticated user

    try:
        # Use filters for pagination and ordering if provided
        resolved_limit = filters.page_size if filters.page_size is not None else limit
        resolved_offset = offset
        if filters.page is not None:
            resolved_offset = (filters.page - 1) * resolved_limit
        resolved_ordering = filters.ordering if filters.ordering is not None else ordering
        
        result = await service.list_chats(
            session,
            current_user.uuid,
            filters=filters,
            limit=resolved_limit,
            offset=resolved_offset,
            ordering=resolved_ordering,
            request_url=str(request.url),
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc


@router.post("/", response_model=AIChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: AIChatCreate,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    """
    Create a new AI chat conversation.
    
    The user is automatically set from the authenticated user's token.
    The chat ID is a UUID generated automatically.
    Messages can be empty initially and added later via update.
    """
    # Create new AI chat conversation
    try:
        result = await service.create_chat(session, current_user.uuid, chat_data)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to create chat
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data"
        ) from exc


@router.get("/{chat_id}/", response_model=AIChatResponse)
async def get_chat(
    chat_id: str,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    """
    Get detailed information about a specific AI chat conversation, including all messages.
    
    Only the chat owner can access their chats.
    """
    # Get chat details for authenticated user
    try:
        result = await service.get_chat(session, chat_id, current_user.uuid)
        return result
    except HTTPException as exc:
        if exc.status_code == 404:
            log_api_error(
                endpoint=f"/api/v2/ai-chats/{chat_id}/",
                method="GET",
                status_code=404,
                error_type="NotFoundException",
                error_message=f"AI chat not found: {chat_id}",
                user_id=str(current_user.uuid),
                context={"chat_id": chat_id}
            )
        raise
    except Exception as exc:
        # Failed to get chat
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc


@router.put("/{chat_id}/", response_model=AIChatResponse)
async def update_chat(
    chat_id: str,
    update_data: AIChatUpdate,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    """
    Update an existing AI chat conversation (typically to add new messages or update the title).
    
    All fields are optional - only provided fields will be updated (partial update).
    When updating messages, provide the complete messages array (it replaces existing messages).
    Only the chat owner can update their chats.
    """
    # Update existing AI chat conversation
    try:
        result = await service.update_chat(session, chat_id, current_user.uuid, update_data)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to update chat
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data"
        ) from exc


@router.post("/{chat_id}/message", response_model=AIChatResponse)
async def send_message(
    chat_id: str,
    message_data: AIChatMessageRequest,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_by_user),  # Rate limiting
) -> AIChatResponse:
    """
    Send a message in a chat and get AI response.
    
    This endpoint adds the user's message to the chat, generates an AI response
    using Gemini, and returns the updated chat with both messages.
    Only the chat owner can send messages.
    """
    # Send message in chat and get AI response
    try:
        model_name = message_data.model.value if message_data.model else None
        result = await service.send_message(
            session,
            chat_id,
            current_user.uuid,
            message_data.message,
            model_name=model_name,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to send message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc


@router.post("/{chat_id}/message/stream")
async def send_message_stream(
    chat_id: str,
    stream_request: ChatStreamRequest,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_by_user),  # Rate limiting
) -> StreamingResponse:
    """
    Send a message in a chat and stream AI response using Server-Sent Events (SSE).
    
    This endpoint streams the AI response as it's generated, providing a better
    user experience for longer responses. The response is sent as Server-Sent Events.
    
    Only the chat owner can send messages.
    """
    # Send message in chat and stream AI response using SSE

    async def generate_stream():
        """Generator function for streaming response."""
        try:
            model_name = stream_request.model.value if stream_request.model else None
            async for chunk in service.send_message_stream(
                session=session,
                chat_id=chat_id,
                user_id=current_user.uuid,
                user_message=stream_request.message,
                model_name=model_name,
            ):
                # Format as SSE
                yield f"data: {chunk}\n\n"
            
            # Send completion marker
            yield "data: [DONE]\n\n"
        except HTTPException:
            raise
        except Exception as exc:
            # Failed to send message (streaming)
            yield f"data: Error: {str(exc)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.delete("/{chat_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    filters: AIChatFilterParams = Depends(resolve_ai_chat_filters),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete an AI chat conversation.
    
    Only the chat owner can delete their chats.
    Deletion is permanent and cannot be undone.
    """
    # Delete AI chat conversation
    try:
        await service.delete_chat(session, chat_id, current_user.uuid)
    except HTTPException:
        raise
    except Exception as exc:
        # Failed to delete chat
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc

