-- ============================================================================
-- Endpoint: GET /api/v1/contacts/technologies/
-- API Version: v1
-- Description: Return distinct values for /contacts/technologies/ using AttributeListParams. The separated parameter controls whether array columns are split into unique tokens.
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
--     separated (boolean, default: false) - Split array columns into unique tokens
--
--   All other ContactFilterParams can be applied to filter the base contact set.
--   See list_contacts.sql for complete filter parameter list.
-- ============================================================================

-- Query 1: Basic query with separated=false (comma-separated strings)
-- GET /api/v1/contacts/technologies/
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 2: With separated=true (unnest array into individual values)
-- GET /api/v1/contacts/technologies/?separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With separated=false (explicit)
-- GET /api/v1/contacts/technologies/?separated=false
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 4: With distinct=true and separated=true
-- GET /api/v1/contacts/technologies/?distinct=true&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With distinct=false and separated=true
-- GET /api/v1/contacts/technologies/?distinct=false&separated=true
SELECT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 6: With ordering=value and separated=true
-- GET /api/v1/contacts/technologies/?ordering=value&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 7: With ordering=-value and separated=true
-- GET /api/v1/contacts/technologies/?ordering=-value&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 8: With search parameter and separated=true
-- GET /api/v1/contacts/technologies/?search=Salesforce&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 9: With search parameter and separated=false
-- GET /api/v1/contacts/technologies/?search=Salesforce&separated=false
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 10: With company filter and separated=true
-- GET /api/v1/contacts/technologies/?company=Bandura&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.name ILIKE '%Bandura%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 11: With limit parameter and separated=true
-- GET /api/v1/contacts/technologies/?limit=50&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 12: With offset parameter and separated=true
-- GET /api/v1/contacts/technologies/?offset=25&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 25;

-- Query 13: With limit and offset and separated=true
-- GET /api/v1/contacts/technologies/?limit=10&offset=20&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
ORDER BY value ASC
LIMIT 10
OFFSET 20;

-- Query 14: With search and company and separated=true
-- GET /api/v1/contacts/technologies/?search=Salesforce&company=Bandura&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
    AND co.name ILIKE '%Bandura%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 15: With distinct, ordering, search, and separated=true
-- GET /api/v1/contacts/technologies/?distinct=true&ordering=-value&search=Salesforce&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 16: With all attribute parameters and separated=true
-- GET /api/v1/contacts/technologies/?distinct=true&limit=50&offset=0&ordering=value&search=Salesforce&company=Bandura&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
    AND co.name ILIKE '%Bandura%'
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 17: With ContactFilterParams - first_name filter and separated=true
-- GET /api/v1/contacts/technologies/?first_name=Patrick&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.first_name ILIKE '%Patrick%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - last_name filter and separated=true
-- GET /api/v1/contacts/technologies/?last_name=McGarry&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.last_name ILIKE '%McGarry%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - seniority filter and separated=true
-- GET /api/v1/contacts/technologies/?seniority=C suite&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.seniority ILIKE '%C suite%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 20: With ContactFilterParams - email filter and separated=true
-- GET /api/v1/contacts/technologies/?email=banduracyber.com&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.email ILIKE '%banduracyber.com%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 21: With ContactFilterParams - department filter and separated=true
-- GET /api/v1/contacts/technologies/?department=C-Suite&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 22: With ContactFilterParams - employees_min filter and separated=true
-- GET /api/v1/contacts/technologies/?employees_min=20&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.employees_count >= 20
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 23: With ContactFilterParams - employees_max filter and separated=true
-- GET /api/v1/contacts/technologies/?employees_max=100&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.employees_count <= 100
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 24: With ContactFilterParams - employees range and separated=true
-- GET /api/v1/contacts/technologies/?employees_min=20&employees_max=100&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 25: With ContactFilterParams - industries filter and separated=true
-- GET /api/v1/contacts/technologies/?industries=information technology&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 26: With ContactFilterParams - keywords filter and separated=true
-- GET /api/v1/contacts/technologies/?keywords=cyber security&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 27: With ContactFilterParams - city filter and separated=true
-- GET /api/v1/contacts/technologies/?city=Miamisburg&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 28: With ContactFilterParams - state filter and separated=true
-- GET /api/v1/contacts/technologies/?state=Ohio&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND cm.state ILIKE '%Ohio%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 29: With ContactFilterParams - country filter and separated=true
-- GET /api/v1/contacts/technologies/?country=United States&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND cm.country ILIKE '%United States%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 30: With ContactFilterParams - annual_revenue_min filter and separated=true
-- GET /api/v1/contacts/technologies/?annual_revenue_min=7000000&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.annual_revenue >= 7000000
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 31: With ContactFilterParams - annual_revenue_max filter and separated=true
-- GET /api/v1/contacts/technologies/?annual_revenue_max=9000000&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.annual_revenue <= 9000000
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 32: With ContactFilterParams - exclude_technologies filter and separated=true
-- GET /api/v1/contacts/technologies/?exclude_technologies=Legacy,Old&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['Legacy', 'Old']) AS exclude_val 
        WHERE array_to_string(co.technologies, ',') ILIKE '%' || exclude_val || '%'
    )
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 33: With ContactFilterParams - exclude_company_ids filter and separated=true
-- GET /api/v1/contacts/technologies/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND (c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c'])))
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 34: With ContactFilterParams - created_at_after filter and separated=true
-- GET /api/v1/contacts/technologies/?created_at_after=2024-01-01T00:00:00&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 35: With ContactFilterParams - created_at_before filter and separated=true
-- GET /api/v1/contacts/technologies/?created_at_before=2024-12-31T23:59:59&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 36: With multiple ContactFilterParams combined and separated=true
-- GET /api/v1/contacts/technologies/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 37: With search parameter and ContactFilterParams and separated=true
-- GET /api/v1/contacts/technologies/?search=Salesforce&company=Bandura&distinct=true&ordering=-value&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
    AND co.name ILIKE '%Bandura%'
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 38: With separated=false and ContactFilterParams
-- GET /api/v1/contacts/technologies/?company=Bandura&separated=false
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND co.name ILIKE '%Bandura%'
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 39: With separated=false, search, and company
-- GET /api/v1/contacts/technologies/?search=Salesforce&company=Bandura&separated=false
SELECT DISTINCT array_to_string(co.technologies, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
    AND co.name ILIKE '%Bandura%'
ORDER BY array_to_string(co.technologies, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 40: Complex query with all parameters and separated=true
-- GET /api/v1/contacts/technologies/?distinct=true&limit=50&offset=0&ordering=value&search=Salesforce&company=Bandura&seniority=C suite&employees_min=20&separated=true
SELECT DISTINCT unnest(co.technologies) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.technologies IS NOT NULL
    AND array_length(co.technologies, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(co.technologies) AS technology 
        WHERE technology ILIKE '%Salesforce%'
    )
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
ORDER BY value ASC
LIMIT 50
OFFSET 0;
