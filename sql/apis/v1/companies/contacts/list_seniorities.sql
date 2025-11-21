-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/seniority/
-- API Version: v1
-- Description: Return a list of distinct seniority levels for contacts belonging to a specific company.
--              Supports CompanyContactFilterParams for filtering contacts before extracting attribute values.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     company_uuid (text, required) - Company UUID identifier
--
--   Query Parameters:
--     distinct (boolean, default: true) - Return distinct seniority values
--     limit (integer, optional) - Maximum number of values to return
--     offset (integer, default: 0) - Zero-based offset into the result set
--     ordering (text, optional) - Sort order (e.g., "seniority" or "-seniority")
--     search (text, optional) - Search term to filter seniority values
--     All CompanyContactFilterParams apply for filtering contacts (see list_company_contacts.sql)
--
-- Response Structure:
--   Returns List[str] - Array of seniority level strings
--
-- Response Codes:
--   200 OK: Seniorities retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   404 Not Found: Company not found
--   500 Internal Server Error: Error occurred while retrieving seniorities
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/companies/company/{company_uuid}/contacts/seniority/?limit=50
--   GET /api/v1/companies/company/{company_uuid}/contacts/seniority/?search=Senior&distinct=true
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values_by_company() is used for this endpoint:
--   - Always joins Company, ContactMetadata, and CompanyMetadata (for filter support)
--   - Column mapping: "seniority" → Contact.seniority
--   - Filters applied via _apply_company_contact_filters() which handles all CompanyContactFilterParams
--   - Returns list[str] of distinct values

-- Query: Get distinct seniorities for company contacts
-- GET /api/v1/companies/company/{company_uuid}/contacts/seniority/
-- Note: Always joins all tables to support all filter parameters. This simplified version shows the concept.
SELECT DISTINCT
    c.seniority as value
FROM contacts c
LEFT JOIN companies comp ON c.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON c.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE c.company_id = $1
    AND c.seniority IS NOT NULL
    AND TRIM(c.seniority) != ''
    AND c.seniority != '_'  -- Exclude placeholder values
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query with search filter:
-- GET /api/v1/companies/company/{company_uuid}/contacts/seniority/?search=Senior
SELECT DISTINCT
    c.seniority
FROM contacts c
WHERE c.company_id = $1
    AND c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority ILIKE '%' || $4 || '%'
ORDER BY c.seniority ASC
LIMIT COALESCE($2, 1000)
OFFSET COALESCE($3, 0);

-- Notes:
-- - The ORM uses ContactRepository.list_attribute_values_by_company() which filters contacts
--   by company_uuid and applies CompanyContactFilterParams before extracting attribute values
-- - Additional filters from CompanyContactFilterParams would be applied in the WHERE clause
-- - Results are automatically deduplicated and sorted

