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

## 2. ContactRepository - Conditional JOIN Optimization

### JOIN Detection Methods

**Purpose:** Determine which tables need to be joined based on filters and ordering.

#### `_needs_company_join(filters)`

**Checks for:**

- Company name filters
- Company location filters
- Employee count filters
- Revenue/funding filters
- Technology/keyword/industry filters
- Company address filters

**Returns:** `bool` - Whether Company table join is needed

#### `_needs_contact_metadata_join(filters)`

**Checks for:**

- Phone number filters (work, home, other)
- Location filters (city, state, country)
- LinkedIn/website/stage filters
- Social media URL filters

**Returns:** `bool` - Whether ContactMetadata join is needed

#### `_needs_company_metadata_join(filters)`

**Checks for:**

- Domain list filters
- Company metadata fields (phone, city, state, country)
- Latest funding filters
- Company LinkedIn URL

**Returns:** `bool` - Whether CompanyMetadata join is needed

#### `_needs_joins_for_ordering(ordering)`

**Purpose:** Determine joins needed for ORDER BY clause

**Checks ordering field:**

- Company fields → needs Company join
- CompanyMetadata fields → needs Company + CompanyMetadata joins
- ContactMetadata fields → needs ContactMetadata join

**Returns:** `tuple[bool, bool, bool]` - (needs_company, needs_contact_meta, needs_company_meta)

### Base Query Methods

#### `base_query_minimal()`

**Returns:** `SELECT * FROM contacts`

- No joins
- Fastest query
- Used when no filters require joins

#### `base_query_with_company()`

**Returns:** `SELECT * FROM contacts LEFT JOIN companies`

- Only Company join
- Used when company filters present but no metadata needed

#### `base_query_with_metadata()`

**Returns:** `SELECT * FROM contacts LEFT JOIN companies LEFT JOIN contacts_metadata LEFT JOIN companies_metadata`

- All joins
- Used when metadata filters present

### Query Building Strategy

**Conditional JOIN Selection:**

```python
# Determine joins needed
needs_company = self._needs_company_join(filters)
needs_contact_meta = self._needs_contact_metadata_join(filters)
needs_company_meta = self._needs_company_metadata_join(filters)

# Check ordering requirements
order_company, order_contact_meta, order_company_meta = self._needs_joins_for_ordering(filters.ordering)

# Combine requirements
needs_company = needs_company or order_company
needs_contact_meta = needs_contact_meta or order_contact_meta
needs_company_meta = needs_company_meta or order_company_meta

# Select appropriate base query
if needs_company_meta or needs_contact_meta:
    stmt, company, contact_meta, company_meta = self.base_query_with_metadata()
elif needs_company:
    stmt, company = self.base_query_with_company()
    contact_meta = None
    company_meta = None
else:
    stmt = self.base_query_minimal()
    company = None
    contact_meta = None
    company_meta = None
```

**Benefits:**

- Minimal queries when possible
- Only joins tables when needed
- Significant performance improvement
- Reduces query complexity

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

### EXISTS Subqueries (Fallback)

**When No Company Join:**

- Uses EXISTS subqueries for company filters
- Avoids JOIN overhead
- Less efficient than JOINs but works

**Method:** `_apply_filters_with_exists()`

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

- Conditional JOIN detection
- Minimal vs full queries
- Filter application order
- Metadata handling

**Key Differences:**

- Simpler (no contact metadata)
- Only Company and CompanyMetadata
- Fewer filter types

### Base Query Methods

- `base_query_minimal()`: Company only
- `base_query_with_metadata()`: Company + CompanyMetadata

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

### LEFT JOIN NULLs

**Pattern:**

- All joins are LEFT OUTER JOIN
- NULL values handled gracefully
- Filters check for NULL before applying

**Example:**

```python
if company_meta is not None:
    stmt = self._apply_multi_value_filter(stmt, company_meta.city, filters.city)
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

- Tuple of (Contact, Company, ContactMetadata, CompanyMetadata)
- Some values may be None if not joined
- Service layer handles None values

## 13. Performance Optimizations

### Conditional JOINs

**Impact:**

- Minimal queries: ~10x faster
- Reduced query complexity
- Better index usage

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

### 1. Conditional JOIN Pattern

- Detect required joins
- Select minimal base query
- Only join when necessary

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

1. **Sophisticated Optimization**: Conditional JOINs based on filters
2. **Complex Filter Logic**: Multi-phase filter application
3. **Performance Focus**: Minimal queries, batch processing, monitoring
4. **Flexible Querying**: Supports various filter types and combinations
5. **Maintainable Code**: Clear separation of concerns, well-documented

The conditional JOIN optimization is the most significant performance feature, allowing queries to be 10x faster when no joins are needed.

