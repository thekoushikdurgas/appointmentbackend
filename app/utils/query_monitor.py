"""Query performance monitoring utilities.

This module provides database query performance monitoring to identify and log
slow queries. The monitor is automatically set up in db/session.py when
ENABLE_QUERY_MONITORING is enabled in configuration.

The monitor tracks:
- Total query count
- Slow queries (exceeding threshold)
- Average query time
- Query execution statistics

Usage:
    The monitor is automatically initialized when the database engine is created.
    To access statistics:
        from app.utils.query_monitor import get_query_monitor
        monitor = get_query_monitor()
        stats = monitor.get_stats()
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from app.utils.logger import get_logger

logger = get_logger(__name__)

from app.core.config import get_settings

settings = get_settings()

# Configuration
SLOW_QUERY_THRESHOLD = 1.0  # seconds
ENABLE_QUERY_MONITORING = True


class QueryMonitor:
    """Monitor and log slow database queries."""

    def __init__(self, slow_query_threshold: float = SLOW_QUERY_THRESHOLD):
        """
        Initialize query monitor.
        
        Args:
            slow_query_threshold: Threshold in seconds for logging slow queries
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_count = 0
        self.slow_query_count = 0
        self.total_query_time = 0.0

    def setup_engine_monitoring(self, engine: AsyncEngine) -> None:
        """
        Set up query monitoring for an async engine.
        
        Args:
            engine: SQLAlchemy async engine
        """
        if not ENABLE_QUERY_MONITORING:
            return

        try:
            # Get sync engine for event listeners
            sync_engine = engine.sync_engine

            @event.listens_for(sync_engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                """Record query start time."""
                context._query_start_time = time.time()
                return None

            @event.listens_for(sync_engine, "after_cursor_execute")
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                """Log slow queries and capture query plans for very slow queries."""
                if hasattr(context, "_query_start_time"):
                    query_time = time.time() - context._query_start_time
                    self.query_count += 1
                    self.total_query_time += query_time

                    if query_time > self.slow_query_threshold:
                        self.slow_query_count += 1

        except AttributeError:
            pass

    def get_stats(self) -> dict[str, Any]:
        """
        Get query monitoring statistics.
        
        Returns:
            Dictionary with query statistics
        """
        avg_time = (
            self.total_query_time / self.query_count
            if self.query_count > 0
            else 0.0
        )
        return {
            "total_queries": self.query_count,
            "slow_queries": self.slow_query_count,
            "total_query_time": self.total_query_time,
            "average_query_time": avg_time,
            "slow_query_threshold": self.slow_query_threshold,
        }

    def reset_stats(self) -> None:
        """Reset query monitoring statistics."""
        self.query_count = 0
        self.slow_query_count = 0
        self.total_query_time = 0.0


# Global query monitor instance
_query_monitor: Optional[QueryMonitor] = None


def get_query_monitor() -> QueryMonitor:
    """Get the global query monitor instance."""
    global _query_monitor
    if _query_monitor is None:
        _query_monitor = QueryMonitor()
    return _query_monitor


@asynccontextmanager
async def measure_query_time(operation_name: str):
    """
    Context manager to measure query execution time.
    
    Usage:
        async with measure_query_time("list_contacts"):
            result = await repository.list_contacts(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time

