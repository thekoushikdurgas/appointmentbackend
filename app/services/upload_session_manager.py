"""Upload session manager for tracking multipart upload sessions.

This module provides in-memory session management for multipart uploads.
Designed with Redis-compatible interface for easy migration to Redis in production.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional

from app.core.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class UploadSession:
    """Represents an active upload session."""

    def __init__(
        self,
        upload_id: str,
        file_key: str,
        file_size: int,
        s3_upload_id: str,
        chunk_size: int = 100 * 1024 * 1024,
    ):
        """
        Initialize upload session.

        Args:
            upload_id: Unique upload identifier
            file_key: S3 object key (path)
            file_size: Total file size in bytes
            s3_upload_id: S3 multipart upload ID
            chunk_size: Chunk size in bytes (default: 100MB)
        """
        self.upload_id = upload_id
        self.file_key = file_key
        self.file_size = file_size
        self.s3_upload_id = s3_upload_id
        self.chunk_size = chunk_size
        self.parts: Dict[int, str] = {}  # part_number -> ETag
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.status = "in_progress"  # in_progress, completed, aborted


class UploadSessionManager:
    """In-memory upload session manager with Redis-compatible interface."""

    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        """
        Initialize session manager.

        Args:
            ttl_seconds: Time-to-live for sessions in seconds (default: 86400 = 24 hours)
        """
        self._sessions: Dict[str, UploadSession] = {}
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    async def create_session(self, session: UploadSession) -> None:
        """
        Create a new upload session.

        Args:
            session: UploadSession instance to store
        """
        async with self._lock:
            self._sessions[session.upload_id] = session

    async def get_session(self, upload_id: str) -> Optional[UploadSession]:
        """
        Get an upload session by ID.

        Args:
            upload_id: Session identifier

        Returns:
            UploadSession if found and not expired, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(upload_id)
            if session:
                # Check if expired
                now = datetime.utcnow()
                if (now - session.updated_at).total_seconds() > self._ttl:
                    # Session expired, remove it
                    del self._sessions[upload_id]
                    return None
            return session

    async def update_part(self, upload_id: str, part_number: int, etag: str) -> None:
        """
        Update session with uploaded part information.

        Args:
            upload_id: Session identifier
            part_number: Part number (1-indexed)
            etag: ETag from S3 for this part
        """
        async with self._lock:
            if session := self._sessions.get(upload_id):
                session.parts[part_number] = etag
                session.updated_at = datetime.utcnow()

    async def delete_session(self, upload_id: str) -> None:
        """
        Delete an upload session.

        Args:
            upload_id: Session identifier
        """
        async with self._lock:
            self._sessions.pop(upload_id, None)

    async def cleanup_expired(self) -> int:
        """
        Remove expired sessions (TTL-based).

        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                uid
                for uid, sess in self._sessions.items()
                if (now - sess.updated_at).total_seconds() > self._ttl
            ]
            for uid in expired:
                del self._sessions[uid]
            return len(expired)


# Singleton instance
_upload_manager: Optional[UploadSessionManager] = None


def get_upload_manager() -> UploadSessionManager:
    """Get the singleton upload session manager instance."""
    global _upload_manager
    if _upload_manager is None:
        ttl = getattr(settings, "UPLOAD_SESSION_TTL", 86400)
        _upload_manager = UploadSessionManager(ttl_seconds=ttl)
    return _upload_manager

