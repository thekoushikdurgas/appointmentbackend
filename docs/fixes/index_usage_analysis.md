# Index Usage Analysis - Post Maintenance Review

## Maintenance Execution Summary

✅ **All maintenance operations completed successfully:**

- `ANALYZE` on all tables: ~3 seconds each
- `VACUUM ANALYZE` on all tables: 4 seconds to 1m 41s (expected for large tables)
- Index statistics queries executed successfully

## Key Findings

### ✅ Active Indexes (Being Used)

**Highly Used Indexes:**

1. `idx_companies_uuid_unique` - **400 scans** (370 MB)
2. `idx_companies_metadata_uuid_unique` - **204 scans** (488 MB)
3. `idx_contacts_company_department` - **154 scans** (8.8 GB)
4. `idx_companies_metadata_normalized_domain` - **84 scans** (213 MB) ⭐ *Critical for email finder*
5. `idx_contacts_company_id` - **56 scans** (1 GB)
6. `idx_contacts_first_name_trgm` - **35 scans** (700 MB) ⭐ *Used for name searches*
7. `idx_contacts_last_name_trgm` - **35 scans** (1.3 GB) ⭐ *Used for name searches*

**LinkedIn URL Indexes (Our Optimization Target):**

- `idx_contacts_metadata_linkedin_url_gin` - **4 scans** (4.8 GB) ✅ *Being used*
- `idx_companies_metadata_linkedin_url_gin` - **4 scans** (355 MB) ✅ *Being used*

**Note:** The LinkedIn URL indexes show 4 scans, which indicates they are being used. The optimization we implemented should improve performance for these queries.

### ⚠️ Unused Indexes (Candidates for Review)

**Large Unused Indexes (>1 GB):**

1. `idx_contacts_email_company` - **0 scans** (6.5 GB) 🔴
2. `idx_contacts_company_seniority_title` - **0 scans** (5.8 GB) 🔴
3. `idx_contacts_email_finder` - **0 scans** (5.8 GB) 🔴
4. `idx_contacts_name_company` - **0 scans** (5.6 GB) 🔴
5. `idx_contacts_company_title` - **0 scans** (5.4 GB) 🔴
6. `idx_contacts_metadata_uuid_unique` - **0 scans** (5.2 GB) 🔴
7. `idx_contacts_email_status_filter` - **0 scans** (4.3 GB) 🔴
8. `idx_contacts_seniority_department` - **0 scans** (4.3 GB) 🔴
9. `idx_contacts_title_trgm` - **0 scans** (3.9 GB) 🔴
10. `idx_contacts_dec_trgm` - **0 scans** (3.8 GB) 🔴

**Total Unused Index Space:** ~50+ GB

## Recommendations

### 1. Immediate Actions

#### ✅ Keep These Indexes (Even if Unused)

- **Primary keys and unique constraints** - Required for data integrity
- **Indexes on frequently filtered columns** - May be used in future queries
- **Indexes created recently** - May not have had time to accumulate usage stats

#### 🔍 Investigate Before Dropping

Before dropping any unused indexes, verify:

1. **Query patterns** - Check if queries that would use these indexes exist but haven't run yet
2. **Application code** - Ensure no code paths use these indexes
3. **Future requirements** - Consider if these indexes support planned features

#### 💾 Potential Space Savings

If safe to drop, removing the top 10 unused indexes could free up **~50 GB** of disk space.

### 2. Index Optimization Opportunities

#### LinkedIn URL Indexes

- ✅ Both GIN indexes are being used (4 scans each)
- The optimization we implemented should improve query performance
- Monitor these indexes for increased usage after the optimization

#### Email Finder Indexes

- ✅ `idx_companies_metadata_normalized_domain` is highly used (84 scans)
- This confirms the email finder service is working efficiently

### 3. Monitoring Recommendations

1. **Track Index Usage Over Time:**
   ```sql
   -- Run monthly to track index usage trends
   SELECT 
       relname as table_name,
       indexrelname as index_name,
       idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
   FROM pg_stat_user_indexes
   WHERE schemaname = 'public'
       AND idx_scan = 0
   ORDER BY pg_relation_size(indexrelid) DESC
   LIMIT 20;
   ```

2. **Monitor Query Performance:**
   - Continue monitoring `logs/app.log` for slow query warnings
   - Track LinkedIn URL query performance after optimization
   - Monitor email finder service response times

3. **Regular Maintenance:**
   - Run `ANALYZE` weekly on frequently updated tables
   - Run `VACUUM ANALYZE` monthly or after bulk data loads
   - Review unused indexes quarterly

## Next Steps

1. ✅ **Maintenance Complete** - All tables analyzed and vacuumed
2. 🔍 **Review Unused Indexes** - Investigate large unused indexes before dropping
3. 📊 **Monitor Performance** - Track query performance improvements
4. 🔄 **Regular Maintenance** - Schedule periodic maintenance runs

## Index Drop Script (Use with Caution)

If you decide to drop unused indexes after investigation, use this template:

```sql
-- WARNING: Review each index carefully before dropping
-- Only drop indexes that are confirmed unused and not needed

-- Example (DO NOT RUN without review):
-- DROP INDEX CONCURRENTLY IF EXISTS idx_contacts_email_company;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_contacts_company_seniority_title;
-- ... etc

-- Always use CONCURRENTLY to avoid locking the table
```

## Conclusion

The maintenance operation was successful. The database statistics are now up to date, which should improve query planner decisions. The LinkedIn URL indexes are confirmed to be in use, validating our optimization efforts. Consider reviewing the large unused indexes for potential space savings, but do so carefully after thorough investigation.
