-- ============================================================================
-- Endpoint: GET /api/v1/companies/city/
-- API Version: v1
-- Description: Return distinct values for /companies/city/ using AttributeListParams.
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
-- GET /api/v1/companies/city/
SELECT DISTINCT com.city as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city IS NOT NULL
    AND com.city != ''
GROUP BY com.city
ORDER BY com.city ASC
LIMIT 25
OFFSET 0;

-- Query 2: With ordering=-count
-- GET /api/v1/companies/city/?ordering=-count
SELECT DISTINCT com.city as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city IS NOT NULL
    AND com.city != ''
GROUP BY com.city
ORDER BY COUNT(*) DESC, com.city ASC
LIMIT 25
OFFSET 0;

-- Query 3: With search parameter
-- GET /api/v1/companies/city/?search=san
SELECT DISTINCT com.city as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city IS NOT NULL
    AND com.city != ''
    AND com.city ILIKE '%san%'
GROUP BY com.city
ORDER BY com.city ASC
LIMIT 25
OFFSET 0;

-- Query 4: With company filters
-- GET /api/v1/companies/city/?employees_min=100&state=California
SELECT DISTINCT com.city as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city IS NOT NULL
    AND com.city != ''
    AND co.employees_count >= 100
    AND com.state ILIKE '%California%'
GROUP BY com.city
ORDER BY com.city ASC
LIMIT 25
OFFSET 0;

-- Query 5: With search and ordering
-- GET /api/v1/companies/city/?search=francisco&ordering=-count
SELECT DISTINCT com.city as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city IS NOT NULL
    AND com.city != ''
    AND com.city ILIKE '%francisco%'
GROUP BY com.city
ORDER BY COUNT(*) DESC, com.city ASC
LIMIT 25
OFFSET 0;

