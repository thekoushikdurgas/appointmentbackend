-- ============================================================================
-- Endpoint: GET /api/v1/contacts/title/
-- API Version: v1
-- Description: Return distinct values for /contacts/title/ using AttributeListParams.
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
--   Returns array of strings: ["Chief Technology Officer", "Software Engineer", ...]
--
-- Response Codes:
--   200 OK: Titles retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying titles
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/title/
--   GET /api/v1/contacts/title/?search=Chief&limit=50
--   GET /api/v1/contacts/title/?company=Bandura&seniority=C suite
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactsService.list_titles_paginated() uses list_attribute_values() with conditional JOINs:
--   - Applies alphanumeric filter at SQL level (apply_title_alphanumeric_filter=True)
--   - Filters out titles that don't contain at least one alphanumeric character
--   - Only joins Company/ContactMetadata/CompanyMetadata when filters require them
--   - Uses same conditional JOIN logic as list_contacts (see list_contacts.sql for details)
--   - Column factory: lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.title

-- Query 1: Basic query - Get all distinct titles (minimal - no joins)
-- GET /api/v1/contacts/title/
-- Note: When no filters require joins, queries only Contact table. Alphanumeric filter applied at SQL level.
--       Joins added conditionally based on filters.
SELECT DISTINCT c.title as value
FROM contacts c
WHERE c.title IS NOT NULL
    AND TRIM(c.title) != ''
    AND EXISTS (SELECT 1 FROM regexp_split_to_table(c.title, '') AS char WHERE char ~ '[[:alnum:]]')
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 2: With company filter (requires Company join)
-- GET /api/v1/contacts/title/?company=TechCorp
-- Note: When company filters are present, Company join is added. Alphanumeric filter still applied.
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE c.title IS NOT NULL
    AND TRIM(c.title) != ''
    AND EXISTS (SELECT 1 FROM regexp_split_to_table(c.title, '') AS char WHERE char ~ '[[:alnum:]]')
    AND co.name ILIKE '%TechCorp%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/title/?distinct=false
SELECT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/title/?ordering=value
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/title/?ordering=-value
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/title/?search=Chief
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%Chief%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter
-- GET /api/v1/contacts/title/?company=Bandura
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.name ILIKE '%Bandura%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/title/?limit=50
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/title/?offset=25
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/title/?limit=10&offset=20
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
ORDER BY c.title ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/title/?search=Engineer&company=Bandura
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%Engineer%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, and search
-- GET /api/v1/contacts/title/?distinct=true&ordering=-value&search=Chief
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%Chief%'
ORDER BY c.title DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/title/?distinct=true&limit=50&offset=0&ordering=value&search=Technology&company=Bandura
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%Technology%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.title ASC
LIMIT 50
OFFSET 0;

-- Query 14: With ContactFilterParams - first_name filter
-- GET /api/v1/contacts/title/?first_name=Patrick
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.first_name ILIKE '%Patrick%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - last_name filter
-- GET /api/v1/contacts/title/?last_name=McGarry
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.last_name ILIKE '%McGarry%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - seniority filter
-- GET /api/v1/contacts/title/?seniority=C suite
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.seniority ILIKE '%C suite%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - email filter
-- GET /api/v1/contacts/title/?email=banduracyber.com
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.email ILIKE '%banduracyber.com%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - department filter
-- GET /api/v1/contacts/title/?department=C-Suite
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - employees_min filter
-- GET /api/v1/contacts/title/?employees_min=20
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.employees_count >= 20
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 20: With ContactFilterParams - employees_max filter
-- GET /api/v1/contacts/title/?employees_max=100
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.employees_count <= 100
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 21: With ContactFilterParams - employees range
-- GET /api/v1/contacts/title/?employees_min=20&employees_max=100
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 22: With ContactFilterParams - industries filter
-- GET /api/v1/contacts/title/?industries=information technology
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 23: With ContactFilterParams - technologies filter
-- GET /api/v1/contacts/title/?technologies=Salesforce
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 24: With ContactFilterParams - keywords filter
-- GET /api/v1/contacts/title/?keywords=cyber security
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 25: With ContactFilterParams - city filter
-- GET /api/v1/contacts/title/?city=Miamisburg
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND cm.city ILIKE '%Miamisburg%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 26: With ContactFilterParams - state filter
-- GET /api/v1/contacts/title/?state=Ohio
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND cm.state ILIKE '%Ohio%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 27: With ContactFilterParams - country filter
-- GET /api/v1/contacts/title/?country=United States
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND cm.country ILIKE '%United States%'
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 28: With ContactFilterParams - annual_revenue_min filter
-- GET /api/v1/contacts/title/?annual_revenue_min=7000000
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.annual_revenue >= 7000000
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 29: With ContactFilterParams - annual_revenue_max filter
-- GET /api/v1/contacts/title/?annual_revenue_max=9000000
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.annual_revenue <= 9000000
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 30: With ContactFilterParams - exclude_titles filter
-- GET /api/v1/contacts/title/?exclude_titles=Intern,Junior
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['Intern', 'Junior']) AS exclude_val 
        WHERE LOWER(c.title) = LOWER(exclude_val)
    )
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 31: With ContactFilterParams - exclude_company_ids filter
-- GET /api/v1/contacts/title/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND (c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c'])))
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 32: With ContactFilterParams - created_at_after filter
-- GET /api/v1/contacts/title/?created_at_after=2024-01-01T00:00:00
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 33: With ContactFilterParams - created_at_before filter
-- GET /api/v1/contacts/title/?created_at_before=2024-12-31T23:59:59
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 34: With multiple ContactFilterParams combined
-- GET /api/v1/contacts/title/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.title ASC
LIMIT 25
OFFSET 0;

-- Query 35: With search parameter and ContactFilterParams
-- GET /api/v1/contacts/title/?search=Technology&company=Bandura&distinct=true&ordering=-value
SELECT DISTINCT c.title as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.title IS NOT NULL
    AND c.title != ''
    AND c.title ILIKE '%Technology%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.title DESC
LIMIT 25
OFFSET 0;
