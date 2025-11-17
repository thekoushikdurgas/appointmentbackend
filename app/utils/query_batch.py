"""Query batching utilities for efficient bulk database operations."""

from __future__ import annotations

from typing import AsyncIterator, Callable, Generic, Optional, TypeVar, Sequence, Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from app.core.logging import get_logger

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
        logger.debug(
            "Initialized QueryBatcher batch_size=%d",
            batch_size,
        )

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
            
            logger.debug("Fetched batch offset=%d size=%d", offset, len(batch))
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
        logger.debug("Fetched all results via batching total=%d", len(all_results))
        return all_results


async def batch_insert(
    session: AsyncSession,
    model_class: type[Any],
    data_list: list[dict[str, Any]],
    batch_size: int = 1000,
) -> list[Any]:
    """
    Insert records in batches for better performance.

    Args:
        session: Async database session
        model_class: SQLAlchemy model class
        data_list: List of dictionaries with data to insert
        batch_size: Number of records to insert per batch

    Returns:
        List of inserted model instances
    """
    logger.debug(
        "Starting batch insert model=%s total_records=%d batch_size=%d",
        model_class.__name__,
        len(data_list),
        batch_size,
    )
    
    all_inserted: list[Any] = []
    
    for i in range(0, len(data_list), batch_size):
        batch_data = data_list[i : i + batch_size]
        batch_instances = [model_class(**data) for data in batch_data]
        session.add_all(batch_instances)
        await session.flush()
        all_inserted.extend(batch_instances)
        
        logger.debug(
            "Inserted batch %d-%d model=%s count=%d",
            i,
            min(i + batch_size, len(data_list)),
            model_class.__name__,
            len(batch_instances),
        )
    
    await session.commit()
    logger.debug(
        "Completed batch insert model=%s total_inserted=%d",
        model_class.__name__,
        len(all_inserted),
    )
    return all_inserted


async def batch_update(
    session: AsyncSession,
    query: Select,
    update_data: dict,
    batch_size: int = 1000,
) -> int:
    """
    Update records in batches.

    Args:
        session: Async database session
        query: SQLAlchemy select query for records to update
        update_data: Dictionary of fields to update
        batch_size: Number of records to update per batch

    Returns:
        Total number of records updated
    """
    logger.debug(
        "Starting batch update batch_size=%d update_fields=%s",
        batch_size,
        sorted(update_data.keys()),
    )
    
    total_updated = 0
    offset = 0
    
    while True:
        batch_query = query.offset(offset).limit(batch_size)
        result: Result = await session.execute(batch_query)
        batch = result.scalars().all()
        
        if not batch:
            break
        
        for record in batch:
            for key, value in update_data.items():
                setattr(record, key, value)
        
        await session.flush()
        total_updated += len(batch)
        offset += batch_size
        
        logger.debug(
            "Updated batch offset=%d count=%d total_updated=%d",
            offset - batch_size,
            len(batch),
            total_updated,
        )
        
        if len(batch) < batch_size:
            break
    
    await session.commit()
    logger.debug("Completed batch update total_updated=%d", total_updated)
    return total_updated


async def execute_in_batches(
    session: AsyncSession,
    query_factory: Callable[[int, int], Select],
    processor: Callable[[Sequence[Any]], None],
    batch_size: int = 1000,
    total_limit: Optional[int] = None,
) -> int:
    """
    Execute a query in batches and process each batch.

    Args:
        session: Async database session
        query_factory: Function that creates a query given offset and limit
        processor: Async function to process each batch
        batch_size: Number of records per batch
        total_limit: Maximum total records to process (None for all)

    Returns:
        Total number of records processed
    """
    logger.debug(
        "Starting batch execution batch_size=%d total_limit=%s",
        batch_size,
        total_limit,
    )
    
    total_processed = 0
    offset = 0
    
    while True:
        if total_limit and total_processed >= total_limit:
            break
        
        current_batch_size = batch_size
        if total_limit:
            remaining = total_limit - total_processed
            current_batch_size = min(batch_size, remaining)
        
        batch_query = query_factory(offset, current_batch_size)
        result: Result = await session.execute(batch_query)
        batch = result.fetchall()
        
        if not batch:
            break
        
        await processor(batch)
        total_processed += len(batch)
        offset += current_batch_size
        
        logger.debug(
            "Processed batch offset=%d count=%d total_processed=%d",
            offset - current_batch_size,
            len(batch),
            total_processed,
        )
        
        if len(batch) < current_batch_size:
            break
    
    logger.debug("Completed batch execution total_processed=%d", total_processed)
    return total_processed

