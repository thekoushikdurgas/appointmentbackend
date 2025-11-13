-- ============================================================================
-- Endpoint: GET /api/v1/companies/address/
-- API Version: v1
-- Description: Return distinct values for /companies/address/ using AttributeListParams. Returns Company.text_search covering address fields.
-- ============================================================================
--
-- Parameters:
--   All CompanyFilterParams are supported for filtering which companies to consider.
--   Attribute list specific parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value', '-value', 'count', '-count')
--     search (text, optional) - Optional case-insensitive search term
--
--   All other CompanyFilterParams can be applied to filter the base company set.
--   See list_companies.sql for complete filter parameter list.
-- ============================================================================

-- Query 1: Basic query with distinct=true
-- GET /api/v1/companies/address/
SELECT DISTINCT co.text_search as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
GROUP BY co.text_search
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 2: With ordering=-count
-- GET /api/v1/companies/address/?ordering=-count
SELECT DISTINCT co.text_search as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
GROUP BY co.text_search
ORDER BY COUNT(*) DESC, co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 3: With search parameter
-- GET /api/v1/companies/address/?search=main
SELECT DISTINCT co.text_search as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%main%'
GROUP BY co.text_search
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 4: With company filters
-- GET /api/v1/companies/address/?employees_min=100&city=San Francisco
SELECT DISTINCT co.text_search as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.employees_count >= 100
    AND com.city ILIKE '%San Francisco%'
GROUP BY co.text_search
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 5: With search and ordering
-- GET /api/v1/companies/address/?search=california&ordering=-count
SELECT DISTINCT co.text_search as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%california%'
GROUP BY co.text_search
ORDER BY COUNT(*) DESC, co.text_search ASC
LIMIT 25
OFFSET 0;

