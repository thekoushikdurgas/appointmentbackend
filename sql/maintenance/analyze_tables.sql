-- Database Maintenance Script
-- Run this script periodically to update table statistics and optimize query performance
-- This is especially important after bulk data loads or index creation

-- Analyze tables to update statistics for query planner
-- This helps PostgreSQL choose optimal query plans and use indexes effectively
ANALYZE contacts;
ANALYZE companies;
ANALYZE contacts_metadata;
ANALYZE companies_metadata;

-- Analyze indexes (PostgreSQL 12+)
-- Updates statistics for indexes to help with index usage decisions
ANALYZE contacts_metadata (linkedin_url);
ANALYZE companies_metadata (linkedin_url);

-- Optional: Vacuum analyze for more thorough maintenance (can be slow on large tables)
-- Uncomment if you want to reclaim space and update visibility maps
-- VACUUM ANALYZE contacts;
-- VACUUM ANALYZE companies;
-- VACUUM ANALYZE contacts_metadata;
-- VACUUM ANALYZE companies_metadata;

-- Check index usage statistics
-- This helps identify which indexes are being used and which might be candidates for removal
SELECT 
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND (
        relname IN ('contacts', 'companies', 'contacts_metadata', 'companies_metadata')
        OR indexrelname LIKE '%linkedin%'
    )
ORDER BY idx_scan DESC, relname, indexrelname;

-- Check for unused indexes (candidates for removal)
-- Note: Review carefully before dropping any indexes
SELECT 
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
    AND idx_scan = 0
    AND indexrelid NOT IN (
        SELECT conindid FROM pg_constraint
    )
ORDER BY pg_relation_size(indexrelid) DESC;

