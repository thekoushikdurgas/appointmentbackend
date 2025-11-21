-- ============================================================================
-- Endpoint: GET /api/v1/contacts/technologies/
-- API Version: v1
-- Description: Return distinct technology values directly from the Company table.
-- Technologies are always returned as individual values (one per technology), 
-- not as comma-separated strings.
-- 
-- This endpoint queries ONLY the Company table and ignores all contact filters.
-- Always uses: separated=true, distinct=true (hardcoded for optimal performance)
-- 
-- Equivalent to: SELECT DISTINCT unnest(technologies) FROM companies WHERE technologies IS NOT NULL
-- ============================================================================
--
-- Parameters:
--   Query Parameters:
--     distinct (boolean, always true) - Always enforced as true (hardcoded for optimal performance)
--     limit (integer, optional) - Maximum number of results. If not provided, returns all matching values (unlimited)
--     offset (integer, default: 0) - Offset for pagination
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term to filter technologies
--     company (text or array, optional) - Filter by exact company name(s). Supports multiple values:
--       - Multiple query params: ?company=Acme&company=Corp
--       - Comma-separated: ?company=Acme,Corp
--       - Mixed: ?company=Acme,Corp&company=Tech
--
--   Note: ContactFilterParams are NOT supported - this endpoint queries only the Company table.
--
-- Response Structure:
--   Returns array of strings: ["Salesforce", "Python", "JavaScript", ...]
--   Technologies are always returned as individual values (one per technology).
--
-- Response Codes:
--   200 OK: Technologies retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying technologies
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Implementation Notes:
--   The ContactRepository.list_technologies_simple() queries ONLY the Company table:
--   - No contact filters are supported (ignores ContactFilterParams)
--   - Always uses unnest(Company.technologies) - separated=true is hardcoded
--   - Always uses DISTINCT - distinct=true is hardcoded
--   - Company filter (if provided) is applied early (before unnest) for better performance
--   - Only uses AttributeListParams: distinct (always true), limit, offset, ordering, search, company
--
-- Example Usage:
--   GET /api/v1/contacts/technologies/
--   GET /api/v1/contacts/technologies/?search=Salesforce&limit=50
--   GET /api/v1/contacts/technologies/?company=Bandura&company=Acme
-- ============================================================================

-- Query 1: Basic query (unnest array into individual values - always uses unnest)
-- GET /api/v1/contacts/technologies/
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=true (always enforced, but shown for clarity)
-- GET /api/v1/contacts/technologies/?distinct=true
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With ordering=value
-- GET /api/v1/contacts/technologies/?ordering=value
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=-value
-- GET /api/v1/contacts/technologies/?ordering=-value
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 5: With search parameter
-- GET /api/v1/contacts/technologies/?search=Salesforce
-- Note: Uses subquery pattern - unnest first, then filter, then distinct, then paginate
SELECT DISTINCT unnested.value
FROM (
    SELECT unnest(technologies) as value
    FROM companies
    WHERE technologies IS NOT NULL
) AS unnested
WHERE unnested.value IS NOT NULL
    AND trim(unnested.value) != ''
    AND unnested.value ILIKE '%Salesforce%'
ORDER BY unnested.value ASC
LIMIT 25
OFFSET 0;

-- Query 6: With company filter (exact match, single company)
-- GET /api/v1/contacts/technologies/?company=Bandura
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
    AND name IN ('Bandura')
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter (exact match, multiple companies)
-- GET /api/v1/contacts/technologies/?company=Bandura&company=Acme
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
    AND name IN ('Bandura', 'Acme')
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/technologies/?limit=50
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/technologies/?offset=25
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/technologies/?limit=10&offset=20
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
ORDER BY value ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/technologies/?search=Salesforce&company=Bandura
-- Note: Company filter is applied early (before unnest) for better performance
SELECT DISTINCT unnested.value
FROM (
    SELECT unnest(technologies) as value
    FROM companies
    WHERE technologies IS NOT NULL
        AND name IN ('Bandura')
) AS unnested
WHERE unnested.value IS NOT NULL
    AND trim(unnested.value) != ''
    AND unnested.value ILIKE '%Salesforce%'
ORDER BY unnested.value ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, search
-- GET /api/v1/contacts/technologies/?distinct=true&ordering=-value&search=Salesforce
-- Note: distinct=true is always enforced (hardcoded)
SELECT DISTINCT unnested.value
FROM (
    SELECT unnest(technologies) as value
    FROM companies
    WHERE technologies IS NOT NULL
) AS unnested
WHERE unnested.value IS NOT NULL
    AND trim(unnested.value) != ''
    AND unnested.value ILIKE '%Salesforce%'
ORDER BY unnested.value DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/technologies/?distinct=true&limit=50&offset=0&ordering=value&search=Salesforce&company=Bandura
-- Note: distinct=true is always enforced (hardcoded), company filter applied early
SELECT DISTINCT unnested.value
FROM (
    SELECT unnest(technologies) as value
    FROM companies
    WHERE technologies IS NOT NULL
        AND name IN ('Bandura')
) AS unnested
WHERE unnested.value IS NOT NULL
    AND trim(unnested.value) != ''
    AND unnested.value ILIKE '%Salesforce%'
ORDER BY unnested.value ASC
LIMIT 50
OFFSET 0;

-- Query 14: With multiple companies (comma-separated format)
-- GET /api/v1/contacts/technologies/?company=Bandura,Acme
SELECT DISTINCT unnest(technologies) as value
FROM companies
WHERE technologies IS NOT NULL
    AND array_length(technologies, 1) > 0
    AND name IN ('Bandura', 'Acme')
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 15: With search, multiple companies, and ordering
-- GET /api/v1/contacts/technologies/?search=Python&company=Bandura&company=Acme&ordering=-value
-- Note: Company filter is applied early (before unnest) for better performance, search after unnest
SELECT DISTINCT unnested.value
FROM (
    SELECT unnest(technologies) as value
    FROM companies
    WHERE technologies IS NOT NULL
        AND name IN ('Bandura', 'Acme')
) AS unnested
WHERE unnested.value IS NOT NULL
    AND trim(unnested.value) != ''
    AND unnested.value ILIKE '%Python%'
ORDER BY unnested.value DESC
LIMIT 25
OFFSET 0;
