-- ============================================================================
-- Endpoint: GET /api/v1/companies/industry/
-- API Version: v1
-- Description: Return distinct values for /companies/industry/ using AttributeListParams. The separated parameter (true/false) controls whether array columns are split into unique tokens.
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
--     separated (boolean, default: false) - Split array columns into unique tokens
--
--   All other CompanyFilterParams can be applied to filter the base company set.
--   See list_companies.sql for complete filter parameter list.
-- ============================================================================

-- Query 1: Basic query with separated=false (comma-separated strings)
-- GET /api/v1/companies/industry/
SELECT DISTINCT array_to_string(co.industries, ',') as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY array_to_string(co.industries, ',')
ORDER BY array_to_string(co.industries, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 2: With separated=true (unnest array into individual values)
-- GET /api/v1/companies/industry/?separated=true
SELECT DISTINCT unnest(co.industries) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY unnest(co.industries)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With separated=true and ordering=-count
-- GET /api/v1/companies/industry/?separated=true&ordering=-count
SELECT DISTINCT unnest(co.industries) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY unnest(co.industries)
ORDER BY COUNT(*) DESC, value ASC
LIMIT 25
OFFSET 0;

-- Query 4: With separated=true and search
-- GET /api/v1/companies/industry/?separated=true&search=technology
SELECT DISTINCT unnest(co.industries) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY unnest(co.industries)
HAVING unnest(co.industries) ILIKE '%technology%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With separated=false and distinct=true
-- GET /api/v1/companies/industry/?separated=false&distinct=true
SELECT DISTINCT array_to_string(co.industries, ',') as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY array_to_string(co.industries, ',')
ORDER BY array_to_string(co.industries, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 6: With separated=true, distinct=false
-- GET /api/v1/companies/industry/?separated=true&distinct=false
SELECT unnest(co.industries) as value
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 7: With separated=true and company filters
-- GET /api/v1/companies/industry/?separated=true&employees_min=100&city=San Francisco
SELECT DISTINCT unnest(co.industries) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
    AND co.employees_count >= 100
    AND com.city ILIKE '%San Francisco%'
GROUP BY unnest(co.industries)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 8: With separated=true, search, and ordering
-- GET /api/v1/companies/industry/?separated=true&search=tech&ordering=-count&limit=50
SELECT DISTINCT unnest(co.industries) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NOT NULL
    AND array_length(co.industries, 1) > 0
GROUP BY unnest(co.industries)
HAVING unnest(co.industries) ILIKE '%tech%'
ORDER BY COUNT(*) DESC, value ASC
LIMIT 50
OFFSET 0;

