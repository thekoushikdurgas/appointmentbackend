-- ============================================================================
-- Endpoint: POST /api/v2/apollo/contacts/count
-- API Version: v2
-- Description: Count contacts matching Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns the total count of matching contacts from your database.
-- ============================================================================
--
-- Request Body Parameters:
--   $1: url (text, required) - Apollo.io URL to analyze and convert. Must be from the apollo.io domain.
--
-- Query Parameters (All optional):
--   include_company_name (text) - Include contacts whose company name matches (case-insensitive substring). Supports comma-separated values for OR logic.
--   exclude_company_name (text[]) - Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times.
--
-- Response Structure:
-- {
--   "count": 1234
-- }
--
-- Response Codes:
--   200 OK: Count retrieved successfully
--   400 Bad Request: Invalid URL, not from Apollo.io domain, or invalid filter parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while counting contacts
--
-- Note: The Apollo URL is parsed in the application layer and converted to ContactFilterParams.
-- The actual database query uses the same filter logic as list_contacts.sql but returns COUNT(*)
-- instead of the actual rows. All filter conditions from list_contacts.sql apply here.
--
-- Parameter Mappings:
--   Same as /api/v2/apollo/contacts endpoint - all Apollo URL parameters are mapped to contact filters using the same logic.
--   See search_contacts.sql for complete parameter mapping details.
--
-- Example Usage:
--   POST /api/v2/apollo/contacts/count?include_company_name=TechCorp
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified"
--   }
-- ============================================================================

-- Query 1: Count contacts matching Apollo URL filters
-- POST /api/v2/apollo/contacts/count
-- The Apollo URL is parsed and converted to ContactFilterParams in the application layer.
-- The actual query uses the same structure as count_contacts.sql with the converted filters.
SELECT 
    COUNT(c.id) as count
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply converted Apollo filter conditions here
    -- See search_contacts.sql for parameter mapping details
    -- Example: Apollo personTitles[]=CEO → title filter
    -- AND c.title ILIKE '%CEO%'
    -- Example: Apollo personLocations[]=California → contact_location filter
    -- AND c.text_search ILIKE '%California%'
    -- Example: Apollo organizationNumEmployeesRanges[]=11,50 → employees_min=11, employees_max=50
    -- AND co.employees_count >= 11 AND co.employees_count <= 50
    -- Example: Apollo contactEmailStatusV2[]=verified → email_status filter
    -- AND c.email_status ILIKE '%verified%'
    -- Example: include_company_name query parameter
    -- AND co.name ILIKE '%TechCorp%'
    -- Example: exclude_company_name query parameter
    -- AND (co.name IS NULL OR NOT (LOWER(co.name) = ANY(SELECT LOWER(unnest(ARRAY['ExcludedCorp'])))))
;

-- Query 2: Count with distinct filter
-- POST /api/v2/apollo/contacts/count?distinct=true
SELECT 
    COUNT(DISTINCT c.id) as count
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply converted Apollo filter conditions here
    -- (same as Query 1)
;

