-- ============================================================================
-- Endpoint: GET /api/v1/companies/count/uuids/
-- API Version: v1
-- Description: Return a list of company UUIDs that match the provided filters. Supports all CompanyFilterParams. Returns count and list of UUIDs. Useful for bulk operations or exporting specific company sets.
-- ============================================================================
--
-- Parameters (All optional, same as list_companies.sql):
--   See list_companies.sql for complete parameter list (40+ filter parameters)
--   All filter parameters from /api/v1/companies/ are supported.
--
--   Additional Parameters:
--     limit (integer, optional) - Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).
--
-- Response Structure:
-- {
--   "count": 567,
--   "uuids": ["uuid1", "uuid2", "uuid3", ...]
-- }
--
-- Note: This query uses the same filter logic as list_companies.sql but returns only UUIDs
-- instead of full company records. All filter conditions from list_companies.sql apply here.
--
-- Example Usage:
--   GET /api/v1/companies/count/uuids/?industries=Technology&employees_min=100&limit=200
--   Returns up to 200 company UUIDs matching the filters.
-- ============================================================================

-- Query 1: Get all matching company UUIDs (no limit)
-- GET /api/v1/companies/count/uuids/?industries=Technology&employees_min=100
SELECT 
    COUNT(co.uuid) as count,
    array_agg(co.uuid ORDER BY co.created_at DESC) as uuids
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply all filter conditions from list_companies.sql here
    -- See list_companies.sql for complete WHERE clause implementation
    -- Example filters:
    -- AND array_to_string(co.industries, ',') ILIKE '%Technology%'
    -- AND co.employees_count >= 100
;

-- Query 2: Get company UUIDs with limit
-- GET /api/v1/companies/count/uuids/?industries=Technology&employees_min=100&limit=200
WITH filtered_companies AS (
    SELECT co.uuid
    FROM companies co
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply all filter conditions from list_companies.sql here
        -- See list_companies.sql for complete WHERE clause implementation
    ORDER BY co.created_at DESC
    LIMIT 200
)
SELECT 
    (SELECT COUNT(*) FROM companies co
     LEFT JOIN companies_metadata com ON co.uuid = com.uuid
     WHERE 1=1
        -- Apply same filter conditions here for count
    ) as count,
    array_agg(uuid ORDER BY uuid) as uuids
FROM filtered_companies;

-- Query 3: Get company UUIDs with distinct filter
-- GET /api/v1/companies/count/uuids/?industries=Technology&distinct=true&limit=100
WITH filtered_companies AS (
    SELECT DISTINCT ON (co.id) co.uuid
    FROM companies co
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply all filter conditions from list_companies.sql here
    ORDER BY co.id, co.created_at DESC
    LIMIT 100
)
SELECT 
    (SELECT COUNT(DISTINCT co.id) FROM companies co
     LEFT JOIN companies_metadata com ON co.uuid = com.uuid
     WHERE 1=1
        -- Apply same filter conditions here for count
    ) as count,
    array_agg(uuid ORDER BY uuid) as uuids
FROM filtered_companies;

