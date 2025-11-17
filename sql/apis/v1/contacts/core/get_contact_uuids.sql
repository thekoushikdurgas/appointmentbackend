-- ============================================================================
-- Endpoint: GET /api/v1/contacts/count/uuids/
-- API Version: v1
-- Description: Return a list of contact UUIDs that match the provided filters. Supports all ContactFilterParams. Returns count and list of UUIDs. Useful for bulk operations or exporting specific contact sets.
-- ============================================================================
--
-- Parameters (All optional, same as list_contacts.sql):
--   See list_contacts.sql for complete parameter list (50+ filter parameters)
--   All filter parameters from /api/v1/contacts/ are supported.
--
--   Additional Parameters:
--     limit (integer, optional) - Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).
--
-- Response Structure:
-- {
--   "count": 1234,
--   "uuids": ["uuid1", "uuid2", "uuid3", ...]
-- }
--
-- Note: This query uses the same filter logic as list_contacts.sql but returns only UUIDs
-- instead of full contact records. All filter conditions from list_contacts.sql apply here.
--
-- Example Usage:
--   GET /api/v1/contacts/count/uuids/?company=Bandura&search=cyber&limit=100
--   Returns up to 100 contact UUIDs matching the filters.
-- ============================================================================

-- Query 1: Get all matching contact UUIDs (no limit)
-- GET /api/v1/contacts/count/uuids/?company=Bandura&search=cyber
SELECT 
    COUNT(c.uuid) as count,
    array_agg(c.uuid ORDER BY c.created_at DESC) as uuids
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply all filter conditions from list_contacts.sql here
    -- See list_contacts.sql for complete WHERE clause implementation
    -- Example filters:
    -- AND co.name ILIKE '%Bandura%'
    -- AND (
    --     c.first_name ILIKE '%cyber%' OR
    --     c.last_name ILIKE '%cyber%' OR
    --     c.email ILIKE '%cyber%' OR
    --     co.name ILIKE '%cyber%'
    -- )
;

-- Query 2: Get contact UUIDs with limit
-- GET /api/v1/contacts/count/uuids/?company=Bandura&search=cyber&limit=100
WITH filtered_contacts AS (
    SELECT c.uuid
    FROM contacts c
    LEFT JOIN companies co ON c.company_id = co.uuid
    LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply all filter conditions from list_contacts.sql here
        -- See list_contacts.sql for complete WHERE clause implementation
    ORDER BY c.created_at DESC
    LIMIT 100
)
SELECT 
    (SELECT COUNT(*) FROM contacts c
     LEFT JOIN companies co ON c.company_id = co.uuid
     LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
     LEFT JOIN companies_metadata com ON co.uuid = com.uuid
     WHERE 1=1
        -- Apply same filter conditions here for count
    ) as count,
    array_agg(uuid ORDER BY uuid) as uuids
FROM filtered_contacts;

-- Query 3: Get contact UUIDs with distinct filter
-- GET /api/v1/contacts/count/uuids/?company=Bandura&distinct=true&limit=50
WITH filtered_contacts AS (
    SELECT DISTINCT ON (c.id) c.uuid
    FROM contacts c
    LEFT JOIN companies co ON c.company_id = co.uuid
    LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply all filter conditions from list_contacts.sql here
    ORDER BY c.id, c.created_at DESC
    LIMIT 50
)
SELECT 
    (SELECT COUNT(DISTINCT c.id) FROM contacts c
     LEFT JOIN companies co ON c.company_id = co.uuid
     LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
     LEFT JOIN companies_metadata com ON co.uuid = com.uuid
     WHERE 1=1
        -- Apply same filter conditions here for count
    ) as count,
    array_agg(uuid ORDER BY uuid) as uuids
FROM filtered_contacts;

