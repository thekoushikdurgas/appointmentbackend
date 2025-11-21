# Technologies Query Performance Analysis

## Problem Summary

After implementing optimizations, queries are still taking **~3.7-4.4 seconds** instead of the target **<2 seconds**. Analysis of query plans reveals the root cause.

## Root Cause Analysis

### Query Plan Observations

From `result_02_10_08_20_11_25.txt`:

1. **Parallel Seq Scan**: PostgreSQL is scanning ALL companies (1.6M+ rows) sequentially
   ```
   ->  Parallel Seq Scan on public.companies (cost=0.00..530709.26 rows=687472 width=189)
         Filter: ((companies.technologies IS NOT NULL) AND (array_length(companies.technologies, 1) > 0))
   ```

2. **Massive Unnest Operation**: Unnesting 16M+ technology values before distinct
   ```
   ->  ProjectSet (cost=0.00..570238.90 rows=6874720 width=32)
         Output: unnest(technologies)
         actual rows=16488669 loops=3
   ```

3. **HashAggregate on 16M+ rows**: Processing all unnested values before pagination
   ```
   ->  HashAggregate (cost=1100881.35..1207848.66 rows=1038160 width=32)
         Group Key: unnest(companies.technologies)
         actual rows=1875 loops=3
   ```

4. **GIN Index Not Used**: The `idx_companies_technologies_gin` index cannot help with unnest operations
   - GIN indexes on arrays are for containment queries (`WHERE technologies @> ARRAY['Python']`)
   - They cannot be used for `unnest()` operations

### Why Current Optimizations Don't Help Enough

The fundamental issue is that `SELECT DISTINCT unnest(technologies)` **requires**:
1. Scanning all companies with technologies
2. Unnesting all technologies from all companies
3. Finding all distinct values (processing 16M+ rows)
4. Sorting all distinct values
5. Applying OFFSET/LIMIT

**No amount of query optimization can avoid steps 1-4** when you need all distinct technologies across all companies.

### Performance Breakdown

- **Query #4 (offset=50, distinct=true)**: 4.4265s
  - Parallel Seq Scan: ~600ms
  - ProjectSet (unnest): ~1700ms  
  - HashAggregate (distinct): ~3700ms
  - Sort + Limit: ~4ms

- **Query #7 (with search filter)**: 28.6762s
  - Sequential scan with subplan: Very slow because it checks each company's technologies individually

- **Query #8 (with company filter)**: 0.6560s ✅
  - Index Scan on name: Fast because it only processes a few companies

## Solutions

### Solution 1: Materialized View (Recommended for Production)

**Performance**: <0.1s for pagination queries

**Implementation**: See `sql/optimizations/technologies_materialized_view.sql`

**Pros**:
- Dramatically faster pagination (<0.1s vs 4.4s)
- Simple index-based queries
- Works with search filters efficiently

**Cons**:
- Requires periodic refresh (can be automated)
- Slight delay in seeing new technologies
- Additional storage (~few MB)

**Usage**:
```sql
-- Fast pagination query
SELECT value FROM mv_distinct_technologies 
ORDER BY value ASC 
LIMIT 25 OFFSET 50;

-- With search
SELECT value FROM mv_distinct_technologies 
WHERE value ILIKE '%Python%' 
ORDER BY value ASC 
LIMIT 25 OFFSET 50;
```

**Refresh Strategy**:
- Manual: `REFRESH MATERIALIZED VIEW mv_distinct_technologies;`
- Concurrent (no lock): `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;`
- Scheduled: Set up cron/pg_cron to refresh every 6 hours

### Solution 2: Accept Current Performance (If Acceptable)

**Performance**: ~3.7-4.4s

If 4 seconds is acceptable for your use case:
- Current optimizations are working as well as possible
- The query is doing the minimum work required
- Further improvements require schema changes

### Solution 3: Cursor-Based Pagination (Alternative)

Instead of OFFSET, use WHERE clauses:
```sql
-- First page
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
ORDER BY value ASC
LIMIT 25;

-- Next page (using last value from previous page)
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
  AND unnest(technologies) > 'last_value_from_previous_page'
ORDER BY value ASC
LIMIT 25;
```

**Pros**: Can be faster for large offsets
**Cons**: Requires API changes, more complex pagination logic

### Solution 4: Denormalized Table

Create a separate `company_technologies` table:
```sql
CREATE TABLE company_technologies AS
SELECT company_id, unnest(technologies) as technology
FROM companies
WHERE technologies IS NOT NULL;

CREATE INDEX idx_company_technologies_tech ON company_technologies(technology);
```

**Pros**: Fast queries, can filter by company easily
**Cons**: Requires maintaining denormalized data, more storage

## Recommended Approach

### Immediate (No Schema Changes)

1. **For queries with company filters**: Already fast (0.6s) ✅
2. **For unfiltered queries**: Accept ~4s or implement materialized view

### Long-term (Best Performance)

1. **Implement Materialized View**: See `sql/optimizations/technologies_materialized_view.sql`
2. **Update application code** to use materialized view when no company filters
3. **Set up automated refresh** (every 6 hours or on-demand)
4. **Fallback to direct query** when company filters are present (already fast)

## Code Changes Required for Materialized View

Update `app/repositories/contacts.py` - `list_technologies_simple()`:

```python
# Check if we can use materialized view (no company filters, distinct=true)
if params.distinct and not company and not params.search:
    # Use materialized view for fast pagination
    from app.models.technologies import DistinctTechnology  # New model
    stmt = select(DistinctTechnology.value)
    # ... apply ordering and pagination
else:
    # Use existing query (fast with company filters)
    # ... existing code
```

## Performance Comparison

| Approach | Query Time | Notes |
|----------|------------|-------|
| Current (optimized) | 3.7-4.4s | Best possible without schema changes |
| Materialized View | <0.1s | Requires periodic refresh |
| With Company Filter | 0.6s | Already optimized ✅ |
| With Search Filter | 28.6s | Needs materialized view or different approach |

## Conclusion

The current query performance (~4s) is **the best possible** given the constraints:
- Need all distinct technologies across all companies
- Must unnest arrays before distinct
- GIN indexes can't help with unnest operations

To achieve <2s performance, **materialized view is required**. This is a common pattern for expensive aggregation queries in PostgreSQL.

