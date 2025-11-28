"""Utilities for streaming database query results efficiently.

This module provides utilities for streaming large database result sets
without loading everything into memory at once. This is essential for
handling big data efficiently.

Usage:
    from app.utils.streaming_queries import stream_query_results
    
    async for batch in stream_query_results(session, query, batch_size=1000):
        # Process batch of results
        for row in batch:
            process_row(row)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Generic, Optional, Sequence, TypeVar

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")


async def stream_query_results(
    session: AsyncSession,
    query: Select,
    batch_size: Optional[int] = None,
    max_results: Optional[int] = None,
) -> AsyncIterator[Sequence[T]]:
    """
    Stream query results in batches to avoid loading everything into memory.
    
    Args:
        session: Async database session
        query: SQLAlchemy Select query
        batch_size: Number of rows to fetch per batch (defaults to STREAMING_CHUNK_SIZE)
        max_results: Maximum total results to stream (None = unlimited)
        
    Yields:
        Sequences of results for each batch
        
    Example:
        async for batch in stream_query_results(session, select(Contact)):
            for contact in batch:
                process_contact(contact)
    """
    if batch_size is None:
        # Use a reasonable default based on chunk size setting
        # For database rows, use smaller batches than file chunks
        batch_size = min(settings.STREAMING_CHUNK_SIZE // 1024, 1000)  # ~1KB per row estimate
    
    offset = 0
    total_fetched = 0
    
    logger.debug(
        "Starting query stream: batch_size=%d max_results=%s",
        batch_size,
        max_results,
    )
    
    while True:
        # Apply limit and offset to query
        batch_query = query.offset(offset).limit(batch_size)
        
        try:
            result: Result = await session.execute(batch_query)
            batch = result.fetchall()
        except Exception as exc:
            logger.exception("Error executing streaming query batch: offset=%d", offset)
            raise
        
        if not batch:
            logger.debug("Query stream completed: total_fetched=%d", total_fetched)
            break
        
        logger.debug("Fetched batch: offset=%d size=%d", offset, len(batch))
        yield batch
        
        total_fetched += len(batch)
        
        # Check max results limit
        if max_results is not None and total_fetched >= max_results:
            logger.debug("Query stream reached max_results limit: %d", max_results)
            break
        
        # If we got fewer results than requested, we've reached the end
        if len(batch) < batch_size:
            logger.debug("Query stream completed (partial batch): total_fetched=%d", total_fetched)
            break
        
        offset += batch_size


async def stream_query_scalars(
    session: AsyncSession,
    query: Select,
    batch_size: Optional[int] = None,
    max_results: Optional[int] = None,
) -> AsyncIterator[list[T]]:
    """
    Stream query results as scalars (single values) in batches.
    
    Args:
        session: Async database session
        query: SQLAlchemy Select query that returns scalar values
        batch_size: Number of rows to fetch per batch
        max_results: Maximum total results to stream (None = unlimited)
        
    Yields:
        Lists of scalar results for each batch
        
    Example:
        async for batch in stream_query_scalars(session, select(Contact.id)):
            for contact_id in batch:
                process_id(contact_id)
    """
    if batch_size is None:
        batch_size = min(settings.STREAMING_CHUNK_SIZE // 1024, 1000)
    
    offset = 0
    total_fetched = 0
    
    logger.debug(
        "Starting scalar query stream: batch_size=%d max_results=%s",
        batch_size,
        max_results,
    )
    
    while True:
        batch_query = query.offset(offset).limit(batch_size)
        
        try:
            result: Result = await session.execute(batch_query)
            batch = result.scalars().all()
        except Exception as exc:
            logger.exception("Error executing streaming scalar query batch: offset=%d", offset)
            raise
        
        if not batch:
            logger.debug("Scalar query stream completed: total_fetched=%d", total_fetched)
            break
        
        logger.debug("Fetched scalar batch: offset=%d size=%d", offset, len(batch))
        yield batch
        
        total_fetched += len(batch)
        
        if max_results is not None and total_fetched >= max_results:
            logger.debug("Scalar query stream reached max_results limit: %d", max_results)
            break
        
        if len(batch) < batch_size:
            logger.debug("Scalar query stream completed (partial batch): total_fetched=%d", total_fetched)
            break
        
        offset += batch_size


class StreamingQuery(Generic[T]):
    """
    A context manager for streaming query results with automatic resource management.
    
    Example:
        async with StreamingQuery(session, select(Contact)) as streamer:
            async for batch in streamer:
                for contact in batch:
                    process_contact(contact)
    """
    
    def __init__(
        self,
        session: AsyncSession,
        query: Select,
        batch_size: Optional[int] = None,
        max_results: Optional[int] = None,
    ):
        """
        Initialize streaming query.
        
        Args:
            session: Async database session
            query: SQLAlchemy Select query
            batch_size: Number of rows per batch
            max_results: Maximum total results
        """
        self.session = session
        self.query = query
        self.batch_size = batch_size
        self.max_results = max_results
        self._iterator: Optional[AsyncIterator[Sequence[T]]] = None
    
    async def __aenter__(self) -> AsyncIterator[Sequence[T]]:
        """Enter context and start streaming."""
        self._iterator = stream_query_results(
            self.session,
            self.query,
            batch_size=self.batch_size,
            max_results=self.max_results,
        )
        return self._iterator
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context - iterator cleanup is automatic."""
        self._iterator = None
        return False  # Don't suppress exceptions

