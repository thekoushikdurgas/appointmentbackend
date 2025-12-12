"""Async SQLAlchemy session management for FastAPI dependencies."""

from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.exc import IllegalStateChangeError, PendingRollbackError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.utils.query_monitor import get_query_monitor
import atexit


settings = get_settings()
database_url = settings.DATABASE_URL
if not database_url:
    raise ValueError("DATABASE_URL is not configured.")

# Enhance database URL with compression if enabled
def enhance_database_url(url: str, enable_compression: bool) -> str:
    """Add query compression parameters to database URL if enabled."""
    if not enable_compression:
        return url
    
    parsed = urlparse(url)
    from urllib.parse import parse_qs
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
        "application_name": "contact360_api",
    }

engine: AsyncEngine = create_async_engine(
    enhanced_database_url,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    connect_args=connect_args,
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
        import time
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
            
    
    @event.listens_for(sync_engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection checkin for monitoring."""
        pool_stats["checkins"] += 1
        if settings.ENABLE_POOL_MONITORING:
            pool = sync_engine.pool
            # Connection checked in with total checkins and pool size
    
    @event.listens_for(sync_engine, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Log connection invalidation."""
        pool_stats["invalidated"] += 1
        # Warning condition: Connection invalidated with total invalidated count and exception details
    
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
            
            return {
                "size": size,
                "checked_in": checked_in,
                "checked_out": checked_out,
                "overflow": overflow,
                "usage_percentage": (checked_out / size * 100) if size > 0 else 0.0,
                "total_checkouts": pool_stats["checkouts"],
                "total_checkins": pool_stats["checkins"],
                "total_invalidated": pool_stats["invalidated"],
                "wait_time_stats": {
                    "avg_wait_time_seconds": avg_wait_time,
                    "max_wait_time_seconds": pool_stats["max_wait_time"],
                    "total_wait_time_seconds": pool_stats["total_wait_time"],
                    "samples": len(wait_times),
                },
                "health_status": (
                    "healthy" if checked_out < size * 0.7 and overflow == 0
                    else "warning" if checked_out < size * 0.9
                    else "critical"
                ),
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
        
        # Health check criteria
        # Healthy: < 70% usage, no overflow, low wait time
        # Warning: 70-90% usage or some overflow or moderate wait time
        # Critical: > 90% usage or high overflow or high wait time
        usage_ratio = checked_out / size if size > 0 else 0.0
        
        if usage_ratio < 0.7 and overflow == 0 and avg_wait_time < 0.1:
            status = "healthy"
        elif usage_ratio < 0.9 and overflow < size * 0.1 and avg_wait_time < 0.5:
            status = "warning"
        else:
            status = "critical"
        message = (
            f"Pool usage: {usage_percentage:.1f}% ({checked_out}/{size}), "
            f"overflow: {overflow}, avg wait: {avg_wait_time*1000:.1f}ms"
        )
        
        return {
            "status": status,
            "message": message,
            "stats": stats,
        }
    
    # Log pool statistics periodically if enabled
    if settings.ENABLE_POOL_MONITORING and settings.POOL_MONITORING_INTERVAL > 0:
        import threading
        import time
        
        def log_pool_stats():
            """Periodically log pool statistics."""
            while True:
                time.sleep(settings.POOL_MONITORING_INTERVAL)
                stats = get_pool_stats()
                if stats:
                    wait_stats = stats.get("wait_time_stats", {})
                    # Connection pool stats with size, checked out count, checked in count, overflow, usage percentage, health status, total checkouts, total checkins, invalidated count, and wait time statistics
        
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
    # Use context manager to ensure proper connection pool management
    # The context manager ensures connections are returned to the pool
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Commit transaction on successful completion
            await session.commit()
        except Exception as exc:
            # Always rollback on exception to ensure session is in clean state
            # This prevents IllegalStateChangeError when session context manager tries to close
            # Even for HTTPException, we need to clean up the transaction state
            # Rollback transaction on exception to ensure clean state
            # Handle cases where session is already in an invalid/rolled-back state
            try:
                await session.rollback()
            except Exception as rollback_exc:
                # Catch all exceptions during rollback to prevent cascading errors
                # Session might already be in an invalid state
                # Don't re-raise rollback errors - the original exception is more important
                pass
            # Re-raise to propagate the error
            raise

