"""Utilities for managing FastAPI background tasks efficiently.

This module provides utilities for common background task patterns,
including retry logic, result tracking, rate limiting, graceful shutdown,
and task management following FastAPI best practices.

Usage:
    from app.utils.background_tasks import add_background_task_with_retry
    
    @app.post("/data")
    async def create_data(data: str, background_tasks: BackgroundTasks):
        add_background_task_with_retry(
            background_tasks,
            process_data,
            data,
            max_retries=3
        )
        return {"message": "Processing started"}
"""

from __future__ import annotations

import asyncio
import uuid
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Dict

from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo:
    """Information about a background task."""
    
    def __init__(self, task_id: str, func_name: str):
        self.task_id = task_id
        self.func_name = func_name
        self.status = TaskStatus.PENDING
        self.created_at = asyncio.get_event_loop().time()
        self.completed_at: Optional[float] = None
        self.error: Optional[str] = None


# In-memory task store for tracking task status
_task_store: Dict[str, TaskInfo] = {}
_task_store_lock = asyncio.Lock()

# Global semaphore for rate limiting concurrent tasks
_task_semaphore: Optional[asyncio.Semaphore] = None
_max_concurrent_tasks = 10  # Default limit

# Track active tasks for graceful shutdown
_active_tasks: set[asyncio.Task] = set()
_active_tasks_lock = asyncio.Lock()


def initialize_task_limiting(max_concurrent: int = 10) -> None:
    """
    Initialize task rate limiting.
    
    Args:
        max_concurrent: Maximum number of concurrent background tasks
    """
    global _task_semaphore, _max_concurrent_tasks
    _max_concurrent_tasks = max_concurrent
    _task_semaphore = asyncio.Semaphore(max_concurrent)
    logger.info("Background task rate limiting initialized: max_concurrent=%d", max_concurrent)


async def get_task_status(task_id: str) -> Optional[TaskInfo]:
    """
    Get status of a background task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        TaskInfo if found, None otherwise
    """
    async with _task_store_lock:
        return _task_store.get(task_id)


async def get_all_tasks() -> Dict[str, TaskInfo]:
    """
    Get all tracked tasks.
    
    Returns:
        Dictionary of task_id -> TaskInfo
    """
    async with _task_store_lock:
        return _task_store.copy()


async def cleanup_old_tasks(max_age_seconds: int = 3600) -> None:
    """
    Clean up old completed/failed tasks from memory.
    
    Args:
        max_age_seconds: Maximum age in seconds for tasks to keep
    """
    current_time = asyncio.get_event_loop().time()
    async with _task_store_lock:
        to_remove = [
            task_id
            for task_id, info in _task_store.items()
            if info.completed_at
            and (current_time - info.completed_at) > max_age_seconds
        ]
        for task_id in to_remove:
            del _task_store[task_id]
        
        if to_remove:
            logger.debug("Cleaned up %d old tasks", len(to_remove))


def add_background_task_with_retry(
    background_tasks: BackgroundTasks,
    func: Callable,
    *args,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    track_status: bool = False,
    **kwargs,
) -> Optional[str]:
    """
    Add a background task with automatic retry logic.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        func: Function to execute in background
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        track_status: Whether to track task status (returns task_id if True)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Task ID if track_status is True, None otherwise
    """
    task_id = str(uuid.uuid4()) if track_status else None
    
    async def task_with_retry():
        """Execute task with retry logic."""
        # Track task if requested
        if task_id:
            async with _task_store_lock:
                _task_store[task_id] = TaskInfo(task_id, func.__name__)
                _task_store[task_id].status = TaskStatus.RUNNING
        
        # Rate limiting
        if _task_semaphore:
            await _task_semaphore.acquire()
        
        try:
            # Track active task for graceful shutdown
            current_task = asyncio.current_task()
            if current_task:
                async with _active_tasks_lock:
                    _active_tasks.add(current_task)
            
            last_exception = None
            for attempt in range(max_retries):
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        # Use threadpool for CPU-bound tasks
                        await run_in_threadpool(func, *args, **kwargs)
                    
                    # Task completed successfully
                    if task_id:
                        async with _task_store_lock:
                            if task_id in _task_store:
                                _task_store[task_id].status = TaskStatus.COMPLETED
                                _task_store[task_id].completed_at = asyncio.get_event_loop().time()
                    
                    logger.debug("Background task completed successfully: func=%s attempt=%d", func.__name__, attempt + 1)
                    return
                except Exception as exc:
                    last_exception = exc
                    logger.warning(
                        "Background task failed: func=%s attempt=%d/%d error=%s",
                        func.__name__,
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            
            # All retries failed
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.FAILED
                        _task_store[task_id].error = str(last_exception)
                        _task_store[task_id].completed_at = asyncio.get_event_loop().time()
            
            logger.error(
                "Background task failed after %d attempts: func=%s error=%s",
                max_retries,
                func.__name__,
                last_exception,
            )
        finally:
            # Release semaphore
            if _task_semaphore:
                _task_semaphore.release()
            
            # Remove from active tasks
            if current_task:
                async with _active_tasks_lock:
                    _active_tasks.discard(current_task)
    
    background_tasks.add_task(task_with_retry)
    return task_id


def background_task(
    max_retries: int = 3,
    retry_delay: float = 1.0,
):
    """
    Decorator for functions that should run as background tasks with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Example:
        @background_task(max_retries=5)
        async def process_data(data: str):
            # Process data
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    logger.warning(
                        "Background task failed: func=%s attempt=%d/%d error=%s",
                        func.__name__,
                        attempt + 1,
                        max_retries,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
            
            logger.error(
                "Background task failed after %d attempts: func=%s error=%s",
                max_retries,
                func.__name__,
                last_exception,
            )
            raise last_exception
        
        return wrapper
    return decorator


def add_background_task_safe(
    background_tasks: BackgroundTasks,
    func: Callable,
    *args,
    track_status: bool = False,
    **kwargs,
) -> Optional[str]:
    """
    Add a background task with error handling that won't crash the application.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        func: Function to execute in background
        *args: Positional arguments for the function
        track_status: Whether to track task status (returns task_id if True)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Task ID if track_status is True, None otherwise
    """
    task_id = str(uuid.uuid4()) if track_status else None
    
    async def safe_task():
        """Execute task with error handling."""
        # Track task if requested
        if task_id:
            async with _task_store_lock:
                _task_store[task_id] = TaskInfo(task_id, func.__name__)
                _task_store[task_id].status = TaskStatus.RUNNING
        
        # Rate limiting
        if _task_semaphore:
            await _task_semaphore.acquire()
        
        try:
            # Track active task for graceful shutdown
            current_task = asyncio.current_task()
            if current_task:
                async with _active_tasks_lock:
                    _active_tasks.add(current_task)
            
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                # Use threadpool for CPU-bound tasks
                await run_in_threadpool(func, *args, **kwargs)
            
            # Task completed successfully
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.COMPLETED
                        _task_store[task_id].completed_at = asyncio.get_event_loop().time()
            
            logger.debug("Background task completed: func=%s", func.__name__)
        except Exception as exc:
            # Task failed - log but don't raise
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.FAILED
                        _task_store[task_id].error = str(exc)
                        _task_store[task_id].completed_at = asyncio.get_event_loop().time()
            
            logger.exception("Background task failed (non-critical): func=%s error=%s", func.__name__, exc)
        finally:
            # Release semaphore
            if _task_semaphore:
                _task_semaphore.release()
            
            # Remove from active tasks
            current_task = asyncio.current_task()
            if current_task:
                async with _active_tasks_lock:
                    _active_tasks.discard(current_task)
    
    background_tasks.add_task(safe_task)
    return task_id


async def wait_for_active_tasks(timeout: float = 30.0) -> bool:
    """
    Wait for all active background tasks to complete (for graceful shutdown).
    
    Args:
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if all tasks completed, False if timeout
    """
    async with _active_tasks_lock:
        tasks = list(_active_tasks)
    
    if not tasks:
        return True
    
    logger.info("Waiting for %d active background tasks to complete...", len(tasks))
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
        logger.info("All background tasks completed")
        return True
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for background tasks to complete")
        return False


# Guidelines for when to use BackgroundTasks
BACKGROUND_TASKS_GUIDELINES = """
When to use FastAPI BackgroundTasks:
- Simple, non-critical operations
- Tasks that complete quickly (< 30 seconds)
- Tasks that don't need persistence or retry guarantees
- Tasks that don't need to be distributed across workers
- Tasks that are tied to the request lifecycle
- I/O-bound tasks (database operations, file processing)
- Tasks that can use connection pooling

Best Practices:
- Use run_in_threadpool for CPU-bound operations
- Always handle errors gracefully (don't raise exceptions)
- Use rate limiting (semaphores) for resource-intensive tasks
- Track task status for long-running operations
- Use connection pooling for database operations
- Implement graceful shutdown for critical tasks
"""

