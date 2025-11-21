-- ============================================================================
-- Endpoint: GET /api/v1/contacts/count/
-- API Version: v1
-- Description: Return the total number of contacts that satisfy the provided filters. 
--              Supports all ContactFilterParams. Uses the same conditional JOIN logic as list_contacts.
--              Use distinct=true to count unique contacts.
-- ============================================================================
--
-- Parameters (All optional, same as list_contacts.sql):
--   Query Parameters:
--     distinct (boolean, default: false) - Request distinct contacts based on primary key
--     All filter parameters from list_contacts.sql apply here (50+ filter parameters)
--     See list_contacts.sql for complete parameter documentation
--
-- Response Structure:
--   Returns CountResponse:
--   {
--     "count": 1234
--   }
--
-- Response Codes:
--   200 OK: Count retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while counting contacts
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Query Optimization Notes:
--   The ContactRepository.count_contacts() uses the same conditional JOIN logic as list_contacts():
--   
--   JOIN Decision Logic (same as list_contacts):
--   1. Minimal query: Only contacts table - COUNT(c.id)
--      - Used when: No company filters, no metadata filters
--      - Uses EXISTS subqueries for company/metadata filters when needed
--   
--   2. Company join: Contact + Company - COUNT(DISTINCT c.id)
--      - Used when: Company filters present OR company search
--      - COUNT(DISTINCT) handles potential duplicates from joins
--   
--   3. Full metadata joins: All tables - COUNT(DISTINCT c.id)
--      - Used when: ContactMetadata filters OR CompanyMetadata filters
--      - COUNT(DISTINCT) ensures accurate count with multiple joins
--   
--   COUNT Logic:
--   - With joins: COUNT(DISTINCT c.id) to handle duplicates from joins
--   - Without joins: COUNT(c.id) - no need for DISTINCT
--   - EXISTS subqueries: Used when no company join needed but company filters present
--   
--   Approximate Count Option:
--   - For very large unfiltered queries, can use approximate count from pg_class
--   - Only used when use_approximate=true and no filters present
--   
--   Filter Application Order (same as list_contacts):
--   1. Contact filters → 2. Company filters → 3. Special filters → 4. Search terms
--
-- Example Usage:
--   GET /api/v1/contacts/count/
--   GET /api/v1/contacts/count/?company=TechCorp&employees_min=50
--   GET /api/v1/contacts/count/?distinct=true&city=San Francisco
-- ============================================================================

-- Query 1: Count all contacts (minimal query - no joins when no filters)
-- GET /api/v1/contacts/count/
SELECT 
    COUNT(c.id) as count
FROM contacts c;

-- Query 2: Count with distinct=true (minimal query)
-- GET /api/v1/contacts/count/?distinct=true
SELECT 
    COUNT(DISTINCT c.id) as count
FROM contacts c;

-- Query 3: Count with company filter (requires company join)
-- GET /api/v1/contacts/count/?company=TechCorp
-- Note: When company join is present, uses COUNT(DISTINCT c.id) to handle potential duplicates
SELECT 
    COUNT(DISTINCT c.id) as count
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE co.name ILIKE '%TechCorp%';

-- Query 4: Count with metadata filter (requires metadata joins)
-- GET /api/v1/contacts/count/?city=San Francisco
-- Note: When metadata joins are present, uses COUNT(DISTINCT c.id) to handle potential duplicates
SELECT 
    COUNT(DISTINCT c.id) as count
FROM contacts c
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
WHERE cm.city ILIKE '%San Francisco%';

-- Query 5: Count with all joins and multiple filters
-- GET /api/v1/contacts/count/?company=TechCorp&employees_min=50&city=San Francisco
-- Note: When multiple joins are present, always uses COUNT(DISTINCT c.id) regardless of distinct parameter
--       The distinct parameter in count_contacts is not used - COUNT(DISTINCT) is automatic with joins
SELECT 
    COUNT(DISTINCT c.id) as count
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%TechCorp%'
    AND co.employees_count >= 50
    AND cm.city ILIKE '%San Francisco%';

-- Query 6: Count with company filter but no join (EXISTS subquery fallback)
-- GET /api/v1/contacts/count/?company=TechCorp
-- Note: When no company join is needed but company filters are present, uses EXISTS subqueries
--       This is more efficient for count queries when only company filters are needed
--       The ORM uses this approach when company_alias is None
SELECT 
    COUNT(c.id) as count
FROM contacts c
WHERE EXISTS (
    SELECT 1
    FROM companies co
    WHERE co.uuid = c.company_id
      AND co.name ILIKE '%TechCorp%'
);

-- Query 7: Approximate count for very large unfiltered queries
-- Note: Only used when use_approximate=true and no filters present
--       Uses PostgreSQL pg_class statistics for fast approximate count
SELECT 
    COALESCE(reltuples::bigint, 0) as count
FROM pg_class
WHERE relname = 'contacts';

-- Notes:
-- - The ORM applies filters in the same order as list_contacts: contact filters, company filters, 
--   special filters, then search terms
-- - JOINs are conditional - only added when filters require them
-- - COUNT(DISTINCT c.id) is used when joins are present, COUNT(c.id) when no joins
-- - EXISTS subqueries are used when no company join needed but company filters present
-- - All filter conditions from list_contacts.sql apply here (see list_contacts.sql for complete filter logic)

