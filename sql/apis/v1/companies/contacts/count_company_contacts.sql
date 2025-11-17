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
-- Note: This query uses the same filter logic as list_company_contacts.sql but returns COUNT(*)
-- instead of the actual rows. All filter conditions apply here.
--
-- Example Usage:
--   SELECT COUNT(co.id) as count
--   FROM contacts co
--   LEFT JOIN companies comp ON co.company_id = comp.uuid
--   LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
--   LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
--   WHERE co.company_id = $1
--     AND co.title ILIKE '%engineer%';
-- ============================================================================

SELECT COUNT(co.id) as count
FROM contacts co
LEFT JOIN companies comp ON co.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE co.company_id = $1
    -- Add filter conditions here based on query parameters
    -- Example filters:
    -- AND co.title ILIKE '%engineer%'
    -- AND co.seniority = 'senior'
    -- AND co.created_at >= '2024-01-01'
    -- AND co.first_name ILIKE '%john%'
;

