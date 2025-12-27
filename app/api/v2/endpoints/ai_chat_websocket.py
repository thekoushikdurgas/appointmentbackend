"""WebSocket endpoints for real-time AI chat."""

import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.ai_chat import ModelSelection
from app.services.ai_chat_service import AIChatService
from app.services.websocket_manager import get_connection_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ai-chats", tags=["AI Chat WebSocket"])
service = AIChatService()
manager = get_connection_manager()


async def get_user_from_token(token: Optional[str] = None) -> Optional[User]:
    """
    Get user from JWT token for WebSocket authentication.
    
    Args:
        token: JWT token from query parameter or header
        
    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Get user from database
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository()
            user = await user_repo.get_by_uuid(session, user_id)
            return user
    except Exception as e:
        return None


@router.websocket("/ws/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: str,
    token: Optional[str] = Query(None, description="JWT token for authentication"),
):
    """
    WebSocket endpoint for real-time AI chat with streaming responses.
    
    Authentication:
    - Pass JWT token as query parameter: ?token=<your_jwt_token>
    - Or include in Authorization header (if supported by client)
    
    Message Format:
    - Send: {"message": "user message text", "model": "gemini-1.5-flash"} (model optional)
    - Receive: {"type": "chunk", "data": "text chunk"} or {"type": "complete", "data": "full response"}
    """
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Verify chat ownership
    async with AsyncSessionLocal() as session:
        chat = await service.repository.get_by_uuid_and_user_uuid(session, chat_id, user.uuid)
        if not chat:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    
    # Connect to manager
    try:
        await manager.connect(websocket, chat_id)
        
        # Send connection confirmation
        await manager.send_personal_message(
            {
                "type": "connected",
                "chat_id": chat_id,
                "message": "Connected to chat",
            },
            websocket,
        )
    except Exception as e:
        await websocket.close()
        return
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "").strip()
                model_name = message_data.get("model")
                
                if not user_message:
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": "Message cannot be empty",
                        },
                        websocket,
                    )
                    continue
                
                # Convert model enum if provided
                if model_name and isinstance(model_name, str):
                    try:
                        model_enum = ModelSelection(model_name)
                        model_name = model_enum.value
                    except ValueError:
                        model_name = None
                
                # Send acknowledgment
                await manager.send_personal_message(
                    {
                        "type": "message_received",
                        "message": "Processing your message...",
                    },
                    websocket,
                )
                
                # Get database session for streaming
                async with AsyncSessionLocal() as session:
                    # Stream AI response
                    full_response = ""
                    async for chunk in service.send_message_stream(
                        session=session,
                        chat_id=chat_id,
                        user_id=user.uuid,
                        user_message=user_message,
                        model_name=model_name,
                    ):
                        full_response += chunk
                        # Send chunk to client
                        await manager.send_personal_message(
                            {
                                "type": "chunk",
                                "data": chunk,
                            },
                            websocket,
                        )
                    
                    # Send completion message
                    await manager.send_personal_message(
                        {
                            "type": "complete",
                            "data": full_response,
                        },
                        websocket,
                    )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    },
                    websocket,
                )
            except Exception as e:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "An error occurred while processing your message",
                    },
                    websocket,
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except Exception:
            pass

