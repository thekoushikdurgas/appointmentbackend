-- ============================================================================
-- Endpoint: POST /api/v2/apollo/contacts
-- API Version: v2
-- Description: Search contacts using Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns matching contacts from your database. It provides a seamless way to replicate Apollo.io searches in your own contact database.
-- ============================================================================
--
-- Request Body Parameters:
--   $1: url (text, required) - Apollo.io URL to analyze and convert. Must be from the apollo.io domain.
--
-- Query Parameters (All optional):
--   limit (integer, >=1) - Maximum number of results per page. If not provided, returns all matching contacts (no pagination limit). When provided, limits results to the specified number (capped at MAX_PAGE_SIZE).
--   offset (integer, >=0) - Starting offset for results (default: 0)
--   cursor (text) - Opaque cursor token for pagination
--   view (text) - When set to 'simple', returns ContactSimpleItem. Omit for full ContactListItem.
--   include_company_name (text) - Include contacts whose company name matches (case-insensitive substring). Supports comma-separated values for OR logic.
--   exclude_company_name (text[]) - Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times.
--   include_domain_list (text[]) - Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website. Can be provided multiple times.
--   exclude_domain_list (text[]) - Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from CompanyMetadata.website. Can be provided multiple times.
--
-- Response Structure:
--   Returns ApolloContactsSearchResponse containing:
--   - CursorPage with ContactListItem or ContactSimpleItem results
--   - apollo_url: The original Apollo URL
--   - mapping_summary: Statistics about parameter mapping (total, mapped, unmapped counts)
--   - unmapped_categories: Detailed information about parameters that were not mapped, grouped by category with reasons
--
-- Response Codes:
--   200 OK: Contacts retrieved successfully with mapping metadata
--   400 Bad Request: Invalid URL, not from Apollo.io domain, or invalid filter parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while searching contacts
--
-- Note: The Apollo URL is parsed in the application layer and converted to ContactFilterParams.
-- The actual database query uses the same logic as /api/v1/contacts/ endpoint.
-- See list_contacts.sql for complete filter implementation details.
--
-- Parameter Mappings (Apollo → Database):
--   page → page
--   sortByField + sortAscending → ordering (with '-' prefix for descending)
--   personTitles[] → title (comma-separated for OR logic)
--   personNotTitles[] → exclude_titles
--   personSeniorities[] → seniority (comma-separated)
--   personDepartmentOrSubdepartments[] → department (comma-separated)
--   personLocations[] → contact_location (comma-separated)
--   personNotLocations[] → exclude_contact_locations
--   organizationNumEmployeesRanges[] → employees_min, employees_max
--   organizationLocations[] → company_location (comma-separated)
--   organizationNotLocations[] → exclude_company_locations
--   revenueRange[min/max] → annual_revenue_min, annual_revenue_max
--   contactEmailStatusV2[] → email_status (comma-separated)
--   organizationIndustryTagIds[] → industries (Tag IDs converted to industry names from CSV)
--   organizationNotIndustryTagIds[] → exclude_industries (Tag IDs converted to industry names from CSV)
--   qOrganizationKeywordTags[] → keywords (comma-separated)
--   qNotOrganizationKeywordTags[] → exclude_keywords
--   qKeywords → search
--   currentlyUsingAnyOfTechnologyUids[] → technologies_uids (mapped to technologies)
--
-- Example Usage:
--   POST /api/v2/apollo/contacts?limit=25&offset=0
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified&page=1&sortByField=employees&sortAscending=false"
--   }
-- ============================================================================

-- ORM Implementation Notes:
--   The ApolloContactsService.search_contacts() uses ContactRepository.list_contacts():
--   - Uses the SAME conditional JOIN logic as list_contacts (see list_contacts.sql for details)
--   - Apollo URL parameters are parsed and converted to ContactFilterParams in application layer
--   - Only joins tables when filters require them (optimized for performance)
--   - Default ordering: created_at DESC NULLS LAST, id DESC
--   - Returns normalized 4-tuple: (Contact, Company, ContactMetadata, CompanyMetadata)

-- Query 1: Basic search with Apollo URL (converted to filters, minimal - no joins)
-- POST /api/v2/apollo/contacts?limit=25&offset=0
-- Note: The Apollo URL is parsed and converted to ContactFilterParams in the application layer.
--       The actual query uses the same conditional JOIN logic as list_contacts.sql.
--       This example shows minimal query when no filters require joins.
SELECT 
    c.id,
    c.uuid,
    c.first_name,
    c.last_name,
    c.company_id,
    c.email,
    c.title,
    c.departments,
    c.mobile_phone,
    c.email_status,
    c.text_search,
    c.seniority,
    c.created_at,
    c.updated_at,
    co.name as company,
    co.employees_count as employees,
    co.annual_revenue,
    co.total_funding,
    co.text_search as company_address,
    com.company_name_for_emails,
    com.phone_number as corporate_phone,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country,
    com.linkedin_url as company_linkedin_url,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.linkedin_url as person_linkedin_url,
    cm.website,
    cm.stage,
    array_to_string(co.industries, ',') as industry,
    array_to_string(co.keywords, ',') as keywords,
    array_to_string(co.technologies, ',') as technologies,
    array_to_string(c.departments, ',') as departments_display,
    COALESCE(cm.facebook_url, com.facebook_url) as facebook_url,
    COALESCE(cm.twitter_url, com.twitter_url) as twitter_url
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply converted Apollo filter conditions here
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
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 2: With view=simple (returns simplified contact data)
-- POST /api/v2/apollo/contacts?limit=25&offset=0&view=simple
SELECT 
    c.id,
    c.uuid,
    c.first_name,
    c.last_name,
    c.title,
    cm.city,
    cm.state,
    cm.country,
    co.name as company_name,
    cm.linkedin_url as person_linkedin_url,
    com.website as company_domain
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply converted Apollo filter conditions here
    -- (same as Query 1)
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 3: With cursor pagination
-- POST /api/v2/apollo/contacts?limit=25&cursor=bz0w
-- Cursor is decoded to offset in the application layer
SELECT 
    c.id,
    c.uuid,
    c.first_name,
    c.last_name,
    c.company_id,
    c.email,
    c.title,
    c.departments,
    c.mobile_phone,
    c.email_status,
    c.text_search,
    c.seniority,
    c.created_at,
    c.updated_at,
    co.name as company,
    co.employees_count as employees,
    co.annual_revenue,
    co.total_funding,
    co.text_search as company_address,
    com.company_name_for_emails,
    com.phone_number as corporate_phone,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country,
    com.linkedin_url as company_linkedin_url,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.linkedin_url as person_linkedin_url,
    cm.website,
    cm.stage,
    array_to_string(co.industries, ',') as industry,
    array_to_string(co.keywords, ',') as keywords,
    array_to_string(co.technologies, ',') as technologies,
    array_to_string(c.departments, ',') as departments_display,
    COALESCE(cm.facebook_url, com.facebook_url) as facebook_url,
    COALESCE(cm.twitter_url, com.twitter_url) as twitter_url
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 1=1
    -- Apply converted Apollo filter conditions here
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Note: The response includes mapping_summary and unmapped_categories metadata
-- which are generated in the application layer based on the Apollo URL analysis.

