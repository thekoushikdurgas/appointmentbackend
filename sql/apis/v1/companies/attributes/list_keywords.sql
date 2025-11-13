-- ============================================================================
-- Endpoint: GET /api/v1/companies/keywords/
-- API Version: v1
-- Description: Return distinct values for /companies/keywords/ using AttributeListParams. The separated parameter (true/false) controls whether array columns are split into unique tokens.
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
-- GET /api/v1/companies/keywords/
SELECT DISTINCT array_to_string(co.keywords, ',') as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
GROUP BY array_to_string(co.keywords, ',')
ORDER BY array_to_string(co.keywords, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 2: With separated=true (unnest array into individual values)
-- GET /api/v1/companies/keywords/?separated=true
SELECT DISTINCT unnest(co.keywords) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
GROUP BY unnest(co.keywords)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With separated=true and ordering=-count
-- GET /api/v1/companies/keywords/?separated=true&ordering=-count
SELECT DISTINCT unnest(co.keywords) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
GROUP BY unnest(co.keywords)
ORDER BY COUNT(*) DESC, value ASC
LIMIT 25
OFFSET 0;

-- Query 4: With separated=true and search
-- GET /api/v1/companies/keywords/?separated=true&search=saas
SELECT DISTINCT unnest(co.keywords) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
GROUP BY unnest(co.keywords)
HAVING unnest(co.keywords) ILIKE '%saas%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With separated=true and company filters
-- GET /api/v1/companies/keywords/?separated=true&employees_min=50&annual_revenue_min=5000000
SELECT DISTINCT unnest(co.keywords) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
    AND co.employees_count >= 50
    AND co.annual_revenue >= 5000000
GROUP BY unnest(co.keywords)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 6: With separated=true, search, and ordering
-- GET /api/v1/companies/keywords/?separated=true&search=cloud&ordering=-count&limit=50
SELECT DISTINCT unnest(co.keywords) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.keywords IS NOT NULL
    AND array_length(co.keywords, 1) > 0
GROUP BY unnest(co.keywords)
HAVING unnest(co.keywords) ILIKE '%cloud%'
ORDER BY COUNT(*) DESC, value ASC
LIMIT 50
OFFSET 0;

