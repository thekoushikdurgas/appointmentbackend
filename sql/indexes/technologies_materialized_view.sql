-- ============================================================================
-- Materialized View for Distinct Technologies
-- ============================================================================
-- This materialized view pre-computes distinct technology values, making
-- pagination queries much faster (from ~4s to <0.1s).
--
-- Usage:
--   1. Create the materialized view: Run this script
--   2. Create index on the view for fast ordering
--   3. Refresh periodically: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;
--   4. Update application code to query the materialized view instead
-- ============================================================================

-- Drop existing materialized view if it exists
DROP MATERIALIZED VIEW IF EXISTS mv_distinct_technologies CASCADE;

-- Create materialized view with all distinct technologies
CREATE MATERIALIZED VIEW mv_distinct_technologies AS
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
  AND array_length(technologies, 1) > 0;

-- Create index on value for fast ordering and pagination
CREATE INDEX idx_mv_distinct_technologies_value_asc 
ON mv_distinct_technologies (value ASC);

CREATE INDEX idx_mv_distinct_technologies_value_desc 
ON mv_distinct_technologies (value DESC);

-- Add comment
COMMENT ON MATERIALIZED VIEW mv_distinct_technologies IS 
'Pre-computed distinct technology values for fast pagination. Refresh with: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;';

-- ============================================================================
-- Refresh Strategy
-- ============================================================================
-- Option 1: Manual refresh (faster, locks table briefly)
-- REFRESH MATERIALIZED VIEW mv_distinct_technologies;
--
-- Option 2: Concurrent refresh (slower, no lock, can be done during operation)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;
--
-- Option 3: Scheduled refresh (recommended)
-- Set up a cron job or pg_cron to refresh periodically:
-- SELECT cron.schedule('refresh-technologies', '0 */6 * * *', 
--   'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_distinct_technologies;');
-- ============================================================================

-- Initial refresh
REFRESH MATERIALIZED VIEW mv_distinct_technologies;

-- ============================================================================
-- Example Queries Using Materialized View
-- ============================================================================
-- Fast pagination query (should be <0.1s):
-- SELECT value FROM mv_distinct_technologies ORDER BY value ASC LIMIT 25 OFFSET 50;
--
-- With search filter:
-- SELECT value FROM mv_distinct_technologies 
-- WHERE value ILIKE '%Python%' 
-- ORDER BY value ASC LIMIT 25 OFFSET 50;
-- ============================================================================

