-- ============================================================================
-- Endpoint: GET /api/v1/contacts/count/
-- API Version: v1
-- Description: Return the total number of contacts that satisfy the provided filters. Supports all ContactFilterParams. Use distinct=true to count unique contacts.
-- ============================================================================
--
-- Parameters: (All optional, same as list_contacts.sql)
--   See list_contacts.sql for complete parameter list (50+ filter parameters)
--   Key parameters:
--   $1: distinct (boolean, default: false) - Request distinct contacts based on primary key
--
-- Response Structure:
-- {
--   "count": 1234
-- }
--
-- Note: This query uses the same filter logic as list_contacts.sql but returns COUNT(*)
-- instead of the actual rows. All filter conditions from list_contacts.sql apply here.
--
-- Example Usage:
--   SELECT COUNT(DISTINCT c.id) as count
--   FROM contacts c
--   LEFT JOIN companies co ON c.company_id = co.uuid
--   LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
--   LEFT JOIN companies_metadata com ON co.uuid = com.uuid
--   WHERE [filter conditions from list_contacts.sql];
-- ============================================================================

-- Base query structure (same as list_contacts but with COUNT)
-- Note: All filter conditions from list_contacts.sql should be applied here
-- This is a simplified version - see list_contacts.sql for complete filter logic

SELECT 
    CASE 
        WHEN $1 = true THEN COUNT(DISTINCT c.id)
        ELSE COUNT(c.id)
    END as count
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply all filter conditions from list_contacts.sql here
    -- See list_contacts.sql for complete WHERE clause implementation
    -- This includes:
    --   - Contact field filters (first_name, last_name, title, email, etc.)
    --   - Company field filters (name, employees_count, annual_revenue, etc.)
    --   - Metadata filters (city, state, country, phones, etc.)
    --   - Array filters (departments, industries, keywords, technologies)
    --   - Exclusion filters (exclude_titles, exclude_company_ids, etc.)
    --   - Date range filters (created_at_after, updated_at_before, etc.)
    --   - Search term matching across multiple columns
;

