-- ============================================================================
-- Endpoint: GET /api/v1/contacts/contact_address/
-- API Version: v1
-- Description: Return distinct values for /contacts/contact_address/ using AttributeListParams.
-- ============================================================================
--
-- Parameters:
--   Query Parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term
--     company (text, optional) - Restrict results to a single company
--
--   All ContactFilterParams are supported for filtering which contacts to consider.
--   See list_contacts.sql for complete filter parameter list.
--
-- Response Structure:
--   Returns array of strings: ["Address 1", "Address 2", ...]
--
-- Response Codes:
--   200 OK: Contact addresses retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying contact addresses
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/contact_address/
--   GET /api/v1/contacts/contact_address/?search=Ohio&limit=50
--   GET /api/v1/contacts/contact_address/?company=Bandura&city=Miamisburg
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_attribute_values() uses conditional JOINs based on filters:
--   - Always uses Contact table (since selecting Contact.text_search)
--   - Only joins Company/ContactMetadata/CompanyMetadata when filters require them
--   - Uses same conditional JOIN logic as list_contacts (see list_contacts.sql for details)
--   - Column factory: lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.text_search

-- Query 1: Basic query - Get all distinct contact addresses (minimal - only Contact table)
-- GET /api/v1/contacts/contact_address/
-- Note: Always uses Contact table since selecting Contact.text_search. Other joins only added when filters require them.
SELECT DISTINCT c.text_search as value
FROM contacts c
WHERE c.text_search IS NOT NULL
    AND TRIM(c.text_search) != ''
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 2: With company filter (requires Company join)
-- GET /api/v1/contacts/contact_address/?company=TechCorp
-- Note: When company filters are present, Company join is added
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE c.text_search IS NOT NULL
    AND TRIM(c.text_search) != ''
    AND co.name ILIKE '%TechCorp%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/contact_address/?distinct=false
SELECT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/contact_address/?ordering=value
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/contact_address/?ordering=-value
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/contact_address/?search=Ohio
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter
-- GET /api/v1/contacts/contact_address/?company=Bandura
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.name ILIKE '%Bandura%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/contact_address/?limit=50
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/contact_address/?offset=25
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/contact_address/?limit=10&offset=20
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
ORDER BY c.text_search ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/contact_address/?search=Ohio&company=Bandura
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, and search
-- GET /api/v1/contacts/contact_address/?distinct=true&ordering=-value&search=Ohio
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
ORDER BY c.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/contact_address/?distinct=true&limit=50&offset=0&ordering=value&search=Ohio&company=Bandura
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 14: With ContactFilterParams - first_name filter
-- GET /api/v1/contacts/contact_address/?first_name=Patrick
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.first_name ILIKE '%Patrick%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - last_name filter
-- GET /api/v1/contacts/contact_address/?last_name=McGarry
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.last_name ILIKE '%McGarry%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - title filter
-- GET /api/v1/contacts/contact_address/?title=Chief Technology Officer
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.title ILIKE '%Chief Technology Officer%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - seniority filter
-- GET /api/v1/contacts/contact_address/?seniority=C suite
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.seniority ILIKE '%C suite%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - email filter
-- GET /api/v1/contacts/contact_address/?email=banduracyber.com
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.email ILIKE '%banduracyber.com%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - department filter
-- GET /api/v1/contacts/contact_address/?department=C-Suite
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 20: With ContactFilterParams - employees_min filter
-- GET /api/v1/contacts/contact_address/?employees_min=20
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.employees_count >= 20
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 21: With ContactFilterParams - employees_max filter
-- GET /api/v1/contacts/contact_address/?employees_max=100
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.employees_count <= 100
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 22: With ContactFilterParams - employees range
-- GET /api/v1/contacts/contact_address/?employees_min=20&employees_max=100
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 23: With ContactFilterParams - industries filter
-- GET /api/v1/contacts/contact_address/?industries=information technology
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 24: With ContactFilterParams - technologies filter
-- GET /api/v1/contacts/contact_address/?technologies=Salesforce
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 25: With ContactFilterParams - keywords filter
-- GET /api/v1/contacts/contact_address/?keywords=cyber security
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 26: With ContactFilterParams - city filter
-- GET /api/v1/contacts/contact_address/?city=Miamisburg
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 27: With ContactFilterParams - state filter
-- GET /api/v1/contacts/contact_address/?state=Ohio
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND cm.state ILIKE '%Ohio%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 28: With ContactFilterParams - country filter
-- GET /api/v1/contacts/contact_address/?country=United States
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND cm.country ILIKE '%United States%'
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 29: With ContactFilterParams - annual_revenue_min filter
-- GET /api/v1/contacts/contact_address/?annual_revenue_min=7000000
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.annual_revenue >= 7000000
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 30: With ContactFilterParams - annual_revenue_max filter
-- GET /api/v1/contacts/contact_address/?annual_revenue_max=9000000
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.annual_revenue <= 9000000
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 31: With ContactFilterParams - exclude_contact_locations filter
-- GET /api/v1/contacts/contact_address/?exclude_contact_locations=Remote,Virtual
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['Remote', 'Virtual']) AS exclude_val 
        WHERE c.text_search ILIKE '%' || exclude_val || '%'
    )
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 32: With ContactFilterParams - exclude_company_ids filter
-- GET /api/v1/contacts/contact_address/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND (c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c'])))
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 33: With ContactFilterParams - created_at_after filter
-- GET /api/v1/contacts/contact_address/?created_at_after=2024-01-01T00:00:00
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 34: With ContactFilterParams - created_at_before filter
-- GET /api/v1/contacts/contact_address/?created_at_before=2024-12-31T23:59:59
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 35: With ContactFilterParams - updated_at_after filter
-- GET /api/v1/contacts/contact_address/?updated_at_after=2024-06-01T00:00:00
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.updated_at >= '2024-06-01 00:00:00'::timestamp
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 36: With ContactFilterParams - updated_at_before filter
-- GET /api/v1/contacts/contact_address/?updated_at_before=2024-10-01T00:00:00
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.updated_at <= '2024-10-01 00:00:00'::timestamp
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 37: With multiple ContactFilterParams combined
-- GET /api/v1/contacts/contact_address/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.text_search ASC
LIMIT 25
OFFSET 0;

-- Query 38: With search parameter and ContactFilterParams
-- GET /api/v1/contacts/contact_address/?search=Ohio&company=Bandura&distinct=true&ordering=-value
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.text_search DESC
LIMIT 25
OFFSET 0;

-- Query 39: Complex query with multiple filters
-- GET /api/v1/contacts/contact_address/?company=Bandura&seniority=C suite&employees_min=20&city=Miamisburg&limit=50
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY c.text_search ASC
LIMIT 50
OFFSET 0;

-- Query 40: With all attribute and filter parameters
-- GET /api/v1/contacts/contact_address/?distinct=true&limit=50&offset=0&ordering=value&search=Ohio&company=Bandura&seniority=C suite&employees_min=20
SELECT DISTINCT c.text_search as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.text_search IS NOT NULL
    AND c.text_search != ''
    AND c.text_search ILIKE '%Ohio%'
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
ORDER BY c.text_search ASC
LIMIT 50
OFFSET 0;
