-- ============================================================================
-- Endpoint: GET /api/v1/companies/state/
-- API Version: v1
-- Description: Return distinct values for /companies/state/ using AttributeListParams.
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

-- ORM Implementation Notes:
--   The CompanyRepository.list_attribute_values() always joins CompanyMetadata:
--   - Always uses LEFT JOIN to CompanyMetadata (unlike list_companies which uses conditional JOINs)
--   - This allows applying all CompanyFilterParams including metadata filters
--   - Column factory: lambda Company, CompanyMetadata: CompanyMetadata.state
--   - Filters applied via apply_filters() which handles both Company and CompanyMetadata filters
--   - Note: The COUNT(*) in GROUP BY queries is for ordering by count only, not returned by ORM

-- Query 1: Basic query with distinct=true
-- GET /api/v1/companies/state/
-- Note: Always joins CompanyMetadata to support all filter parameters. COUNT(*) is for ordering only.
SELECT DISTINCT com.state as value
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state IS NOT NULL
    AND TRIM(com.state) != ''
ORDER BY com.state ASC
LIMIT 25
OFFSET 0;

-- Query 2: With ordering=-count
-- GET /api/v1/companies/state/?ordering=-count
SELECT DISTINCT com.state as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state IS NOT NULL
    AND com.state != ''
GROUP BY com.state
ORDER BY COUNT(*) DESC, com.state ASC
LIMIT 25
OFFSET 0;

-- Query 3: With search parameter
-- GET /api/v1/companies/state/?search=california
SELECT DISTINCT com.state as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state IS NOT NULL
    AND com.state != ''
    AND com.state ILIKE '%california%'
GROUP BY com.state
ORDER BY com.state ASC
LIMIT 25
OFFSET 0;

-- Query 4: With company filters
-- GET /api/v1/companies/state/?employees_min=100&industries=Technology
SELECT DISTINCT com.state as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state IS NOT NULL
    AND com.state != ''
    AND co.employees_count >= 100
    AND array_to_string(co.industries, ',') ILIKE '%Technology%'
GROUP BY com.state
ORDER BY com.state ASC
LIMIT 25
OFFSET 0;

-- Query 5: With search and ordering
-- GET /api/v1/companies/state/?search=york&ordering=-count
SELECT DISTINCT com.state as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state IS NOT NULL
    AND com.state != ''
    AND com.state ILIKE '%york%'
GROUP BY com.state
ORDER BY COUNT(*) DESC, com.state ASC
LIMIT 25
OFFSET 0;

