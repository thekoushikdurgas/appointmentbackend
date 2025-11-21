-- ============================================================================
-- Endpoint: GET /api/v1/companies/technologies/
-- API Version: v1
-- Description: Return distinct values for /companies/technologies/ using AttributeListParams. The separated parameter (true/false) controls whether array columns are split into unique tokens.
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

-- ORM Implementation Notes:
--   The CompanyRepository.list_attribute_values() with array_mode uses optimized PostgreSQL unnesting:
--   - When separated=true and PostgreSQL: Uses _list_array_attribute_values() with lateral unnesting
--   - When separated=false: Uses array_to_string() with regular query
--   - Always joins CompanyMetadata (unlike list_companies which uses conditional JOINs)
--   - Column factory: lambda Company, CompanyMetadata: Company.technologies
--   - Note: COUNT(*) in GROUP BY queries is for ordering by count only, not returned by ORM

-- Query 1: Basic query with separated=false (comma-separated strings)
-- GET /api/v1/companies/technologies/
-- Note: Always joins CompanyMetadata to support all filter parameters. COUNT(*) is for ordering only.
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 2: With separated=true (unnest array into individual values)
-- GET /api/v1/companies/technologies/?separated=true
SELECT DISTINCT unnest(co.technologies) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
GROUP BY unnest(co.technologies)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With separated=true and ordering=-count
-- GET /api/v1/companies/technologies/?separated=true&ordering=-count
SELECT DISTINCT unnest(co.technologies) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
GROUP BY unnest(co.technologies)
ORDER BY COUNT(*) DESC, value ASC
LIMIT 25
OFFSET 0;

-- Query 4: With separated=true and search
-- GET /api/v1/companies/technologies/?separated=true&search=python
SELECT DISTINCT unnest(co.technologies) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
GROUP BY unnest(co.technologies)
HAVING unnest(co.technologies) ILIKE '%python%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With separated=true and company filters
-- GET /api/v1/companies/technologies/?separated=true&industries=Technology&employees_min=100
SELECT DISTINCT unnest(co.technologies) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(co.industries, ',') ILIKE '%Technology%'
    AND co.employees_count >= 100
GROUP BY unnest(co.technologies)
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 6: With separated=true, search, and ordering
-- GET /api/v1/companies/technologies/?separated=true&search=aws&ordering=-count&limit=50
SELECT DISTINCT unnest(co.technologies) as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
GROUP BY unnest(co.technologies)
HAVING unnest(co.technologies) ILIKE '%aws%'
ORDER BY COUNT(*) DESC, value ASC
LIMIT 50
OFFSET 0;

