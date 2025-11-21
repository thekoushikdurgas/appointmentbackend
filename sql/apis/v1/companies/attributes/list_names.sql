-- ============================================================================
-- Endpoint: GET /api/v1/companies/name/
-- API Version: v1
-- Description: Return distinct values for /companies/name/ using AttributeListParams.
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
--   - Column factory: lambda Company, CompanyMetadata: Company.name
--   - Filters applied via apply_filters() which handles both Company and CompanyMetadata filters
--   - Note: The COUNT(*) in GROUP BY queries is for ordering by count, not returned by ORM

-- Query 1: Basic query with distinct=true
-- GET /api/v1/companies/name/
-- Note: Always joins CompanyMetadata to support all filter parameters. COUNT(*) is for ordering only.
SELECT DISTINCT co.name as value
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=false
-- GET /api/v1/companies/name/?distinct=false
SELECT co.name as value
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 3: With ordering=value (ascending)
-- GET /api/v1/companies/name/?ordering=value
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
GROUP BY co.name
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=-value (descending)
-- GET /api/v1/companies/name/?ordering=-value
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
GROUP BY co.name
ORDER BY co.name DESC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=count (ascending)
-- GET /api/v1/companies/name/?ordering=count
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
GROUP BY co.name
ORDER BY COUNT(*) ASC, co.name ASC
LIMIT 25
OFFSET 0;

-- Query 6: With ordering=-count (descending)
-- GET /api/v1/companies/name/?ordering=-count
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
GROUP BY co.name
ORDER BY COUNT(*) DESC, co.name ASC
LIMIT 25
OFFSET 0;

-- Query 7: With search parameter
-- GET /api/v1/companies/name/?search=acme
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
    AND co.name ILIKE '%acme%'
GROUP BY co.name
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit and offset
-- GET /api/v1/companies/name/?limit=50&offset=25
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
GROUP BY co.name
ORDER BY co.name ASC
LIMIT 50
OFFSET 25;

-- Query 9: With search and ordering
-- GET /api/v1/companies/name/?search=tech&ordering=-count
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
    AND co.name ILIKE '%tech%'
GROUP BY co.name
ORDER BY COUNT(*) DESC, co.name ASC
LIMIT 25
OFFSET 0;

-- Query 10: With company filter parameters
-- GET /api/v1/companies/name/?employees_min=100&industries=Technology
SELECT DISTINCT co.name as value, COUNT(*) as count
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name IS NOT NULL
    AND co.name != ''
    AND co.employees_count >= 100
    AND array_to_string(co.industries, ',') ILIKE '%Technology%'
GROUP BY co.name
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

