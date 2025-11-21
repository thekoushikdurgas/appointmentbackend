-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/department/
-- API Version: v1
-- Description: Return a list of distinct department values for contacts belonging to a specific company.
--              Supports CompanyContactFilterParams for filtering contacts before extracting attribute values.
--              Departments are stored as an array, so values are extracted and flattened.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     company_uuid (text, required) - Company UUID identifier
--
--   Query Parameters:
--     distinct (boolean, default: true) - Return distinct department values
--     limit (integer, optional) - Maximum number of values to return
--     offset (integer, default: 0) - Zero-based offset into the result set
--     ordering (text, optional) - Sort order (e.g., "department" or "-department")
--     search (text, optional) - Search term to filter department values
--     All CompanyContactFilterParams apply for filtering contacts (see list_company_contacts.sql)
--
-- Response Structure:
--   Returns List[str] - Array of department strings (flattened from arrays)
--
-- Response Codes:
--   200 OK: Departments retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   404 Not Found: Company not found
--   500 Internal Server Error: Error occurred while retrieving departments
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/companies/company/{company_uuid}/contacts/department/?limit=50
--   GET /api/v1/companies/company/{company_uuid}/contacts/department/?search=Engineering&distinct=true
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values_by_company() is used for this endpoint:
--   - Always joins Company, ContactMetadata, and CompanyMetadata (for filter support)
--   - Column mapping: "department" → Contact.departments (array field)
--   - Uses lateral unnest subquery for array fields (more complex than shown here)
--   - Filters applied via _apply_company_contact_filters() which handles all CompanyContactFilterParams
--   - Returns list[str] of distinct values (flattened from arrays)

-- Query: Get distinct departments for company contacts (flattened from arrays)
-- GET /api/v1/companies/company/{company_uuid}/contacts/department/
-- Note: Uses lateral unnest subquery in ORM. This simplified version shows the concept.
--       The ORM uses a more complex subquery structure for better performance.
SELECT DISTINCT
    unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies comp ON c.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON c.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE c.company_id = $1
    AND c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query with search filter:
-- GET /api/v1/companies/company/{company_uuid}/contacts/department/?search=Engineering
SELECT DISTINCT
    unnest(c.departments) as department
FROM contacts c
WHERE c.company_id = $1
    AND c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(c.departments) AS dept
        WHERE dept ILIKE '%' || $4 || '%'
    )
ORDER BY department ASC
LIMIT COALESCE($2, 1000)
OFFSET COALESCE($3, 0);

-- Notes:
-- - The ORM uses ContactRepository.list_attribute_values_by_company() which filters contacts
--   by company_uuid and applies CompanyContactFilterParams before extracting attribute values
-- - Departments are stored as PostgreSQL text[] arrays, so unnest() is used to flatten them
-- - Additional filters from CompanyContactFilterParams would be applied in the WHERE clause
-- - Results are automatically deduplicated and sorted

