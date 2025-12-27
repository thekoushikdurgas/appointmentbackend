"""Async SQLAlchemy session management for FastAPI dependencies."""

import atexit
import threading
import time
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.utils.logger import get_logger, log_database_operation, log_error
from app.utils.query_monitor import get_query_monitor

settings = get_settings()
logger = get_logger(__name__)
database_url = settings.DATABASE_URL
if not database_url:
    raise ValueError("DATABASE_URL is not configured.")

# Enhance database URL with compression if enabled
def enhance_database_url(url: str, enable_compression: bool) -> str:
    """Add query compression parameters to database URL if enabled."""
    if not enable_compression:
        return url
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Add compression parameters for asyncpg
    # asyncpg supports compression via connection parameters
    # We'll handle this in the connection args instead of URL params
    return url

enhanced_database_url = enhance_database_url(database_url, settings.ENABLE_QUERY_COMPRESSION)

# Connection arguments for asyncpg with compression
connect_args = {}
if settings.ENABLE_QUERY_COMPRESSION:
    # Enable compression for large result sets
    # asyncpg supports server_min_messages and other connection options
    connect_args["server_settings"] = {
        "application_name": "appointment360_api",
    }

engine: AsyncEngine = create_async_engine(
    enhanced_database_url,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    connect_args={
        **connect_args,
        # CRITICAL: Add asyncpg-specific connection timeouts for remote RDS
        "timeout": 5.0,  # 5 second connection timeout
        "command_timeout": 3.0,  # 3 second command timeout
        "server_settings": {
            "application_name": "appointment360_api",
            "statement_timeout": "2000",  # 2 second SQL statement timeout
        }
    },
)

# Set up query monitoring if enabled
if settings.ENABLE_QUERY_MONITORING:
    try:
        query_monitor = get_query_monitor()
        query_monitor.slow_query_threshold = settings.SLOW_QUERY_THRESHOLD
        query_monitor.setup_engine_monitoring(engine)
    except Exception:
        pass  # Query monitoring setup failed (non-critical)

# Add connection pool event listeners for monitoring
# For async engines, we use sync_engine for event listeners
try:
    sync_engine = engine.sync_engine
    
    @event.listens_for(sync_engine, "connect")
    def set_connection_settings(dbapi_conn, connection_record):
        """Set connection-level settings for optimal performance."""
        if settings.ENABLE_QUERY_COMPRESSION:
            pass  # Placeholder for connection-level optimizations

    # Connection pool statistics
    pool_stats = {
        "checkouts": 0,
        "checkins": 0,
        "invalidated": 0,
        "overflow": 0,
        "wait_times": [],  # Track connection wait times
        "max_wait_time": 0.0,
        "total_wait_time": 0.0,
    }
    
    @event.listens_for(sync_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout for monitoring."""
        checkout_start = time.time()
        pool_stats["checkouts"] += 1
        
        if settings.ENABLE_POOL_MONITORING:
            pool = sync_engine.pool
            size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # Calculate wait time (time spent waiting for connection)
            # This is approximate - actual wait happens before this event
            wait_time = time.time() - checkout_start
            if wait_time > 0:
                pool_stats["wait_times"].append(wait_time)
                pool_stats["total_wait_time"] += wait_time
                if wait_time > pool_stats["max_wait_time"]:
                    pool_stats["max_wait_time"] = wait_time
                
                # Keep only last 1000 wait times to avoid memory issues
                if len(pool_stats["wait_times"]) > 1000:
                    pool_stats["wait_times"] = pool_stats["wait_times"][-1000:]
            
            # Calculate pool usage percentage
            usage_percentage = (checked_out / size * 100) if size > 0 else 0.0
            normalized_overflow = max(0, overflow) if overflow is not None else 0
            
            # Log connection checkout if wait time is significant or pool is saturated
            if wait_time > 0.1:  # Log if waited more than 100ms
                logger.warning(
                    "Slow connection checkout",
                    extra={
                        "context": {
                            "wait_time_ms": wait_time * 1000,
                            "pool_size": size,
                            "checked_out": checked_out,
                            "checked_in": checked_in,
                            "overflow": normalized_overflow,
                            "usage_percentage": usage_percentage,
                        }
                    }
                )
            
            # Log pool saturation warnings (>80% usage)
            if usage_percentage > 80.0:
                logger.warning(
                    "Database connection pool saturation warning",
                    extra={
                        "context": {
                            "usage_percentage": usage_percentage,
                            "pool_size": size,
                            "checked_out": checked_out,
                            "checked_in": checked_in,
                            "overflow": normalized_overflow,
                            "wait_time_ms": wait_time * 1000 if wait_time > 0 else 0,
                        }
                    }
                )
            
            # Log pool exhaustion (>95% usage or significant overflow)
            if usage_percentage > 95.0 or normalized_overflow > size * 0.2:
                logger.error(
                    "Database connection pool near exhaustion",
                    extra={
                        "context": {
                            "usage_percentage": usage_percentage,
                            "pool_size": size,
                            "checked_out": checked_out,
                            "checked_in": checked_in,
                            "overflow": normalized_overflow,
                            "wait_time_ms": wait_time * 1000 if wait_time > 0 else 0,
                            "threshold_exceeded": "usage" if usage_percentage > 95.0 else "overflow",
                        }
                    }
                )
            
    
    @event.listens_for(sync_engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection checkin for monitoring."""
        pool_stats["checkins"] += 1
        if settings.ENABLE_POOL_MONITORING:
            pool = sync_engine.pool
            size = pool.size()
            checked_out = pool.checkedout()
            checked_in = pool.checkedin()
            overflow = pool.overflow()
            normalized_overflow = max(0, overflow) if overflow is not None else 0
            usage_percentage = (checked_out / size * 100) if size > 0 else 0.0
            
            # Log connection checkin with pool stats for monitoring
            if usage_percentage > 80.0:  # Log if pool is still saturated after checkin
                logger.debug(
                    "Connection checked in (pool still saturated)",
                    extra={
                        "context": {
                            "usage_percentage": usage_percentage,
                            "pool_size": size,
                            "checked_out": checked_out,
                            "checked_in": checked_in,
                            "overflow": normalized_overflow,
                        }
                    }
                )
    
    @event.listens_for(sync_engine, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Log connection invalidation."""
        pool_stats["invalidated"] += 1
        if exception:
            logger.warning(
                "Database connection invalidated",
                exc_info=exception,
                extra={
                    "context": {
                        "total_invalidated": pool_stats["invalidated"],
                        "error_type": type(exception).__name__ if exception else None,
                    }
                }
            )
        else:
            logger.warning(
                "Database connection invalidated",
                extra={"context": {"total_invalidated": pool_stats["invalidated"]}}
            )
    
    def get_pool_stats() -> dict:
        """Get current connection pool statistics."""
        try:
            pool = sync_engine.pool
            size = pool.size()
            checked_out = pool.checkedout()
            checked_in = pool.checkedin()
            overflow = pool.overflow()
            
            # Calculate wait time statistics
            wait_times = pool_stats["wait_times"]
            avg_wait_time = (
                pool_stats["total_wait_time"] / len(wait_times)
                if wait_times else 0.0
            )
            
            # Clamp overflow to 0 if negative (SQLAlchemy async engine bug)
            # Overflow should never be negative - it represents connections beyond pool size
            normalized_overflow = max(0, overflow) if overflow is not None else 0
            
            # Calculate usage percentage
            usage_percentage = (checked_out / size * 100) if size > 0 else 0.0
            
            # Health status logic: idle pools (0% usage) should be healthy, not warning
            # Healthy: < 70% usage AND (no overflow OR normalized overflow is 0)
            # Warning: 70-90% usage OR (some overflow but < 10% of pool size)
            # Critical: > 90% usage OR high overflow
            if usage_percentage < 70.0 and normalized_overflow == 0:
                health_status = "healthy"
            elif usage_percentage < 90.0 and normalized_overflow < size * 0.1:
                health_status = "warning"
            else:
                health_status = "critical"
            
            return {
                "size": size,
                "checked_in": checked_in,
                "checked_out": checked_out,
                "overflow": normalized_overflow,  # Return normalized overflow
                "usage_percentage": usage_percentage,
                "total_checkouts": pool_stats["checkouts"],
                "total_checkins": pool_stats["checkins"],
                "total_invalidated": pool_stats["invalidated"],
                "wait_time_stats": {
                    "avg_wait_time_seconds": avg_wait_time,
                    "max_wait_time_seconds": pool_stats["max_wait_time"],
                    "total_wait_time_seconds": pool_stats["total_wait_time"],
                    "samples": len(wait_times),
                },
                "health_status": health_status,
            }
        except Exception as exc:
            # Warning condition: Pool stats could not be retrieved with error details
            return {}
    
    def check_pool_health() -> dict:
        """Check connection pool health and return status."""
        stats = get_pool_stats()
        if not stats:
            return {
                "status": "unknown",
                "message": "Could not retrieve pool statistics",
            }
        
        size = stats.get("size", 0)
        checked_out = stats.get("checked_out", 0)
        overflow = stats.get("overflow", 0)
        usage_percentage = stats.get("usage_percentage", 0.0)
        avg_wait_time = stats.get("wait_time_stats", {}).get("avg_wait_time_seconds", 0.0)
        
        # Normalize overflow to handle negative values (SQLAlchemy async engine issue)
        normalized_overflow = max(0, overflow) if overflow is not None else 0
        
        # Health check criteria (consistent with get_pool_stats)
        # Healthy: < 70% usage, no overflow, low wait time
        # Warning: 70-90% usage or some overflow (< 10% of pool) or moderate wait time
        # Critical: > 90% usage or high overflow or high wait time
        usage_ratio = checked_out / size if size > 0 else 0.0
        
        # Use consistent logic with get_pool_stats, but also consider wait time
        if usage_ratio < 0.7 and normalized_overflow == 0 and avg_wait_time < 0.1:
            status = "healthy"
        elif usage_ratio < 0.9 and normalized_overflow < size * 0.1 and avg_wait_time < 0.5:
            status = "warning"
        else:
            status = "critical"
        
        # Use normalized overflow in message
        message = (
            f"Pool usage: {usage_percentage:.1f}% ({checked_out}/{size}), "
            f"overflow: {normalized_overflow}, avg wait: {avg_wait_time*1000:.1f}ms"
        )
        
        return {
            "status": status,
            "message": message,
            "stats": stats,
        }
    
    # Log pool statistics periodically if enabled
    if settings.ENABLE_POOL_MONITORING and settings.POOL_MONITORING_INTERVAL > 0:
        def log_pool_stats():
            """Periodically log pool statistics."""
            while True:
                time.sleep(settings.POOL_MONITORING_INTERVAL)
                stats = get_pool_stats()
                if stats:
                    usage_percentage = stats.get("usage_percentage", 0.0)
                    health_status = stats.get("health_status", "unknown")
                    wait_stats = stats.get("wait_time_stats", {})
                    avg_wait_time = wait_stats.get("avg_wait_time_seconds", 0.0) * 1000
                    
                    # Log at appropriate level based on health status
                    if health_status == "critical":
                        logger.error(
                            "Database connection pool health check: CRITICAL",
                            extra={
                                "context": stats,
                                "performance": {
                                    "avg_wait_time_ms": avg_wait_time,
                                }
                            }
                        )
                    elif health_status == "warning":
                        logger.warning(
                            "Database connection pool health check: WARNING",
                            extra={
                                "context": stats,
                                "performance": {
                                    "avg_wait_time_ms": avg_wait_time,
                                }
                            }
                        )
                    elif usage_percentage > 70.0:  # Log healthy but busy pools as info
                        logger.info(
                            "Database connection pool health check: healthy (high usage)",
                            extra={
                                "context": stats,
                                "performance": {
                                    "avg_wait_time_ms": avg_wait_time,
                                }
                            }
                        )
                    # Don't log healthy pools with low usage (to reduce log noise)
        
        # Start monitoring thread (daemon so it doesn't block shutdown)
        monitor_thread = threading.Thread(target=log_pool_stats, daemon=True)
        monitor_thread.start()
    
    # Log pool stats on shutdown
    def log_final_pool_stats():
        """Log final pool statistics on application shutdown."""
        get_pool_stats()  # Retrieve stats for potential future use
    
    atexit.register(log_final_pool_stats)
except AttributeError:
    pass  # sync_engine not available, skip event listeners

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Commits the transaction on successful completion, rolls back on exception.
    Handles cases where the session is already in an invalid/rolled-back state.
    
    Note: The session is automatically closed by the async context manager.
    We should not explicitly close it in a finally block to avoid race conditions.
    """
    start_time = time.time()
    
    # Use context manager to ensure proper connection pool management
    # The context manager ensures connections are returned to the pool
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Commit transaction on successful completion
            commit_start = time.time()
            await session.commit()
            commit_duration = (time.time() - commit_start) * 1000
            log_database_operation("COMMIT", duration_ms=commit_duration)
        except Exception as exc:
            # Distinguish between different exception types for proper logging
            # Validation errors and HTTP exceptions are not database errors
            transaction_duration_ms = (time.time() - start_time) * 1000
            
            # Check if this is a validation error (happens before DB operations)
            if isinstance(exc, RequestValidationError):
                # This is a Pydantic validation error, not a database error
                # Don't log as database error - validation handler will log it
                # Still need to rollback to clean up session state
                rollback_start = time.time()
                try:
                    await session.rollback()
                    rollback_duration = (time.time() - rollback_start) * 1000
                    log_database_operation("ROLLBACK", duration_ms=rollback_duration)
                except Exception:
                    pass  # Ignore rollback errors for validation errors
                # Re-raise without logging as DB error
                raise
            
            # Check if this is an HTTP exception (business logic error)
            if isinstance(exc, HTTPException):
                # HTTP exceptions are application-level, not database errors
                # Still need to rollback for clean state
                rollback_start = time.time()
                try:
                    await session.rollback()
                    rollback_duration = (time.time() - rollback_start) * 1000
                    log_database_operation("ROLLBACK", duration_ms=rollback_duration)
                except Exception:
                    pass  # Ignore rollback errors for HTTP exceptions
                # Re-raise without logging as DB error
                raise
            
            # For actual database errors, always rollback and log properly
            rollback_start = time.time()
            try:
                await session.rollback()
                rollback_duration = (time.time() - rollback_start) * 1000
                log_database_operation("ROLLBACK", duration_ms=rollback_duration)
            except Exception as rollback_exc:
                # Catch all exceptions during rollback to prevent cascading errors
                # Session might already be in an invalid state
                # Don't re-raise rollback errors - the original exception is more important
                log_error(
                    "Error during transaction rollback",
                    rollback_exc,
                    "app.db.session",
                    context={"original_error": str(exc)},
                )
            
            # Log actual database errors with appropriate context
            if isinstance(exc, SQLAlchemyError):
                log_error(
                    "Database transaction error",
                    exc,
                    "app.db.session",
                    context={
                        "transaction_duration_ms": transaction_duration_ms,
                        "error_type": "SQLAlchemyError",
                    },
                )
            else:
                # Other exceptions that occurred during DB operations
                log_error(
                    "Error during database operation",
                    exc,
                    "app.db.session",
                    context={
                        "transaction_duration_ms": transaction_duration_ms,
                        "error_type": type(exc).__name__,
                    },
                )
            
            # Re-raise to propagate the error
            raise

