-- ============================================================================
-- Endpoint: GET /api/v1/contacts/
-- API Version: v1
-- Description: Return a paginated list of contacts using every supported filter parameter.
-- ============================================================================
--
-- Parameters (All optional):
--   Pagination:
--     limit (integer, >=1) - Number of contacts per page
--     offset (integer, >=0) - Zero-based offset into the result set
--     cursor (text) - Opaque cursor token for pagination (base64 encoding of offset)
--     page (integer, >=1) - Optional 1-indexed page number (converts to offset)
--     page_size (integer, >=1) - Explicit page size override
--     distinct (boolean, default: false) - Return distinct contacts based on primary key
--     view (text) - View mode: 'simple' returns ContactSimpleItem, omit for full ContactListItem
--
--   Contact Fields, Company Filters, Company Metrics, Array Filters, Metadata Filters,
--   Social Media Filters, Exclusion Filters, Search, Ordering, Date Range Filters
--   See full parameter documentation in the header comments above.
--
-- Response Structure:
--   Returns CursorPage with results array containing ContactListItem or ContactSimpleItem objects.
-- ============================================================================

-- Query 1: Basic query - Get all contacts (default pagination)
-- GET /api/v1/contacts/
c

-- Query 2: With limit parameter
-- GET /api/v1/contacts/?limit=50
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
LIMIT 50
OFFSET 0;

-- Query 3: With offset parameter
-- GET /api/v1/contacts/?offset=25
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
OFFSET 25;

-- Query 4: With page parameter (page 2, converts to offset 25)
-- GET /api/v1/contacts/?page=2
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
OFFSET 25;

-- Query 5: With limit and offset
-- GET /api/v1/contacts/?limit=10&offset=20
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
LIMIT 10
OFFSET 20;

-- Query 6: With distinct=true
-- GET /api/v1/contacts/?distinct=true
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
ORDER BY c.id, c.created_at DESC NULLS LAST
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

-- Query 8: With ordering=-last_name (descending)
-- GET /api/v1/contacts/?ordering=-last_name
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

-- Query 13: With first_name filter
-- GET /api/v1/contacts/?first_name=Patrick
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
WHERE c.first_name ILIKE '%Patrick%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 14: With last_name filter
-- GET /api/v1/contacts/?last_name=McGarry
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
WHERE c.last_name ILIKE '%McGarry%'
ORDER BY c.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 15: With title filter
-- GET /api/v1/contacts/?title=Chief Technology Officer
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
WHERE c.title ILIKE '%Chief Technology Officer%'
ORDER BY c.created_at DESC NULLS LAST
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
