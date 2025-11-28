# Big Data Optimizations Guide

This document provides comprehensive information about the big data handling optimizations implemented in the Contact360 FastAPI backend.

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

The Contact360 backend is optimized to handle large datasets efficiently through:

- **Streaming Responses**: Send large datasets in chunks without loading everything into memory
- **Chunked File Uploads**: Process file uploads in configurable chunks
- **Query Caching**: In-memory caching with TTL support for frequently accessed queries
- **Parallel Processing**: Utilities for CPU-intensive and I/O-bound parallel tasks
- **Database-Level Aggregations**: Use PostgreSQL functions instead of Python-side processing
- **Connection Pool Optimization**: Tuned connection pooling with monitoring
- **Background Tasks**: FastAPI BackgroundTasks with status tracking, rate limiting, and graceful shutdown

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

In-memory query result caching reduces database load for frequently accessed queries. The cache uses a thread-safe dictionary with TTL (time-to-live) support and automatic cleanup of expired entries.

### Configuration

Enable caching in `.env`:
```env
ENABLE_QUERY_CACHING=true
QUERY_CACHE_TTL=300  # 5 minutes
```

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
from app.utils.query_cache import get_query_cache

cache = get_query_cache()

# Get cached result
result = await cache.get("contacts:list", filters={...}, limit=100, offset=0)

# Set cache
await cache.set("contacts:list", data, filters={...}, limit=100, offset=0)

# Invalidate cache
await cache.invalidate_pattern("query_cache:contacts:list:*")
```

## Parallel Processing

### Overview

Utilities for executing tasks in parallel, supporting both I/O-bound and CPU-intensive workloads.

### I/O-Bound Tasks (ThreadPoolExecutor)

Use for database queries, API calls, file I/O:

```python
from app.utils.parallel_processing import process_in_parallel

def fetch_user(user_id):
    return db.get_user(user_id)

results = await process_in_parallel(
    tasks=[
        lambda: fetch_user(1),
        lambda: fetch_user(2),
        lambda: fetch_user(3),
    ],
    max_workers=4,
    executor_type="thread"
)
```

### CPU-Intensive Tasks (ProcessPoolExecutor)

Use for data processing, calculations (bypasses Python's GIL):

```python
from app.utils.parallel_processing import process_cpu_intensive

def process_chunk(chunk):
    # CPU-intensive processing
    return processed_chunk

results = await process_cpu_intensive(
    tasks=[
        lambda: process_chunk(chunk1),
        lambda: process_chunk(chunk2),
    ],
    max_workers=4
)
```

### Batch Processing

Process large datasets in batches:

```python
from app.utils.parallel_processing import process_batches

results = await process_batches(
    items=contacts,
    processor=enrich_contact,
    batch_size=50,
    max_workers=4
)
```

### Context Manager

```python
from app.utils.parallel_processing import ParallelProcessor

async with ParallelProcessor(max_workers=4) as processor:
    results = await processor.process([
        lambda: task1(),
        lambda: task2(),
    ])
```

## Database Optimizations

### Connection Pooling

The connection pool is optimized for large datasets:

- **Pool Size**: 25 connections (configurable)
- **Max Overflow**: 50 additional connections
- **Pool Monitoring**: Automatic statistics tracking and warnings

### Pool Monitoring

Pool statistics are logged periodically:
- Connection checkouts/checkins
- Pool usage warnings (>80% utilization)
- Invalidated connections

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

# Connection Pool Monitoring
ENABLE_POOL_MONITORING=true
POOL_MONITORING_INTERVAL=60  # Log stats every 60 seconds
```

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

### Query Cache TTL

**Recommendations**:
- **Frequently accessed, rarely changing**: 3600s (1 hour)
- **Moderate access, occasional changes**: 300s (5 minutes)
- **High change rate**: 60s (1 minute) or disable caching

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

❌ **Don't cache**:
- User-specific queries with high variability
- Real-time data
- Queries that change frequently

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

Monitor these metrics:
- Pool utilization (checked_out / pool_size)
- Overflow usage
- Connection invalidation rate
- Average checkout time

### Query Performance

- Slow query threshold: 1.0 seconds (configurable)
- Query monitoring logs slow queries automatically
- Use database query logs for detailed analysis

### Cache Performance

Monitor cache hit/miss ratios:
- High hit ratio (>80%): Cache is effective
- Low hit ratio (<50%): Consider adjusting TTL or disabling cache

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

