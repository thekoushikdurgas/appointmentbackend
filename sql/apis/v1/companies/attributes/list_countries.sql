-- ============================================================================
-- Endpoint: GET /api/v1/companies/country/
-- API Version: v1
-- Description: Return distinct values for /companies/country/ using AttributeListParams.
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
-- GET /api/v1/companies/country/
SELECT DISTINCT com.country as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country IS NOT NULL
    AND com.country != ''
GROUP BY com.country
ORDER BY com.country ASC
LIMIT 25
OFFSET 0;

-- Query 2: With ordering=-count
-- GET /api/v1/companies/country/?ordering=-count
SELECT DISTINCT com.country as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country IS NOT NULL
    AND com.country != ''
GROUP BY com.country
ORDER BY COUNT(*) DESC, com.country ASC
LIMIT 25
OFFSET 0;

-- Query 3: With search parameter
-- GET /api/v1/companies/country/?search=united
SELECT DISTINCT com.country as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country IS NOT NULL
    AND com.country != ''
    AND com.country ILIKE '%united%'
GROUP BY com.country
ORDER BY com.country ASC
LIMIT 25
OFFSET 0;

-- Query 4: With company filters
-- GET /api/v1/companies/country/?employees_min=500&annual_revenue_min=50000000
SELECT DISTINCT com.country as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country IS NOT NULL
    AND com.country != ''
    AND co.employees_count >= 500
    AND co.annual_revenue >= 50000000
GROUP BY com.country
ORDER BY com.country ASC
LIMIT 25
OFFSET 0;

-- Query 5: With search and ordering
-- GET /api/v1/companies/country/?search=states&ordering=-count
SELECT DISTINCT com.country as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country IS NOT NULL
    AND com.country != ''
    AND com.country ILIKE '%states%'
GROUP BY com.country
ORDER BY COUNT(*) DESC, com.country ASC
LIMIT 25
OFFSET 0;

