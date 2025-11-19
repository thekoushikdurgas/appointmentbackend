# Query Optimization Guide for Large Tables

This document provides guidance on optimizing database queries for large tables (50M contacts, 5M companies).

## Database Indexes

### Applying Optimization Indexes

Run the optimization indexes SQL file to add performance indexes:

```bash
psql -h your_host -U postgres -d your_database -f sql/indexes/optimization_indexes.sql
```

### Index Maintenance

After creating indexes, update table statistics:

```sql
ANALYZE contacts;
ANALYZE companies;
ANALYZE contacts_metadata;
ANALYZE companies_metadata;
```

Monitor index usage:

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## PostgreSQL Configuration Tuning

### Recommended PostgreSQL Settings

For large datasets (50M+ rows), consider these PostgreSQL configuration settings:

```ini
# Memory Settings
shared_buffers = 4GB                    # 25% of total RAM for dedicated DB server
effective_cache_size = 12GB             # 50-75% of total RAM
work_mem = 64MB                         # Per-operation memory
maintenance_work_mem = 1GB              # For VACUUM, CREATE INDEX, etc.

# Query Planner
random_page_cost = 1.1                  # For SSD storage (default 4.0 for HDD)
effective_io_concurrency = 200          # For SSD storage

# Connection Settings
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

# Autovacuum (Critical for large tables)
autovacuum = on
autovacuum_max_workers = 4
autovacuum_naptime = 10s
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.02
autovacuum_vacuum_cost_delay = 10ms
autovacuum_vacuum_cost_limit = 2000

# Query Statistics
pg_stat_statements.max = 10000
pg_stat_statements.track = all
```

### Applying Configuration

1. Edit `postgresql.conf` on your PostgreSQL server
2. Restart PostgreSQL service
3. Verify settings: `SHOW shared_buffers;`

### Monitoring Query Performance

Enable `pg_stat_statements` extension:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

View slow queries:

```sql
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

## Connection Pool Optimization

The application is configured with:

- `DATABASE_POOL_SIZE = 25` - Base connection pool size
- `DATABASE_MAX_OVERFLOW = 50` - Maximum overflow connections
- `DATABASE_POOL_TIMEOUT = 30` - Timeout for getting connection
- `DATABASE_POOL_RECYCLE = 1800` - Connection recycle time (30 minutes)
- `DATABASE_POOL_PRE_PING = True` - Verify connections before use

For high concurrency, consider increasing:
- `DATABASE_POOL_SIZE` to 50-100
- `DATABASE_MAX_OVERFLOW` to 100-200

## Vacuum and Analyze Configuration

### Automatic Maintenance

PostgreSQL autovacuum should handle most maintenance automatically with the recommended settings above.

### Manual Maintenance

For large tables, periodic manual maintenance may be needed:

```sql
-- Analyze tables (update statistics)
ANALYZE contacts;
ANALYZE companies;

-- Vacuum (reclaim space, update visibility map)
VACUUM ANALYZE contacts;
VACUUM ANALYZE companies;

-- Reindex GIN indexes (periodically)
REINDEX INDEX CONCURRENTLY idx_contacts_dec_trgm;
REINDEX INDEX CONCURRENTLY idx_contacts_title_trgm;
REINDEX INDEX CONCURRENTLY idx_companies_name_trgm;
```

### Monitoring Table Bloat

Check table bloat:

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_dead_tup,
    n_live_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Query Optimization Features

### Approximate Counts

For very large unfiltered queries, enable approximate counts:

```python
# In your service layer
count = await repository.count_contacts(
    session,
    filters,
    use_approximate=True  # Uses pg_class.reltuples
)
```

### Query Caching

Enable Redis-based query caching:

1. Set up Redis connection
2. Enable caching in config: `ENABLE_QUERY_CACHING = True`
3. Initialize cache with Redis client:

```python
from app.utils.query_cache import QueryCache, set_query_cache
import redis.asyncio as redis

redis_client = redis.from_url(settings.REDIS_URL)
cache = QueryCache(redis_client)
set_query_cache(cache)
```

### Query Monitoring

Query monitoring is enabled by default. Slow queries (>1 second) are automatically logged.

View monitoring stats:

```python
from app.utils.query_monitor import get_query_monitor

monitor = get_query_monitor()
stats = monitor.get_stats()
print(stats)
```

## Performance Testing

### Before Optimization

1. Record baseline query times
2. Identify slow queries using `pg_stat_statements`
3. Check index usage

### After Optimization

1. Run `ANALYZE` on all tables
2. Test query performance
3. Monitor slow query logs
4. Compare with baseline

## Best Practices

1. **Always use pagination** - Never fetch all records without limits
2. **Use indexes** - Ensure frequently filtered columns are indexed
3. **Monitor slow queries** - Review and optimize queries >1 second
4. **Regular maintenance** - Run VACUUM and ANALYZE regularly
5. **Connection pooling** - Use appropriate pool sizes for your workload
6. **Query caching** - Cache frequently accessed, rarely changing data

## Troubleshooting

### Slow Queries

1. Check if indexes are being used: `EXPLAIN ANALYZE <query>`
2. Verify table statistics are up to date: `ANALYZE <table>`
3. Check for table bloat: See monitoring queries above
4. Review query plan for sequential scans

### High Memory Usage

1. Reduce `work_mem` if seeing high memory usage
2. Check connection pool size
3. Monitor active connections: `SELECT count(*) FROM pg_stat_activity;`

### Index Issues

1. Check index usage: `pg_stat_user_indexes`
2. Rebuild unused indexes: `REINDEX INDEX <index_name>`
3. Consider dropping unused indexes to save space

