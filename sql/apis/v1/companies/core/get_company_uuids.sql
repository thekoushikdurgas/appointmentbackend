-- ============================================================================
-- Endpoint: GET /api/v1/companies/count/uuids/
-- API Version: v1
-- Description: Return a list of company UUIDs that match the provided filters.
--              Supports all CompanyFilterParams. Returns count and list of UUIDs.
--              Useful for bulk operations or exporting specific company sets.
--              Uses the same conditional JOIN logic as list_companies.
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

-- ORM Implementation Notes:
--   The CompanyRepository.get_uuids_by_filters() uses the same conditional JOIN logic as list_companies():
--   
--   JOIN Decision Logic (same as list_companies):
--   1. Minimal query: Only companies table - SELECT Company.uuid
--      - Used when: No metadata filters, no metadata search
--      - Uses EXISTS subqueries for metadata filters when needed
--   
--   2. Metadata join: Company + CompanyMetadata - SELECT Company.uuid FROM joined query
--      - Used when: Metadata filters present OR metadata search
--   
--   Return Format:
--   - Returns list[str] of UUIDs (not array_agg in SQL)
--   - Service layer builds response with count and uuids list
--   - Optional limit parameter

-- Query 1: Get all matching company UUIDs (no limit, with metadata filter)
-- GET /api/v1/companies/count/uuids/?city=San Francisco
-- Note: When metadata filters are present, metadata join is added. Returns list of UUIDs, not array_agg.
SELECT co.uuid
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city ILIKE '%San Francisco%'
ORDER BY co.created_at DESC NULLS LAST;

-- Query 2: Get company UUIDs with limit (minimal - no metadata join)
-- GET /api/v1/companies/count/uuids/?name=TechCorp&limit=200
-- Note: When no metadata filters, queries only Company table. Service layer builds count separately.
SELECT co.uuid
FROM companies co
WHERE co.name ILIKE '%TechCorp%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 200;

-- Query 3: Get company UUIDs with distinct filter (with metadata join)
-- GET /api/v1/companies/count/uuids/?city=San Francisco&distinct=true&limit=100
-- Note: When distinct=true and metadata join present, uses DISTINCT ON. Returns list of UUIDs, not array_agg.
SELECT DISTINCT ON (co.id) co.uuid
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city ILIKE '%San Francisco%'
ORDER BY co.id, co.created_at DESC NULLS LAST
LIMIT 100;

