# Key Patterns Documentation

## Overview

This document catalogs the key design patterns, optimization techniques, and architectural patterns used throughout the codebase.

## 1. UUID-Based Lookup Pattern (No JOINs)

### Pattern Description

**Purpose:** Optimize database queries by using EXISTS subqueries instead of JOINs, then batch fetching related entities by UUID.

**Implementation:**
```python
# Always use minimal query (no JOINs)
stmt = self.base_query_minimal()  # Only contacts table

# Determine which EXISTS subqueries are needed
needs_company = self._needs_company_exists_subquery(filters)
needs_contact_meta = self._needs_contact_metadata_exists_subquery(filters)
needs_company_meta = self._needs_company_metadata_exists_subquery(filters)

# Apply filters using EXISTS subqueries (no JOINs)
if needs_company:
    company_subq = select(1).select_from(Company).where(Company.uuid == Contact.company_id)
    # ... apply company filters ...
    stmt = stmt.where(exists(company_subq))

# Repository returns only Contact objects
# Service layer batch fetches related entities by UUIDs
```

**Benefits:**
- No JOIN overhead - queries are simpler and faster
- Better scalability - can optimize each query independently
- Reduced query complexity - easier to understand and maintain
- Reduced query complexity
- Better index usage
- Lower database load

**Use Cases:**
- Contact listing with optional filters
- Company listing with optional filters
- Apollo searches with varying filter complexity

## 2. Filter Application Pattern

### Three-Phase Filter Application

**Phase 1: Contact Filters**
```python
stmt = self._apply_contact_filters(stmt, filters, contact_meta)
# Filters: first_name, last_name, title, email, etc.
```

**Phase 2: Company Filters**
```python
stmt = self._apply_company_filters(stmt, filters, company, company_meta)
# Filters: company name, employees, revenue, industries, etc.
```

**Phase 3: Special Filters**
```python
stmt = self._apply_special_filters(stmt, filters, company, company_meta)
# Filters: domain, keywords with field control, search terms
```

**Benefits:**
- Clear separation of concerns
- Efficient filter application
- Maintainable code
- Easy to extend

## 3. Apollo Parameter Mapping Pattern

### Mapping Strategy

**Direct Mappings:**
```python
# Simple one-to-one
"page" → "page"
"personSeniorities[]" → "seniority"
```

**Combined Mappings:**
```python
# Multiple params → single filter
"sortByField" + "sortAscending" → "ordering"
```

**Complex Mappings:**
```python
# Parameter transformation
"organizationNumEmployeesRanges[]" → "employees_min", "employees_max"
```

**Special Handling:**
```python
# Title normalization
if includeSimilarTitles:
    "personTitles[]" → "jumble_title_words" (AND logic)
else:
    "personTitles[]" → "title" + "normalize_title_column" (normalized)
```

**Benefits:**
- Flexible mapping logic
- Handles Apollo-specific features
- Tracks unmapped parameters
- Clear conversion rules

## 4. Data Normalization Pattern

### Text Normalization

**Pattern:**
```python
def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    # Remove wrapping quotes
    # Handle placeholders
    return text or None
```

**Features:**
- Handles None values
- Removes quotes from CSV exports
- Handles placeholders
- Consistent text cleaning

### Sequence Normalization

**Pattern:**
```python
def _normalize_sequence(values: Optional[Iterable[Any]]) -> list[str]:
    if not values:
        return []
    cleaned = []
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            cleaned.append(normalized)
    return cleaned
```

**Features:**
- Handles None/empty
- Filters empty values
- Trims whitespace
- Returns clean list

## 5. Repository Pattern

### Generic Base Repository

**Pattern:**
```python
class AsyncRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get_by_uuid(self, session, uuid: str):
        # Generic UUID lookup
        pass
```

**Benefits:**
- Reusable base functionality
- Type-safe operations
- Consistent patterns
- Easy to extend

### Specialized Repositories

**Pattern:**
```python
class ContactRepository(AsyncRepository[Contact]):
    def __init__(self):
        super().__init__(Contact)
    
    async def list_contacts(self, session, filters, limit, offset):
        # Specialized query logic
        pass
```

**Features:**
- Extends base repository
- Adds domain-specific methods
- Conditional JOIN logic
- Filter application

## 6. Service Layer Pattern

### Service Structure

**Pattern:**
```python
class ContactsService:
    def __init__(self, repository: Optional[ContactRepository] = None):
        self.repository = repository or ContactRepository()
    
    async def list_contacts(self, session, filters, limit, offset):
        # Business logic
        rows = await self.repository.list_contacts(session, filters, limit, offset)
        # Data transformation
        results = [self._hydrate_contact(...) for ... in rows]
        # Response building
        return CursorPage(results=results, next=next_link, previous=prev_link)
```

**Features:**
- Dependency injection
- Business logic orchestration
- Data transformation
- Response building

## 7. Dependency Injection Pattern

### FastAPI Dependencies

**Pattern:**
```python
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    # Authentication logic
    return user

@router.get("/endpoint")
async def endpoint(current_user: User = Depends(get_current_user)):
    # Use authenticated user
    pass
```

**Benefits:**
- Reusable dependencies
- Automatic injection
- Testable code
- Clear dependencies

## 8. Error Handling Pattern

### Consistent Error Handling

**Pattern:**
```python
try:
    result = await service.operation(session, ...)
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except Exception as exc:
    logger.exception("Operation failed: %s", exc)
    raise HTTPException(status_code=500, detail="Operation failed") from exc
```

**Features:**
- Preserves HTTP exceptions
- Logs unexpected errors
- User-friendly messages
- Exception chaining

## 9. Pagination Pattern

### Cursor-Based Pagination

**Pattern:**
```python
# Encode cursor
cursor = encode_offset_cursor(offset + limit)

# Build link
next_link = build_cursor_link(request_url, cursor)

# Response
return CursorPage(
    next=next_link,
    previous=previous_link,
    results=results
)
```

**Benefits:**
- Opaque cursors
- URL-safe encoding
- Consistent pagination
- Easy to use

### Offset-Based Pagination

**Pattern:**
```python
# Build link
next_link = build_pagination_link(
    request_url,
    limit=limit,
    offset=offset + limit
)
```

**Features:**
- Simple offset/limit
- Preserves query parameters
- Easy to understand

## 10. Caching Pattern

### Query Result Caching

**Pattern:**
```python
# Check cache
cached = await cache.get("apollo_url_analysis", url=url)
if cached:
    return cached

# Compute result
result = compute_expensive_operation(url)

# Cache result
await cache.set("apollo_url_analysis", result, ttl=3600, url=url)
return result
```

**Features:**
- TTL-based expiration
- Consistent cache keys
- Graceful degradation
- Performance improvement

## 11. Batch Processing Pattern

### Query Batching

**Pattern:**
```python
if limit and limit > 10000:
    batcher = QueryBatcher(session, stmt, batch_size=5000)
    rows = await batcher.fetch_all()
else:
    result = await session.execute(stmt)
    rows = result.fetchall()
```

**Benefits:**
- Memory efficient
- Handles large result sets
- Prevents timeout
- Maintains performance

### Import Batching

**Pattern:**
```python
batch_processed = 0
for row in csv_reader:
    process_row(row)
    batch_processed += 1
    
    if batch_processed >= 200:
        await session.commit()
        await import_service.increment_progress(...)
        batch_processed = 0
```

**Features:**
- Periodic commits
- Progress tracking
- Error isolation
- Memory management

## 12. Logging Pattern

### Function Logging Decorator

**Pattern:**
```python
@log_function_call(
    logger=logger,
    log_arguments=True,
    log_result=True
)
async def my_function(arg1, arg2):
    # Automatically logged
    pass
```

**Features:**
- Entry/exit logging
- Argument logging
- Result logging
- Exception logging
- Async/sync support

## 13. Schema Validation Pattern

### Pydantic Validation

**Pattern:**
```python
class ContactFilterParams(BaseModel):
    first_name: Optional[str] = Field(description="First name filter")
    limit: Optional[int] = Field(ge=1, description="Page size")
    
    model_config = ConfigDict(extra="ignore")
```

**Features:**
- Type validation
- Field descriptions
- Constraint validation
- Automatic serialization

## 14. WebSocket Connection Management Pattern

### Connection Manager

**Pattern:**
```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user: User):
        await websocket.accept()
        self.active_connections[str(user.id)] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
```

**Features:**
- Per-user connection tracking
- Automatic cleanup
- Connection management
- Error handling

## 15. UUID Generation Pattern

### Deterministic UUIDs

**Pattern:**
```python
def _company_uuid(row: Dict[str, str]) -> str:
    key = f"{row.get('company','')}{row.get('company_linkedin_url','')}"
    return str(uuid5(NAMESPACE_URL, key))
```

**Benefits:**
- Consistent UUIDs across imports
- Deduplication
- Reproducible
- Namespace-based

## 16. Array Filter Pattern

### PostgreSQL Array Operations

**Pattern:**
```python
# OR logic
if filters.industries:
    stmt = stmt.where(
        or_(*[cast(company.industries, Text).ilike(f'%{ind}%') 
              for ind in industries])
    )

# AND logic
if filters.keywords_and:
    conditions = [cast(company.keywords, Text).ilike(f'%{kw}%') 
                  for kw in keywords]
    stmt = stmt.where(and_(*conditions))
```

**Features:**
- Uses PostgreSQL array types
- Efficient array operations
- Supports OR and AND logic
- GIN index usage

## 17. Domain Extraction Pattern

### URL Domain Extraction

**Pattern:**
```python
def extract_domain_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    # Remove www., port, etc.
    return domain.lower()
```

**Features:**
- Handles various URL formats
- Normalizes domains
- Case-insensitive
- NULL-safe

## 18. Title Normalization Pattern

### Three Modes

**1. Standard:**
```python
# Direct ILIKE matching
stmt = stmt.where(Contact.title.ilike(f'%{title}%'))
```

**2. Normalized:**
```python
# Sort words alphabetically
normalized = " ".join(sorted(title.lower().split()))
stmt = stmt.where(
    func.array_to_string(
        func.string_to_array(func.lower(Contact.title), ' '),
        ' '
    ).ilike(f'%{normalized}%')
)
```

**3. Jumble:**
```python
# Match individual words (AND logic)
words = title.lower().split()
conditions = [Contact.title.ilike(f'%{word}%') for word in words]
stmt = stmt.where(and_(*conditions))
```

## 19. Progress Tracking Pattern

### Background Task Progress

**Pattern:**
```python
processed = 0
for item in items:
    process_item(item)
    processed += 1
    
    if processed % BATCH_SIZE == 0:
        await update_progress(processed, total)
        await session.commit()
```

**Features:**
- Periodic updates
- Database commits
- Real-time tracking
- Error isolation

## 20. Response Building Pattern

### Paginated Response

**Pattern:**
```python
results = [transform(row) for row in rows]

next_link = None
if limit and len(results) == limit:
    next_link = build_pagination_link(request_url, limit, offset + limit)

previous_link = None
if offset > 0:
    previous_link = build_pagination_link(request_url, limit, offset - limit)

return CursorPage(
    next=next_link,
    previous=previous_link,
    results=results
)
```

**Features:**
- Conditional link generation
- Preserves query parameters
- Clear pagination metadata
- Consistent format

## Summary

These patterns demonstrate:

1. **Performance Focus**: Conditional JOINs, batching, caching
2. **Maintainability**: Clear patterns, separation of concerns
3. **Flexibility**: Multiple approaches for different use cases
4. **Consistency**: Reusable patterns across codebase
5. **Error Handling**: Graceful degradation, comprehensive logging

The patterns work together to create a robust, performant, and maintainable system.

