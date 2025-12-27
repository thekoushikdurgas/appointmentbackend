# Technologies Materialized View Implementation Guide

## Quick Start

To achieve <0.1s query performance, implement the materialized view:

### Step 1: Create Materialized View

```bash
psql -d your_database -f sql/optimizations/technologies_materialized_view.sql
```

This will:
- Create `mv_distinct_technologies` materialized view
- Create indexes for fast ordering
- Do initial refresh

### Step 2: Test Performance

```sql
-- Should be <0.1s
EXPLAIN ANALYZE
SELECT value FROM mv_distinct_technologies 
ORDER BY value ASC 
LIMIT 25 OFFSET 50;
```

### Step 3: Update Application Code

See code changes section below.

### Step 4: Set Up Automated Refresh

```sql
-- Using pg_cron (if available)
SELECT cron.schedule(
    'refresh-technologies',
    '0 */6 * * *',  -- Every 6 hours
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;'
);
```

Or set up a cron job:
```bash
# In crontab
0 */6 * * * psql -d your_database -c "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;"
```

## Code Changes

### Option A: Use Materialized View for Unfiltered Queries

Modify `app/repositories/contacts.py`:

```python
async def list_technologies_simple(...):
    # Use materialized view when: distinct=true, no company filter, no search
    if params.distinct and not company and not params.search:
        # Fast path: Use materialized view
        from sqlalchemy import Table, MetaData
        metadata = MetaData()
        mv_technologies = Table('mv_distinct_technologies', metadata, autoload_with=session.bind)
        
        stmt = select(mv_technologies.c.value)
        
        # Apply ordering
        if params.ordering == "value" or params.ordering is None:
            stmt = stmt.order_by(mv_technologies.c.value.asc())
        elif params.ordering == "-value":
            stmt = stmt.order_by(mv_technologies.c.value.desc())
        
        # Apply pagination
        stmt = stmt.offset(params.offset)
        if params.limit:
            stmt = stmt.limit(params.limit + 1)  # +1 for has_more detection
        
        result = await session.execute(stmt)
        values = [row[0] for row in result.fetchall()]
        
        has_more = len(values) > params.limit if params.limit else False
        if has_more:
            values = values[:params.limit]
        
        return (values, has_more)
    else:
        # Existing code path (fast with company filters)
        # ... existing implementation
```

### Option B: Always Use Materialized View (Simpler)

Always query the materialized view, but refresh it more frequently:

```python
# Always use materialized view
# Refresh on-demand or frequently
```

## Refresh Strategies

### 1. On-Demand Refresh

Refresh when technologies are updated:
```python
# After updating company technologies
await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;"))
```

### 2. Scheduled Refresh

Refresh every 6 hours (recommended):
- Technologies don't change frequently
- 6 hours is a good balance between freshness and performance

### 3. Real-time Refresh (If Needed)

Use triggers to refresh on every change (not recommended - too expensive):
```sql
CREATE OR REPLACE FUNCTION refresh_technologies_mv()
RETURNS TRIGGER AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER refresh_technologies_on_update
AFTER INSERT OR UPDATE OR DELETE ON companies
FOR EACH ROW
WHEN (NEW.technologies IS DISTINCT FROM OLD.technologies)
EXECUTE FUNCTION refresh_technologies_mv();
```

## Monitoring

### Check Materialized View Size

```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('mv_distinct_technologies')) as total_size,
    pg_size_pretty(pg_relation_size('mv_distinct_technologies')) as table_size,
    pg_size_pretty(pg_indexes_size('mv_distinct_technologies')) as indexes_size;
```

### Check Last Refresh Time

```sql
-- Add a last_refreshed column to track refresh times
ALTER TABLE mv_distinct_technologies 
ADD COLUMN IF NOT EXISTS last_refreshed TIMESTAMP DEFAULT NOW();

-- Update on refresh (requires custom refresh function)
```

### Monitor Query Performance

```sql
-- Check if materialized view is being used
EXPLAIN ANALYZE
SELECT value FROM mv_distinct_technologies 
ORDER BY value ASC 
LIMIT 25 OFFSET 50;
```

Should show:
- Index Scan on `idx_mv_distinct_technologies_value_asc`
- Execution time <0.1s

## Troubleshooting

### Materialized View Not Refreshing

```sql
-- Check if refresh is running
SELECT * FROM pg_stat_activity 
WHERE query LIKE '%REFRESH MATERIALIZED VIEW%';

-- Manual refresh
REFRESH MATERIALIZED VIEW mv_distinct_technologies;
```

### Performance Still Slow

1. Check if indexes exist:
   ```sql
   \d mv_distinct_technologies
   ```

2. Check if query uses index:
   ```sql
   EXPLAIN ANALYZE SELECT value FROM mv_distinct_technologies ORDER BY value ASC LIMIT 25;
   ```

3. Update statistics:
   ```sql
   ANALYZE mv_distinct_technologies;
   ```

### Data Staleness

If users report missing technologies:
1. Check last refresh time
2. Refresh manually if needed
3. Consider more frequent refresh schedule

## Rollback Plan

If materialized view causes issues:

1. **Disable in code**: Comment out materialized view path, use existing query
2. **Drop materialized view**: `DROP MATERIALIZED VIEW mv_distinct_technologies;`
3. **No data loss**: Materialized view is read-only, dropping it doesn't affect source data

## Performance Expectations

| Query Type | Before | After Materialized View |
|------------|--------|-------------------------|
| Unfiltered, distinct=true | 4.4s | <0.1s |
| With company filter | 0.6s | 0.6s (unchanged) |
| With search filter | 28.6s | <0.5s (with materialized view + search) |

## Next Steps

1. ✅ Create materialized view
2. ✅ Test performance
3. ⏳ Update application code
4. ⏳ Set up automated refresh
5. ⏳ Monitor and adjust refresh frequency

