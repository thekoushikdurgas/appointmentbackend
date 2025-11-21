-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/count/
-- API Version: v1
-- Description: Return the total count of contacts for a specific company matching filters.
-- ============================================================================
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--
-- Query Parameters: (All optional, same as list_company_contacts.sql)
--   See list_company_contacts.sql for complete parameter list.
--   All CompanyContactFilterParams are supported.
--
-- Response Structure:
-- {
--   "count": 42
-- }
--
-- ORM Implementation Notes:
--   The ContactRepository.count_contacts_by_company() uses optimized queries:
--   - Uses minimal query (only contacts table) with EXISTS subqueries
--   - No JOINs unless ContactMetadata filters require them (uses EXISTS instead)
--   - Optimized for performance - avoids unnecessary joins in count queries
--   - Applies all CompanyContactFilterParams filters

-- Query 1: Count contacts for company (minimal - no joins, uses EXISTS for metadata filters)
-- GET /api/v1/companies/company/{company_uuid}/contacts/count/
-- Note: Uses EXISTS subqueries for ContactMetadata filters instead of JOINs for better performance.
SELECT COUNT(co.id) as count
FROM contacts co
WHERE co.company_id = $1
    -- Add filter conditions here based on query parameters
    -- Example filters:
    -- AND co.title ILIKE '%engineer%'
    -- AND co.seniority = 'senior'
    -- AND co.created_at >= '2024-01-01'
    -- AND co.first_name ILIKE '%john%'
;

