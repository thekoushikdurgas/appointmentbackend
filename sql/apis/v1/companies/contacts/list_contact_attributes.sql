-- ============================================================================
-- Endpoints: GET /api/v1/companies/company/{company_uuid}/contacts/{attribute}/
-- API Version: v1
-- Description: Return distinct attribute values for contacts within a specific company.
-- ============================================================================
--
-- Supported Attributes:
--   - first_name: Contact.first_name
--   - last_name: Contact.last_name
--   - title: Contact.title
--   - seniority: Contact.seniority
--   - email_status: Contact.email_status
--   - department: Contact.departments (array field, automatically expanded)
--   - city: ContactMetadata.city
--   - state: ContactMetadata.state
--   - country: ContactMetadata.country
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--   $2: attribute (text, required) - Attribute name (e.g., 'title', 'seniority')
--
-- Query Parameters:
--   All CompanyContactFilterParams for filtering base contacts
--   Attribute list specific parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort order ('value', '-value', 'count', '-count')
--     search (text, optional) - Optional case-insensitive search term
--
-- Response Structure:
--   Returns array of strings: ["value1", "value2", "value3"]
--
-- Example Usage for scalar fields (title, seniority, etc.):
--   SELECT DISTINCT co.title
--   FROM contacts co
--   LEFT JOIN companies comp ON co.company_id = comp.uuid
--   LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
--   WHERE co.company_id = $1
--     AND co.title IS NOT NULL
--     AND co.title != ''
--   ORDER BY co.title ASC
--   LIMIT 25;
--
-- Example Usage for array fields (department):
--   SELECT DISTINCT unnest(co.departments) as value
--   FROM contacts co
--   LEFT JOIN companies comp ON co.company_id = comp.uuid
--   LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
--   WHERE co.company_id = $1
--     AND co.departments IS NOT NULL
--   ORDER BY value ASC
--   LIMIT 25;
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values_by_company() always joins all tables:
--   - Always joins Company, ContactMetadata, and CompanyMetadata (for filter support)
--   - For array fields (department): Uses lateral unnest subquery
--   - For scalar fields: Direct column selection with filters
--   - Column mapping: first_name, last_name, title, seniority, email_status, department, city, state, country
--   - Filters applied via _apply_company_contact_filters() which handles all CompanyContactFilterParams

-- Query for scalar attributes (first_name, last_name, title, seniority, email_status)
-- GET /api/v1/companies/company/{company_uuid}/contacts/title/
-- Note: Always joins all tables to support all filter parameters.
SELECT DISTINCT co.title as value
FROM contacts co
LEFT JOIN companies comp ON co.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE co.company_id = $1
    AND co.title IS NOT NULL
    AND TRIM(co.title) != ''
    -- Add filter conditions here based on CompanyContactFilterParams
    -- Example: AND co.seniority = 'senior'
ORDER BY value ASC
LIMIT 25 OFFSET 0;

-- Query for array attributes (department)
-- GET /api/v1/companies/company/{company_uuid}/contacts/department/
-- Note: Uses lateral unnest subquery in ORM. This simplified version shows the concept.
--       The ORM uses a more complex subquery structure for better performance.
SELECT DISTINCT unnest(co.departments) as value
FROM contacts co
LEFT JOIN companies comp ON co.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE co.company_id = $1
    AND co.departments IS NOT NULL
    AND array_length(co.departments, 1) > 0
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY value ASC
LIMIT 25 OFFSET 0;

-- Query for metadata attributes (city, state, country)
SELECT DISTINCT com.city as value
FROM contacts co
LEFT JOIN companies comp ON co.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE co.company_id = $1
    AND com.city IS NOT NULL
    AND com.city != ''
    -- Add filter conditions here based on CompanyContactFilterParams
ORDER BY value ASC
LIMIT 25 OFFSET 0;

