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
import time
import uuid
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

from fastapi import BackgroundTasks

from app.utils.logger import get_logger

logger = get_logger(__name__)
from fastapi.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()


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
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.duration_seconds: Optional[float] = None
        self.error: Optional[str] = None
        self.error_type: Optional[str] = None
        self.is_cpu_bound: bool = False


# In-memory task store for tracking task status
_task_store: Dict[str, TaskInfo] = {}
_task_store_lock = asyncio.Lock()

# Global semaphore for rate limiting concurrent tasks
_task_semaphore: Optional[asyncio.Semaphore] = None
_max_concurrent_tasks = 10  # Default limit

# Track active tasks for graceful shutdown
_active_tasks: set[asyncio.Task] = set()
_active_tasks_lock = asyncio.Lock()

# Task execution statistics
_task_stats: Dict[str, Dict[str, Any]] = {}
_task_stats_lock = asyncio.Lock()


def initialize_task_limiting(max_concurrent: Optional[int] = None) -> None:
    """
    Initialize task rate limiting from settings.
    
    Args:
        max_concurrent: Maximum number of concurrent background tasks.
                       If None, uses MAX_CONCURRENT_BACKGROUND_TASKS from settings.
    """
    global _task_semaphore, _max_concurrent_tasks
    if max_concurrent is None:
        max_concurrent = getattr(settings, 'MAX_CONCURRENT_BACKGROUND_TASKS', 10)
    _max_concurrent_tasks = max_concurrent
    _task_semaphore = asyncio.Semaphore(max_concurrent)


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
    current_time = time.time()
    async with _task_store_lock:
        to_remove = [
            task_id
            for task_id, info in _task_store.items()
            if info.completed_at
            and (current_time - info.completed_at) > max_age_seconds
        ]
        for task_id in to_remove:
            del _task_store[task_id]
    
    # Also clean up old stats
    async with _task_stats_lock:
        to_remove_stats = [
            func_name
            for func_name, stats in _task_stats.items()
            if stats.get('last_run_time', 0) > 0
            and (current_time - stats.get('last_run_time', 0)) > max_age_seconds
        ]
        for func_name in to_remove_stats:
            del _task_stats[func_name]


def _is_cpu_bound_task(func: Callable) -> bool:
    """
    Detect if a task is likely CPU-bound.
    
    Heuristics:
    - Non-async functions are typically CPU-bound or blocking I/O
    - Functions with specific naming patterns (process, compute, calculate, etc.)
    - Can be overridden with explicit flag in kwargs
    
    Args:
        func: Function to check
        
    Returns:
        True if likely CPU-bound, False otherwise
    """
    # Check if explicitly marked
    # This can be set via kwargs in the calling code
    
    # Check function name patterns
    func_name_lower = func.__name__.lower()
    cpu_bound_patterns = [
        'process', 'compute', 'calculate', 'transform', 'parse',
        'encode', 'decode', 'compress', 'decompress', 'generate',
        'render', 'convert', 'format', 'serialize', 'deserialize'
    ]
    
    if any(pattern in func_name_lower for pattern in cpu_bound_patterns):
        return True
    
    # Non-async functions are likely CPU-bound or blocking
    if not asyncio.iscoroutinefunction(func):
        return True
    
    return False


async def get_task_statistics() -> Dict[str, Any]:
    """
    Get statistics about background task execution.
    
    Returns:
        Dictionary with task statistics including:
        - total_tasks: Total number of tasks executed
        - active_tasks: Number of currently running tasks
        - completed_tasks: Number of completed tasks
        - failed_tasks: Number of failed tasks
        - avg_duration: Average task duration in seconds
        - by_function: Statistics grouped by function name
    """
    async with _task_store_lock:
        total = len(_task_store)
        active = sum(1 for info in _task_store.values() if info.status == TaskStatus.RUNNING)
        completed = sum(1 for info in _task_store.values() if info.status == TaskStatus.COMPLETED)
        failed = sum(1 for info in _task_store.values() if info.status == TaskStatus.FAILED)
        
        durations = [
            info.duration_seconds
            for info in _task_store.values()
            if info.duration_seconds is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
    
    async with _task_stats_lock:
        by_function = _task_stats.copy()
    
    return {
        "total_tasks": total,
        "active_tasks": active,
        "completed_tasks": completed,
        "failed_tasks": failed,
        "avg_duration_seconds": avg_duration,
        "by_function": by_function,
    }


def add_background_task_with_retry(
    background_tasks: BackgroundTasks,
    func: Callable,
    *args,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    track_status: bool = False,
    cpu_bound: Optional[bool] = None,
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
        cpu_bound: Explicitly mark task as CPU-bound (None = auto-detect)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Task ID if track_status is True, None otherwise
    """
    task_id = str(uuid.uuid4()) if track_status else None
    is_cpu_bound = cpu_bound if cpu_bound is not None else _is_cpu_bound_task(func)
    
    async def task_with_retry():
        """Execute task with retry logic."""
        start_time = time.time()
        # Track task if requested
        if task_id:
            async with _task_store_lock:
                _task_store[task_id] = TaskInfo(task_id, func.__name__)
                _task_store[task_id].status = TaskStatus.RUNNING
                _task_store[task_id].started_at = start_time
                _task_store[task_id].is_cpu_bound = is_cpu_bound
        
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
            last_exception_type = None
            for attempt in range(max_retries):
                try:
                    if is_cpu_bound and not asyncio.iscoroutinefunction(func):
                        # Explicitly use threadpool for CPU-bound sync functions
                        await run_in_threadpool(func, *args, **kwargs)
                    elif asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        # Sync function that's not CPU-bound - still use threadpool to avoid blocking
                        await run_in_threadpool(func, *args, **kwargs)
                    
                    # Task completed successfully
                    duration = time.time() - start_time
                    if task_id:
                        async with _task_store_lock:
                            if task_id in _task_store:
                                _task_store[task_id].status = TaskStatus.COMPLETED
                                _task_store[task_id].completed_at = time.time()
                                _task_store[task_id].duration_seconds = duration
                    
                    # Update statistics
                    async with _task_stats_lock:
                        if func.__name__ not in _task_stats:
                            _task_stats[func.__name__] = {
                                'total_runs': 0,
                                'successful_runs': 0,
                                'failed_runs': 0,
                                'total_duration': 0.0,
                                'avg_duration': 0.0,
                                'last_run_time': 0.0,
                            }
                        stats = _task_stats[func.__name__]
                        stats['total_runs'] += 1
                        stats['successful_runs'] += 1
                        stats['total_duration'] += duration
                        stats['avg_duration'] = stats['total_duration'] / stats['successful_runs']
                        stats['last_run_time'] = time.time()
                    
                    return
                except Exception as exc:
                    last_exception = exc
                    last_exception_type = type(exc).__name__
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            
            # All retries failed
            duration = time.time() - start_time
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.FAILED
                        _task_store[task_id].error = str(last_exception)
                        _task_store[task_id].error_type = last_exception_type
                        _task_store[task_id].completed_at = time.time()
                        _task_store[task_id].duration_seconds = duration
            
            # Update statistics
            async with _task_stats_lock:
                if func.__name__ not in _task_stats:
                    _task_stats[func.__name__] = {
                        'total_runs': 0,
                        'successful_runs': 0,
                        'failed_runs': 0,
                        'total_duration': 0.0,
                        'avg_duration': 0.0,
                        'last_run_time': 0.0,
                    }
                stats = _task_stats[func.__name__]
                stats['total_runs'] += 1
                stats['failed_runs'] += 1
                stats['last_run_time'] = time.time()
        finally:
            # Release semaphore
            if _task_semaphore:
                _task_semaphore.release()
            
            # Remove from active tasks
            current_task = asyncio.current_task()
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
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
            
            raise last_exception
        
        return wrapper
    return decorator


def add_background_task_safe(
    background_tasks: BackgroundTasks,
    func: Callable,
    *args,
    track_status: bool = False,
    cpu_bound: Optional[bool] = None,
    **kwargs,
) -> Optional[str]:
    """
    Add a background task with error handling that won't crash the application.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        func: Function to execute in background
        *args: Positional arguments for the function
        track_status: Whether to track task status (returns task_id if True)
        cpu_bound: Explicitly mark task as CPU-bound (None = auto-detect)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Task ID if track_status is True, None otherwise
    """
    task_id = str(uuid.uuid4()) if track_status else None
    is_cpu_bound = cpu_bound if cpu_bound is not None else _is_cpu_bound_task(func)
    
    async def safe_task():
        """Execute task with error handling."""
        start_time = time.time()
        # Track task if requested
        if task_id:
            async with _task_store_lock:
                _task_store[task_id] = TaskInfo(task_id, func.__name__)
                _task_store[task_id].status = TaskStatus.RUNNING
                _task_store[task_id].started_at = start_time
                _task_store[task_id].is_cpu_bound = is_cpu_bound
        
        # Rate limiting
        if _task_semaphore:
            await _task_semaphore.acquire()
        
        try:
            # Track active task for graceful shutdown
            current_task = asyncio.current_task()
            if current_task:
                async with _active_tasks_lock:
                    _active_tasks.add(current_task)
            
            if is_cpu_bound and not asyncio.iscoroutinefunction(func):
                # Explicitly use threadpool for CPU-bound sync functions
                await run_in_threadpool(func, *args, **kwargs)
            elif asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                # Sync function that's not CPU-bound - still use threadpool to avoid blocking
                await run_in_threadpool(func, *args, **kwargs)
            
            # Task completed successfully
            duration = time.time() - start_time
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.COMPLETED
                        _task_store[task_id].completed_at = time.time()
                        _task_store[task_id].duration_seconds = duration
            
            # Update statistics
            async with _task_stats_lock:
                if func.__name__ not in _task_stats:
                    _task_stats[func.__name__] = {
                        'total_runs': 0,
                        'successful_runs': 0,
                        'failed_runs': 0,
                        'total_duration': 0.0,
                        'avg_duration': 0.0,
                        'last_run_time': 0.0,
                    }
                stats = _task_stats[func.__name__]
                stats['total_runs'] += 1
                stats['successful_runs'] += 1
                stats['total_duration'] += duration
                stats['avg_duration'] = stats['total_duration'] / stats['successful_runs']
                stats['last_run_time'] = time.time()
        except Exception as exc:
            # Task failed - log but don't raise
            duration = time.time() - start_time
            error_type = type(exc).__name__
            if task_id:
                async with _task_store_lock:
                    if task_id in _task_store:
                        _task_store[task_id].status = TaskStatus.FAILED
                        _task_store[task_id].error = str(exc)
                        _task_store[task_id].error_type = error_type
                        _task_store[task_id].completed_at = time.time()
                        _task_store[task_id].duration_seconds = duration
            
            # Update statistics
            async with _task_stats_lock:
                if func.__name__ not in _task_stats:
                    _task_stats[func.__name__] = {
                        'total_runs': 0,
                        'successful_runs': 0,
                        'failed_runs': 0,
                        'total_duration': 0.0,
                        'avg_duration': 0.0,
                        'last_run_time': 0.0,
                    }
                stats = _task_stats[func.__name__]
                stats['total_runs'] += 1
                stats['failed_runs'] += 1
                stats['last_run_time'] = time.time()
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


async def wait_for_active_tasks(timeout: Optional[float] = None) -> bool:
    """
    Wait for all active background tasks to complete (for graceful shutdown).
    
    Args:
        timeout: Maximum time to wait in seconds.
                If None, uses BACKGROUND_TASK_TIMEOUT from settings.
        
    Returns:
        True if all tasks completed, False if timeout
    """
    if timeout is None:
        timeout = getattr(settings, 'BACKGROUND_TASK_TIMEOUT', 30.0)
    
    async with _active_tasks_lock:
        tasks = list(_active_tasks)
    
    if not tasks:
        return True
    
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


# Guidelines for when to use BackgroundTasks vs Celery
BACKGROUND_TASKS_GUIDELINES = """
When to use FastAPI BackgroundTasks:
- Simple, non-critical operations
- Tasks that complete quickly (< 2 seconds recommended, < 30 seconds acceptable)
- Tasks that don't need persistence or retry guarantees
- Tasks that don't need to be distributed across workers
- Tasks that are tied to the request lifecycle
- I/O-bound tasks (database operations, file processing, API calls)
- Tasks that can use connection pooling
- Fire-and-forget operations (logging, analytics, cache updates)

When to use Celery/RQ instead:
- CPU-intensive tasks (data processing, image manipulation, calculations)
- Long-running operations (> 2 seconds, especially > 30 seconds)
- Critical tasks requiring retry logic and persistence
- Tasks needing monitoring and status tracking
- Distributed processing across multiple workers
- Scheduled/periodic tasks (cron-like)
- Tasks that need priority queues
- Tasks that need result storage and querying

Best Practices for BackgroundTasks:
- Use run_in_threadpool for CPU-bound operations (automatically detected)
- Always handle errors gracefully (don't raise exceptions)
- Use rate limiting (semaphores) for resource-intensive tasks
- Track task status for long-running operations
- Use connection pooling for database operations
- Implement graceful shutdown for critical tasks
- Monitor task execution times and failure rates
- Keep tasks short and focused (break down complex operations)

Connection Pooling in Background Tasks:
- Background tasks share the same database connection pool as the main application
- Use dependency injection to get database sessions: `session: AsyncSession = Depends(get_db)`
- Don't create new database connections in background tasks - reuse the pool
- The connection pool is managed at the application level, not per-task
- Example:
    async def update_analytics(user_id: int, session: AsyncSession):
        # Use the provided session from the connection pool
        await session.execute(update(User).where(User.id == user_id))
        await session.commit()

Decision Matrix:
┌─────────────────────┬──────────────────┬──────────────┐
│ Requirement         │ BackgroundTasks  │ Celery       │
├─────────────────────┼──────────────────┼──────────────┤
│ Task duration       │ < 2 seconds      │ Any          │
│ Criticality         │ Non-critical     │ Critical     │
│ Retry logic         │ Manual           │ Built-in     │
│ Monitoring          │ Basic (logging)  │ Flower       │
│ Persistence         │ No               │ Yes          │
│ Distributed         │ No               │ Yes          │
│ Setup complexity    │ None             │ Medium       │
│ Worker management   │ With Gunicorn    │ Separate     │
└─────────────────────┴──────────────────┴──────────────┘
"""


def recommend_task_type(
    duration_estimate: Optional[float] = None,
    is_critical: bool = False,
    needs_retry: bool = False,
    needs_persistence: bool = False,
    needs_distributed: bool = False,
    is_cpu_intensive: bool = False,
) -> str:
    """
    Recommend whether to use BackgroundTasks or Celery based on task characteristics.
    
    Args:
        duration_estimate: Estimated task duration in seconds
        is_critical: Whether task is critical (must not fail silently)
        needs_retry: Whether task needs automatic retry logic
        needs_persistence: Whether task must survive server restarts
        needs_distributed: Whether task needs to run across multiple workers
        is_cpu_intensive: Whether task is CPU-intensive
        
    Returns:
        "background_tasks" or "celery"
    """
    # If any of these are true, recommend Celery
    if (
        (duration_estimate and duration_estimate > 2.0)
        or is_critical
        or needs_retry
        or needs_persistence
        or needs_distributed
        or is_cpu_intensive
    ):
        return "celery"
    
    return "background_tasks"


# Task chaining utilities

def chain_background_tasks(
    background_tasks: BackgroundTasks,
    *task_functions: tuple[Callable, tuple, dict],
) -> None:
    """
    Chain multiple background tasks to execute sequentially.
    
    Tasks execute in the order provided. Each task receives the result
    of the previous task (if any) as input.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        *task_functions: Variable number of tuples: (func, args, kwargs)
        
    Example:
        chain_background_tasks(
            background_tasks,
            (send_email, (user_id,), {}),
            (update_analytics, (user_id,), {}),
            (log_event, ("user_registered",), {"user_id": user_id})
        )
    """
    async def chained_executor():
        previous_result = None
        for func, args, kwargs in task_functions:
            try:
                if asyncio.iscoroutinefunction(func):
                    if previous_result is not None:
                        result = await func(previous_result, *args, **kwargs)
                    else:
                        result = await func(*args, **kwargs)
                else:
                    if previous_result is not None:
                        result = await run_in_threadpool(func, previous_result, *args, **kwargs)
                    else:
                        result = await run_in_threadpool(func, *args, **kwargs)
                previous_result = result
            except Exception as exc:
                # Continue with next task even if one fails
                previous_result = None
    
    background_tasks.add_task(chained_executor)


def add_task_with_dependencies(
    background_tasks: BackgroundTasks,
    task_func: Callable,
    dependencies: list[Callable],
    *args,
    **kwargs,
) -> None:
    """
    Add a background task that depends on other tasks completing first.
    
    Note: This is a simplified version. In practice, you'd use a task queue
    like Celery for complex dependency management.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        task_func: Task function to execute
        dependencies: List of dependency task functions (executed first)
        *args: Arguments for task_func
        **kwargs: Keyword arguments for task_func
        
    Example:
        async def validate_data(data):
            # Validation task
            return validated_data
        
        async def process_data(data):
            # Processing task
            return processed_data
        
        add_task_with_dependencies(
            background_tasks,
            process_data,
            [validate_data],
            data
        )
    """
    async def task_with_deps():
        # Execute dependencies first
        dep_results = []
        for dep_func in dependencies:
            try:
                if asyncio.iscoroutinefunction(dep_func):
                    result = await dep_func(*args, **kwargs)
                else:
                    result = await run_in_threadpool(dep_func, *args, **kwargs)
                dep_results.append(result)
            except Exception as exc:
                raise
        
        # Execute main task with dependency results
        if asyncio.iscoroutinefunction(task_func):
            await task_func(*dep_results, *args, **kwargs)
        else:
            await run_in_threadpool(task_func, *dep_results, *args, **kwargs)
    
    background_tasks.add_task(task_with_deps)


# Connection pooling examples and helpers

async def background_task_with_db_session(
    task_func: Callable,
    *args,
    db_session_factory: Optional[Callable] = None,
    **kwargs,
) -> None:
    """
    Execute a background task with a database session from the connection pool.
    
    This demonstrates proper use of connection pooling in background tasks.
    The session is obtained from the application's connection pool and
    properly closed after use.
    
    Args:
        task_func: Async function that takes a session as first argument
        *args: Additional arguments for task_func
        db_session_factory: Function to get database session (defaults to get_db)
        **kwargs: Keyword arguments for task_func
        
    Example:
        async def update_user_analytics(session: AsyncSession, user_id: int):
            # Use session from connection pool
            await session.execute(update(User).where(User.id == user_id))
            await session.commit()
        
        # In endpoint:
        background_tasks.add_task(
            background_task_with_db_session,
            update_user_analytics,
            user_id=123
        )
    """
    if db_session_factory is None:
        db_session_factory = get_db
    
    # Get session from connection pool
    async for session in db_session_factory():
        try:
            # Execute task with session
            if asyncio.iscoroutinefunction(task_func):
                await task_func(session, *args, **kwargs)
            else:
                # Sync function - use threadpool
                await run_in_threadpool(task_func, session, *args, **kwargs)
        except Exception as exc:
            raise
        finally:
            # Session is automatically closed by get_db context manager
            pass


# Task result storage (in-memory with optional Redis)

_task_results: Dict[str, Any] = {}
_task_results_lock = asyncio.Lock()


async def store_task_result(task_id: str, result: Any, ttl: Optional[int] = None) -> None:
    """
    Store task result for later retrieval.
    
    Args:
        task_id: Task identifier
        result: Task result to store
        ttl: Time to live in seconds (None = no expiration)
    """
    async with _task_results_lock:
        _task_results[task_id] = {
            "result": result,
            "stored_at": time.time(),
            "ttl": ttl,
        }


async def get_task_result(task_id: str) -> Optional[Any]:
    """
    Retrieve stored task result.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task result if found and not expired, None otherwise
    """
    async with _task_results_lock:
        if task_id not in _task_results:
            return None
        
        task_data = _task_results[task_id]
        current_time = time.time()
        
        # Check expiration
        if task_data["ttl"]:
            if current_time - task_data["stored_at"] > task_data["ttl"]:
                del _task_results[task_id]
                return None
        
        return task_data["result"]


async def clear_task_result(task_id: str) -> bool:
    """
    Clear stored task result.
    
    Args:
        task_id: Task identifier
        
    Returns:
        True if result was cleared, False if not found
    """
    async with _task_results_lock:
        if task_id in _task_results:
            del _task_results[task_id]
            return True
        return False
