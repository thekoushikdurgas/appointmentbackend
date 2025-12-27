"""Repository for email pattern operations."""

from typing import Optional, Sequence

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_patterns import EmailPattern
from app.repositories.base import AsyncRepository
from app.utils.logger import get_logger, log_database_query

logger = get_logger(__name__)


class EmailPatternRepository(AsyncRepository[EmailPattern]):
    """Data access helpers for email pattern queries."""

    def __init__(self) -> None:
        """Initialize the repository for the EmailPattern model."""
        super().__init__(EmailPattern)

    async def get_by_company_uuid(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> Sequence[EmailPattern]:
        """Get all email patterns for a company."""
        stmt: Select[tuple[EmailPattern]] = (
            select(self.model)
            .where(self.model.company_uuid == company_uuid)
            .order_by(self.model.contact_count.desc(), self.model.created_at.desc())
        )
        result = await session.execute(stmt)
        patterns = result.scalars().all()
        return patterns

    async def get_by_pattern_format(
        self,
        session: AsyncSession,
        company_uuid: str,
        pattern_format: str,
    ) -> Optional[EmailPattern]:
        """Find a pattern by format and company UUID."""
        stmt: Select[tuple[EmailPattern]] = select(self.model).where(
            self.model.company_uuid == company_uuid,
            self.model.pattern_format == pattern_format,
        )
        result = await session.execute(stmt)
        pattern = result.scalar_one_or_none()
        return pattern

    async def increment_contact_count(
        self,
        session: AsyncSession,
        pattern_uuid: str,
        increment: int = 1,
    ) -> Optional[EmailPattern]:
        """
        Atomically increment the contact count for a pattern.
        
        Uses database-level atomic update to prevent race conditions.
        """
        # Use atomic database update to prevent race conditions
        stmt = (
            update(EmailPattern)
            .where(EmailPattern.uuid == pattern_uuid)
            .values(
                contact_count=func.coalesce(EmailPattern.contact_count, 0) + increment
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        # Don't commit here - let the service layer handle commits
        
        # Fetch updated pattern (refresh from database)
        pattern = await self.get_by_uuid(session, pattern_uuid)
        return pattern

    async def increment_contact_count_by_pattern_format(
        self,
        session: AsyncSession,
        company_uuid: str,
        pattern_format: str,
        increment: int = 1,
    ) -> Optional[EmailPattern]:
        """
        Atomically increment the contact count for a pattern by company and format.
        
        Uses database-level atomic update to prevent race conditions.
        This is useful when you have company_uuid and pattern_format but not pattern_uuid.
        """
        # Use atomic database update to prevent race conditions
        stmt = (
            update(EmailPattern)
            .where(
                EmailPattern.company_uuid == company_uuid,
                EmailPattern.pattern_format == pattern_format,
            )
            .values(
                contact_count=func.coalesce(EmailPattern.contact_count, 0) + increment
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        # Don't commit here - let the service layer handle commits
        
        # Fetch updated pattern (refresh from database)
        pattern = await self.get_by_pattern_format(session, company_uuid, pattern_format)
        return pattern

    async def decrement_contact_count(
        self,
        session: AsyncSession,
        pattern_uuid: str,
        decrement: int = 1,
    ) -> Optional[EmailPattern]:
        """
        Atomically decrement the contact count for a pattern.
        
        Uses database-level atomic update to prevent race conditions.
        Contact count will not go below 0.
        """
        # Use atomic database update with max(0, ...) to prevent negative values
        stmt = (
            update(EmailPattern)
            .where(EmailPattern.uuid == pattern_uuid)
            .values(
                contact_count=func.greatest(
                    func.coalesce(EmailPattern.contact_count, 0) - decrement,
                    0
                )
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt)
        # Don't commit here - let the service layer handle commits
        
        # Fetch updated pattern (refresh from database)
        pattern = await self.get_by_uuid(session, pattern_uuid)
        return pattern

    async def get_patterns_with_stats(
        self,
        session: AsyncSession,
        company_uuid: str,
    ) -> tuple[Sequence[EmailPattern], int]:
        """Get patterns for a company with aggregated statistics."""
        patterns = await self.get_by_company_uuid(session, company_uuid)
        total_contacts = sum(p.contact_count or 0 for p in patterns)
        return patterns, total_contacts

