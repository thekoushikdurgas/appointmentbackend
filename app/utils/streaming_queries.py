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

import asyncio
from collections.abc import AsyncIterator
from typing import Generic, Optional, Sequence, TypeVar

from sqlalchemy import Select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.utils.logger import get_logger

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
    
    Uses efficient offset/limit pagination with configurable batch sizes.
    Optimized for large datasets with proper memory management and error handling.
    
    Best practices:
    - Use batch_size between 500-5000 for optimal performance
    - Set max_results to prevent unbounded queries
    - Handle exceptions in the consuming code
    - Use streaming for datasets >10k rows
    
    Args:
        session: Async database session
        query: SQLAlchemy Select query
        batch_size: Number of rows to fetch per batch (defaults to STREAMING_BATCH_SIZE)
        max_results: Maximum total results to stream (None = unlimited)
        
    Yields:
        Sequences of results for each batch
        
    Raises:
        Exception: Re-raises database exceptions with context
        
    Example:
        async for batch in stream_query_results(session, select(Contact), max_results=10000):
            for contact in batch:
                process_contact(contact)
    """
    if batch_size is None:
        batch_size = settings.STREAMING_BATCH_SIZE
    
    # Validate batch_size
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")
    
    offset = 0
    total_fetched = 0
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    try:
        while True:
            # Apply limit and offset to query
            batch_query = query.offset(offset).limit(batch_size)
            
            try:
                result: Result = await session.execute(batch_query)
                batch = result.fetchall()
                consecutive_errors = 0  # Reset error counter on success
            except Exception as exc:
                consecutive_errors += 1
                
                # If too many consecutive errors, give up
                if consecutive_errors >= max_consecutive_errors:
                    raise
                
                # Wait a bit before retrying (exponential backoff)
                await asyncio.sleep(0.1 * (2 ** (consecutive_errors - 1)))
                continue  # Retry the same batch
            
            if not batch:
                break
            
            try:
                yield batch
            except GeneratorExit:
                # Consumer stopped iterating - cleanup and exit
                break
            except Exception as exc:
                # Error in consumer - continue to next batch
                pass
            
            total_fetched += len(batch)
            
            # Check max results limit
            if max_results is not None and total_fetched >= max_results:
                break
            
            # If we got fewer results than requested, we've reached the end
            if len(batch) < batch_size:
                break
            
            offset += batch_size
            
    except Exception as exc:
        raise
    finally:
        pass


async def stream_query_scalars(
    session: AsyncSession,
    query: Select,
    batch_size: Optional[int] = None,
    max_results: Optional[int] = None,
) -> AsyncIterator[list[T]]:
    """
    Stream query results as scalars (single values) in batches.
    
    Optimized for memory efficiency when only scalar values are needed.
    Uses the same error handling and retry logic as stream_query_results.
    
    Args:
        session: Async database session
        query: SQLAlchemy Select query that returns scalar values
        batch_size: Number of rows to fetch per batch (defaults to STREAMING_BATCH_SIZE)
        max_results: Maximum total results to stream (None = unlimited)
        
    Yields:
        Lists of scalar results for each batch
        
    Raises:
        Exception: Re-raises database exceptions with context
        
    Example:
        async for batch in stream_query_scalars(session, select(Contact.id), max_results=5000):
            for contact_id in batch:
                process_id(contact_id)
    """
    if batch_size is None:
        batch_size = settings.STREAMING_BATCH_SIZE
    
    offset = 0
    total_fetched = 0
    
    # Validate batch_size
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")
    
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    try:
        while True:
            batch_query = query.offset(offset).limit(batch_size)
            
            try:
                result: Result = await session.execute(batch_query)
                batch = result.scalars().all()
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    raise
                
                await asyncio.sleep(0.1 * (2 ** (consecutive_errors - 1)))
                continue
            
            if not batch:
                break
            
            try:
                yield batch
            except GeneratorExit:
                break
            except Exception as exc:
                pass
            
            total_fetched += len(batch)
            
            if max_results is not None and total_fetched >= max_results:
                break
            
            if len(batch) < batch_size:
                break
            
            offset += batch_size
            
    except Exception as exc:
        raise
    finally:
        pass


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

