-- ============================================================================
-- Endpoint: GET /api/v1/contacts/company_address/
-- API Version: v1
-- Description: Return distinct values for /contacts/company_address/ using AttributeListParams.
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

-- Query 1: Basic query - Get all distinct company addresses
-- GET /api/v1/contacts/company_address/
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=true
-- GET /api/v1/contacts/company_address/?distinct=true
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/company_address/?distinct=false
SELECT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/company_address/?ordering=value
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/company_address/?ordering=-value
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/company_address/?search=Virginia
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter
-- GET /api/v1/contacts/company_address/?company=Bandura
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.name ILIKE '%Bandura%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/company_address/?limit=50
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/company_address/?offset=25
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/company_address/?limit=10&offset=20
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
ORDER BY co.text_search ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/company_address/?search=Virginia&company=Bandura
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
    AND co.name ILIKE '%Bandura%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, and search
-- GET /api/v1/contacts/company_address/?distinct=true&ordering=-value&search=Virginia
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
ORDER BY co.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/company_address/?distinct=true&limit=50&offset=0&ordering=value&search=Virginia&company=Bandura
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
    AND co.name ILIKE '%Bandura%'
ORDER BY co.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 14: With ContactFilterParams - first_name filter
-- GET /api/v1/contacts/company_address/?first_name=Patrick
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.first_name ILIKE '%Patrick%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - last_name filter
-- GET /api/v1/contacts/company_address/?last_name=McGarry
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.last_name ILIKE '%McGarry%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - title filter
-- GET /api/v1/contacts/company_address/?title=Chief Technology Officer
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.title ILIKE '%Chief Technology Officer%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - seniority filter
-- GET /api/v1/contacts/company_address/?seniority=C suite
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.seniority ILIKE '%C suite%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - email filter
-- GET /api/v1/contacts/company_address/?email=banduracyber.com
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.email ILIKE '%banduracyber.com%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - department filter
-- GET /api/v1/contacts/company_address/?department=C-Suite
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 20: With ContactFilterParams - employees_min filter
-- GET /api/v1/contacts/company_address/?employees_min=20
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.employees_count >= 20
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 21: With ContactFilterParams - employees_max filter
-- GET /api/v1/contacts/company_address/?employees_max=100
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.employees_count <= 100
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 22: With ContactFilterParams - employees range
-- GET /api/v1/contacts/company_address/?employees_min=20&employees_max=100
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 23: With ContactFilterParams - industries filter
-- GET /api/v1/contacts/company_address/?industries=information technology
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 24: With ContactFilterParams - technologies filter
-- GET /api/v1/contacts/company_address/?technologies=Salesforce
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 25: With ContactFilterParams - keywords filter
-- GET /api/v1/contacts/company_address/?keywords=cyber security
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 26: With ContactFilterParams - company_city filter
-- GET /api/v1/contacts/company_address/?company_city=McLean
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND com.city ILIKE '%McLean%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 27: With ContactFilterParams - company_state filter
-- GET /api/v1/contacts/company_address/?company_state=Virginia
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND com.state ILIKE '%Virginia%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 28: With ContactFilterParams - company_country filter
-- GET /api/v1/contacts/company_address/?company_country=United States
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND com.country ILIKE '%United States%'
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 29: With ContactFilterParams - annual_revenue_min filter
-- GET /api/v1/contacts/company_address/?annual_revenue_min=7000000
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.annual_revenue >= 7000000
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 30: With ContactFilterParams - annual_revenue_max filter
-- GET /api/v1/contacts/company_address/?annual_revenue_max=9000000
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.annual_revenue <= 9000000
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 31: With ContactFilterParams - exclude_company_locations filter
-- GET /api/v1/contacts/company_address/?exclude_company_locations=Remote,Virtual
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['Remote', 'Virtual']) AS exclude_val 
        WHERE co.text_search ILIKE '%' || exclude_val || '%'
    )
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 32: With ContactFilterParams - exclude_company_ids filter
-- GET /api/v1/contacts/company_address/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND (c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c'])))
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 33: With ContactFilterParams - created_at_after filter
-- GET /api/v1/contacts/company_address/?created_at_after=2024-01-01T00:00:00
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 34: With ContactFilterParams - created_at_before filter
-- GET /api/v1/contacts/company_address/?created_at_before=2024-12-31T23:59:59
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 35: With ContactFilterParams - updated_at_after filter
-- GET /api/v1/contacts/company_address/?updated_at_after=2024-06-01T00:00:00
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.updated_at >= '2024-06-01 00:00:00'::timestamp
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 36: With ContactFilterParams - updated_at_before filter
-- GET /api/v1/contacts/company_address/?updated_at_before=2024-10-01T00:00:00
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND c.updated_at <= '2024-10-01 00:00:00'::timestamp
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 37: With multiple ContactFilterParams combined
-- GET /api/v1/contacts/company_address/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY co.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 38: With search parameter and ContactFilterParams
-- GET /api/v1/contacts/company_address/?search=Virginia&company=Bandura&distinct=true&ordering=-value
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
    AND co.name ILIKE '%Bandura%'
ORDER BY co.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 39: Complex query with multiple filters
-- GET /api/v1/contacts/company_address/?company=Bandura&seniority=C suite&employees_min=20&company_city=McLean&limit=50
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND com.city ILIKE '%McLean%'
ORDER BY co.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 40: With all attribute and filter parameters
-- GET /api/v1/contacts/company_address/?distinct=true&limit=50&offset=0&ordering=value&search=Virginia&company=Bandura&seniority=C suite&employees_min=20
SELECT DISTINCT co.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.text_search IS NOT NULL
    AND co.text_search != ''
    AND co.text_search ILIKE '%Virginia%'
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
ORDER BY co.text_search ASC
LIMIT 50
OFFSET 0;
