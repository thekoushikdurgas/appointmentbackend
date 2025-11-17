-- ============================================================================
-- Endpoint: GET /api/v1/companies/count/
-- API Version: v1
-- Description: Return the total number of companies that satisfy the provided filters. Supports all CompanyFilterParams.
-- ============================================================================
--
-- Parameters: (All optional, same as list_companies.sql)
--   See list_companies.sql for complete parameter list (40+ filter parameters)
--   Key parameters:
--   $1: distinct (boolean, default: false) - Request distinct companies based on primary key
--
-- Response Structure:
-- {
--   "count": 1234
-- }
--
-- Note: This query uses the same filter logic as list_companies.sql but returns COUNT(*)
-- instead of the actual rows. All filter conditions from list_companies.sql apply here.
--
-- Example Usage:
--   SELECT COUNT(DISTINCT co.id) as count
--   FROM companies co
--   LEFT JOIN companies_metadata com ON co.uuid = com.uuid
--   WHERE [filter conditions from list_companies.sql];
-- ============================================================================

-- Base query structure (same as list_companies but with COUNT)
-- Note: All filter conditions from list_companies.sql should be applied here
-- This is a simplified version - see list_companies.sql for complete filter logic

SELECT 
    CASE 
        WHEN $1 = true THEN COUNT(DISTINCT co.id)
        ELSE COUNT(co.id)
    END as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply all filter conditions from list_companies.sql here
    -- See list_companies.sql for complete WHERE clause implementation
    -- This includes:
    --   - Company field filters (name, employees_count, annual_revenue, total_funding, address, etc.)
    --   - Metadata filters (city, state, country, phone_number, website, social URLs, etc.)
    --   - Array filters (industries, keywords, technologies)
    --   - Exclusion filters (exclude_industries, exclude_keywords, exclude_technologies)
    --   - Date range filters (created_at_after, updated_at_before, etc.)
    --   - Search term matching across multiple columns
;

