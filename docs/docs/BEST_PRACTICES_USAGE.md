# FastAPI Best Practices Usage Guide

This document provides practical examples and usage patterns for the FastAPI best practices implemented in the Appointment360 backend.

## Table of Contents

1. [Caching Strategies](#caching-strategies)
2. [Background Task Patterns](#background-task-patterns)
3. [Big Data Handling](#big-data-handling)
4. [Performance Optimization](#performance-optimization)
5. [Code Optimization Patterns](#code-optimization-patterns)

## Caching Strategies

### When to Use Each Caching Strategy

#### 1. functools.lru_cache for Immutable Data

**Use for:**
- Application settings and configuration
- ML model loading (once per process)
- Static reference data
- Read-only lookups that never change

**Example:**
```python
from functools import lru_cache
from app.utils.cache_helpers import get_app_config_cached

# Settings are cached automatically
@lru_cache(maxsize=1)
def get_application_settings():
    return load_settings_from_file()

# Use in endpoint
@app.get("/config")
async def get_config():
    settings = get_application_settings()  # Cached per process
    return settings
```

#### 2. cachetools.TTLCache for Time-Based Expiration

**Use for:**
- Data with acceptable staleness
- Frequently changing data with TTL needs
- Single-worker deployments

**Example:**
```python
from app.utils.query_cache import get_query_cache

cache = get_query_cache()

# Cache with TTL
@app.get("/popular-contacts")
async def get_popular_contacts():
    cached = await cache.get("popular_contacts", limit=100)
    if cached:
        return cached
    
    # Fetch from database
    contacts = await db.get_popular_contacts(limit=100)
    await cache.set("popular_contacts", contacts, ttl=300, limit=100)  # 5 min TTL
    return contacts
```

#### 3. Redis for Distributed Caching

**Use for:**
- Multi-worker deployments
- Shared mutable state
- Large cache sizes (>1GB)
- Cache persistence requirements

**Example:**
```python
# Configure in .env:
# ENABLE_REDIS_CACHE=True
# REDIS_URL=redis://localhost:6379/0

# Usage is the same as TTLCache - automatically uses Redis if configured
cache = get_query_cache()  # Uses Redis if ENABLE_REDIS_CACHE=True
```

#### 4. HTTP Cache Headers

**Use for:**
- Client-side caching
- Reducing server load for static/semi-static data
- API responses that don't change frequently

**Example:**
```python
from app.utils.http_cache import cache_response, create_cached_response
from fastapi import Request

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
        max_age=600,  # 10 minutes
        public=False,  # Private cache
    )
```

### Cache Invalidation Patterns

#### Event-Driven Invalidation

```python
from app.utils.query_cache import invalidate_with_event, get_query_cache

cache = get_query_cache()

@app.put("/users/{user_id}")
async def update_user(user_id: int, data: dict):
    # Update in database
    await db.update_user(user_id, data)
    
    # Invalidate cache with event
    await invalidate_with_event(
        cache,
        "user",
        reason="user_updated",
        metadata={"user_id": user_id},
        user_id=user_id
    )
    
    return {"status": "updated"}
```

#### Pattern-Based Invalidation

```python
# Invalidate all contact-related cache entries
await cache.invalidate_pattern("query_cache:contacts:*")
```

## Background Task Patterns

### Simple Background Task

```python
from fastapi import BackgroundTasks
from app.utils.background_tasks import add_background_task_safe

@app.post("/users")
async def create_user(user_data: dict, background_tasks: BackgroundTasks):
    user = await db.create_user(user_data)
    
    # Add background task (errors are logged but don't crash)
    add_background_task_safe(
        background_tasks,
        send_welcome_email,
        user.email,
        track_status=False
    )
    
    return user
```

### Background Task with Retry

```python
from app.utils.background_tasks import add_background_task_with_retry

@app.post("/data")
async def process_data(data: dict, background_tasks: BackgroundTasks):
    add_background_task_with_retry(
        background_tasks,
        process_data_chunk,
        data,
        max_retries=3,
        retry_delay=1.0,
        track_status=True
    )
    return {"status": "processing"}
```

### Task Chaining

```python
from app.utils.background_tasks import chain_background_tasks

@app.post("/register")
async def register_user(user_data: dict, background_tasks: BackgroundTasks):
    user = await db.create_user(user_data)
    
    # Chain tasks to execute sequentially
    chain_background_tasks(
        background_tasks,
        (send_welcome_email, (user.id,), {}),
        (update_analytics, (user.id,), {}),
        (log_event, ("user_registered",), {"user_id": user.id})
    )
    
    return user
```

### Background Task with Database Session

```python
from app.utils.background_tasks import background_task_with_db_session
from app.db.session import get_db

async def update_user_analytics(session: AsyncSession, user_id: int):
    # Use session from connection pool
    await session.execute(
        update(UserAnalytics)
        .where(UserAnalytics.user_id == user_id)
        .values(last_active=datetime.now())
    )
    await session.commit()

@app.post("/activity")
async def record_activity(
    activity_data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Task uses connection pool automatically
    background_tasks.add_task(
        background_task_with_db_session,
        update_user_analytics,
        current_user.id
    )
    return {"status": "recorded"}
```

## Big Data Handling

### Streaming Large Datasets

#### JSONL Streaming

```python
from app.utils.streaming_responses import stream_jsonl_async, get_content_type_for_format
from fastapi.responses import StreamingResponse

@app.get("/contacts/stream")
async def stream_contacts():
    async def generate_contacts():
        async for contact in db.stream_contacts():
            yield contact
    
    generator = stream_jsonl_async(generate_contacts(), chunk_size=1000)
    return StreamingResponse(
        generator,
        media_type=get_content_type_for_format("jsonl")
    )
```

#### CSV Streaming

```python
from app.utils.streaming_responses import stream_csv

@app.get("/contacts/export")
async def export_contacts_csv():
    def generate_contacts():
        for contact in db.get_all_contacts():
            yield {
                "id": contact.id,
                "name": contact.name,
                "email": contact.email
            }
    
    generator = stream_csv(
        generate_contacts(),
        headers=["id", "name", "email"],
        chunk_size=5000
    )
    return StreamingResponse(generator, media_type="text/csv")
```

### Efficient Pagination

#### Cursor-Based Pagination (Recommended for Deep Pagination)

```python
from app.utils.pagination import optimize_pagination_params
from app.utils.cursor import encode_offset_cursor

@app.get("/contacts")
async def list_contacts(
    offset: int = 0,
    limit: int = 100,
    cursor: Optional[str] = None
):
    # Optimize pagination parameters
    params = optimize_pagination_params(
        offset=offset,
        limit=limit,
        cursor=cursor
    )
    
    if params["use_cursor"]:
        # Use cursor-based pagination for better performance
        resolved_offset = params["offset"]
        # ... fetch with cursor
    else:
        # Use offset-based pagination
        resolved_offset = params["offset"]
        # ... fetch with offset
    
    # ... fetch and return results
```

### Efficient Serialization

#### Using Pydantic TypeAdapter

```python
from app.utils.serialization import serialize_with_type_adapter
from app.schemas.contacts import ContactListItem

@app.get("/contacts")
async def get_contacts():
    contacts = await db.get_contacts()
    
    # Efficient serialization for large collections
    json_bytes = serialize_with_type_adapter(
        contacts,
        model=ContactListItem,
        use_orjson=True
    )
    
    return Response(content=json_bytes, media_type="application/json")
```

#### Filtering Response Data

```python
from app.utils.serialization import filter_response_data

@app.get("/users")
async def get_users():
    users = await db.get_users()
    
    # Exclude sensitive fields
    filtered = filter_response_data(
        users,
        exclude_fields={"password", "api_key", "secret_token"}
    )
    
    return filtered
```

### Chunked File Uploads

```python
from app.utils.file_uploads import save_upload_file_chunked, validate_file_upload

@app.post("/upload")
async def upload_file(file: UploadFile):
    # Validate file
    validation = await validate_file_upload(
        file,
        allowed_types=["text/csv", "application/vnd.ms-excel"],
        max_size=10 * 1024 * 1024  # 10MB
    )
    
    if not validation["valid"]:
        raise HTTPException(400, detail=validation["errors"])
    
    # Save with chunked upload
    result = await save_upload_file_chunked(
        file,
        Path("/uploads/data.csv"),
        chunk_size=1024 * 1024,  # 1MB chunks
        max_size=10 * 1024 * 1024
    )
    
    return {"status": "uploaded", "size": result["total_bytes"]}
```

### Resumable Uploads

```python
from app.utils.file_uploads import ResumableUpload

@app.post("/upload/resumable")
async def start_resumable_upload(
    upload_id: str,
    total_size: int,
    file: UploadFile
):
    upload = ResumableUpload(
        upload_id=upload_id,
        destination=Path(f"/uploads/{upload_id}.csv"),
        total_size=total_size
    )
    
    # Check if resuming
    status = await upload.get_upload_status()
    if status["can_resume"]:
        result = await upload.resume_upload(file)
    else:
        result = await upload._continue_upload(file, 0)
    
    return result
```

### Parallel Processing

#### Async Parallel Processing (I/O-bound)

```python
from app.utils.parallel_processing import process_in_parallel_async

async def fetch_user_data(user_id: int):
    return await db.get_user(user_id)

@app.get("/users/batch")
async def get_users_batch(user_ids: list[int]):
    # Process in parallel (I/O-bound)
    users = await process_in_parallel_async(
        user_ids,
        fetch_user_data,
        max_concurrent=10
    )
    return users
```

#### Sync Parallel Processing (CPU-intensive)

```python
from app.utils.parallel_processing import process_in_parallel_sync

def process_data_chunk(chunk: list[dict]):
    # CPU-intensive processing
    return transform_data(chunk)

@app.post("/process")
async def process_large_dataset(data: list[dict]):
    chunks = [data[i:i+100] for i in range(0, len(data), 100)]
    
    # Process in parallel threads (CPU-bound)
    results = process_in_parallel_sync(
        chunks,
        process_data_chunk,
        max_workers=4
    )
    
    return {"processed": len(results)}
```

#### Batch Processing

```python
from app.utils.parallel_processing import process_batches_async

async def process_contact_batch(batch: list[Contact]):
    return await db.bulk_insert_contacts(batch)

@app.post("/import")
async def import_contacts(contacts: list[Contact]):
    # Process in batches asynchronously
    results = await process_batches_async(
        contacts,
        process_contact_batch,
        batch_size=100,
        max_concurrent_batches=5
    )
    
    return {"imported": sum(len(r) for r in results)}
```

## Query Optimization

### Select Only Needed Columns

```python
from app.utils.query_optimization import select_only_columns
from app.models.contacts import Contact

# Instead of: select(Contact)
query = select_only_columns(
    select(Contact),
    [Contact.id, Contact.name, Contact.email]
)
```

### Prevent N+1 Queries

```python
from app.utils.query_optimization import prevent_n_plus_one

# Eager load relationships
query = prevent_n_plus_one(
    select(Contact),
    relationships=["company", "activities"],
    strategy="selectin"
)
```

### Database-Level Aggregations

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

### Query Analysis

```python
from app.utils.query_optimization import analyze_query_performance

query = select(Contact).where(Contact.email.like("%@example.com"))
analysis = await analyze_query_performance(session, query)

if analysis["warnings"]:
    logger.warning("Query performance issues: %s", analysis["warnings"])
```

## Performance Optimization Checklist

- [ ] Use appropriate caching strategy (lru_cache, TTLCache, or Redis)
- [ ] Add HTTP cache headers for static/semi-static data
- [ ] Use streaming for datasets >10k rows
- [ ] Implement pagination with reasonable limits
- [ ] Use cursor-based pagination for deep pagination (>1000 offset)
- [ ] Select only needed columns in queries
- [ ] Prevent N+1 queries with eager loading
- [ ] Use database-level aggregations
- [ ] Use parallel processing for CPU-intensive tasks
- [ ] Use async parallel processing for I/O-bound tasks
- [ ] Implement chunked file uploads for large files
- [ ] Validate file uploads early
- [ ] Use Pydantic TypeAdapter for large collection serialization
- [ ] Filter response data to reduce payload size
- [ ] Monitor query performance and optimize slow queries

## Decision Guides

### Caching Strategy Decision Tree

```
Is data truly immutable?
├─ Yes → Use @lru_cache()
└─ No → Does it need TTL?
    ├─ Yes → Single worker?
    │   ├─ Yes → Use TTLCache
    │   └─ No → Use Redis
    └─ No → Multi-worker?
        ├─ Yes → Use Redis
        └─ No → Use TTLCache
```

### Background Task vs Celery Decision

```
Task duration > 2 seconds?
├─ Yes → Use Celery
└─ No → Is it critical?
    ├─ Yes → Use Celery
    └─ No → Needs retry/persistence?
        ├─ Yes → Use Celery
        └─ No → Use BackgroundTasks
```

### Pagination Strategy Decision

```
Offset > 1000?
├─ Yes → Use cursor-based pagination
└─ No → Use offset-based pagination
```

## Code Optimization Patterns

### Service Base Class Pattern

**Use BaseService for all services** to get common functionality:

```python
from app.services.base import BaseService
from app.repositories.contacts import ContactRepository

class ContactsService(BaseService[ContactRepository]):
    def __init__(self, repository: Optional[ContactRepository] = None):
        super().__init__(repository or ContactRepository())
    
    async def create_contact(self, session, payload):
        # ... create logic ...
        # Use inherited cache invalidation helper
        await self._invalidate_on_create("contacts")
        return detail
```

**Benefits**:
- Automatic logger initialization
- Common error handling helpers
- Cache invalidation helpers
- Replica detection utility

### Cache Invalidation Pattern

**Use cache_service utilities** instead of direct cache access:

```python
from app.utils.cache_service import invalidate_on_create, invalidate_on_update, invalidate_on_delete

# After create operation
await invalidate_on_create("contacts", self.logger)

# After update operation
await invalidate_on_update("contacts", self.logger)

# After delete operation
await invalidate_on_delete("contacts", self.logger)
```

**Benefits**:
- Consistent error handling
- Automatic cache pattern generation
- Reduced code duplication

### Pagination and Caching Pattern

**Use pagination_cache utilities** for list operations:

```python
from app.utils.pagination_cache import (
    get_cached_list_result,
    build_pagination_links,
    build_list_meta,
    cache_list_result,
)

async def list_contacts(self, session, filters, limit, offset, request_url, use_cursor):
    # Check cache
    cached = await get_cached_list_result("contacts", filters, limit, offset, use_cursor, self.logger)
    if cached:
        return CursorPage(**cached)
    
    # Execute query and hydrate results
    contacts = await self.repository.list_contacts(session, filters, limit, offset)
    results = [self._hydrate_contact(...) for ... in contacts]
    
    # Build pagination
    next_link, previous_link = build_pagination_links(
        request_url, limit, offset, len(results), use_cursor
    )
    meta = build_list_meta(filters, use_cursor, len(results), limit, self._is_using_replica())
    
    page = CursorPage(next=next_link, previous=previous_link, results=results, meta=meta)
    
    # Cache result
    await cache_list_result("contacts", page, filters, limit, offset, use_cursor, self.logger)
    return page
```

**Benefits**:
- Consistent pagination logic
- Automatic cache management
- Reduced code duplication

### EXISTS Subquery Detection Pattern

**Use ExistsSubqueryDetector** for conditional subquery logic:

```python
from app.utils.exists_subquery_detector import ContactFilterSubqueryDetector

# In repository
if ContactFilterSubqueryDetector.needs_company_subquery(filters):
    # Add Company EXISTS subquery
    stmt = stmt.where(exists(company_subquery))

if ContactFilterSubqueryDetector.needs_contact_metadata_subquery(filters):
    # Add ContactMetadata EXISTS subquery
    stmt = stmt.where(exists(contact_meta_subquery))
```

**Benefits**:
- Clearer, more maintainable logic
- Reduced code duplication
- Easier to extend

### Safe Attribute Access Pattern

**Use safe_getattr** when working with ORM objects or Row objects:

```python
from app.utils.hydration import safe_getattr

# Works with both ORM instances and Row objects
name = safe_getattr(contact, "first_name", "Unknown")
email = safe_getattr(contact, "email")
company_name = safe_getattr(company, "name") if company else None
```

**Benefits**:
- Handles both ORM instances and SQLAlchemy Row objects
- Eliminates complex attribute access logic
- Reduces code complexity

### Normalization Pattern

**Always use centralized normalization utilities**:

```python
from app.utils.normalization import (
    PLACEHOLDER_VALUE,
    normalize_text,
    normalize_sequence,
    coalesce_text,
)

# Normalize text fields
name = normalize_text(data.get("name"))
email = normalize_text(data.get("email"))

# Normalize sequences
industries = normalize_sequence(data.get("industries"))

# Coalesce multiple values
phone = coalesce_text(work_phone, home_phone, mobile_phone)
```

**Benefits**:
- Consistent normalization across codebase
- Single source of truth for normalization logic
- Easier to maintain and update

## References

- [Optimization Guide](OPTIMIZATION_GUIDE.md) - Detailed guide on all optimizations
- [Big Data Optimizations](BIG_DATA_OPTIMIZATIONS.md) - Performance optimizations for large datasets

