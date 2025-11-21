-- ============================================================================
-- Endpoint: GET /api/v1/contacts/
-- API Version: v1
-- Description: Return a paginated list of contacts using every supported filter parameter.
--              The ORM implementation uses conditional JOINs - only joining tables when filters require them.
--              This optimizes query performance by avoiding unnecessary joins.
-- ============================================================================
--
-- Parameters (All optional):
--   Query Parameters:
--     limit (integer, >=1) - Number of contacts per page. If not provided, returns all matching contacts.
--     offset (integer, >=0) - Zero-based offset into the result set (default: 0)
--     cursor (text) - Opaque cursor token for pagination (base64 encoding of offset)
--     page (integer, >=1) - Optional 1-indexed page number (converts to offset)
--     page_size (integer, >=1) - Explicit page size override
--     distinct (boolean, default: false) - Return distinct contacts based on primary key
--     view (text) - View mode: 'simple' returns ContactSimpleItem, omit for full ContactListItem
--     ordering (text) - Sort field. Prepend '-' for descending. Valid: created_at, updated_at, first_name, 
--                      last_name, title, email, company, employees, annual_revenue, etc.
--     search (text) - Full-text search across multiple contact and company fields
--
--   Filter Parameters (50+ available):
--     Contact Fields: first_name, last_name, title, email, email_status, seniority, departments, mobile_phone
--     Company Filters: company, company_location, employees_count, employees_min, employees_max, 
--                     annual_revenue, annual_revenue_min, annual_revenue_max, total_funding, etc.
--     Array Filters: industries, keywords, technologies (comma-separated for OR logic)
--     Metadata Filters: city, state, country, work_direct_phone, home_phone, corporate_phone, etc.
--     Exclusion Filters: exclude_titles, exclude_company_ids, exclude_industries, exclude_keywords, etc.
--     Date Range Filters: created_at_after, created_at_before, updated_at_after, updated_at_before
--
-- Response Structure:
--   Returns CursorPage with results array containing ContactListItem or ContactSimpleItem objects.
--   Each result includes contact data and optionally company/metadata data based on JOINs performed.
--
-- Response Codes:
--   200 OK: Contacts retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying contacts
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Query Optimization Notes:
--   The ContactRepository.list_contacts() uses conditional JOINs based on filters and ordering:
--   
--   JOIN Decision Logic:
--   1. Minimal query (base_query_minimal): Only contacts table
--      - Used when: No company filters, no metadata filters, no company/metadata ordering
--      - Returns: (Contact, None, None, None) - normalized to 4-tuple format
--   
--   2. Company join (base_query_with_company): Contact + Company (LEFT JOIN)
--      - Used when: Company filters present OR company ordering OR company search
--      - Returns: (Contact, Company, None, None) - normalized to 4-tuple format
--   
--   3. Full metadata joins (base_query_with_metadata): All tables (LEFT JOINs)
--      - Used when: ContactMetadata filters OR CompanyMetadata filters OR metadata ordering
--      - Returns: (Contact, Company, ContactMetadata, CompanyMetadata) - full 4-tuple
--   
--   Filter Application Order (when joins are present):
--   1. Contact filters (_apply_contact_filters) - filters Contact table
--   2. Company filters (_apply_company_filters) - filters Company table
--   3. Special filters (_apply_special_filters) - domain, keywords with field control
--   4. Search terms (apply_search_terms) - multi-column search across joined tables
--   
--   When no company join is needed:
--   - Uses EXISTS subqueries (_apply_filters_with_exists) for company/metadata filters
--   - More efficient for count queries and when only contact filters are present
--   
--   Default Ordering:
--   - created_at DESC NULLS LAST, id DESC (no Company join required, uses indexed field)
--   - This avoids unnecessary Company join and significantly improves performance
--   
--   Result Normalization:
--   - Always returns 4-tuple: (Contact, Company, ContactMetadata, CompanyMetadata)
--   - Missing joins result in None values in the tuple
--   - Service layer handles None values gracefully when building response
--
-- Example Usage:
--   GET /api/v1/contacts/?limit=25&offset=0
--   GET /api/v1/contacts/?company=TechCorp&employees_min=50&ordering=-created_at
--   GET /api/v1/contacts/?search=engineer&city=San Francisco&limit=50
-- ============================================================================

-- Query 1: Basic query - Get all contacts (default pagination, minimal query - no joins)
-- GET /api/v1/contacts/
-- Note: The ORM uses conditional JOINs. This example shows the minimal query when no filters require joins.
-- The ORM returns a normalized 4-tuple: (Contact, Company, ContactMetadata, CompanyMetadata)
-- When no joins are performed, Company, ContactMetadata, and CompanyMetadata are None in the tuple.
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
    c.updated_at
FROM contacts c
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 2: With company filter (requires Company join)
-- GET /api/v1/contacts/?company=TechCorp&limit=50
-- Note: When company filter is present, ORM joins Company table. If no metadata filters,
--       ContactMetadata and CompanyMetadata are None in the returned 4-tuple.
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
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue,
    co.total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE co.name ILIKE '%TechCorp%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 50
OFFSET 0;

-- Query 3: With metadata filters (requires all joins)
-- GET /api/v1/contacts/?city=San Francisco&company_city=New York&limit=25&offset=25
-- Note: When metadata filters are present, ORM joins ContactMetadata and/or CompanyMetadata.
--       Returns full 4-tuple: (Contact, Company, ContactMetadata, CompanyMetadata)
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
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue,
    co.total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at,
    cm.id as contact_metadata_id,
    cm.uuid as contact_metadata_uuid,
    cm.linkedin_url as person_linkedin_url,
    cm.facebook_url as contact_facebook_url,
    cm.twitter_url as contact_twitter_url,
    cm.website,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.stage,
    com.id as company_metadata_id,
    com.uuid as company_metadata_uuid,
    com.linkedin_url as company_linkedin_url,
    com.facebook_url as company_facebook_url,
    com.twitter_url as company_twitter_url,
    com.website as company_website,
    com.company_name_for_emails,
    com.phone_number as corporate_phone,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE cm.city ILIKE '%San Francisco%'
  AND com.city ILIKE '%New York%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 25;

-- Query 4: With ordering by company name (requires Company join)
-- GET /api/v1/contacts/?ordering=company&limit=25&offset=25
-- Note: Ordering by company fields requires Company join. Default ordering uses created_at (no join needed).
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
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue,
    co.total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
ORDER BY co.name ASC NULLS LAST, c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 25;

-- Query 5: With search parameter (may require joins based on search scope)
-- GET /api/v1/contacts/?search=engineer&limit=10&offset=20
-- Note: Search across contact fields only - no joins needed. If search includes company fields,
--       Company join is required. Returns minimal query when search is contact-only.
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
    c.updated_at
FROM contacts c
WHERE (
    c.first_name ILIKE '%engineer%' OR
    c.last_name ILIKE '%engineer%' OR
    c.email ILIKE '%engineer%' OR
    c.title ILIKE '%engineer%' OR
    c.seniority ILIKE '%engineer%' OR
    c.text_search ILIKE '%engineer%'
)
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 10
OFFSET 20;

-- Query 6: With distinct=true and company filter
-- GET /api/v1/contacts/?distinct=true&company=TechCorp
-- Note: DISTINCT ON (c.id) is used when joins are present to handle potential duplicates.
--       The ORM normalizes results to 4-tuple format regardless of joins performed.
SELECT DISTINCT ON (c.id)
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
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue,
    co.total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
WHERE co.name ILIKE '%TechCorp%'
ORDER BY c.id, c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 7: With ordering=last_name (ascending)
-- GET /api/v1/contacts/?ordering=last_name
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
ORDER BY c.last_name ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 8: With ordering=-last_name (descending, no joins needed)
-- GET /api/v1/contacts/?ordering=-last_name
-- Note: Ordering by Contact fields does not require joins. Deterministic ordering ensures consistent pagination.
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
    c.updated_at
FROM contacts c
ORDER BY c.last_name DESC NULLS LAST, c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 9: Complex filter example with all joins
-- GET /api/v1/contacts/?company=TechCorp&city=San Francisco&company_city=New York&keywords=AI&limit=25
-- Note: This example shows when all joins are required due to filters on multiple tables.
--       Filter application order: Contact filters → Company filters → Special filters → Search
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
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue,
    co.total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at,
    cm.id as contact_metadata_id,
    cm.uuid as contact_metadata_uuid,
    cm.linkedin_url as person_linkedin_url,
    cm.facebook_url as contact_facebook_url,
    cm.twitter_url as contact_twitter_url,
    cm.website,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.stage,
    com.id as company_metadata_id,
    com.uuid as company_metadata_uuid,
    com.linkedin_url as company_linkedin_url,
    com.facebook_url as company_facebook_url,
    com.twitter_url as company_twitter_url,
    com.website as company_website,
    com.company_name_for_emails,
    com.phone_number as corporate_phone,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country
FROM contacts c
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%TechCorp%'
  AND cm.city ILIKE '%San Francisco%'
  AND com.city ILIKE '%New York%'
  AND array_to_string(co.keywords, ',') ILIKE '%AI%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;
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
ORDER BY c.last_name DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 9: With ordering=created_at
-- GET /api/v1/contacts/?ordering=created_at
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
ORDER BY c.created_at ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 10: With ordering=-created_at
-- GET /api/v1/contacts/?ordering=-created_at
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
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 11: With ordering=company
-- GET /api/v1/contacts/?ordering=company
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
ORDER BY co.name ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 12: With search parameter
-- GET /api/v1/contacts/?search=Bandura
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
WHERE (
    c.first_name ILIKE '%Bandura%' OR
    c.last_name ILIKE '%Bandura%' OR
    c.email ILIKE '%Bandura%' OR
    c.title ILIKE '%Bandura%' OR
    c.seniority ILIKE '%Bandura%' OR
    c.text_search ILIKE '%Bandura%' OR
    co.name ILIKE '%Bandura%' OR
    co.address ILIKE '%Bandura%' OR
    array_to_string(co.industries, ',') ILIKE '%Bandura%' OR
    array_to_string(co.keywords, ',') ILIKE '%Bandura%' OR
    (com.city IS NOT NULL AND com.city ILIKE '%Bandura%') OR
    (com.state IS NOT NULL AND com.state ILIKE '%Bandura%') OR
    (com.country IS NOT NULL AND com.country ILIKE '%Bandura%') OR
    (com.phone_number IS NOT NULL AND com.phone_number ILIKE '%Bandura%') OR
    (com.website IS NOT NULL AND com.website ILIKE '%Bandura%') OR
    (cm.city IS NOT NULL AND cm.city ILIKE '%Bandura%') OR
    (cm.state IS NOT NULL AND cm.state ILIKE '%Bandura%') OR
    (cm.country IS NOT NULL AND cm.country ILIKE '%Bandura%') OR
    (cm.linkedin_url IS NOT NULL AND cm.linkedin_url ILIKE '%Bandura%') OR
    (cm.twitter_url IS NOT NULL AND cm.twitter_url ILIKE '%Bandura%')
)
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 13: With first_name filter (no joins needed - contact-only filter)
-- GET /api/v1/contacts/?first_name=Patrick
-- Note: Contact-only filters (first_name, last_name, email, title, etc.) do not require joins.
--       Returns minimal query: (Contact, None, None, None)
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
    c.updated_at
FROM contacts c
WHERE c.first_name ILIKE '%Patrick%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 14: With last_name filter (no joins needed - contact-only filter)
-- GET /api/v1/contacts/?last_name=McGarry
-- Note: Contact-only filters do not require joins. Returns minimal query.
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
    c.updated_at
FROM contacts c
WHERE c.last_name ILIKE '%McGarry%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 15: With title filter (no joins needed - contact-only filter)
-- GET /api/v1/contacts/?title=Chief Technology Officer
-- Note: Title filter uses trigram optimization when many values provided, but still no joins needed.
--       Returns minimal query: (Contact, None, None, None)
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
    c.updated_at
FROM contacts c
WHERE c.title ILIKE '%Chief Technology Officer%'
ORDER BY c.created_at DESC NULLS LAST, c.id DESC
LIMIT 25
OFFSET 0;

-- Query 16: With company filter
-- GET /api/v1/contacts/?company=Bandura
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
WHERE co.name ILIKE '%Bandura%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 17: With email filter
-- GET /api/v1/contacts/?email=banduracyber.com
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
WHERE c.email ILIKE '%banduracyber.com%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 18: With seniority filter
-- GET /api/v1/contacts/?seniority=C suite
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
WHERE c.seniority ILIKE '%C suite%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 19: With department filter
-- GET /api/v1/contacts/?department=C-Suite
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
WHERE array_to_string(c.departments, ',') ILIKE '%C-Suite%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 20: With employees_min filter
-- GET /api/v1/contacts/?employees_min=20
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
WHERE co.employees_count >= 20
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 21: With employees_max filter
-- GET /api/v1/contacts/?employees_max=100
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
WHERE co.employees_count <= 100
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 22: With employees range
-- GET /api/v1/contacts/?employees_min=20&employees_max=100
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
WHERE co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 23: With industries filter
-- GET /api/v1/contacts/?industries=information technology
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
WHERE array_to_string(co.industries, ',') ILIKE '%information technology%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 24: With technologies filter
-- GET /api/v1/contacts/?technologies=Salesforce
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
WHERE array_to_string(co.technologies, ',') ILIKE '%Salesforce%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 25: With keywords filter
-- GET /api/v1/contacts/?keywords=cyber security
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
WHERE array_to_string(co.keywords, ',') ILIKE '%cyber security%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 26: With city filter
-- GET /api/v1/contacts/?city=Miamisburg
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
WHERE cm.city ILIKE '%Miamisburg%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 27: With state filter
-- GET /api/v1/contacts/?state=Ohio
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
WHERE cm.state ILIKE '%Ohio%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 28: With country filter
-- GET /api/v1/contacts/?country=United States
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
WHERE cm.country ILIKE '%United States%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 29: With annual_revenue_min filter
-- GET /api/v1/contacts/?annual_revenue_min=7000000
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
WHERE co.annual_revenue >= 7000000
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 30: With annual_revenue_max filter
-- GET /api/v1/contacts/?annual_revenue_max=9000000
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
WHERE co.annual_revenue <= 9000000
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 31: With exclude_titles filter
-- GET /api/v1/contacts/?exclude_titles=Intern,Junior
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
WHERE c.title IS NULL OR NOT (LOWER(c.title) = ANY(SELECT LOWER(unnest(ARRAY['Intern', 'Junior']))))
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 32: With exclude_company_ids filter
-- GET /api/v1/contacts/?exclude_company_ids=398cce44-233d-5f7c-aea1-e4a6a79df10c
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
WHERE c.company_id IS NULL OR NOT (c.company_id = ANY(ARRAY['398cce44-233d-5f7c-aea1-e4a6a79df10c']))
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 33: With created_at_after filter
-- GET /api/v1/contacts/?created_at_after=2024-01-01T00:00:00
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
WHERE c.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 34: With created_at_before filter
-- GET /api/v1/contacts/?created_at_before=2024-12-31T23:59:59
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
WHERE c.created_at <= '2024-12-31 23:59:59'::timestamp
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 35: With multiple filters combined
-- GET /api/v1/contacts/?company=Bandura&seniority=C suite&employees_min=20&employees_max=100
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
WHERE co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND co.employees_count <= 100
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 36: With search and ordering
-- GET /api/v1/contacts/?search=Bandura&ordering=last_name
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
WHERE (
    c.first_name ILIKE '%Bandura%' OR
    c.last_name ILIKE '%Bandura%' OR
    c.email ILIKE '%Bandura%' OR
    c.title ILIKE '%Bandura%' OR
    c.seniority ILIKE '%Bandura%' OR
    c.text_search ILIKE '%Bandura%' OR
    co.name ILIKE '%Bandura%' OR
    co.address ILIKE '%Bandura%' OR
    array_to_string(co.industries, ',') ILIKE '%Bandura%' OR
    array_to_string(co.keywords, ',') ILIKE '%Bandura%' OR
    (com.city IS NOT NULL AND com.city ILIKE '%Bandura%') OR
    (com.state IS NOT NULL AND com.state ILIKE '%Bandura%') OR
    (com.country IS NOT NULL AND com.country ILIKE '%Bandura%') OR
    (com.phone_number IS NOT NULL AND com.phone_number ILIKE '%Bandura%') OR
    (com.website IS NOT NULL AND com.website ILIKE '%Bandura%') OR
    (cm.city IS NOT NULL AND cm.city ILIKE '%Bandura%') OR
    (cm.state IS NOT NULL AND cm.state ILIKE '%Bandura%') OR
    (cm.country IS NOT NULL AND cm.country ILIKE '%Bandura%') OR
    (cm.linkedin_url IS NOT NULL AND cm.linkedin_url ILIKE '%Bandura%') OR
    (cm.twitter_url IS NOT NULL AND cm.twitter_url ILIKE '%Bandura%')
)
ORDER BY c.last_name ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 37: Complex query with multiple filters and pagination
-- GET /api/v1/contacts/?company=Bandura&seniority=C suite&employees_min=20&state=Ohio&limit=50&ordering=-created_at
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
WHERE co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND cm.state ILIKE '%Ohio%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 50
OFFSET 0;

-- Query 38: With all major filters combined
-- GET /api/v1/contacts/?company=Bandura&seniority=C suite&employees_min=20&industries=information technology&state=Ohio&limit=50&ordering=-created_at
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
WHERE co.name ILIKE '%Bandura%'
    AND c.seniority ILIKE '%C suite%'
    AND co.employees_count >= 20
    AND array_to_string(co.industries, ',') ILIKE '%information technology%'
    AND cm.state ILIKE '%Ohio%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 50
OFFSET 0;

-- Query 39: With view=simple (returns simplified contact data)
-- GET /api/v1/contacts/?view=simple
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
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 40: With view=simple and filters
-- GET /api/v1/contacts/?view=simple&company=Bandura&state=Ohio
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
WHERE co.name ILIKE '%Bandura%'
    AND cm.state ILIKE '%Ohio%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;
