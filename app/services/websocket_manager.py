"""WebSocket connection manager for real-time chat."""

from typing import Dict, Set

from fastapi import WebSocket

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for chat sessions."""

    def __init__(self):
        """Initialize connection manager."""
        # Map of chat_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of WebSocket -> chat_id for quick lookup
        self.connection_to_chat: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, chat_id: str) -> None:
        """
        Accept a WebSocket connection and register it for a chat.
        
        Args:
            websocket: WebSocket connection
            chat_id: Chat ID this connection belongs to
        """
        await websocket.accept()
        
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = set()
        
        self.active_connections[chat_id].add(websocket)
        self.connection_to_chat[websocket] = chat_id

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        chat_id = self.connection_to_chat.pop(websocket, None)
        
        if chat_id and chat_id in self.active_connections:
            self.active_connections[chat_id].discard(websocket)
            
            # Clean up empty chat sets
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Message dict to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            # Remove dead connection
            self.disconnect(websocket)
            raise

    async def send_to_chat(self, message: dict, chat_id: str) -> None:
        """
        Send a message to all connections in a specific chat.
        
        Args:
            message: Message dict to send
            chat_id: Chat ID to broadcast to
        """
        if chat_id not in self.active_connections:
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = list(self.active_connections[chat_id])
        dead_connections = []
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)

    def get_chat_connections_count(self, chat_id: str) -> int:
        """
        Get the number of active connections for a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(chat_id, set()))

    def get_total_connections_count(self) -> int:
        """
        Get the total number of active connections across all chats.
        
        Returns:
            Total number of active connections
        """
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager instance."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager

