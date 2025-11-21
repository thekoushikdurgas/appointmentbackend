-- ============================================================================
-- Endpoint: GET /api/v1/companies/
-- API Version: v1
-- Description: Return a paginated list of companies using every supported filter parameter.
--              The ORM implementation uses conditional JOINs - only joining CompanyMetadata when filters require it.
--              This optimizes query performance by avoiding unnecessary joins.
-- ============================================================================
--
-- Parameters (All optional):
--   Pagination:
--     limit (integer, >=1) - Number of companies per page
--     offset (integer, >=0) - Zero-based offset into the result set
--     cursor (text) - Opaque cursor token for pagination (base64 encoding of offset)
--     page (integer, >=1) - Optional 1-indexed page number (converts to offset)
--     page_size (integer, >=1) - Explicit page size override
--     distinct (boolean, default: false) - Return distinct companies based on primary key
--
--   Company Fields:
--     name (text) - Case-insensitive substring match against Company.name
--     employees_count (integer, >=0) - Exact match against Company.employees_count
--     employees_min (integer, >=0) - Lower-bound filter for Company.employees_count
--     employees_max (integer, >=0) - Upper-bound filter for Company.employees_count
--     annual_revenue (integer, >=0) - Exact match against Company.annual_revenue
--     annual_revenue_min (integer, >=0) - Lower-bound filter for Company.annual_revenue
--     annual_revenue_max (integer, >=0) - Upper-bound filter for Company.annual_revenue
--     total_funding (integer, >=0) - Exact match against Company.total_funding
--     total_funding_min (integer, >=0) - Lower-bound filter for Company.total_funding
--     total_funding_max (integer, >=0) - Upper-bound filter for Company.total_funding
--     address (text) - Substring match against Company.address
--     company_location (text) - Substring match against Company.text_search (location fields)
--
--   Array Filters (comma-separated for OR logic):
--     industries (text) - Substring match within Company.industries array
--     keywords (text) - Substring match within Company.keywords array
--     technologies (text) - Substring match within Company.technologies array
--
--   Metadata Filters:
--     city (text) - Substring match against CompanyMetadata.city
--     state (text) - Substring match against CompanyMetadata.state
--     country (text) - Substring match against CompanyMetadata.country
--     phone_number (text) - Substring match against CompanyMetadata.phone_number
--     website (text) - Substring match against CompanyMetadata.website
--     linkedin_url (text) - Substring match against CompanyMetadata.linkedin_url
--     facebook_url (text) - Substring match against CompanyMetadata.facebook_url
--     twitter_url (text) - Substring match against CompanyMetadata.twitter_url
--
--   Exclusion Filters (multi-value, case-insensitive):
--     exclude_industries (array of text) - Exclude companies in specified industries
--     exclude_keywords (array of text) - Exclude companies with specified keywords
--     exclude_technologies (array of text) - Exclude companies using specified technologies
--
--   Date Range Filters (ISO datetime format):
--     created_at_after (timestamp) - Filter companies created after this date
--     created_at_before (timestamp) - Filter companies created before this date
--     updated_at_after (timestamp) - Filter companies updated after this date
--     updated_at_before (timestamp) - Filter companies updated before this date
--
--   Search and Ordering:
--     search (text) - Full-text search across multiple fields
--     ordering (text) - Sort results by field. Valid fields: created_at, updated_at, name, 
--                       employees_count, annual_revenue, total_funding. Prepend '-' for descending.
--
-- Response Structure:
--   Returns CursorPage with results array containing CompanyListItem objects.
--   Each result includes company data and optionally metadata data based on JOINs performed.
--
-- Response Codes:
--   200 OK: Companies retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying companies
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Implementation Notes:
--   The CompanyRepository.list_companies() uses conditional JOINs based on filters and ordering:
--   
--   JOIN Decision Logic:
--   1. Minimal query (base_query_minimal): Only companies table
--      - Used when: No metadata filters, no metadata ordering, no metadata search
--      - Returns: (Company, None) - normalized to 2-tuple format
--   
--   2. Metadata join (base_query_with_metadata): Company + CompanyMetadata (LEFT JOIN)
--      - Used when: Metadata filters present OR metadata ordering OR metadata search
--      - Returns: (Company, CompanyMetadata) - normalized to 2-tuple format
--   
--   Filter Application:
--   - When metadata join present: Filters applied directly to joined tables
--   - When no metadata join: Uses EXISTS subqueries for metadata filters (optimized for count queries)
--   
--   Default Ordering:
--   - created_at DESC NULLS LAST (no join required, uses indexed field)
--   - Unlike contacts, companies don't have id DESC fallback (Company.id is not used for ordering)
--   
--   Result Format:
--   - Returns normalized 2-tuple: (Company, CompanyMetadata)
--   - Service layer builds CompanyListItem from the 2-tuple
--
-- Example Usage:
--   GET /api/v1/companies/?limit=25&offset=0
--   GET /api/v1/companies/?name=TechCorp&employees_min=50&ordering=-annual_revenue
--   GET /api/v1/companies/?search=technology&city=San Francisco&limit=50
-- ============================================================================

-- Query 1: Basic query - Get all companies (default pagination, minimal query - no metadata join)
-- GET /api/v1/companies/
-- Note: The ORM uses conditional JOINs. This example shows the minimal query when no metadata filters require joins.
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at
FROM companies co
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 1b: With metadata join (when metadata filters or ordering require it)
-- GET /api/v1/companies/?city=San Francisco
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 2: With limit parameter
-- GET /api/v1/companies/?limit=50
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.created_at DESC NULLS LAST
LIMIT 50
OFFSET 0;

-- Query 3: With offset parameter
-- GET /api/v1/companies/?offset=25
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 25;

-- Query 4: With page parameter (page 2, converts to offset 25)
-- GET /api/v1/companies/?page=2
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 25;

-- Query 5: With distinct=true
-- GET /api/v1/companies/?distinct=true
SELECT DISTINCT ON (co.id)
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.id, co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 6: With ordering=name (ascending)
-- GET /api/v1/companies/?ordering=name
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.name ASC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 7: With ordering=-employees_count (descending)
-- GET /api/v1/companies/?ordering=-employees_count
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
ORDER BY co.employees_count DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 8: With search parameter
-- GET /api/v1/companies/?search=technology
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE (
    co.name ILIKE '%technology%' OR
    co.address ILIKE '%technology%' OR
    co.text_search ILIKE '%technology%' OR
    array_to_string(co.industries, ',') ILIKE '%technology%' OR
    array_to_string(co.keywords, ',') ILIKE '%technology%' OR
    array_to_string(co.technologies, ',') ILIKE '%technology%' OR
    (com.city IS NOT NULL AND com.city ILIKE '%technology%') OR
    (com.state IS NOT NULL AND com.state ILIKE '%technology%') OR
    (com.country IS NOT NULL AND com.country ILIKE '%technology%') OR
    (com.phone_number IS NOT NULL AND com.phone_number ILIKE '%technology%') OR
    (com.website IS NOT NULL AND com.website ILIKE '%technology%')
)
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 9: With name filter
-- GET /api/v1/companies/?name=Acme
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%Acme%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 10: With employees_min filter
-- GET /api/v1/companies/?employees_min=100
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.employees_count >= 100
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 11: With employees range
-- GET /api/v1/companies/?employees_min=100&employees_max=500
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.employees_count >= 100
    AND co.employees_count <= 500
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 12: With annual_revenue_min filter
-- GET /api/v1/companies/?annual_revenue_min=10000000
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.annual_revenue >= 10000000
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 13: With industries filter
-- GET /api/v1/companies/?industries=Technology,Software
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE array_to_string(co.industries, ',') ILIKE '%Technology%'
    OR array_to_string(co.industries, ',') ILIKE '%Software%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 14: With keywords filter
-- GET /api/v1/companies/?keywords=enterprise,saas
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE array_to_string(co.keywords, ',') ILIKE '%enterprise%'
    OR array_to_string(co.keywords, ',') ILIKE '%saas%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 15: With technologies filter
-- GET /api/v1/companies/?technologies=Python,AWS
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE array_to_string(co.technologies, ',') ILIKE '%Python%'
    OR array_to_string(co.technologies, ',') ILIKE '%AWS%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 16: With city filter
-- GET /api/v1/companies/?city=San Francisco
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.city ILIKE '%San Francisco%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 17: With state filter
-- GET /api/v1/companies/?state=California
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.state ILIKE '%California%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 18: With country filter
-- GET /api/v1/companies/?country=United States
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE com.country ILIKE '%United States%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 19: With exclude_industries filter
-- GET /api/v1/companies/?exclude_industries=Retail,Healthcare
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.industries IS NULL 
    OR NOT (
        array_to_string(co.industries, ',') ILIKE '%Retail%' OR
        array_to_string(co.industries, ',') ILIKE '%Healthcare%'
    )
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 20: With created_at_after filter
-- GET /api/v1/companies/?created_at_after=2024-01-01T00:00:00
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.created_at >= '2024-01-01 00:00:00'::timestamp
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 21: With multiple filters combined
-- GET /api/v1/companies/?name=Acme&employees_min=100&industries=Technology&city=San Francisco
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.name ILIKE '%Acme%'
    AND co.employees_count >= 100
    AND array_to_string(co.industries, ',') ILIKE '%Technology%'
    AND com.city ILIKE '%San Francisco%'
ORDER BY co.created_at DESC NULLS LAST
LIMIT 25
OFFSET 0;

-- Query 22: Complex query with multiple filters, search, and ordering
-- GET /api/v1/companies/?search=technology&employees_min=50&annual_revenue_min=5000000&state=California&ordering=-annual_revenue&limit=50
SELECT 
    co.id,
    co.uuid,
    co.name,
    co.employees_count,
    co.annual_revenue,
    co.total_funding,
    co.industries,
    co.keywords,
    co.technologies,
    co.address,
    co.text_search,
    co.created_at,
    co.updated_at,
    com.city,
    com.state,
    com.country,
    com.phone_number,
    com.website,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.company_name_for_emails,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE (
    co.name ILIKE '%technology%' OR
    co.address ILIKE '%technology%' OR
    co.text_search ILIKE '%technology%' OR
    array_to_string(co.industries, ',') ILIKE '%technology%' OR
    array_to_string(co.keywords, ',') ILIKE '%technology%' OR
    array_to_string(co.technologies, ',') ILIKE '%technology%' OR
    (com.city IS NOT NULL AND com.city ILIKE '%technology%') OR
    (com.state IS NOT NULL AND com.state ILIKE '%technology%') OR
    (com.country IS NOT NULL AND com.country ILIKE '%technology%') OR
    (com.phone_number IS NOT NULL AND com.phone_number ILIKE '%technology%') OR
    (com.website IS NOT NULL AND com.website ILIKE '%technology%')
)
    AND co.employees_count >= 50
    AND co.annual_revenue >= 5000000
    AND com.state ILIKE '%California%'
ORDER BY co.annual_revenue DESC NULLS LAST
LIMIT 50
OFFSET 0;

