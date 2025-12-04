"""Repository providing user scraping query utilities."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user_scraping import UserScraping
from app.repositories.base import AsyncRepository
from app.utils.validation import is_valid_uuid

logger = get_logger(__name__)


class UserScrapingRepository(AsyncRepository[UserScraping]):
    """Data access helpers for user scraping queries."""

    def __init__(self) -> None:
        """Initialize the repository for the UserScraping model."""
        logger.debug("Entering UserScrapingRepository.__init__")
        super().__init__(UserScraping)
        logger.debug("Exiting UserScrapingRepository.__init__")

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        timestamp: datetime,
        version: str,
        source: str,
        search_context: Optional[dict] = None,
        pagination: Optional[dict] = None,
        user_info: Optional[dict] = None,
        application_info: Optional[dict] = None,
    ) -> UserScraping:
        """
        Create a new user scraping record.
        
        Args:
            session: Database session
            user_id: User ID (must be a valid UUID format)
            timestamp: Timestamp of the scraping operation
            version: Version of the extraction logic
            source: Source identifier (e.g., "api_request")
            search_context: Optional search context metadata as dict
            pagination: Optional pagination metadata as dict
            user_info: Optional user info metadata as dict
            application_info: Optional application info metadata as dict
            
        Returns:
            Created UserScraping record
            
        Raises:
            ValueError: If user_id is not a valid UUID format
        """
        # Validate user_id is a valid UUID format
        if not is_valid_uuid(user_id):
            raise ValueError(f"user_id must be a valid UUID format, got: {user_id}")
        
        logger.debug("Creating user scraping record: user_id=%s timestamp=%s version=%s source=%s", 
                    user_id, timestamp, version, source)
        scraping = UserScraping(
            user_id=user_id,
            timestamp=timestamp,
            version=version,
            source=source,
            search_context=search_context,
            pagination=pagination,
            user_info=user_info,
            application_info=application_info,
        )
        session.add(scraping)
        await session.flush()
        await session.refresh(scraping)
        logger.debug("Created user scraping record: id=%d user_id=%s", scraping.id, scraping.user_id)
        return scraping

    async def get_by_id(
        self,
        session: AsyncSession,
        scraping_id: int,
    ) -> Optional[UserScraping]:
        """Get a single scraping record by ID."""
        logger.debug("Getting user scraping by id: id=%d", scraping_id)
        stmt: Select[tuple[UserScraping]] = select(self.model).where(self.model.id == scraping_id)
        result = await session.execute(stmt)
        scraping = result.scalar_one_or_none()
        logger.debug("User scraping %sfound for id=%d", "" if scraping else "not ", scraping_id)
        return scraping

    async def list_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[UserScraping], int]:
        """
        List scraping records for a user with pagination.
        
        Args:
            session: Database session
            user_id: User ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            Tuple of (list of scraping records, total count)
        """
        logger.debug("Listing user scraping records: user_id=%s limit=%d offset=%d", user_id, limit, offset)
        
        # Build query
        stmt: Select[tuple[UserScraping]] = select(self.model).where(self.model.user_id == user_id)
        
        # Get total count
        count_stmt: Select[tuple[int]] = select(func.count(self.model.id)).where(
            self.model.user_id == user_id
        )
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get paginated results (ordered by timestamp, newest first)
        stmt = stmt.order_by(self.model.timestamp.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        scraping_records = list(result.scalars().all())
        
        logger.debug("Listed user scraping records: returned=%d total=%d", len(scraping_records), total)
        return scraping_records, total

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Count scraping records for a user."""
        logger.debug("Counting user scraping records: user_id=%s", user_id)
        count_stmt: Select[tuple[int]] = select(func.count(self.model.id)).where(
            self.model.user_id == user_id
        )
        result = await session.execute(count_stmt)
        count = result.scalar_one()
        logger.debug("User scraping count: user_id=%s count=%d", user_id, count)
        return count

