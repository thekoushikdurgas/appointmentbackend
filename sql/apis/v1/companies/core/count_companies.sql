-- ============================================================================
-- Endpoint: GET /api/v1/companies/count/
-- API Version: v1
-- Description: Return the total number of companies that satisfy the provided filters.
--              Supports all CompanyFilterParams. Uses the same conditional JOIN logic as list_companies.
--              Use distinct=true to count unique companies.
-- ============================================================================
--
-- Parameters (All optional, same as list_companies.sql):
--   Query Parameters:
--     distinct (boolean, default: false) - Request distinct companies based on primary key
--     All filter parameters from list_companies.sql apply here (40+ filter parameters)
--     See list_companies.sql for complete parameter documentation
--
-- Response Structure:
--   Returns CountResponse:
--   {
--     "count": 1234
--   }
--
-- Response Codes:
--   200 OK: Count retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while counting companies
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Implementation Notes:
--   The CompanyRepository.count_companies() uses the same conditional JOIN logic as list_companies():
--   
--   JOIN Decision Logic (same as list_companies):
--   1. Minimal query: Only companies table - COUNT(co.id)
--      - Used when: No metadata filters, no metadata search
--      - Uses EXISTS subqueries for metadata filters when needed
--   
--   2. Metadata join: Company + CompanyMetadata - COUNT(co.id) or COUNT(DISTINCT co.id)
--      - Used when: Metadata filters present OR metadata search
--      - COUNT(co.id) when distinct=false (no duplicates from LEFT JOIN)
--      - COUNT(DISTINCT co.id) when distinct=true (handles potential duplicates)
--   
--   Filter Application:
--   - When metadata join present: Filters applied directly to joined tables
--   - When no metadata join: Uses EXISTS subqueries for metadata filters (optimized for performance)
--   
--   Note: Unlike contacts, companies don't use COUNT(DISTINCT) by default because LEFT JOIN
--         with CompanyMetadata doesn't create duplicates (one-to-one relationship)
--
-- Example Usage:
--   GET /api/v1/companies/count/
--   GET /api/v1/companies/count/?name=TechCorp&employees_min=50
--   GET /api/v1/companies/count/?distinct=true&city=San Francisco
-- ============================================================================

-- Query 1: Count all companies (minimal query - no joins when no filters)
-- GET /api/v1/companies/count/
SELECT 
    COUNT(co.id) as count
FROM companies co;

-- Query 2: Count with distinct=true (minimal query)
-- GET /api/v1/companies/count/?distinct=true
SELECT 
    COUNT(DISTINCT co.id) as count
FROM companies co;

-- Query 3: Count with metadata filter (requires metadata join)
-- GET /api/v1/companies/count/?city=San Francisco
SELECT 
    COUNT(co.id) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city ILIKE '%San Francisco%';

-- Query 4: Count with company field filter (no metadata join needed)
-- GET /api/v1/companies/count/?name=TechCorp&employees_min=50
SELECT 
    COUNT(co.id) as count
FROM companies co
WHERE co.name ILIKE '%TechCorp%'
    AND co.employees_count >= 50;

-- Query 5: Count with all filters
-- GET /api/v1/companies/count/?name=TechCorp&employees_min=50&city=San Francisco&distinct=true
SELECT 
    COUNT(DISTINCT co.id) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%TechCorp%'
    AND co.employees_count >= 50
    AND com.city ILIKE '%San Francisco%';

-- Notes:
-- - The ORM applies filters with EXISTS subqueries when metadata join is not needed
-- - JOINs are conditional - only added when filters require them
-- - When distinct=true, COUNT(DISTINCT co.id) ensures unique company counts even with joins
-- - All filter conditions from list_companies.sql apply here (see list_companies.sql for complete filter logic)

