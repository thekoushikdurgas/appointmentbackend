"""Parallel processing utilities for CPU-intensive and I/O-bound tasks.

This module provides utilities for executing tasks in parallel using
ThreadPoolExecutor (for I/O-bound) and ProcessPoolExecutor (for CPU-intensive).

Usage:
    from app.utils.parallel_processing import process_in_parallel
    
    # I/O-bound tasks (database queries, API calls)
    results = await process_in_parallel(
        tasks=[query1, query2, query3],
        max_workers=4,
        executor_type="thread"
    )
    
    # CPU-intensive tasks (data processing, calculations)
    results = await process_cpu_intensive(
        tasks=[process1, process2, process3],
        max_workers=4
    )
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, List, Optional, TypeVar

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar("T")


async def process_in_parallel(
    tasks: Iterable[Callable[[], T]],
    max_workers: Optional[int] = None,
    executor_type: str = "thread",
    return_exceptions: bool = False,
) -> List[T]:
    """
    Execute I/O-bound tasks in parallel using ThreadPoolExecutor.
    
    Args:
        tasks: Iterable of callable tasks to execute
        max_workers: Maximum number of worker threads (defaults to PARALLEL_PROCESSING_WORKERS)
        executor_type: "thread" for I/O-bound, "process" for CPU-intensive
        return_exceptions: If True, exceptions are returned as results instead of raising
        
    Returns:
        List of results in the same order as tasks
        
    Example:
        def fetch_user(user_id):
            return db.get_user(user_id)
        
        results = await process_in_parallel(
            [lambda: fetch_user(1), lambda: fetch_user(2), lambda: fetch_user(3)],
            max_workers=4
        )
    """
    if max_workers is None:
        max_workers = settings.PARALLEL_PROCESSING_WORKERS
    
    tasks_list = list(tasks)
    if not tasks_list:
        return []
    
    logger.debug(
        "Processing %d tasks in parallel: executor=%s workers=%d",
        len(tasks_list),
        executor_type,
        max_workers,
    )
    
    if executor_type == "process":
        executor_class = ProcessPoolExecutor
    else:
        executor_class = ThreadPoolExecutor
    
    loop = asyncio.get_event_loop()
    results = []
    
    with executor_class(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            loop.run_in_executor(executor, task): idx
            for idx, task in enumerate(tasks_list)
        }
        
        # Collect results in order
        task_results = [None] * len(tasks_list)
        completed = 0
        
        for future in as_completed(future_to_task):
            task_idx = future_to_task[future]
            try:
                result = await future
                task_results[task_idx] = result
                completed += 1
                logger.debug("Completed task %d/%d", completed, len(tasks_list))
            except Exception as exc:
                if return_exceptions:
                    task_results[task_idx] = exc
                    completed += 1
                else:
                    logger.exception("Task %d failed", task_idx)
                    raise
        
        results = task_results
    
    logger.debug("Completed %d parallel tasks", len(results))
    return results


async def process_cpu_intensive(
    tasks: Iterable[Callable[[], T]],
    max_workers: Optional[int] = None,
    return_exceptions: bool = False,
) -> List[T]:
    """
    Execute CPU-intensive tasks in parallel using ProcessPoolExecutor.
    
    This bypasses Python's GIL by using separate processes.
    
    Args:
        tasks: Iterable of callable tasks to execute
        max_workers: Maximum number of worker processes
        return_exceptions: If True, exceptions are returned as results
        
    Returns:
        List of results in the same order as tasks
        
    Example:
        def process_data_chunk(chunk):
            # CPU-intensive processing
            return processed_chunk
        
        results = await process_cpu_intensive(
            [lambda: process_data_chunk(chunk1), lambda: process_data_chunk(chunk2)],
            max_workers=4
        )
    """
    return await process_in_parallel(
        tasks,
        max_workers=max_workers,
        executor_type="process",
        return_exceptions=return_exceptions,
    )


async def process_batches(
    items: Iterable[T],
    processor: Callable[[T], Any],
    batch_size: int = 100,
    max_workers: Optional[int] = None,
    executor_type: str = "thread",
) -> List[Any]:
    """
    Process items in batches with parallel execution within each batch.
    
    Args:
        items: Items to process
        processor: Function to process each item
        batch_size: Number of items per batch
        max_workers: Maximum workers per batch
        executor_type: "thread" or "process"
        
    Returns:
        List of processed results
        
    Example:
        def process_contact(contact):
            return enrich_contact(contact)
        
        results = await process_batches(
            contacts,
            process_contact,
            batch_size=50,
            max_workers=4
        )
    """
    items_list = list(items)
    if not items_list:
        return []
    
    if max_workers is None:
        max_workers = settings.PARALLEL_PROCESSING_WORKERS
    
    all_results = []
    
    for i in range(0, len(items_list), batch_size):
        batch = items_list[i:i + batch_size]
        logger.debug("Processing batch %d-%d of %d items", i, min(i + batch_size, len(items_list)), len(items_list))
        
        # Create tasks for this batch
        batch_tasks = [lambda item=item: processor(item) for item in batch]
        
        # Process batch in parallel
        batch_results = await process_in_parallel(
            batch_tasks,
            max_workers=max_workers,
            executor_type=executor_type,
        )
        
        all_results.extend(batch_results)
    
    logger.debug("Processed %d items in batches", len(all_results))
    return all_results


class ParallelProcessor:
    """
    Context manager for parallel processing with automatic resource cleanup.
    
    Example:
        async with ParallelProcessor(max_workers=4) as processor:
            results = await processor.process([
                lambda: task1(),
                lambda: task2(),
                lambda: task3(),
            ])
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        executor_type: str = "thread",
    ):
        """
        Initialize parallel processor.
        
        Args:
            max_workers: Maximum number of workers
            executor_type: "thread" or "process"
        """
        self.max_workers = max_workers or settings.PARALLEL_PROCESSING_WORKERS
        self.executor_type = executor_type
        self.executor: Optional[ThreadPoolExecutor | ProcessPoolExecutor] = None
    
    async def __aenter__(self):
        """Enter context and create executor."""
        if self.executor_type == "process":
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and shutdown executor."""
        if self.executor:
            self.executor.shutdown(wait=True)
        return False
    
    async def process(
        self,
        tasks: Iterable[Callable[[], T]],
        return_exceptions: bool = False,
    ) -> List[T]:
        """
        Process tasks using the executor.
        
        Args:
            tasks: Tasks to execute
            return_exceptions: If True, return exceptions as results
            
        Returns:
            List of results
        """
        if not self.executor:
            raise RuntimeError("ParallelProcessor must be used as context manager")
        
        return await process_in_parallel(
            tasks,
            max_workers=self.max_workers,
            executor_type=self.executor_type,
            return_exceptions=return_exceptions,
        )

