-- ============================================================================
-- Endpoint: GET /api/v1/contacts/department/
-- API Version: v1
-- Description: Return distinct values for /contacts/department/ using AttributeListParams. The separated parameter (true/false) controls whether array columns are split into unique tokens.
-- ============================================================================
--
-- Parameters:
--   Query Parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term
--     separated (boolean, default: true) - Split array columns into unique tokens
--
--   All ContactFilterParams are supported for filtering which contacts to consider.
--   See list_contacts.sql for complete filter parameter list.
--
-- Response Structure:
--   Returns array of strings: ["Engineering", "Sales", ...] when separated=true
--   Returns array of comma-separated strings: ["Engineering,Sales", ...] when separated=false
--
-- Response Codes:
--   200 OK: Departments retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying departments
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/department/
--   GET /api/v1/contacts/department/?search=Engineering&separated=true
--   GET /api/v1/contacts/department/?company=Bandura&separated=false
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_departments_simple() uses conditional JOINs based on filters:
--   - When separated=true and PostgreSQL: Uses unnest(Contact.departments) with conditional JOINs
--   - When separated=false: Uses array_to_string(Contact.departments, ',') with conditional JOINs
--   - Only joins Company/ContactMetadata/CompanyMetadata when filters require them
--   - Uses same conditional JOIN logic as list_contacts (see list_contacts.sql for details)

-- Query 1: Basic query with separated=true (unnest array into individual values, minimal - no joins)
-- GET /api/v1/contacts/department/
-- Note: When no filters require joins, queries only Contact table. Joins added conditionally based on filters.
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 2: With company filter (requires Company join)
-- GET /api/v1/contacts/department/?separated=true&company=TechCorp
-- Note: When company filters are present, Company join is added
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND co.name ILIKE '%TechCorp%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With separated=false (comma-separated strings)
-- GET /api/v1/contacts/department/?separated=false
SELECT DISTINCT array_to_string(c.departments, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY array_to_string(c.departments, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 4: With distinct=true and separated=true
-- GET /api/v1/contacts/department/?distinct=true&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With distinct=false and separated=true
-- GET /api/v1/contacts/department/?distinct=false&separated=true
SELECT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 6: With ordering=value and separated=true
-- GET /api/v1/contacts/department/?ordering=value&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 7: With ordering=-value and separated=true
-- GET /api/v1/contacts/department/?ordering=-value&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 8: With search parameter and separated=true
-- GET /api/v1/contacts/department/?search=Engineering&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(c.departments) AS department 
        WHERE department ILIKE '%Engineering%'
    )
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 9: With search parameter and separated=false
-- GET /api/v1/contacts/department/?search=Engineering&separated=false
SELECT DISTINCT array_to_string(c.departments, ',') as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND array_to_string(c.departments, ',') ILIKE '%Engineering%'
ORDER BY array_to_string(c.departments, ',') ASC
LIMIT 25
OFFSET 0;

-- Query 10: With company filter and separated=true
-- GET /api/v1/contacts/department/?company=Bandura&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND co.name ILIKE '%Bandura%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 11: With limit parameter and separated=true
-- GET /api/v1/contacts/department/?limit=50&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 12: With offset parameter and separated=true
-- GET /api/v1/contacts/department/?offset=25&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 25
OFFSET 25;

-- Query 13: With limit and offset and separated=true
-- GET /api/v1/contacts/department/?limit=10&offset=20&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
ORDER BY value ASC
LIMIT 10
OFFSET 20;

-- Query 14: With search and company and separated=true
-- GET /api/v1/contacts/department/?search=Engineering&company=Bandura&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(c.departments) AS department 
        WHERE department ILIKE '%Engineering%'
    )
    AND co.name ILIKE '%Bandura%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - first_name filter and separated=true
-- GET /api/v1/contacts/department/?first_name=Patrick&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND c.first_name ILIKE '%Patrick%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - seniority filter and separated=true
-- GET /api/v1/contacts/department/?seniority=C suite&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND c.seniority ILIKE '%C suite%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - title filter and separated=true
-- GET /api/v1/contacts/department/?title=Chief Technology Officer&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND c.title ILIKE '%Chief Technology Officer%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 18: With ContactFilterParams - employees_min filter and separated=true
-- GET /api/v1/contacts/department/?employees_min=20&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND co.employees_count >= 20
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 19: With ContactFilterParams - multiple filters combined and separated=true
-- GET /api/v1/contacts/department/?company=Bandura&seniority=C suite&employees_min=20&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 20: Complex query with all parameters and separated=true
-- GET /api/v1/contacts/department/?distinct=true&limit=50&offset=0&ordering=value&search=Engineering&company=Bandura&seniority=C suite&separated=true
SELECT DISTINCT unnest(c.departments) as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.departments IS NOT NULL
    AND array_length(c.departments, 1) > 0
    AND EXISTS (
        SELECT 1 FROM unnest(c.departments) AS department 
        WHERE department ILIKE '%Engineering%'
    )
    AND co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
ORDER BY value ASC
LIMIT 50
OFFSET 0;

