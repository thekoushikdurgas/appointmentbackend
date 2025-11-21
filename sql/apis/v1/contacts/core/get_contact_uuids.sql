-- ============================================================================
-- Endpoint: GET /api/v1/contacts/count/uuids/
-- API Version: v1
-- Description: Return a list of contact UUIDs that match the provided filters. 
--              Supports all ContactFilterParams. Returns count and list of UUIDs. 
--              Useful for bulk operations or exporting specific contact sets.
--              Uses the same conditional JOIN logic as list_contacts.
-- ============================================================================
--
-- Parameters (All optional, same as list_contacts.sql):
--   Query Parameters:
--     limit (integer, optional) - Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).
--     All filter parameters from list_contacts.sql apply here (50+ filter parameters)
--     See list_contacts.sql for complete parameter documentation
--
-- Response Structure:
--   Returns UuidListResponse:
--   {
--     "count": 1234,
--     "uuids": ["uuid1", "uuid2", "uuid3", ...]
--   }
--
-- Response Codes:
--   200 OK: UUIDs retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while retrieving UUIDs
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Query Optimization Notes:
--   The ContactRepository.get_uuids_by_filters() uses the same conditional JOIN logic as list_contacts():
--   
--   JOIN Decision Logic (same as list_contacts):
--   1. Minimal query: Only contacts table - SELECT Contact.uuid
--      - Used when: No company filters, no metadata filters
--      - Uses EXISTS subqueries for company/metadata filters when needed
--   
--   2. Company join: Contact + Company - SELECT Contact.uuid FROM joined query
--      - Used when: Company filters present OR company search
--   
--   3. Full metadata joins: All tables - SELECT Contact.uuid FROM joined query
--      - Used when: ContactMetadata filters OR CompanyMetadata filters
--   
--   Filter Application Order (same as list_contacts):
--   1. Contact filters → 2. Company filters → 3. Special filters → 4. Search terms
--   
--   Return Format:
--   - Returns list[str] of UUIDs (not SQL array_agg)
--   - Service layer builds UuidListResponse with count and uuids array
--   - Count is length of returned UUID list (not separate COUNT query)
--   
--   Limit Handling:
--   - Optional limit parameter - if provided, applies LIMIT to UUID query
--   - If limit is None, returns all matching UUIDs (unlimited)
--
-- Example Usage:
--   GET /api/v1/contacts/count/uuids/?company=Bandura&search=cyber&limit=100
--   GET /api/v1/contacts/count/uuids/?city=San Francisco&limit=50
-- ============================================================================

-- Query 1: Get all matching contact UUIDs (no limit, with company filter)
-- GET /api/v1/contacts/count/uuids/?company=Bandura&search=cyber
-- Note: When company filter is present, ORM joins Company table.
--       Returns list of UUIDs, count is calculated by service layer (len(uuids)).
SELECT 
    c.uuid
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE co.name ILIKE '%Bandura%'
  AND (
    c.first_name ILIKE '%cyber%' OR
    c.last_name ILIKE '%cyber%' OR
    c.email ILIKE '%cyber%' OR
    c.title ILIKE '%cyber%' OR
    c.seniority ILIKE '%cyber%' OR
    c.text_search ILIKE '%cyber%' OR
    co.name ILIKE '%cyber%' OR
    co.address ILIKE '%cyber%' OR
    co.text_search ILIKE '%cyber%' OR
    array_to_string(co.industries, ',') ILIKE '%cyber%' OR
    array_to_string(co.keywords, ',') ILIKE '%cyber%' OR
    array_to_string(co.technologies, ',') ILIKE '%cyber%'
  )
ORDER BY c.created_at DESC NULLS LAST, c.id DESC;

-- Query 2: Get contact UUIDs with limit (no company filter - minimal query)
-- GET /api/v1/contacts/count/uuids/?first_name=John&limit=100
-- Note: When no company/metadata filters, uses minimal query (no joins).
--       Returns list of UUIDs, count is length of list (not separate COUNT query).
SELECT 
    c.uuid
FROM contacts c
WHERE c.first_name ILIKE '%John%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 100;

-- Query 3: Get contact UUIDs with metadata filters (requires all joins)
-- GET /api/v1/contacts/count/uuids/?company=Bandura&city=San Francisco&limit=50
-- Note: When metadata filters are present, ORM joins ContactMetadata and/or CompanyMetadata.
--       Returns list of UUIDs, count is length of list.
SELECT 
    c.uuid
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%Bandura%'
  AND cm.city ILIKE '%San Francisco%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 50;

-- Query 4: Get contact UUIDs with no company join (EXISTS subquery)
-- GET /api/v1/contacts/count/uuids/?company=TechCorp
-- Note: When no company join is needed but company filters are present, uses EXISTS subqueries.
--       This is more efficient when only company filters are needed.
SELECT 
    c.uuid
FROM contacts c
WHERE EXISTS (
    SELECT 1
    FROM companies co
    WHERE co.uuid = c.company_id
      AND co.name ILIKE '%TechCorp%'
)
ORDER BY c.created_at DESC NULLS LAST, c.id DESC;

