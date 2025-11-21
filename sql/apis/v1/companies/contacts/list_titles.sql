-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/title/
-- API Version: v1
-- Description: Return a list of distinct job titles for contacts belonging to a specific company.
--              Supports CompanyContactFilterParams for filtering contacts before extracting attribute values.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     company_uuid (text, required) - Company UUID identifier
--
--   Query Parameters:
--     distinct (boolean, default: true) - Return distinct title values
--     limit (integer, optional) - Maximum number of values to return
--     offset (integer, default: 0) - Zero-based offset into the result set
--     ordering (text, optional) - Sort order (e.g., "title" or "-title")
--     search (text, optional) - Search term to filter titles
--     All CompanyContactFilterParams apply for filtering contacts (see list_company_contacts.sql)
--
-- Response Structure:
--   Returns List[str] - Array of job title strings
--
-- Response Codes:
--   200 OK: Titles retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   404 Not Found: Company not found
--   500 Internal Server Error: Error occurred while retrieving titles
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/companies/company/{company_uuid}/contacts/title/?limit=50
--   GET /api/v1/companies/company/{company_uuid}/contacts/title/?search=Engineer&distinct=true
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values_by_company() is used for this endpoint:
--   - Always joins Company, ContactMetadata, and CompanyMetadata (for filter support)
--   - Column mapping: "title" → Contact.title
--   - Filters applied via _apply_company_contact_filters() which handles all CompanyContactFilterParams
--   - Returns list[str] of distinct values

-- Query: Get distinct titles for company contacts
-- GET /api/v1/companies/company/{company_uuid}/contacts/title/
-- Note: Always joins all tables to support all filter parameters. This simplified version shows the concept.
SELECT DISTINCT
    c.title as value
FROM contacts c
LEFT JOIN companies comp ON c.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON c.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE c.company_id = $1
    AND c.title IS NOT NULL
    AND TRIM(c.title) != ''
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query with search filter:
-- GET /api/v1/companies/company/{company_uuid}/contacts/title/?search=Engineer
SELECT DISTINCT
    c.title
FROM contacts c
WHERE c.company_id = $1
    AND c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%' || $4 || '%'
ORDER BY c.title ASC
LIMIT COALESCE($2, 1000)
OFFSET COALESCE($3, 0);

-- Notes:
-- - The ORM uses ContactRepository.list_attribute_values_by_company() which filters contacts
--   by company_uuid and applies CompanyContactFilterParams before extracting attribute values
-- - Additional filters from CompanyContactFilterParams would be applied in the WHERE clause
-- - Results are automatically deduplicated and sorted

