# Big Data Optimizations Guide

This document provides comprehensive information about the big data handling optimizations implemented in the Appointment360 FastAPI backend.

## Table of Contents

1. [Overview](#overview)
2. [Streaming Responses](#streaming-responses)
3. [Chunked File Uploads](#chunked-file-uploads)
4. [Query Caching](#query-caching)
5. [Parallel Processing](#parallel-processing)
6. [Database Optimizations](#database-optimizations)
7. [Configuration](#configuration)
8. [Performance Tuning](#performance-tuning)

## Overview

The Appointment360 backend is optimized to handle large datasets efficiently through:

- **Streaming Responses**: Send large datasets in chunks without loading everything into memory
- **Chunked File Uploads**: Process file uploads in configurable chunks
- **Query Caching**: In-memory caching with TTL support for frequently accessed queries
- **Parallel Processing**: Utilities for CPU-intensive and I/O-bound parallel tasks
- **Database-Level Aggregations**: Use PostgreSQL functions instead of Python-side processing
- **Connection Pool Optimization**: Tuned connection pooling with detailed monitoring and health checks
- **Background Tasks**: FastAPI BackgroundTasks with CPU-bound detection, status tracking, duration monitoring, rate limiting, and graceful shutdown
- **Redis Caching**: Optional Redis backend for distributed query caching

## Streaming Responses

### Overview

Streaming responses allow sending large datasets to clients without loading everything into memory. This is essential for exports and bulk operations.

### Endpoints

#### Contacts Streaming
```
GET /api/v1/contacts/stream/?format=jsonl&max_results=10000
GET /api/v1/contacts/stream/?format=csv&email=example.com
```

#### Companies Streaming
```
GET /api/v1/companies/stream/?format=jsonl&max_results=10000
GET /api/v1/companies/stream/?format=csv&name=example
```

### Formats

- **JSONL** (`format=jsonl`): Newline-delimited JSON, one object per line
- **CSV** (`format=csv`): Comma-separated values with header row

### Usage Example

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "GET",
        "http://127.0.0.1:8000/api/v1/contacts/stream/?format=jsonl",
        headers={"Authorization": "Bearer <token>"}
    ) as response:
        async for line in response.aiter_lines():
            contact = json.loads(line)
            process_contact(contact)
```

### Implementation

Streaming uses the `stream_query_results` utility from `app.utils.streaming_queries`, which:
- Fetches results in configurable batch sizes (default: 1000 rows)
- Supports max_results limits
- Uses database cursors for efficient server-side streaming
- **Error handling**: Automatic retry with exponential backoff for transient failures
- **Memory management**: Optimized chunk sizes and cleanup
- **Progress tracking**: Logs batch progress and total fetched count

## Chunked File Uploads

### Overview

File uploads are processed in chunks to avoid loading entire files into memory. This is critical for large CSV imports and file uploads.

### Implementation

All file uploads use `aiofiles` for async chunked reading:

```python
chunk_size = settings.MAX_UPLOAD_CHUNK_SIZE  # Default: 1MB
async with aiofiles.open(file_path, "wb") as async_file:
    while chunk := await file.read(chunk_size):
        await async_file.write(chunk)
```

### Configuration

- `MAX_UPLOAD_CHUNK_SIZE`: Chunk size for file uploads (default: 1MB)
- `MAX_UPLOAD_SIZE`: Maximum file size limit (optional)

### Endpoints

- **Contact Imports**: `/api/v1/contacts/import/` - Chunked CSV upload
- **Avatar Uploads**: `/api/v2/users/profile/avatar/` - Chunked image upload

## Query Caching

### Overview

Query result caching reduces database load for frequently accessed queries. The system supports multiple caching strategies:
- **functools.lru_cache**: For immutable, read-only data
- **cachetools.TTLCache**: For data with time-based expiration
- **Redis**: For distributed caching across workers

### Implementation

The caching system provides three tiers:

1. **functools.lru_cache** (`app.utils.cache_helpers`):
   - Per-process cache for immutable data
   - No TTL (persists for process lifetime)
   - Thread-safe by design
   - Best for: Settings, configs, ML models, static reference data

2. **cachetools.TTLCache** (in-memory):
   - Automatic TTL expiration
   - LRU eviction when maxsize is reached
   - Thread-safe operations
   - Memory efficient with automatic cleanup
   - Best for: Single-worker deployments, mutable data with acceptable staleness

3. **Redis** (distributed):
   - Shared across multiple workers
   - Persistent across restarts
   - Unlimited size (limited by Redis memory)
   - Best for: Multi-worker deployments, large cache sizes

### Configuration

Enable caching in `.env`:
```env
ENABLE_QUERY_CACHING=true
QUERY_CACHE_TTL=300  # 5 minutes
CACHE_MAX_SIZE=1000  # Maximum cache entries (LRU eviction)

# Optional: Redis backend for distributed caching
ENABLE_REDIS_CACHE=true
REDIS_URL=redis://localhost:6379/0

# Optional: Cache warming on startup
ENABLE_CACHE_WARMING=false
CACHE_WARMING_QUERIES=contacts:popular,companies:active
```

### Backend Options

**In-Memory Cache (cachetools.TTLCache)** (default):
- Fast, no external dependencies
- Uses `cachetools.TTLCache` for efficient TTL and LRU management
- Limited to single process (per-worker cache)
- Lost on restart
- Configurable maxsize (default: 1000 entries)
- Automatic expiration and eviction
- **Best for**: Single-worker deployments, immutable/read-only data

**Redis Cache** (optional):
- Distributed across multiple workers
- Persistent across restarts
- Unlimited size (limited by Redis memory)
- Better for production with multiple workers
- **Best for**: Multi-worker deployments, shared mutable state

### When to Use In-Memory vs Redis

**Use In-Memory (cachetools) when:**
- Single-worker deployment
- Read-only, immutable data (settings, configs, ML models)
- Low-latency requirements (sub-millisecond access)
- Small to moderate cache sizes (<1GB per worker)

**Use Redis when:**
- Multi-worker/multi-server deployments
- Shared mutable state across processes
- Large cache sizes (>1GB)
- Cache persistence requirements
- Horizontal scaling scenarios

### Automatic Caching

The following endpoints automatically cache results:
- `GET /api/v1/contacts/` - Caches paginated contact lists
- `GET /api/v1/companies/` - Caches paginated company lists

### Cache Invalidation

Cache is automatically invalidated when:
- Contacts are created, updated, or deleted
- Companies are created, updated, or deleted

### Manual Cache Management

```python
from app.utils.query_cache import get_query_cache, cache_aside, invalidate_on_update

cache = get_query_cache()

# Get cached result
result = await cache.get("contacts:list", filters={...}, limit=100, offset=0)

# Set cache
await cache.set("contacts:list", data, filters={...}, limit=100, offset=0)

# Cache-aside pattern (recommended)
async def fetch_contacts(filters, limit, offset):
    return await db.query_contacts(filters, limit, offset)

result = await cache_aside(
    cache,
    "contacts:list",
    fetch_contacts,
    filters=filters,
    limit=limit,
    offset=offset
)

# Event-driven invalidation (after updates)
await update_contact_in_db(contact_id, data)
await invalidate_on_update(cache, "contact", contact_id=contact_id)

# Pattern-based invalidation
await cache.invalidate_pattern("query_cache:contacts:list:*")

# Get cache statistics
stats = await cache.get_cache_stats()
# Returns: {"enabled": True, "backend": "redis" or "in-memory (cachetools.TTLCache)", ...}
```

### Cache Invalidation Patterns

**Event-Driven Invalidation:**
```python
from app.utils.query_cache import invalidate_with_event, invalidate_on_update, invalidate_on_create, invalidate_on_delete

# After updating data (with event tracking)
await invalidate_with_event(
    cache,
    "user",
    reason="user_updated",
    metadata={"user_id": user_id},
    user_id=user_id
)

# Convenience functions
await invalidate_on_update(cache, "user", user_id=user_id)
await invalidate_on_create(cache, "contacts", list=True)  # Invalidate list cache
await invalidate_on_delete(cache, "contact", contact_id=contact_id)
```

**Cache-Aside Pattern:**
```python
from app.utils.query_cache import cache_aside

# Automatically checks cache, fetches if miss, and caches result
result = await cache_aside(
    cache,
    "user",
    fetch_user_from_db,
    user_id=user_id
)
```

**Pattern-Based Invalidation:**
```python
# Invalidate all contact-related cache entries
await cache.invalidate_pattern("query_cache:contacts:*")
```

**Cache Warming:**
```python
from app.utils.query_cache import warm_cache_entry, warm_cache_batch

# Warm single entry
await warm_cache_entry(
    cache,
    "popular_contacts",
    fetch_popular_contacts,
    limit=100
)

# Warm multiple entries
tasks = [
    {"prefix": "popular_contacts", "fetch_func": fetch_popular_contacts, "kwargs": {"limit": 100}},
    {"prefix": "active_companies", "fetch_func": fetch_active_companies, "ttl": 600}
]
results = await warm_cache_batch(cache, tasks)
```

### Cache Warming

Cache warming pre-populates the cache on application startup to avoid cold starts:

```env
ENABLE_CACHE_WARMING=true
CACHE_WARMING_QUERIES=contacts:popular,companies:active,settings:app
```

The cache warming function runs during application startup and pre-loads frequently accessed data.

### HTTP Cache Headers

The system supports HTTP cache headers for client-side caching:

```python
from app.utils.http_cache import cache_response, create_cached_response, add_cache_headers

# Using decorator
@app.get("/reference-data")
@cache_response(max_age=3600, must_revalidate=True)
async def get_reference_data():
    return {"data": "value"}

# Using helper function
@app.get("/user-settings")
async def get_user_settings(request: Request, user_id: int):
    data = await fetch_user_settings(user_id)
    return create_cached_response(
        data,
        request,
        max_age=600,
        public=False
    )
```

### Best Practices

1. **Use `@lru_cache()` for immutable data**: Settings, configuration, static reference data
2. **Use cachetools.TTLCache for mutable data**: Query results, computed values with TTL
3. **Use Redis for multi-worker deployments**: Prevents cache inconsistency
4. **Use HTTP cache headers**: For client-side caching of static/semi-static data
5. **Invalidate on updates**: Always invalidate related cache entries when data changes
6. **Set appropriate maxsize**: Prevent unbounded cache growth
7. **Monitor cache hit rates**: Use `get_cache_stats()` to track performance
8. **Use cache-aside pattern**: Simplifies cache management
9. **Warm cache on startup**: Pre-populate frequently accessed data

## Parallel Processing

### Overview

Utilities for executing tasks in parallel, supporting both I/O-bound and CPU-intensive workloads.

### Async Parallel Processing (I/O-bound)

Use for database queries, API calls, file I/O:

```python
from app.utils.parallel_processing import process_in_parallel_async

async def fetch_user_data(user_id: int):
    return await db.get_user(user_id)

# Process in parallel (I/O-bound)
user_ids = [1, 2, 3, 4, 5]
users = await process_in_parallel_async(
    user_ids,
    fetch_user_data,
    max_concurrent=10
)
```

### Sync Parallel Processing (CPU-intensive)

Use for data processing, calculations (bypasses Python's GIL):

```python
from app.utils.parallel_processing import process_in_parallel_sync

def process_data_chunk(chunk: list[dict]):
    # CPU-intensive processing
    return transform_data(chunk)

chunks = [chunk1, chunk2, chunk3]
results = process_in_parallel_sync(
    chunks,
    process_data_chunk,
    max_workers=4
)
```

### Mixed CPU and I/O Processing

```python
from app.utils.parallel_processing import process_in_parallel_mixed

def parse_data(raw_data: bytes):
    # CPU-intensive parsing
    return json.loads(raw_data)

async def save_to_db(parsed_data: dict):
    # I/O-intensive database save
    return await db.save(parsed_data)

raw_data_list = [data1, data2, data3]
results = await process_in_parallel_mixed(
    raw_data_list,
    parse_data,  # CPU-bound
    save_to_db   # I/O-bound
)
```

### Batch Processing

Process large datasets in batches:

```python
from app.utils.parallel_processing import process_batches_async, process_batches_sync

# Async batch processing
async def process_contact_batch(batch: list[Contact]):
    return await db.bulk_insert_contacts(batch)

contacts = [contact1, contact2, ...]
results = await process_batches_async(
    contacts,
    process_contact_batch,
    batch_size=100,
    max_concurrent_batches=5
)

# Sync batch processing
def process_chunk_sync(chunk: list[dict]):
    return transform_chunk(chunk)

results = process_batches_sync(
    items,
    process_chunk_sync,
    batch_size=50,
    max_workers=4
)
```

### Context Manager

```python
from app.utils.parallel_processing import ParallelProcessor

with ParallelProcessor(max_workers=4) as processor:
    results = processor.process_sync(items, process_func)
```

## Database Optimizations

### Connection Pooling

The connection pool is optimized for large datasets:

- **Pool Size**: 25 connections (configurable)
- **Max Overflow**: 50 additional connections
- **Pool Monitoring**: Automatic statistics tracking and warnings

### Pool Monitoring

Pool statistics are logged periodically with detailed metrics:
- Connection checkouts/checkins
- Pool usage percentage and warnings (>80% utilization)
- Invalidated connections
- Connection wait times (average and maximum)
- Health status (healthy/degraded/critical)

**Health Check Endpoint**:
```
GET /health/db
```

Returns pool health status, usage statistics, and wait time metrics.

### Query Optimization

#### Select Only Needed Columns

```python
from app.utils.query_optimization import select_only_columns
from app.models.contacts import Contact

# Instead of: select(Contact)
query = select_only_columns(
    select(Contact),
    [Contact.id, Contact.name, Contact.email]
)
```

#### Prevent N+1 Queries

```python
from app.utils.query_optimization import prevent_n_plus_one

# Eager load relationships
query = prevent_n_plus_one(
    select(Contact),
    relationships=["company", "activities"],
    strategy="selectin"
)
```

#### Database-Level Aggregations

```python
from app.utils.query_optimization import use_database_aggregation
from sqlalchemy import func

# Count contacts by company (database-level)
query = use_database_aggregation(
    select(Contact),
    func.count(Contact.id),
    group_by=[Contact.company_id]
)
```

#### Query Analysis

```python
from app.utils.query_optimization import analyze_query_performance

query = select(Contact).where(Contact.email.like("%@example.com"))
analysis = await analyze_query_performance(session, query)

if analysis["warnings"]:
    logger.warning("Query performance issues: %s", analysis["warnings"])
```

### Database-Level Aggregations

Use PostgreSQL functions for aggregations:

```python
from app.utils.db_aggregations import build_json_object, aggregate_array

# Build JSON object in database
query = select(
    build_json_object(
        id=Contact.id,
        name=func.concat(Contact.first_name, ' ', Contact.last_name),
        email=Contact.email
    )
)

# Aggregate into array
query = select(
    aggregate_array(Contact.email, distinct=True)
).group_by(func.split_part(Contact.email, '@', 2))
```

### Streaming Queries

Use server-side cursors for large result sets:

```python
from app.utils.streaming_queries import stream_query_results

async for batch in stream_query_results(session, query, batch_size=1000):
    for row in batch:
        process_row(row)
```

## Configuration

### Environment Variables

Add to `.env`:

```env
# Streaming Configuration
STREAMING_CHUNK_SIZE=1048576  # 1MB
ENABLE_STREAMING_QUERIES=true
MAX_STREAMING_RESULTS=100000  # Optional limit

# File Upload Configuration
MAX_UPLOAD_CHUNK_SIZE=1048576  # 1MB
MAX_UPLOAD_SIZE=52428800  # 50MB (optional)

# Parallel Processing
PARALLEL_PROCESSING_WORKERS=4
PARALLEL_PROCESSING_MAX_WORKERS=8
ENABLE_PARALLEL_PROCESSING=true

# Query Caching
ENABLE_QUERY_CACHING=true
QUERY_CACHE_TTL=300  # 5 minutes
CACHE_MAX_SIZE=1000  # Maximum cache entries (LRU eviction)
ENABLE_REDIS_CACHE=false  # Enable Redis backend (requires REDIS_URL)
REDIS_URL=redis://localhost:6379/0  # Optional Redis connection URL
ENABLE_CACHE_WARMING=false  # Enable cache warming on startup
CACHE_WARMING_QUERIES=contacts:popular,companies:active  # Queries to warm

# Pagination
DEFAULT_PAGE_SIZE=100  # Default items per page (was None = unlimited)
MAX_PAGE_SIZE=1000  # Maximum allowed page size

# Background Tasks
MAX_CONCURRENT_BACKGROUND_TASKS=10  # Maximum concurrent background tasks
BACKGROUND_TASK_TIMEOUT=30.0  # Timeout for waiting for tasks during shutdown

# Streaming Configuration
STREAMING_BATCH_SIZE=1000  # Batch size for streaming database queries

# HTTP Cache Configuration
ENABLE_HTTP_CACHE=true  # Enable HTTP cache headers (ETag, Cache-Control)
HTTP_CACHE_MAX_AGE=300  # Default max-age for HTTP cache (seconds)
HTTP_CACHE_PUBLIC=true  # Whether cache is public or private
HTTP_CACHE_MUST_REVALIDATE=false  # Whether cache must revalidate
HTTP_CACHE_STATIC_MAX_AGE=31536000  # Max-age for static content (1 year)
HTTP_CACHE_API_MAX_AGE=300  # Max-age for API responses (5 minutes)

# Connection Pool Monitoring
ENABLE_POOL_MONITORING=true
POOL_MONITORING_INTERVAL=60  # Log stats every 60 seconds
```

## New Utilities

### Enhanced Streaming Responses

The system now includes optimized streaming response generators:

```python
from app.utils.streaming_responses import (
    stream_jsonl_async,
    stream_csv,
    stream_json_array_async,
    create_streaming_response_generator,
    optimize_chunk_size
)

# Optimize chunk size based on data type
chunk_size = optimize_chunk_size("jsonl", avg_item_size=500, target_chunk_size=1024*1024)

# Create streaming generator
generator = create_streaming_response_generator(
    items_iterator,
    format="jsonl",
    chunk_size=chunk_size
)
```

### Enhanced Pagination

Improved pagination utilities with performance optimizations:

```python
from app.utils.pagination import (
    normalize_page_size,
    should_use_cursor_pagination,
    optimize_pagination_params,
    get_pagination_metadata
)

# Optimize pagination parameters
params = optimize_pagination_params(
    offset=1500,
    limit=100,
    cursor=None
)

# Get pagination metadata
metadata = get_pagination_metadata(
    total_items=10000,
    page_size=100,
    current_offset=500
)
```

### Efficient Serialization

Pydantic TypeAdapter for high-performance serialization:

```python
from app.utils.serialization import (
    serialize_with_type_adapter,
    filter_response_data,
    OptimizedSerializer
)

# Serialize large collection
json_bytes = serialize_with_type_adapter(
    contacts,
    model=ContactListItem,
    use_orjson=True
)

# Filter sensitive data
filtered = filter_response_data(
    users,
    exclude_fields={"password", "api_key"}
)
```

### Enhanced File Uploads

Improved chunked uploads with resumable support:

```python
from app.utils.file_uploads import (
    save_upload_file_chunked,
    ResumableUpload,
    calculate_optimal_chunk_size,
    validate_file_upload
)

# Calculate optimal chunk size
chunk_size = calculate_optimal_chunk_size(
    file_size=100 * 1024 * 1024,
    file_type="video/mp4",
    network_condition="normal"
)

# Resumable upload
upload = ResumableUpload(upload_id, destination, total_size)
status = await upload.get_upload_status()
if status["can_resume"]:
    result = await upload.resume_upload(file)
```

## Background Tasks

### Overview

The backend uses FastAPI's `BackgroundTasks` for short, non-critical operations and Celery for long-running, critical tasks. The system automatically detects CPU-bound tasks and uses thread pools to prevent blocking the event loop.

### When to Use BackgroundTasks vs Celery

**Use FastAPI BackgroundTasks for**:
- ✅ Simple, non-critical operations
- ✅ Tasks that complete quickly (< 2 seconds recommended, < 30 seconds acceptable)
- ✅ Tasks tied to the request lifecycle
- ✅ I/O-bound tasks (database operations, file processing, API calls)
- ✅ Fire-and-forget operations (logging, analytics, cache updates)

**Use Celery/RQ for**:
- ✅ CPU-intensive tasks (data processing, image manipulation, calculations)
- ✅ Long-running operations (> 2 seconds, especially > 30 seconds)
- ✅ Critical tasks requiring retry logic and persistence
- ✅ Tasks needing monitoring and status tracking
- ✅ Distributed processing across multiple workers
- ✅ Scheduled/periodic tasks (cron-like)
- ✅ Tasks that need priority queues

### Decision Matrix

| Requirement | BackgroundTasks | Celery |
|------------|----------------|--------|
| Task duration | < 2 seconds | Any |
| Criticality | Non-critical | Critical |
| Retry logic | Manual | Built-in |
| Monitoring | Basic (logging) | Flower |
| Persistence | No | Yes |
| Distributed | No | Yes |
| Setup complexity | None | Medium |
| Worker management | With Gunicorn | Separate |

### Usage

```python
from app.utils.background_tasks import add_background_task_safe, add_background_task_with_retry

# For non-critical tasks (errors are logged but don't crash)
add_background_task_safe(
    background_tasks,
    process_data,
    data,
    track_status=True,
    cpu_bound=False,  # Auto-detected if not specified
)

# For tasks requiring retry logic
add_background_task_with_retry(
    background_tasks,
    process_data,
    data,
    max_retries=3,
    retry_delay=1.0,
    track_status=True,
)
```

### CPU-Bound Task Detection

The system automatically detects CPU-bound tasks based on:
- Function name patterns (process, compute, calculate, etc.)
- Whether the function is async or sync
- Explicit `cpu_bound` parameter

CPU-bound tasks are automatically executed in a thread pool to prevent blocking the event loop.

### Task Monitoring

Task execution is automatically monitored with:
- Duration tracking
- Success/failure rates
- Error context and types
- Statistics per function

Get task statistics:
```python
from app.utils.background_tasks import get_task_statistics

stats = await get_task_statistics()
# Returns: {
#   "total_tasks": 100,
#   "active_tasks": 5,
#   "completed_tasks": 90,
#   "failed_tasks": 5,
#   "avg_duration_seconds": 0.5,
#   "by_function": {...}
# }
```

### Graceful Shutdown

Background tasks are automatically waited for during application shutdown (configurable timeout via `BACKGROUND_TASK_TIMEOUT`).

### Configuration

```env
MAX_CONCURRENT_BACKGROUND_TASKS=10  # Maximum concurrent tasks
BACKGROUND_TASK_TIMEOUT=30.0  # Shutdown timeout in seconds
```

## Pagination

### Overview

Pagination is essential for managing large result sets efficiently. The backend implements best practices for pagination with reasonable defaults and maximum limits.

### Configuration

```env
DEFAULT_PAGE_SIZE=100  # Default items per page (was None = unlimited)
MAX_PAGE_SIZE=1000  # Maximum allowed page size to prevent abuse
```

### Best Practices

**Default Page Size:**
- Changed from `None` (unlimited) to `100` items per page
- Prevents accidental unbounded queries
- Improves performance and reduces memory usage
- Clients can still request larger pages up to `MAX_PAGE_SIZE`

**Maximum Page Size:**
- Set to `1000` items to prevent abuse and memory exhaustion
- Enforced at the API level
- Prevents single requests from consuming excessive resources

**Rules of Thumb:**
- Use reasonable default limits (50-100 records per page)
- Allow clients to specify limits within reasonable bounds
- Always validate and enforce maximum limits
- For very large datasets, use streaming endpoints instead

### Usage

```python
# Endpoints automatically use DEFAULT_PAGE_SIZE if limit is not specified
GET /api/v1/contacts/?limit=50  # Uses 50 items
GET /api/v1/contacts/  # Uses DEFAULT_PAGE_SIZE (100)

# Maximum limit is enforced
GET /api/v1/contacts/?limit=5000  # Capped at MAX_PAGE_SIZE (1000)
```

### Migration Notes

**Breaking Change**: `DEFAULT_PAGE_SIZE` changed from `None` to `100`
- Clients expecting unlimited results by default will now receive 100 items
- Clients must explicitly request larger limits if needed
- Use streaming endpoints for very large datasets

## Performance Tuning

### Connection Pool Sizing

**Formula**: `pool_size = (expected_concurrent_users * avg_query_time) / target_response_time`

Example:
- 100 concurrent users
- Average query time: 100ms
- Target response time: 500ms
- Pool size: (100 * 0.1) / 0.5 = 20 connections

**Recommendations**:
- Start with pool_size=25, max_overflow=50
- Monitor pool usage and adjust based on metrics
- Increase if you see frequent "pool exhausted" warnings

### Streaming Chunk Size

**Trade-offs**:
- **Larger chunks** (2-4MB): Fewer requests, higher memory usage
- **Smaller chunks** (256KB-512KB): More requests, lower memory usage
- **Default** (1MB): Good balance for most use cases

**Streaming Batch Size** (`STREAMING_BATCH_SIZE`):
- Controls database query batch size for streaming
- Default: 1000 rows per batch
- Larger batches: Fewer queries, more memory per batch
- Smaller batches: More queries, less memory per batch

### Query Cache TTL and Maxsize

**TTL Recommendations**:
- **Frequently accessed, rarely changing**: 3600s (1 hour)
- **Moderate access, occasional changes**: 300s (5 minutes)
- **High change rate**: 60s (1 minute) or disable caching

**Maxsize Recommendations**:
- **Small datasets** (<100k records): 1000-5000 entries
- **Medium datasets** (100k-1M records): 5000-10000 entries
- **Large datasets** (>1M records): 10000+ entries or use Redis
- **Memory constraint**: Monitor memory usage and adjust accordingly

**Cachetools Benefits**:
- Automatic TTL expiration (no manual cleanup needed)
- LRU eviction when maxsize is reached
- Thread-safe operations
- Efficient memory management

### Background Task Concurrency

**Recommendations**:
- **I/O-bound tasks**: Set `MAX_CONCURRENT_BACKGROUND_TASKS` to 10-20
- **CPU-bound tasks**: Set to 2-4x CPU cores (tasks use thread pool)
- **Mixed workload**: Start with 10, monitor and adjust

**Shutdown Timeout**:
- `BACKGROUND_TASK_TIMEOUT`: Time to wait for tasks during shutdown
- Default: 30 seconds
- Increase if you have long-running background tasks

### Parallel Processing Workers

**I/O-Bound Tasks**:
- Workers = 2-4x CPU cores (database/API calls are I/O-bound)
- Default: 4 workers

**CPU-Intensive Tasks**:
- Workers = CPU cores (limited by GIL in threads, but processes bypass GIL)
- Default: 4 workers, max: 8

## Best Practices

### When to Use Streaming

✅ **Use streaming for**:
- Exports of 10,000+ records
- Bulk data downloads
- Real-time data feeds
- Large file generation

❌ **Don't use streaming for**:
- Small datasets (< 1000 records)
- Real-time interactive queries
- When pagination is sufficient

### When to Use Caching

✅ **Cache**:
- Frequently accessed queries
- Expensive aggregations
- Static or slowly-changing data
- Queries with predictable parameters

❌ **Don't cache**:
- User-specific queries with high variability
- Real-time data
- Queries that change frequently
- Queries with many unique parameter combinations

### When to Use BackgroundTasks vs Celery

✅ **Use BackgroundTasks**:
- Email sending after user registration
- Logging analytics events
- Cache warming
- Non-critical data processing (< 2 seconds)

✅ **Use Celery**:
- Large file imports/exports
- Image processing
- Data transformations
- Scheduled reports
- Critical operations requiring retry guarantees

### When to Use Parallel Processing

✅ **Use parallel processing for**:
- Multiple independent database queries
- Batch API calls
- CPU-intensive data transformations
- Processing large datasets in chunks

❌ **Don't use parallel processing for**:
- Sequential operations with dependencies
- Small datasets (< 100 items)
- Operations that are already fast (< 10ms)

## Monitoring

### Connection Pool Metrics

Monitor these metrics via `/health/db` endpoint or logs:
- Pool utilization (checked_out / pool_size)
- Overflow usage
- Connection invalidation rate
- Average and maximum wait times
- Health status (healthy/degraded/critical)

**Health Status**:
- **Healthy**: Usage < 80%, no overflow, avg wait < 100ms
- **Degraded**: Usage 80-95%, some overflow, or wait > 100ms
- **Critical**: Usage > 95% or significant wait times

### Query Performance

- Slow query threshold: 1.0 seconds (configurable)
- Query monitoring logs slow queries automatically
- Use database query logs for detailed analysis

### Cache Performance

Monitor cache hit/miss ratios (Redis backend provides detailed stats):
- High hit ratio (>80%): Cache is effective
- Low hit ratio (<50%): Consider adjusting TTL or disabling cache

Get cache statistics:
```python
from app.utils.query_cache import get_query_cache

cache = get_query_cache()
stats = await cache.get_cache_stats()
# Returns backend-specific statistics
# Redis: includes keyspace_hits, keyspace_misses, total_commands_processed
# In-memory: includes total_entries, valid_entries, max_entries
```

### Background Task Performance

Monitor task execution:
- Average duration per function
- Success/failure rates
- Active task count
- Task queue depth

Access task statistics:
```python
from app.utils.background_tasks import get_task_statistics

stats = await get_task_statistics()
# Returns detailed statistics per function and overall metrics
```

Check application logs for structured task execution metrics with duration, error types, and CPU-bound detection.

## Troubleshooting

### High Memory Usage

1. **Check streaming chunk size**: Reduce `STREAMING_CHUNK_SIZE` if too large
2. **Verify chunked uploads**: Ensure files are uploaded in chunks, not loaded entirely
3. **Monitor connection pool**: Too many connections can increase memory usage
4. **Check query limits**: Ensure `MAX_STREAMING_RESULTS` is set appropriately

### Slow Queries

1. **Enable query monitoring**: Set `ENABLE_QUERY_MONITORING=true`
2. **Check database indexes**: Ensure frequently queried fields are indexed
3. **Use database-level aggregations**: Move Python processing to SQL
4. **Enable query caching**: Cache frequently accessed queries

### Connection Pool Exhausted

1. **Increase pool size**: Adjust `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`
2. **Optimize queries**: Reduce query execution time
3. **Check for connection leaks**: Monitor invalidated connections
4. **Reduce concurrent users**: If pool is consistently exhausted

## Examples

### Streaming Large Export

```python
# Client-side example
import httpx
import json

async def export_contacts():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            "http://127.0.0.1:8000/api/v1/contacts/stream/?format=jsonl",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            count = 0
            async for line in response.aiter_lines():
                contact = json.loads(line)
                # Process contact
                count += 1
            print(f"Exported {count} contacts")
```

### Parallel Batch Processing

```python
from app.utils.parallel_processing import process_batches

async def enrich_contacts_batch(contacts):
    results = await process_batches(
        items=contacts,
        processor=enrich_single_contact,
        batch_size=50,
        max_workers=4,
        executor_type="thread"  # I/O-bound (API calls)
    )
    return results
```

### Cached Query with Invalidation

```python
from app.utils.query_cache import get_query_cache

async def get_cached_contacts(filters, limit, offset):
    cache = get_query_cache()
    
    # Try cache first
    cached = await cache.get("contacts:list", filters=filters, limit=limit, offset=offset)
    if cached:
        return cached
    
    # Fetch from database
    result = await service.list_contacts(session, filters, limit=limit, offset=offset)
    
    # Cache result
    await cache.set("contacts:list", result.model_dump(), filters=filters, limit=limit, offset=offset)
    
    return result
```

## Additional Resources

- [FastAPI Streaming Response Documentation](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/current/)

