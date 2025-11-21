"""AI Chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import get_logger, log_function_call
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_chat import (
    AIChatCreate,
    AIChatResponse,
    AIChatUpdate,
    PaginatedAIChatResponse,
)
from app.schemas.filters import AIChatFilterParams
from app.services.ai_chat_service import AIChatService

router = APIRouter(prefix="/ai-chats", tags=["AI Chat"])
logger = get_logger(__name__)
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
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info(
        "List chats request: user_id=%s limit=%d offset=%d ordering=%s",
        current_user.id,
        limit,
        offset,
        ordering,
    )

    try:
        # Use filters for pagination and ordering if provided
        resolved_limit = filters.page_size if filters.page_size is not None else limit
        resolved_offset = offset
        if filters.page is not None:
            resolved_offset = (filters.page - 1) * resolved_limit
        resolved_ordering = filters.ordering if filters.ordering is not None else ordering
        
        result = await service.list_chats(
            session,
            current_user.id,
            filters=filters,
            limit=resolved_limit,
            offset=resolved_offset,
            ordering=resolved_ordering,
            request_url=str(request.url),
        )
        logger.info("Listed chats: user_id=%s count=%d", current_user.id, result.count)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("List chats failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc


@router.post("/", response_model=AIChatResponse, status_code=status.HTTP_201_CREATED)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Create chat request: user_id=%s", current_user.id)

    try:
        result = await service.create_chat(session, current_user.id, chat_data)
        logger.info("Chat created: id=%s user_id=%s", result.id, current_user.id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Create chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data"
        ) from exc


@router.get("/{chat_id}/", response_model=AIChatResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.debug("Get chat request: id=%s user_id=%s", chat_id, current_user.id)

    try:
        result = await service.get_chat(session, chat_id, current_user.id)
        logger.debug("Chat retrieved: id=%s", chat_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Get chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc


@router.put("/{chat_id}/", response_model=AIChatResponse)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Update chat request: id=%s user_id=%s", chat_id, current_user.id)

    try:
        result = await service.update_chat(session, chat_id, current_user.id, update_data)
        logger.info("Chat updated: id=%s", chat_id)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Update chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request data"
        ) from exc


@router.delete("/{chat_id}/", status_code=status.HTTP_204_NO_CONTENT)
@log_function_call(logger=logger, log_arguments=True, log_result=True)
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
    logger.info("Delete chat request: id=%s user_id=%s", chat_id, current_user.id)

    try:
        await service.delete_chat(session, chat_id, current_user.id)
        logger.info("Chat deleted: id=%s", chat_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Delete chat failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        ) from exc

