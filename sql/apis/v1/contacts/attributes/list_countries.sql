-- ============================================================================
-- Endpoint: GET /api/v1/contacts/country/
-- API Version: v1
-- Description: Return distinct values for /contacts/country/ using AttributeListParams.
-- ============================================================================
--
-- Parameters:
--   All ContactFilterParams are supported for filtering which contacts to consider.
--   Attribute list specific parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term
--     company (text, optional) - Restrict results to a single company
--
--   All other ContactFilterParams can be applied to filter the base contact set.
--   See list_contacts.sql for complete filter parameter list.
-- ============================================================================

-- Query 1: Basic query - Get all distinct countries
-- GET /api/v1/contacts/country/
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=true
-- GET /api/v1/contacts/country/?distinct=true
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/country/?distinct=false
SELECT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/country/?ordering=value
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/country/?ordering=-value
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/country/?search=United States
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter
-- GET /api/v1/contacts/country/?company=Bandura
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.name ILIKE '%Bandura%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/country/?limit=50
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/country/?offset=25
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/country/?limit=10&offset=20
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
ORDER BY cm.country ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/country/?search=United States&company=Bandura
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
    AND co.name ILIKE '%Bandura%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, and search
-- GET /api/v1/contacts/country/?distinct=true&ordering=-value&search=United States
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
ORDER BY cm.country DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/country/?distinct=true&limit=50&offset=0&ordering=value&search=United States&company=Bandura
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
    AND co.name ILIKE '%Bandura%'
ORDER BY cm.country ASC
LIMIT 50
OFFSET 0;

-- Query 14: With ContactFilterParams - first_name filter
-- GET /api/v1/contacts/country/?first_name=Patrick
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.first_name ILIKE '%Patrick%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - last_name filter
-- GET /api/v1/contacts/country/?last_name=McGarry
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.last_name ILIKE '%McGarry%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - title filter
-- GET /api/v1/contacts/country/?title=Chief Technology Officer
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.title ILIKE '%Chief Technology Officer%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - seniority filter
-- GET /api/v1/contacts/country/?seniority=C suite
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.seniority ILIKE '%C suite%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - email filter
-- GET /api/v1/contacts/country/?email=banduracyber.com
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.email ILIKE '%banduracyber.com%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - department filter
-- GET /api/v1/contacts/country/?department=C-Suite
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 20: With ContactFilterParams - employees_min filter
-- GET /api/v1/contacts/country/?employees_min=20
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.employees_count >= 20
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 21: With ContactFilterParams - employees_max filter
-- GET /api/v1/contacts/country/?employees_max=100
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.employees_count <= 100
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 22: With ContactFilterParams - employees range
-- GET /api/v1/contacts/country/?employees_min=20&employees_max=100
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 23: With ContactFilterParams - industries filter
-- GET /api/v1/contacts/country/?industries=information technology
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 24: With ContactFilterParams - technologies filter
-- GET /api/v1/contacts/country/?technologies=Salesforce
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 25: With ContactFilterParams - keywords filter
-- GET /api/v1/contacts/country/?keywords=cyber security
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 26: With ContactFilterParams - city filter
-- GET /api/v1/contacts/country/?city=Miamisburg
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 27: With ContactFilterParams - state filter
-- GET /api/v1/contacts/country/?state=Ohio
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.state ILIKE '%Ohio%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 28: With ContactFilterParams - annual_revenue_min filter
-- GET /api/v1/contacts/country/?annual_revenue_min=7000000
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.annual_revenue >= 7000000
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 29: With ContactFilterParams - annual_revenue_max filter
-- GET /api/v1/contacts/country/?annual_revenue_max=9000000
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.annual_revenue <= 9000000
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 30: With ContactFilterParams - exclude_company_ids filter
-- GET /api/v1/contacts/country/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND (c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c'])))
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 31: With ContactFilterParams - created_at_after filter
-- GET /api/v1/contacts/country/?created_at_after=2024-01-01T00:00:00
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 32: With ContactFilterParams - created_at_before filter
-- GET /api/v1/contacts/country/?created_at_before=2024-12-31T23:59:59
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 33: With ContactFilterParams - updated_at_after filter
-- GET /api/v1/contacts/country/?updated_at_after=2024-06-01T00:00:00
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.updated_at >= '2024-06-01 00:00:00'::timestamp
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 34: With ContactFilterParams - updated_at_before filter
-- GET /api/v1/contacts/country/?updated_at_before=2024-10-01T00:00:00
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.updated_at <= '2024-10-01 00:00:00'::timestamp
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 35: With multiple ContactFilterParams combined
-- GET /api/v1/contacts/country/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 36: With search parameter and ContactFilterParams
-- GET /api/v1/contacts/country/?search=United States&company=Bandura&distinct=true&ordering=-value
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
    AND co.name ILIKE '%Bandura%'
ORDER BY cm.country DESC
LIMIT 25
OFFSET 0;

-- Query 37: With city and state filters
-- GET /api/v1/contacts/country/?city=Miamisburg&state=Ohio
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.city ILIKE '%Miamisburg%'
    AND cm.state ILIKE '%Ohio%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;

-- Query 38: Complex query with multiple filters
-- GET /api/v1/contacts/country/?company=Bandura&seniority=C suite&employees_min=20&city=Miamisburg&limit=50
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY cm.country ASC
LIMIT 50
OFFSET 0;

-- Query 39: With all attribute and filter parameters
-- GET /api/v1/contacts/country/?distinct=true&limit=50&offset=0&ordering=value&search=United States&company=Bandura&seniority=C suite&employees_min=20
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND cm.country ILIKE '%United States%'
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
ORDER BY cm.country ASC
LIMIT 50
OFFSET 0;

-- Query 40: With mobile_phone filter
-- GET /api/v1/contacts/country/?mobile_phone=937-555
SELECT DISTINCT cm.country as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.country IS NOT NULL
    AND cm.country != ''
    AND cm.country != '_'
    AND c.mobile_phone ILIKE '%937-555%'
ORDER BY cm.country ASC
LIMIT 25
OFFSET 0;
