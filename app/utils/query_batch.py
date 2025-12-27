"""Query batching utilities for efficient bulk database operations.

This module provides the QueryBatcher class for efficiently processing large
result sets by fetching data in batches. This prevents memory issues when
working with large datasets.

Note: This utility is primarily used for write operations and other database
operations that don't go through Connectra. Read operations for contacts and
companies now use Connectra batch APIs instead.

Note: The batch_insert, batch_update, and execute_in_batches functions were
removed as they were unused. If batch insert/update functionality is needed
in the future, they can be re-implemented based on actual requirements.
"""

from __future__ import annotations

from typing import AsyncIterator, Generic, Sequence, TypeVar

from sqlalchemy import Select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class QueryBatcher(Generic[T]):
    """Utility for batching database queries to handle large result sets efficiently."""

    def __init__(
        self,
        session: AsyncSession,
        query: Select,
        batch_size: int = 1000,
    ):
        """
        Initialize a query batcher.

        Args:
            session: Async database session
            query: SQLAlchemy select query
            batch_size: Number of rows to fetch per batch
        """
        self.session = session
        self.query = query
        self.batch_size = batch_size

    async def fetch_all_batches(self) -> AsyncIterator[Sequence[T]]:
        """
        Fetch all results in batches.

        Yields:
            Sequences of results for each batch
        """
        offset = 0
        while True:
            batch_query = self.query.offset(offset).limit(self.batch_size)
            result: Result = await self.session.execute(batch_query)
            batch = result.fetchall()
            
            if not batch:
                break
            
            yield batch
            
            if len(batch) < self.batch_size:
                break
            
            offset += self.batch_size

    async def fetch_all(self) -> list[T]:
        """
        Fetch all results by batching internally.

        Returns:
            List of all results
        """
        all_results: list[T] = []
        async for batch in self.fetch_all_batches():
            all_results.extend(batch)
        return all_results


