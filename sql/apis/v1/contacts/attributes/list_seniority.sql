-- ============================================================================
-- Endpoint: GET /api/v1/contacts/seniority/
-- API Version: v1
-- Description: Return distinct values for /contacts/seniority/ using AttributeListParams.
-- Filters out placeholder value "_" (default value in database).
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
--   Returns array of strings: ["C suite", "Senior", "Mid-level", ...]
--   Placeholder value "_" is excluded from results.
--
-- Response Codes:
--   200 OK: Seniority levels retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying seniority levels
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/seniority/
--   GET /api/v1/contacts/seniority/?search=Senior&limit=50
--   GET /api/v1/contacts/seniority/?company=Bandura&title=Chief
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactsService.list_titles_paginated() uses list_attribute_values() with conditional JOINs:
--   - Filters out placeholder "_" values (default value in database)
--   - Only joins Company/ContactMetadata/CompanyMetadata when filters require them
--   - Uses same conditional JOIN logic as list_contacts (see list_contacts.sql for details)
--   - Column factory: lambda Contact, Company, ContactMetadata, CompanyMetadata: Contact.seniority

-- Query 1: Basic query - Get all distinct seniority values (minimal - no joins)
-- GET /api/v1/contacts/seniority/
-- Note: When no filters require joins, queries only Contact table. Joins added conditionally based on filters.
SELECT DISTINCT c.seniority as value
FROM contacts c
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=true
-- GET /api/v1/contacts/seniority/?distinct=true
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/seniority/?distinct=false
SELECT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/seniority/?ordering=value
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/seniority/?ordering=-value
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/seniority/?search=Senior
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.seniority ILIKE '%Senior%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 7: With company filter
-- GET /api/v1/contacts/seniority/?company=Bandura
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 8: With limit parameter
-- GET /api/v1/contacts/seniority/?limit=50
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 50
OFFSET 0;

-- Query 9: With offset parameter
-- GET /api/v1/contacts/seniority/?offset=25
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 25;

-- Query 10: With limit and offset
-- GET /api/v1/contacts/seniority/?limit=10&offset=20
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
ORDER BY c.seniority ASC
LIMIT 10
OFFSET 20;

-- Query 11: With search and company
-- GET /api/v1/contacts/seniority/?search=Senior&company=Bandura
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.seniority ILIKE '%Senior%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 12: With distinct, ordering, and search
-- GET /api/v1/contacts/seniority/?distinct=true&ordering=-value&search=Senior
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.seniority ILIKE '%Senior%'
ORDER BY c.seniority DESC
LIMIT 25
OFFSET 0;

-- Query 13: With all attribute parameters
-- GET /api/v1/contacts/seniority/?distinct=true&limit=50&offset=0&ordering=value&search=Senior&company=Bandura
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.seniority ILIKE '%Senior%'
    AND co.name ILIKE '%Bandura%'
ORDER BY c.seniority ASC
LIMIT 50
OFFSET 0;

-- Query 14: With ContactFilterParams - first_name filter
-- GET /api/v1/contacts/seniority/?first_name=Patrick
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.first_name ILIKE '%Patrick%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 15: With ContactFilterParams - title filter
-- GET /api/v1/contacts/seniority/?title=Chief Technology Officer
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND c.title ILIKE '%Chief Technology Officer%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 16: With ContactFilterParams - department filter
-- GET /api/v1/contacts/seniority/?department=C-Suite
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 17: With ContactFilterParams - employees_min filter
-- GET /api/v1/contacts/seniority/?employees_min=20
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND co.employees_count >= 20
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

-- Query 18: With multiple ContactFilterParams combined
-- GET /api/v1/contacts/seniority/?company=Bandura&title=Chief&employees_min=20&employees_max=100
SELECT DISTINCT c.seniority as value
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.seniority IS NOT NULL
    AND c.seniority != ''
    AND c.seniority != '_'
    AND TRIM(c.seniority) != '_'
    AND co.name ILIKE '%Bandura%'
    AND c.title ILIKE '%Chief%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.seniority ASC
LIMIT 25
OFFSET 0;

