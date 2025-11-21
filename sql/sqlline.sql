
ANALYZE contacts;
ANALYZE companies;
ANALYZE contacts_metadata;
ANALYZE companies_metadata;

ANALYZE contacts_metadata (linkedin_url);
ANALYZE companies_metadata (linkedin_url);

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

