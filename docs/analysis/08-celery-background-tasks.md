# Celery Background Tasks Analysis

## Overview

The application uses Celery for asynchronous background task processing, primarily for CSV import and export operations. This document analyzes the Celery configuration, task patterns, and implementation details.

## 1. Celery Configuration

### Application Setup (`app/tasks/celery_app.py`)

**Celery App:**
```python
celery_app = Celery(
    "contact360",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
```

**Configuration:**

**Serialization:**

- Task serializer: JSON
- Accept content: JSON only
- Result serializer: JSON

**Timezone:**

- UTC timezone
- Enable UTC: True

**Worker Configuration:**

- `worker_max_tasks_per_child`: 1000 (restart worker after 1000 tasks)
- `worker_prefetch_multiplier`: 4 (prefetch 4 tasks per worker)
- `worker_max_memory_per_child`: 200MB (restart if memory exceeds)

**Task Execution:**

- `task_track_started`: True (track when task starts)
- `task_acks_late`: True (acknowledge after completion)
- `task_reject_on_worker_lost`: True (reject if worker dies)

**Concurrency:**

- `worker_concurrency`: From settings (default 4)

**Result Backend:**

- `result_expires`: 3600 seconds (1 hour)
- `result_backend_transport_options`: Redis-specific options

**Task Routing:**

- `imports` queue: Priority 5
- `exports` queue: Priority 4
- `default` queue: Priority 3

**Task Time Limits:**

- `task_time_limit`: 30 minutes (hard limit)
- `task_soft_time_limit`: 25 minutes (soft limit)

**Optimization:**

- `task_compression`: gzip (compress large messages)
- `result_compression`: gzip (compress large results)

**Broker Connection:**

- `broker_connection_retry_on_startup`: True
- `broker_connection_retry`: True
- `broker_connection_max_retries`: 10

**Result Caching:**

- `result_cache_max`: 10000 (cache up to 10k results)

**Auto-Discovery:**

- `autodiscover_tasks(["app.tasks"])`: Auto-discovers tasks

## 2. Task Queues

### Queue Organization

**Three Queues:**

**1. imports Queue:**

- Priority: 5 (highest)
- Tasks: Contact import processing
- Purpose: High-priority data ingestion

**2. exports Queue:**

- Priority: 4
- Tasks: CSV export generation
- Purpose: User-requested exports

**3. default Queue:**

- Priority: 3 (lowest)
- Tasks: Other background tasks
- Purpose: General background work

### Queue Routing

**Pattern:**
```python
task_routes = {
    "app.tasks.import_tasks.*": {"queue": "imports", "priority": 5},
    "app.tasks.export_tasks.*": {"queue": "exports", "priority": 4},
    "app.tasks.*": {"queue": "default", "priority": 3},
}
```

**Benefits:**

- Isolated queues for different workloads
- Priority-based processing
- Independent scaling

## 3. Import Tasks

### Contact Import Task

**Task:** `process_contacts_import`

**Purpose:**

- Process CSV file import asynchronously
- Create/update contacts from CSV rows
- Track progress and errors

**Flow:**

**1. Task Initialization:**

- Receives: `job_id`, `file_path`, `user_id`
- Creates database session
- Retrieves import job record

**2. Status Updates:**

- Sets status to "processing"
- Updates progress counters
- Commits status changes

**3. CSV Processing:**

- Opens CSV file
- Reads rows in batches
- Validates and normalizes data
- Creates/updates contacts
- Tracks errors

**4. Progress Tracking:**

- Increments `processed_rows`
- Updates `error_count`
- Commits progress periodically

**5. Completion:**

- Sets status to "completed" or "failed"
- Updates final counters
- Stores completion message
- Commits final status

**Error Handling:**

- Catches exceptions during processing
- Records error details
- Sets status to "failed"
- Stores error message

**Progress Updates:**

- Updates every N rows (configurable)
- Commits to database
- Allows real-time progress tracking

### Import Job Management

**Job Creation:**

- Created by API endpoint
- Initial status: "pending"
- Stored in `contact_import_jobs` table

**Job Tracking:**

- `total_rows`: Total rows in CSV
- `processed_rows`: Rows processed so far
- `error_count`: Number of errors
- `status`: Current job status

**Error Records:**

- Stored in `contact_import_errors` table
- Links to import job
- Stores row number, error message, payload

## 4. Export Tasks

### Contact Export Task

**Task:** `generate_contact_export`

**Purpose:**

- Generate CSV file from contact UUIDs
- Upload to S3 or save locally
- Update export record with file path

**Flow:**

**1. Task Initialization:**

- Receives: `export_id`, `contact_uuids`
- Creates database session
- Retrieves export record

**2. Status Updates:**

- Sets status to "processing"
- Commits status

**3. CSV Generation:**

- Fetches contacts with all relations
- Generates CSV in memory
- Writes to buffer

**4. File Storage:**

- Uploads to S3 (if configured)
- Or saves to local filesystem
- Returns file path/key

**5. Completion:**

- Updates export with file path
- Sets status to "completed"
- Commits final status

**Error Handling:**

- Catches exceptions
- Sets status to "failed"
- Stores error message

### Company Export Task

**Similar Pattern:**

- Same flow as contact export
- Generates CSV for companies
- Includes company metadata

## 5. Task Patterns

### Standard Task Pattern

**Structure:**
```python
@celery_app.task(
    name="app.tasks.import_tasks.process_contacts_import",
    bind=True,  # Access to task instance
    max_retries=3,  # Retry on failure
    default_retry_delay=60,  # Wait 60s between retries
)
def process_contacts_import(self, job_id: str, file_path: str, user_id: str):
    """Process contact import."""
    try:
        # Task logic
        pass
    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)
```

**Features:**

- `bind=True`: Access to task instance (for retry)
- `max_retries`: Maximum retry attempts
- `default_retry_delay`: Delay between retries
- Exception handling with retry

### Database Session Management

**Pattern:**
```python
async def task_function():
    async with AsyncSessionLocal() as session:
        try:
            # Task logic
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Features:**

- Manual session creation (not dependency injection)
- Explicit commit/rollback
- Proper cleanup

### Progress Tracking

**Pattern:**
```python
# Update progress periodically
if row_count % BATCH_SIZE == 0:
    await import_service.increment_progress(
        session, job_id,
        processed_rows=row_count,
        error_count=error_count
    )
    await session.commit()
```

**Features:**

- Periodic progress updates
- Commits to database
- Real-time progress tracking

## 6. Task Retry Logic

### Retry Configuration

**Settings:**

- `max_retries`: 3 (default)
- `default_retry_delay`: 60 seconds
- Exponential backoff (optional)

**Retry Conditions:**

- Database connection errors
- Temporary failures
- Timeout errors

**No Retry:**

- Validation errors
- Permanent failures
- User errors

### Retry Implementation

**Pattern:**
```python
try:
    # Task logic
except (DatabaseError, ConnectionError) as exc:
    # Retry on transient errors
    raise self.retry(exc=exc, countdown=60)
except Exception as exc:
    # Don't retry on other errors
    logger.exception("Task failed: %s", exc)
    raise
```

## 7. Task Monitoring

### Status Tracking

**Job Status:**

- `pending`: Task queued, not started
- `processing`: Task running
- `completed`: Task finished successfully
- `failed`: Task failed

### Progress Monitoring

**Metrics:**

- `processed_rows`: Rows processed
- `error_count`: Errors encountered
- `total_rows`: Total to process
- Percentage: `processed_rows / total_rows * 100`

### Error Tracking

**Error Records:**

- Row-level errors stored
- Error message and payload
- Links to import job
- Queryable for debugging

## 8. Task Dependencies

### Redis Dependency

**Required:**

- Redis server for broker
- Redis for result backend
- Connection string in settings

### Database Dependency

**Required:**

- PostgreSQL database
- Access to import/export tables
- Session management

### S3 Dependency (Optional)

**If Configured:**

- AWS credentials
- S3 bucket name
- Used for file storage

## 9. Task Execution Flow

### Import Task Flow

```
API Endpoint → Create Import Job → Queue Task
    ↓
Celery Worker → Process Task
    ↓
Read CSV → Validate → Create/Update Contacts
    ↓
Update Progress → Commit Periodically
    ↓
Complete → Update Status → Return Result
```

### Export Task Flow

```
API Endpoint → Create Export Record → Queue Task
    ↓
Celery Worker → Process Task
    ↓
Fetch Contacts → Generate CSV → Upload to S3/Local
    ↓
Update Export Record → Set Status → Return Result
```

## 10. Performance Considerations

### Batch Processing

**Import:**

- Processes rows in batches
- Commits periodically
- Reduces database load

**Export:**

- Fetches contacts in batches
- Generates CSV incrementally
- Reduces memory usage

### Memory Management

**Worker Limits:**

- `worker_max_memory_per_child`: 200MB
- Restarts worker if exceeded
- Prevents memory leaks

### Task Limits

**Time Limits:**

- Soft limit: 25 minutes
- Hard limit: 30 minutes
- Prevents runaway tasks

### Compression

**Message Compression:**

- Compresses large task messages
- Reduces broker load
- Faster task queuing

## 11. Error Handling

### Task-Level Errors

**Handling:**

- Catch exceptions
- Log errors
- Update job status
- Store error details

### Row-Level Errors

**Import Errors:**

- Record per-row errors
- Store error message
- Store row payload
- Continue processing

### Retry Strategy

**Transient Errors:**

- Retry with backoff
- Max 3 retries
- Log retry attempts

**Permanent Errors:**

- Don't retry
- Mark as failed
- Store error details

## 12. Task Results

### Result Storage

**Backend:**

- Redis result backend
- Stores task results
- TTL: 1 hour

### Result Access

**Pattern:**
```python
task_result = process_contacts_import.AsyncResult(task_id)
status = task_result.status
result = task_result.result
```

**Status Values:**

- `PENDING`: Task queued
- `STARTED`: Task running
- `SUCCESS`: Task completed
- `FAILURE`: Task failed
- `RETRY`: Task retrying

## Summary

The Celery background task system provides:

1. **Asynchronous Processing**: Non-blocking import/export operations
2. **Queue Management**: Priority-based task routing
3. **Progress Tracking**: Real-time progress updates
4. **Error Handling**: Comprehensive error tracking
5. **Retry Logic**: Automatic retry on transient failures
6. **Performance**: Batch processing, compression, memory limits
7. **Monitoring**: Status tracking, progress metrics

The system enables long-running operations (CSV imports/exports) without blocking API requests, with comprehensive progress tracking and error handling.

