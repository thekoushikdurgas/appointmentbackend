"""Repository for token blacklist operations."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.models.token_blacklist import TokenBlacklist
from app.repositories.base import AsyncRepository
from app.utils.logger import get_logger, log_database_query

logger = get_logger(__name__)


class TokenBlacklistRepository(AsyncRepository[TokenBlacklist]):
    """Data access helpers for token blacklist queries."""

    def __init__(self) -> None:
        """Initialize the repository for the TokenBlacklist model."""
        super().__init__(TokenBlacklist)

    async def create_blacklist_entry(
        self,
        session: AsyncSession,
        token: str,
        user_id: str,
    ) -> TokenBlacklist:
        """
        Create a blacklist entry for a token.
        
        Args:
            session: Database session
            token: JWT refresh token to blacklist
            user_id: User ID who owns the token
            expires_at: Optional expiration time (extracted from token if not provided)
            
        Returns:
            Created TokenBlacklist entry
        """
        # Extract expiration time from token if possible
        expires_at = None
        payload = decode_token(token)
        if payload and "exp" in payload:
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        blacklist_entry = TokenBlacklist(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
        session.add(blacklist_entry)
        await session.flush()
        await session.refresh(blacklist_entry)
        return blacklist_entry

    async def is_token_blacklisted(
        self,
        session: AsyncSession,
        token: str,
    ) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            session: Database session
            token: JWT token to check
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        stmt: Select[tuple[TokenBlacklist]] = select(self.model).where(self.model.token == token)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        is_blacklisted = entry is not None
        return is_blacklisted

    async def cleanup_expired_tokens(
        self,
        session: AsyncSession,
    ) -> int:
        """
        Remove expired tokens from blacklist.
        
        Args:
            session: Database session
            
        Returns:
            Number of tokens removed
        """
        now = datetime.now(timezone.utc)
        stmt = delete(self.model).where(self.model.expires_at < now)
        result = await session.execute(stmt)
        count = result.rowcount
        await session.flush()
        return count

    async def get_by_token(
        self,
        session: AsyncSession,
        token: str,
    ) -> Optional[TokenBlacklist]:
        """Retrieve a blacklist entry by token."""
        stmt: Select[tuple[TokenBlacklist]] = select(self.model).where(self.model.token == token)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        return entry

