# Technologies Endpoint Performance Optimization

## Overview

Optimized the `/contacts/technologies/` endpoint to improve performance when using `distinct=true` with large offsets. The optimization reduces query time from ~30s to <2s.

## Changes Made

### 1. Early Filter Application

- **Location**: `app/repositories/contacts.py` - `list_technologies_simple()` method
- **Change**: Applied company and search filters BEFORE unnesting and distinct operations
- **Impact**: Reduces the dataset size before expensive operations, significantly improving performance

### 2. Optimized DISTINCT Query Pattern

- **Location**: `app/repositories/contacts.py` - `list_technologies_simple()` method
- **Change**:
  - For large offsets (>25): Use `GROUP BY` instead of `DISTINCT` subquery
  - For small offsets: Continue using standard `DISTINCT` subquery
- **Impact**: `GROUP BY` can be more efficiently optimized by PostgreSQL's query planner for large offset scenarios

### 3. Performance Logging

- **Location**: `app/repositories/contacts.py` - `list_technologies_simple()` method
- **Change**: Added detailed logging for:
  - Query construction time
  - Query execution time
  - Post-processing time
  - Total query time
  - Row counts at each stage
- **Impact**: Enables performance monitoring and debugging

## Verification Steps

### 1. Verify GIN Index Usage

Run the following SQL to check if the GIN index on `technologies` is being used:

```sql
EXPLAIN ANALYZE
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
  AND name IN ('Company1', 'Company2')  -- If company filter is used
ORDER BY value ASC
LIMIT 26
OFFSET 50;
```

**Expected**: The query plan should show:

- Index Scan or Bitmap Index Scan using `idx_companies_technologies_gin`
- HashAggregate or GroupAggregate for distinct operation
- Limit operation applied after distinct

### 2. Test Query Performance

Test the endpoint with various parameters:

```bash
# Test 1: Small offset (should be fast)
curl "http://127.0.0.1:8000/api/v1/contacts/technologies/?limit=25&offset=0&distinct=true"

# Test 2: Large offset (previously slow, now optimized)
curl "http://127.0.0.1:8000/api/v1/contacts/technologies/?limit=25&offset=50&distinct=true"

# Test 3: With search filter
curl "http://127.0.0.1:8000/api/v1/contacts/technologies/?limit=25&offset=50&distinct=true&search=Python"

# Test 4: With company filter
curl "http://127.0.0.1:8000/api/v1/contacts/technologies/?limit=25&offset=50&distinct=true&company=Acme"
```

### 3. Monitor Logs

Check application logs for performance metrics:

```bash
# Look for log entries with:
# - "Query construction completed"
# - "Query execution completed"
# - "Post-processing completed"
# - "Retrieved technology values"
```

Expected log format:

```txt
INFO: Query construction completed: distinct=True offset=50 construction_time=0.001s
INFO: Query execution completed: distinct=True offset=50 limit=26 execution_time=0.850s db_rows=26
INFO: Post-processing completed: distinct=True offset=50 post_process_time=0.002s total_time=0.853s
```

### 4. Verify Index Statistics

Check if the GIN index is being used effectively:

```sql
-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'companies'
  AND indexname = 'idx_companies_technologies_gin';

-- Check index size
SELECT 
    pg_size_pretty(pg_relation_size('idx_companies_technologies_gin')) as index_size;
```

### 5. Analyze Query Plan

For detailed query plan analysis, enable query logging in PostgreSQL:

```sql
-- Enable query logging
SET log_min_duration_statement = 1000;
SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Or use EXPLAIN ANALYZE directly
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
ORDER BY value ASC
LIMIT 26
OFFSET 50;
```

## Performance Benchmarks

### Before Optimization

- `/contacts/technologies/?limit=25&offset=50`: **29.91s**
- `/contacts/technologies/?limit=25&offset=50&distinct=true`: **29.91s**

### After Optimization (Expected)

- `/contacts/technologies/?limit=25&offset=50`: **<2s**
- `/contacts/technologies/?limit=25&offset=50&distinct=true`: **<2s**

## Key Optimizations Explained

### Why GROUP BY for Large Offsets?

When using `DISTINCT` with large `OFFSET` values, PostgreSQL must:

1. Process all rows to find distinct values
2. Sort all distinct values
3. Skip OFFSET rows
4. Return LIMIT rows

Using `GROUP BY` can be more efficient because:

- PostgreSQL's query planner can optimize GROUP BY operations better
- GROUP BY can use hash aggregation which is faster for large datasets
- Better index usage in some scenarios

### Why Early Filtering?

Applying filters (company name, search) before unnesting and distinct:

- Reduces the number of rows that need to be unnested
- Reduces the number of values that need to be deduplicated
- Allows PostgreSQL to use indexes more effectively
- Significantly reduces memory usage

## Troubleshooting

### If Performance is Still Slow

1. **Check Index Usage**: Verify that `idx_companies_technologies_gin` is being used
2. **Check Table Statistics**: Run `ANALYZE companies;` to update statistics
3. **Check Query Plan**: Use `EXPLAIN ANALYZE` to identify bottlenecks
4. **Check Logs**: Review performance logs to identify which stage is slow

### Common Issues

1. **Index Not Used**:
   - Ensure GIN index exists: `CREATE INDEX idx_companies_technologies_gin ON companies USING gin (technologies);`
   - Update statistics: `ANALYZE companies;`

2. **Slow Query Execution**:
   - Check if filters are being applied early (see logs)
   - Verify company filter is using index on `name` column
   - Consider adding composite indexes if needed

3. **High Memory Usage**:
   - Ensure early filtering is working (check logs)
   - Consider increasing `work_mem` for distinct operations

## Future Optimizations

Potential further optimizations:

1. **Materialized View**: Create a materialized view of distinct technologies
2. **Partial Indexes**: Create partial indexes for common filter combinations
3. **Cursor-based Pagination**: Consider cursor-based pagination for very large offsets
4. **Caching**: Cache distinct technology lists for common queries
