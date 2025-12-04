# Repository Layer Patterns Analysis

## Overview

The repository layer handles all database access using SQLAlchemy ORM. This document analyzes the conditional JOIN optimization patterns, filter application logic, query building, and pagination strategies.

## 1. Repository Base Class

### AsyncRepository Pattern

**Base Class (`app/repositories/base.py`):**

```python
class AsyncRepository(Generic[ModelType]):
    """Generic async repository for SQLAlchemy ORM models."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, session, id: int) -> Optional[ModelType]:
        """Retrieve by integer primary key."""
    
    async def get_by_uuid(self, session, uuid: str) -> Optional[ModelType]:
        """Retrieve by UUID column."""
```

**Features:**

- Generic type parameter for model type
- UUID-based lookups (common pattern)
- Async SQLAlchemy throughout
- Logging at entry/exit

## 2. ContactRepository - UUID-Based Lookups (No JOINs)

### EXISTS Subquery Detection Methods

**Purpose:** Determine which tables need EXISTS subqueries based on filters and ordering.

#### `_needs_company_exists_subquery(filters)`

**Checks for:**

- Company name filters
- Company location filters
- Employee count filters
- Revenue/funding filters
- Technology/keyword/industry filters
- Company address filters

**Returns:** `bool` - Whether Company table EXISTS subquery is needed

#### `_needs_contact_metadata_exists_subquery(filters)`

**Checks for:**

- Phone number filters (work, home, other)
- Location filters (city, state, country)
- LinkedIn/website/stage filters
- Social media URL filters

**Returns:** `bool` - Whether ContactMetadata EXISTS subquery is needed

#### `_needs_company_metadata_exists_subquery(filters)`

**Checks for:**

- Domain list filters
- Company metadata fields (phone, city, state, country)
- Latest funding filters
- Company LinkedIn URL

**Returns:** `bool` - Whether CompanyMetadata EXISTS subquery is needed

#### Ordering by Related Tables

**Purpose:** Use scalar subqueries for ordering by related table columns (no JOINs)

**Pattern:**

- Company fields → scalar subquery: `ORDER BY (SELECT name FROM companies WHERE uuid = contacts.company_id)`
- CompanyMetadata fields → scalar subquery through Company
- ContactMetadata fields → scalar subquery: `ORDER BY (SELECT city FROM contacts_metadata WHERE uuid = contacts.uuid)`

**Returns:** Scalar subquery expression for ORDER BY clause

### Base Query Methods

#### `base_query_minimal()`

**Returns:** `SELECT * FROM contacts`

- No JOINs - queries only contacts table
- Fastest query
- Always used as base query

### Query Building Strategy

**UUID-Based Lookup Pattern (No JOINs):**

```python
# Always start with minimal query (no JOINs)
stmt = self.base_query_minimal()

# Determine which EXISTS subqueries are needed
needs_company = self._needs_company_exists_subquery(filters)
needs_contact_meta = self._needs_contact_metadata_exists_subquery(filters)
needs_company_meta = self._needs_company_metadata_exists_subquery(filters)

# Apply filters using EXISTS subqueries (no JOINs)
if needs_company:
    company_subq = select(1).select_from(Company).where(Company.uuid == Contact.company_id)
    # ... apply company filters to subquery ...
    stmt = stmt.where(exists(company_subq))

if needs_contact_meta:
    contact_meta_subq = select(1).select_from(ContactMetadata).where(ContactMetadata.uuid == Contact.uuid)
    # ... apply metadata filters to subquery ...
    stmt = stmt.where(exists(contact_meta_subq))

if needs_company_meta:
    company_meta_subq = select(1).select_from(CompanyMetadata).where(
        CompanyMetadata.uuid.in_(select(Company.uuid).where(Company.uuid == Contact.company_id))
    )
    # ... apply metadata filters to subquery ...
    stmt = stmt.where(exists(company_meta_subq))

# Repository returns only Contact objects
# Service layer batch fetches related entities by UUIDs
```

**Benefits:**

- No JOIN overhead - queries are simpler and faster
- Better scalability - can optimize each query independently
- Reduced query complexity - easier to understand and maintain
- Batch lookups prevent N+1 query problems
- UUID-based foreign key lookups are efficient with proper indexing

## 3. Filter Application Order

### Filter Application Strategy

**Three-Phase Approach:**

#### Phase 1: Contact Filters

**Method:** `_apply_contact_filters()`
**Filters Applied:**

- Contact table fields (name, email, title, seniority, etc.)
- ContactMetadata fields (if joined)
- Exclusion filters for contact fields

**Key Features:**

- Handles title normalization/jumble logic
- Applies array filters for departments
- Handles date range filters

#### Phase 2: Company Filters

**Method:** `_apply_company_filters()`
**Filters Applied:**

- Company table fields (name, employees, revenue, etc.)
- CompanyMetadata fields (if joined)
- Array filters (technologies, keywords, industries)
- Exclusion filters for company fields

**Key Features:**

- Numeric range filters
- Array text filters (OR logic)
- Array text exclusion

#### Phase 3: Special Filters

**Method:** `_apply_special_filters()`
**Filters Applied:**

- Domain list filters (requires CompanyMetadata)
- Keyword filters with field control
- Search terms (multi-column)

**Key Features:**

- Domain extraction from URLs
- Field-specific keyword search
- Multi-column search

### Filter Application Methods

#### `_apply_multi_value_filter()`

**Purpose:** Apply ILIKE filter with OR logic for multiple values

**Logic:**

- Splits comma-separated values
- Creates OR conditions: `column ILIKE '%value1%' OR column ILIKE '%value2%'`
- Uses trigram optimization if available

#### `_apply_multi_value_exclusion()`

**Purpose:** Exclude rows matching any of the provided values

**Logic:**

- Splits comma-separated values
- Creates NOT conditions: `NOT (column ILIKE '%value1%' OR column ILIKE '%value2%')`
- Handles NULL values gracefully

#### `_apply_array_text_filter()`

**Purpose:** Filter on PostgreSQL array columns

**Logic:**

- Uses `ANY()` operator for OR logic
- Converts array to text for ILIKE matching
- Handles NULL arrays

#### `_apply_array_text_filter_and()`

**Purpose:** Filter on array columns with AND logic

**Logic:**

- All values must be present in array
- Uses multiple `ANY()` conditions with AND

#### `_apply_array_text_exclusion()`

**Purpose:** Exclude rows where array contains any of the values

**Logic:**

- Uses `NOT (ANY())` operator
- Handles NULL arrays

#### `_apply_domain_filter()`

**Purpose:** Filter by website domain

**Logic:**

- Extracts domain from URL using `extract_domain_from_url()`
- Compares extracted domain with filter values
- Case-insensitive matching

#### `_apply_keyword_search_with_fields()`

**Purpose:** Search keywords in specific fields

**Logic:**

- Allows specifying which fields to search
- Allows excluding fields from search
- Supports both OR and AND logic

#### `_apply_jumble_title_filter()`

**Purpose:** Match titles by individual words (AND logic)

**Logic:**

- Splits title into words
- Each word must match separately
- Used when `includeSimilarTitles=true` in Apollo

#### `_apply_normalized_title_filter()`

**Purpose:** Match titles with normalized word order

**Logic:**

- Normalizes database column (sorts words alphabetically)
- Compares with normalized filter values
- Used for Apollo title matching

## 4. Search Term Application

### `apply_search_terms()`

**Purpose:** Multi-column case-insensitive search

**Columns Searched:**

- Contact: first_name, last_name, email, title, seniority, text_search
- Company (if joined): name, address, industries, keywords
- CompanyMetadata (if joined): city, state, country, phone, website
- ContactMetadata (if joined): city, state, country, linkedin_url, twitter_url

**Logic:**

- Uses `apply_search()` utility
- Creates OR conditions across all columns
- ILIKE matching with wildcards

**Optimization:**

- Only includes columns from joined tables
- Avoids unnecessary column references

## 5. Ordering Application

### Ordering Map Building

**Dynamic Ordering Map:**

```python
ordering_map = {
    # Contact fields (always available)
    "created_at": Contact.created_at,
    "first_name": Contact.first_name,
    # ... other contact fields
}

# Add company fields if joined
if company_alias is not None:
    ordering_map.update({
        "employees": company_alias.employees_count,
        "company": company_alias.name,
        # ... other company fields
    })

# Add metadata fields if joined
if company_meta_alias is not None:
    ordering_map.update({...})

if contact_meta_alias is not None:
    ordering_map.update({...})
```

**Default Ordering:**

- If no ordering specified: `Contact.created_at DESC NULLS LAST, Contact.id DESC`
- Uses indexed field (created_at)
- No join required
- Deterministic for pagination

**Features:**

- Handles descending order (prefix with `-`)
- NULLS LAST for consistent ordering
- Fallback to `id DESC` for determinism

## 6. Pagination Implementation

### Offset-Based Pagination

**Standard Pattern:**

```python
stmt = stmt.offset(offset)
if limit is not None:
    stmt = stmt.limit(limit)
```

**Features:**

- Supports unlimited queries (limit=None)
- Offset for skipping rows
- Limit for result size

### Batch Query Execution

**For Large Result Sets:**

```python
if limit and limit > 10000:
    batcher = QueryBatcher(session, stmt, batch_size=5000)
    rows = await batcher.fetch_all()
else:
    result = await session.execute(stmt)
    rows = result.fetchall()
```

**Benefits:**

- Reduces memory usage
- Processes in chunks
- Prevents timeout for large queries

## 7. Query Optimization Techniques

### EXISTS Subqueries (Primary Pattern)

**Always Used Instead of JOINs:**

- Uses EXISTS subqueries for all related table filters
- Avoids JOIN overhead entirely
- More efficient than JOINs for filtering
- Used for all company, contact_metadata, and company_metadata filters

**Method:** `_apply_filters_with_exists()`

**Pattern:**
```sql
WHERE EXISTS (
    SELECT 1 FROM companies co 
    WHERE co.uuid = contacts.company_id 
    AND co.name ILIKE '%value%'
)
```

### Trigram Index Optimization

**For Title Column:**

- Uses trigram GIN index
- Faster than standard ILIKE
- Enabled via `use_trigram_optimization=True`

### Query Compilation Logging

**Debug Feature:**

```python
compiled = stmt.compile(compile_kwargs={"literal_binds": False})
logger.debug("SQL query: %s", str(compiled))
```

**Purpose:**

- Debug query generation
- Verify JOINs are correct
- Performance analysis

### Query Performance Monitoring

**Timing:**

```python
query_start_time = time.time()
# ... execute query ...
query_execution_time = time.time() - query_start_time
logger.info("Query executed: duration=%.3fs", query_execution_time)
```

**Slow Query Detection:**

- Logs EXPLAIN ANALYZE for queries > 1 second
- Helps identify performance issues
- Configurable threshold

## 8. Special Filter Handling

### Domain Filtering

**Logic:**

1. Extract domain from `CompanyMetadata.website`
2. Compare with filter domains
3. Case-insensitive matching

**Implementation:**

- Uses `extract_domain_from_url()` utility
- Handles various URL formats
- NULL-safe

### Keyword Field Control

**Features:**

- Specify which fields to search
- Exclude fields from search
- Supports OR and AND logic

**Fields:**

- Company: name, industries, keywords, technologies
- CompanyMetadata: city, state, country, website

### Title Normalization

**Three Modes:**

1. **Standard:** Direct ILIKE matching
2. **Normalized:** Sort words alphabetically before comparison
3. **Jumble:** Match individual words (AND logic)

**Use Cases:**

- Apollo `includeSimilarTitles=true` → Jumble
- Apollo normalized titles → Normalized
- Standard search → Standard

## 9. CompanyRepository Patterns

### Similar Structure

**Follows same patterns as ContactRepository:**

- EXISTS subquery detection (no JOINs)
- Always uses minimal query (Company only)
- Filter application using EXISTS subqueries
- Metadata handling via EXISTS subqueries

**Key Differences:**

- Simpler (no contact metadata)
- Only Company and CompanyMetadata
- Fewer filter types

### Base Query Methods

- `base_query_minimal()`: Company only (always used, no JOINs)

## 10. Array Column Handling

### PostgreSQL Array Types

**Columns:**

- `departments`: StringList (array of strings)
- `industries`: StringList
- `keywords`: StringList
- `technologies`: StringList

### Filtering Arrays

**OR Logic:**

```sql
WHERE 'value' = ANY(array_column)
-- Or for multiple values:
WHERE ('value1' = ANY(array_column) OR 'value2' = ANY(array_column))
```

**AND Logic:**

```sql
WHERE ('value1' = ANY(array_column) AND 'value2' = ANY(array_column))
```

**Exclusion:**

```sql
WHERE NOT ('value' = ANY(array_column))
```

### Text Conversion

**For Search:**

- Converts array to text: `array_to_string(array_column, ',')`
- Enables ILIKE matching on array contents
- Used in multi-column search

## 11. NULL Handling

### UUID-Based Lookup NULLs

**Pattern:**

- No JOINs - queries only main table
- Related entities fetched separately by UUID
- NULL values handled when batch fetching (entity may not exist)
- Filters use EXISTS subqueries which handle NULLs automatically

**Example:**

```python
# Filter using EXISTS subquery (handles NULL company_id automatically)
if filters.company:
    company_subq = select(1).select_from(Company).where(Company.uuid == Contact.company_id)
    company_subq = company_subq.where(Company.name.ilike(f'%{filters.company}%'))
    stmt = stmt.where(exists(company_subq))
```

### Exclusion with NULLs

**Pattern:**

```python
if filters.exclude_company_ids:
    exclusion_condition = ~Contact.company_id.in_(exclusion_values)
    stmt = stmt.where(or_(Contact.company_id.is_(None), exclusion_condition))
```

**Logic:** Include rows where company_id is NULL OR not in exclusion list

## 12. Query Execution Patterns

### Standard Execution

```python
result = await session.execute(stmt)
rows = result.fetchall()
```

### Batch Execution

```python
batcher = QueryBatcher(session, stmt, batch_size=5000)
rows = await batcher.fetch_all()
```

**Benefits:**

- Memory efficient
- Handles large result sets
- Prevents timeout

### Result Transformation

**Returns:**

- Repository returns only Contact objects (or Company objects for CompanyRepository)
- Service layer batch fetches related entities by UUIDs
- Reconstructs response objects with related data
- Handles missing related entities gracefully (None values)

## 13. Performance Optimizations

### UUID-Based Lookups (No JOINs)

**Impact:**

- No JOIN overhead: queries are simpler and faster
- Better scalability: can optimize each query independently
- Reduced query complexity: easier to understand and maintain
- Batch lookups prevent N+1 query problems
- UUID-based foreign key lookups are efficient with proper indexing

### Default Ordering

**Optimization:**

- Uses `created_at DESC` (indexed)
- No join required
- Fast and deterministic

### Batch Processing

**For Large Queries:**

- Processes in 5000-row batches
- Reduces memory usage
- Prevents connection timeout

### Query Caching

**Optional:**

- Redis-based caching
- TTL-based expiration
- Reduces database load

## 14. Key Patterns Summary

### 1. UUID-Based Lookup Pattern (No JOINs)

- Always query only main table (contacts or companies)
- Use EXISTS subqueries for related table filters
- Use scalar subqueries for ordering by related table columns
- Batch fetch related entities by UUIDs in service layer

### 2. Filter Application Order

- Contact filters first
- Company filters second
- Special filters last

### 3. NULL-Safe Filtering

- Check for None before applying
- Handle LEFT JOIN NULLs
- Graceful degradation

### 4. Array Column Handling

- Use PostgreSQL ANY() operator
- Support OR and AND logic
- Text conversion for search

### 5. Performance Monitoring

- Time query execution
- Log slow queries
- EXPLAIN ANALYZE for debugging

## Summary

The repository layer demonstrates:

1. **UUID-Based Lookups**: No JOINs - uses EXISTS subqueries for filtering and scalar subqueries for ordering
2. **Complex Filter Logic**: Multi-phase filter application using EXISTS subqueries
3. **Performance Focus**: No JOIN overhead, batch UUID lookups, monitoring
4. **Flexible Querying**: Supports various filter types and combinations
5. **Maintainable Code**: Clear separation of concerns, well-documented

The UUID-based lookup pattern is the most significant performance feature, eliminating JOIN overhead entirely and allowing queries to be simpler and faster.

