"""Parallel processing utilities for CPU-intensive and I/O-bound tasks.

This module provides utilities for parallel processing using ThreadPoolExecutor
for CPU-intensive tasks and async parallel processing for I/O-bound tasks.

Best practices:
- Use ThreadPoolExecutor for CPU-intensive tasks (bypasses GIL)
- Use asyncio.gather for I/O-bound parallel tasks
- Limit concurrent workers to avoid resource exhaustion
- Use batch processing for large datasets
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterator, Optional, TypeVar

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")
R = TypeVar("R")


# Global thread pool executor (initialized on first use)
_thread_pool: Optional[ThreadPoolExecutor] = None


def get_thread_pool() -> ThreadPoolExecutor:
    """
    Get or create global thread pool executor.
    
    Returns:
        ThreadPoolExecutor instance
    """
    global _thread_pool
    if _thread_pool is None:
        max_workers = settings.PARALLEL_PROCESSING_WORKERS
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    return _thread_pool


async def process_in_parallel_async(
    items: list[T],
    process_func: Callable[[T], Any],
    max_concurrent: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> list[Any]:
    """
    Process items in parallel using async/await.
    
    Ideal for I/O-bound tasks (database queries, API calls, file I/O).
    
    Args:
        items: List of items to process
        process_func: Async function to process each item
        max_concurrent: Maximum concurrent tasks (None = unlimited)
        batch_size: Process in batches of this size (None = process all at once)
        
    Returns:
        List of results in the same order as items
        
    Example:
        async def fetch_user_data(user_id: int):
            return await db.get_user(user_id)
        
        user_ids = [1, 2, 3, 4, 5]
        results = await process_in_parallel_async(
            user_ids,
            fetch_user_data,
            max_concurrent=10
        )
    """
    if not items:
        return []
    
    if max_concurrent:
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(item: T) -> Any:
            async with semaphore:
                return await process_func(item)
        
        process_func = process_with_semaphore
    
    if batch_size:
        # Process in batches
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_results = await asyncio.gather(*[process_func(item) for item in batch])
            results.extend(batch_results)
        return results
    
    # Process all at once
    return await asyncio.gather(*[process_func(item) for item in items])


def process_in_parallel_sync(
    items: list[T],
    process_func: Callable[[T], R],
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
) -> list[R]:
    """
    Process items in parallel using ThreadPoolExecutor.
    
    Ideal for CPU-intensive tasks (data processing, calculations, transformations).
    
    Args:
        items: List of items to process
        process_func: Synchronous function to process each item
        max_workers: Maximum worker threads (None = use settings default)
        batch_size: Process in batches of this size (None = process all at once)
        
    Returns:
        List of results in the same order as items
        
    Example:
        def process_data_chunk(chunk: list[dict]):
            # CPU-intensive processing
            return transform_data(chunk)
        
        chunks = [chunk1, chunk2, chunk3]
        results = process_in_parallel_sync(
            chunks,
            process_data_chunk,
            max_workers=4
        )
    """
    if not items:
        return []
    
    if max_workers is None:
        max_workers = settings.PARALLEL_PROCESSING_WORKERS
    
    executor = ThreadPoolExecutor(max_workers=max_workers)
    
    try:
        if batch_size:
            # Process in batches
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                batch_results = list(executor.map(process_func, batch))
                results.extend(batch_results)
            return results
        
        # Process all at once
        return list(executor.map(process_func, items))
    
    finally:
        executor.shutdown(wait=True)


async def process_in_parallel_mixed(
    items: list[T],
    cpu_func: Callable[[T], R],
    io_func: Callable[[R], Any],
    max_workers: Optional[int] = None,
) -> list[Any]:
    """
    Process items with mixed CPU and I/O operations.
    
    First applies CPU-intensive function in parallel threads,
    then applies I/O-intensive function in parallel async tasks.
    
    Args:
        items: List of items to process
        cpu_func: CPU-intensive synchronous function
        io_func: I/O-intensive async function
        max_workers: Maximum worker threads for CPU tasks
        
    Returns:
        List of results
        
    Example:
        def parse_data(raw_data: bytes):
            # CPU-intensive parsing
            return json.loads(raw_data)
        
        async def save_to_db(parsed_data: dict):
            # I/O-intensive database save
            return await db.save(parsed_data)
        
        raw_data_list = [data1, data2, data3]
        results = await process_in_parallel_mixed(
            raw_data_list,
            parse_data,
            save_to_db
        )
    """
    # Step 1: CPU-intensive processing in parallel threads
    parsed_items = process_in_parallel_sync(items, cpu_func, max_workers=max_workers)
    
    # Step 2: I/O-intensive processing in parallel async
    return await process_in_parallel_async(parsed_items, io_func)


def batch_items(items: list[T], batch_size: int) -> Iterator[list[T]]:
    """
    Split items into batches.
    
    Args:
        items: List of items
        batch_size: Size of each batch
        
    Yields:
        Batches of items
        
    Example:
        items = list(range(100))
        for batch in batch_items(items, batch_size=10):
            process_batch(batch)  # Process 10 items at a time
    """
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


async def process_batches_async(
    items: list[T],
    process_batch_func: Callable[[list[T]], Any],
    batch_size: int,
    max_concurrent_batches: Optional[int] = None,
) -> list[Any]:
    """
    Process items in batches asynchronously.
    
    Args:
        items: List of items to process
        process_batch_func: Async function to process each batch
        batch_size: Size of each batch
        max_concurrent_batches: Maximum concurrent batches (None = unlimited)
        
    Returns:
        List of batch results
        
    Example:
        async def process_contact_batch(batch: list[Contact]):
            return await db.bulk_insert_contacts(batch)
        
        contacts = [contact1, contact2, ...]
        results = await process_batches_async(
            contacts,
            process_contact_batch,
            batch_size=100,
            max_concurrent_batches=5
        )
    """
    batches = list(batch_items(items, batch_size))
    
    if max_concurrent_batches:
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_with_semaphore(batch: list[T]) -> Any:
            async with semaphore:
                return await process_batch_func(batch)
        
        return await asyncio.gather(*[process_with_semaphore(batch) for batch in batches])
    
    return await asyncio.gather(*[process_batch_func(batch) for batch in batches])


def process_batches_sync(
    items: list[T],
    process_batch_func: Callable[[list[T]], R],
    batch_size: int,
    max_workers: Optional[int] = None,
) -> list[R]:
    """
    Process items in batches using ThreadPoolExecutor.
    
    Args:
        items: List of items to process
        process_batch_func: Synchronous function to process each batch
        batch_size: Size of each batch
        max_workers: Maximum worker threads
        
    Returns:
        List of batch results
    """
    batches = list(batch_items(items, batch_size))
    return process_in_parallel_sync(batches, process_batch_func, max_workers=max_workers)


class ParallelProcessor:
    """
    Configurable parallel processor with resource management.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        max_concurrent: Optional[int] = None,
    ):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum worker threads for CPU tasks
            max_concurrent: Maximum concurrent async tasks for I/O tasks
        """
        self.max_workers = max_workers or settings.PARALLEL_PROCESSING_WORKERS
        self.max_concurrent = max_concurrent
        self._executor: Optional[ThreadPoolExecutor] = None
    
    def __enter__(self):
        """Enter context manager."""
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def process_async(
        self,
        items: list[T],
        process_func: Callable[[T], Any],
    ) -> list[Any]:
        """Process items asynchronously."""
        return await process_in_parallel_async(
            items,
            process_func,
            max_concurrent=self.max_concurrent,
        )
    
    def process_sync(
        self,
        items: list[T],
        process_func: Callable[[T], R],
    ) -> list[R]:
        """Process items synchronously using thread pool."""
        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        return list(self._executor.map(process_func, items))
