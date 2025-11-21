-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/first_name/
-- API Version: v1
-- Description: Return a list of distinct first names for contacts belonging to a specific company.
--              Supports CompanyContactFilterParams for filtering contacts before extracting attribute values.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     company_uuid (text, required) - Company UUID identifier
--
--   Query Parameters:
--     distinct (boolean, default: true) - Return distinct first name values
--     limit (integer, optional) - Maximum number of values to return
--     offset (integer, default: 0) - Zero-based offset into the result set
--     ordering (text, optional) - Sort order (e.g., "first_name" or "-first_name")
--     search (text, optional) - Search term to filter first names
--     All CompanyContactFilterParams apply for filtering contacts (see list_company_contacts.sql)
--
-- Response Structure:
--   Returns List[str] - Array of first name strings
--
-- Response Codes:
--   200 OK: First names retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   404 Not Found: Company not found
--   500 Internal Server Error: Error occurred while retrieving first names
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/companies/company/{company_uuid}/contacts/first_name/?limit=50
--   GET /api/v1/companies/company/{company_uuid}/contacts/first_name/?search=John&distinct=true
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values_by_company() is used for this endpoint:
--   - Always joins Company, ContactMetadata, and CompanyMetadata (for filter support)
--   - Column mapping: "first_name" → Contact.first_name
--   - Filters applied via _apply_company_contact_filters() which handles all CompanyContactFilterParams
--   - Returns list[str] of distinct values

-- Query: Get distinct first names for company contacts
-- GET /api/v1/companies/company/{company_uuid}/contacts/first_name/
-- Note: Always joins all tables to support all filter parameters. This simplified version shows the concept.
SELECT DISTINCT
    c.first_name as value
FROM contacts c
LEFT JOIN companies comp ON c.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON c.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE c.company_id = $1
    AND c.first_name IS NOT NULL
    AND TRIM(c.first_name) != ''
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY c.first_name ASC
LIMIT 25
OFFSET 0;

-- Query with search filter:
-- GET /api/v1/companies/company/{company_uuid}/contacts/first_name/?search=John
SELECT DISTINCT
    c.first_name
FROM contacts c
WHERE c.company_id = $1
    AND c.first_name IS NOT NULL
    AND c.first_name != ''
    AND c.first_name ILIKE '%' || $4 || '%'
ORDER BY c.first_name ASC
LIMIT COALESCE($2, 1000)
OFFSET COALESCE($3, 0);

-- Notes:
-- - The ORM uses ContactRepository.list_attribute_values_by_company() which filters contacts
--   by company_uuid and applies CompanyContactFilterParams before extracting attribute values
-- - Additional filters from CompanyContactFilterParams (title, seniority, email_status, etc.)
--   would be applied in the WHERE clause before extracting first_name values
-- - Results are automatically deduplicated and sorted

