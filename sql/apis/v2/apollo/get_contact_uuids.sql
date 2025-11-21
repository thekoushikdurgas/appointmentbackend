-- ============================================================================
-- Endpoint: POST /api/v2/apollo/contacts/count/uuids
-- API Version: v2
-- Description: Get a list of contact UUIDs matching Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns matching contact UUIDs from your database.
-- ============================================================================
--
-- Request Body Parameters:
--   $1: url (text, required) - Apollo.io URL to analyze and convert. Must be from the apollo.io domain.
--
-- Query Parameters (All optional):
--   include_company_name (text) - Include contacts whose company name matches (case-insensitive substring). Supports comma-separated values for OR logic.
--   exclude_company_name (text[]) - Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times.
--   include_domain_list (text[]) - Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website. Can be provided multiple times.
--   exclude_domain_list (text[]) - Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website. Can be provided multiple times.
--   limit (integer, optional) - Maximum number of UUIDs to return. If not provided, returns all matching UUIDs (unlimited).
--
-- Response Structure:
-- {
--   "count": 1234,
--   "uuids": ["uuid1", "uuid2", "uuid3", ...]
-- }
--
-- Response Codes:
--   200 OK: UUIDs retrieved successfully
--   400 Bad Request: Invalid URL, not from Apollo.io domain, or invalid filter parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while retrieving UUIDs
--
-- Note: The Apollo URL is parsed in the application layer and converted to ContactFilterParams.
-- The actual database query uses the same filter logic as list_contacts.sql but returns only UUIDs
-- instead of full contact records. All filter conditions from list_contacts.sql apply here.
--
-- Parameter Mappings:
--   Same as /api/v2/apollo/contacts endpoint - all Apollo URL parameters are mapped to contact filters using the same logic.
--   See search_contacts.sql for complete parameter mapping details.
--
-- Example Usage:
--   POST /api/v2/apollo/contacts/count/uuids?limit=100&include_company_name=TechCorp
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified"
--   }
-- ============================================================================

-- ORM Implementation Notes:
--   The ApolloContactsService.get_contact_uuids() uses ContactRepository.get_uuids_by_filters():
--   - Uses the SAME conditional JOIN logic as get_contact_uuids (see get_contact_uuids.sql for details)
--   - Apollo URL parameters are parsed and converted to ContactFilterParams in application layer
--   - Returns list[str] of UUIDs (not array_agg in SQL)
--   - Service layer builds response with count and uuids list

-- Query 1: Get all matching contact UUIDs (no limit, minimal - no joins)
-- POST /api/v2/apollo/contacts/count/uuids
-- Note: The Apollo URL is parsed and converted to ContactFilterParams in the application layer.
--       The actual query uses the same conditional JOIN logic as get_contact_uuids.sql.
--       Returns list of UUIDs, not array_agg.
SELECT 
    c.uuid
FROM contacts c
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

-- Query 2: Get contact UUIDs with limit
-- POST /api/v2/apollo/contacts/count/uuids?limit=100
WITH filtered_contacts AS (
    SELECT c.uuid
    FROM contacts c
    LEFT JOIN companies co ON c.company_id = co.uuid
    LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply converted Apollo filter conditions here
        -- See search_contacts.sql for parameter mapping details
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
-- POST /api/v2/apollo/contacts/count/uuids?limit=50&distinct=true
WITH filtered_contacts AS (
    SELECT DISTINCT ON (c.id) c.uuid
    FROM contacts c
    LEFT JOIN companies co ON c.company_id = co.uuid
    LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
    LEFT JOIN companies_metadata com ON co.uuid = com.uuid
    WHERE 1=1
        -- Apply converted Apollo filter conditions here
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

