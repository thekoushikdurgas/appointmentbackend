# Utilities Analysis

## Overview

The utilities module provides shared helper functions used across the application. This document analyzes pagination, query batching, caching, monitoring, domain extraction, and other utility patterns.

## 1. Pagination Utilities

### Cursor-Based Pagination

**File:** `app/utils/pagination.py`

**Purpose:** Build pagination links for API responses

#### `build_cursor_link()`

**Purpose:** Build cursor-based pagination link

**Parameters:**
- `request_url`: Original request URL
- `cursor`: Cursor token (base64-encoded offset)

**Returns:** Full URL with cursor parameter

**Example:**
```python
next_link = build_cursor_link(
    "https://api.example.com/contacts/",
    "eyJvZmZzZXQiOjI1fQ=="
)
# Returns: "https://api.example.com/contacts/?cursor=eyJvZmZzZXQiOjI1fQ=="
```

#### `build_pagination_link()`

**Purpose:** Build offset-based pagination link

**Parameters:**
- `request_url`: Original request URL
- `limit`: Page size
- `offset`: Starting offset

**Returns:** Full URL with limit and offset parameters

**Example:**
```python
next_link = build_pagination_link(
    "https://api.example.com/contacts/",
    limit=25,
    offset=50
)
# Returns: "https://api.example.com/contacts/?limit=25&offset=50"
```

**Features:**
- Preserves existing query parameters
- Adds/updates pagination parameters
- Handles URL parsing and reconstruction

## 2. Cursor Encoding/Decoding

### Cursor Utilities

**File:** `app/utils/cursor.py`

**Purpose:** Encode/decode pagination cursors

#### `encode_offset_cursor()`

**Purpose:** Encode offset to cursor token

**Process:**
1. Create dict with offset
2. JSON serialize
3. Base64 encode
4. Return cursor string

**Example:**
```python
cursor = encode_offset_cursor(25)
# Returns: "eyJvZmZzZXQiOjI1fQ=="
```

#### `decode_offset_cursor()`

**Purpose:** Decode cursor token to offset

**Process:**
1. Base64 decode
2. JSON deserialize
3. Extract offset
4. Return offset integer

**Example:**
```python
offset = decode_offset_cursor("eyJvZmZzZXQiOjI1fQ==")
# Returns: 25
```

**Error Handling:**
- Returns None on decode failure
- Handles invalid cursor format
- Logs warnings for invalid cursors

## 3. Query Batching

### QueryBatcher

**File:** `app/utils/query_batch.py`

**Purpose:** Process large queries in batches to reduce memory usage

**Features:**
- Processes queries in configurable batch sizes
- Reduces memory footprint
- Prevents timeout for large result sets
- Streaming result processing

**Usage:**
```python
batcher = QueryBatcher(session, stmt, batch_size=5000)
rows = await batcher.fetch_all()
```

**Implementation:**
- Executes query with LIMIT/OFFSET
- Processes results in batches
- Combines all batches
- Returns complete result set

**Benefits:**
- Handles queries returning >10k rows
- Prevents memory exhaustion
- Maintains query performance

## 4. Query Caching

### Query Cache

**File:** `app/utils/query_cache.py`

**Purpose:** Redis-based query result caching

**Features:**
- TTL-based expiration
- Key generation from query parameters
- Optional caching (can be disabled)
- Redis backend

**Usage:**
```python
cache = get_query_cache()

# Get from cache
result = await cache.get("apollo_url_analysis", url=url)

# Set in cache
await cache.set(
    "apollo_url_analysis",
    data,
    ttl=3600,
    url=url
)
```

**Key Generation:**
- Combines cache name and parameters
- Creates consistent cache keys
- Handles parameter serialization

**Configuration:**
- Enabled via `ENABLE_QUERY_CACHING` setting
- TTL from `QUERY_CACHE_TTL` setting
- Redis connection from settings

## 5. Query Monitoring

### Query Monitor

**File:** `app/utils/query_monitor.py`

**Purpose:** Monitor query performance and log slow queries

**Features:**
- Tracks query execution time
- Logs slow queries (>1 second)
- EXPLAIN ANALYZE for slow queries
- Performance metrics

**Configuration:**
- Enabled via `ENABLE_QUERY_MONITORING` setting
- Threshold from `SLOW_QUERY_THRESHOLD` setting
- Logs to application logger

**Usage:**
- Automatically attached to SQLAlchemy engine
- Monitors all queries
- Logs slow queries with details

**Output:**
- Query execution time
- Slow query warnings
- EXPLAIN ANALYZE results
- Query parameters

## 6. Domain Extraction

### Domain Utilities

**File:** `app/utils/domain.py`

**Purpose:** Extract normalized domain from URLs

#### `extract_domain_from_url()`

**Features:**
- Handles various URL formats
- Removes protocol (http://, https://)
- Removes www. prefix
- Removes port numbers
- Returns lowercase domain

**Supported Formats:**
- `https://example.com` → `example.com`
- `http://www.example.com` → `example.com`
- `https://subdomain.example.com/path` → `subdomain.example.com`
- `example.com` → `example.com`

**Error Handling:**
- Returns None for invalid URLs
- Handles parsing exceptions
- Fallback extraction logic

**Usage:**
- Domain list filters
- Company website domain matching
- Case-insensitive comparison

## 7. Query Building Utilities

### Query Helpers

**File:** `app/utils/query.py`

**Purpose:** Common SQLAlchemy query building patterns

#### `apply_ilike_filter()`

**Purpose:** Apply case-insensitive ILIKE filter

**Features:**
- Handles None values
- Supports prefix matching
- Dialect-aware (PostgreSQL ILIKE)

#### `apply_exact_filter()`

**Purpose:** Apply exact match filter

**Features:**
- Equality comparison
- Handles None values
- Type-safe

#### `apply_numeric_range_filter()`

**Purpose:** Apply min/max range filter

**Features:**
- Handles None min/max
- Single-sided ranges
- Both-sided ranges

#### `apply_ordering()`

**Purpose:** Apply ORDER BY clause

**Features:**
- Descending order (prefix with `-`)
- Multiple sort fields
- Default ordering fallback
- NULLS LAST handling

#### `apply_search()`

**Purpose:** Multi-column case-insensitive search

**Features:**
- Searches across multiple columns
- OR logic (match any column)
- ILIKE matching
- Handles None values

## 8. Industry Mapping

### Industry Tag ID Conversion

**File:** `app/utils/industry_mapping.py`

**Purpose:** Convert Apollo industry Tag IDs to industry names

**Features:**
- CSV-based mapping
- Module-level caching
- Batch conversion
- Invalid ID handling

**Mapping File:**
- ~~`app/data/insdustryids.csv`~~ (REMOVED: File was unused and not referenced in codebase)
- Industry mapping is handled programmatically

**Usage:**
```python
industry_names = get_industry_names_from_ids(["12345", "67890"])
# Returns: ["software", "technology"]
```

**Caching:**
- Loads mapping once
- Caches at module level
- Fast lookups

## 9. Apollo Pattern Detection

### ApolloPatternDetector

**File:** `app/utils/apollo_patterns.py`

**Purpose:** Detect common Apollo filter patterns

**Features:**
- Pattern recognition
- Usage statistics
- Optimization hints
- Pattern information

**Common Patterns:**
- High frequency location (85% usage)
- High frequency employees (82% usage)
- High frequency titles (77% usage)
- Combined patterns

**Usage:**
- Logging and monitoring
- Query optimization hints
- Pattern tracking

## 10. S3 Service

### S3 Utilities

**File:** `app/services/s3_service.py`

**Purpose:** AWS S3 file storage operations

**Features:**
- File upload/download
- Presigned URL generation
- Public URL generation
- S3 key detection

**Operations:**
- `upload_file()`: Upload file to S3
- `download_file()`: Download from S3
- `get_presigned_url()`: Generate presigned URL
- `get_public_url()`: Generate public URL
- `is_s3_key()`: Check if string is S3 key

**Configuration:**
- AWS credentials from settings
- S3 bucket name from settings
- Region from settings
- Presigned URL expiration

## 11. Signed URL Generation

### Signed URLs

**File:** `app/utils/signed_url.py`

**Purpose:** Generate signed URLs for file downloads

**Features:**
- Time-limited URLs
- Secure access
- S3 presigned URLs
- Local file URLs

**Usage:**
- Export file downloads
- Avatar image access
- Secure file sharing

## 12. Common Patterns

### Text Normalization

**Pattern:**
- Strip whitespace
- Handle None values
- Remove quotes
- Handle placeholders

**Usage:**
- Contact/company data cleaning
- CSV import processing
- Filter value normalization

### Array Handling

**Pattern:**
- Parse comma-separated strings
- Handle None/empty values
- Trim whitespace
- Remove empty items

**Usage:**
- Industries, keywords, technologies
- Multi-value filters
- CSV array columns

### UUID Generation

**Pattern:**
- Deterministic UUIDs (uuid5)
- Based on key fields
- Consistent across imports
- Namespace-based

**Usage:**
- Contact/company UUIDs
- Import deduplication
- Consistent identification

## 13. Error Handling Utilities

### Exception Handling

**Patterns:**
- Try/except with logging
- Graceful degradation
- Error message extraction
- User-friendly errors

**Usage:**
- Service layer error handling
- Repository error handling
- API error responses

## 14. Logging Utilities

### Function Logging Decorator

**File:** `app/core/logging.py`

**Purpose:** Automatic function call logging

**Features:**
- Entry/exit logging
- Argument logging (optional)
- Result logging (optional)
- Exception logging
- Async/sync support

**Usage:**
```python
@log_function_call(logger=logger, log_arguments=True)
async def my_function(arg1, arg2):
    # Function automatically logged
    pass
```

## 15. Performance Utilities

### Query Optimization

**Techniques:**
- Conditional JOINs
- Batch processing
- Query caching
- Index usage
- Connection pooling

### Memory Management

**Techniques:**
- Batch processing
- Streaming results
- Query batching
- Memory limits

## Summary

The utilities module provides:

1. **Pagination**: Cursor and offset-based pagination
2. **Query Optimization**: Batching, caching, monitoring
3. **Data Processing**: Normalization, extraction, conversion
4. **Error Handling**: Consistent error patterns
5. **Logging**: Automatic function logging
6. **Storage**: S3 integration utilities
7. **Performance**: Query optimization helpers

These utilities enable consistent patterns across the codebase and provide reusable functionality for common operations.

