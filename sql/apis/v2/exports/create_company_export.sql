-- ============================================================================
-- Endpoint: POST /api/v2/exports/companies/export
-- API Version: v2
-- Description: Create a CSV export of selected companies. Accepts a list of company UUIDs and generates a CSV file containing all company and company metadata fields. Returns a signed temporary download URL that expires after 24 hours.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--   $2: company_uuids (text[], required, min: 1) - List of company UUIDs to export
--
-- Request Body Fields:
--   company_uuids (array[string], required, min: 1) - List of company UUIDs to export. At least one UUID is required.
--
-- Response Structure:
-- {
--   "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
--   "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=...",
--   "expires_at": "2024-12-20T10:30:00Z",
--   "company_count": 2,
--   "status": "completed"
-- }
--
-- Response Codes:
--   201 Created: Export created successfully
--   400 Bad Request: No company UUIDs provided or invalid request data
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: CSV generation failed or export creation failed
--
-- Note: The CSV file is generated in the application layer using the company data.
-- The export record is stored in the user_exports table with status='completed'.
-- The download URL includes a signed token that expires after 24 hours.
--
-- CSV Fields Included:
--   Company fields: company_uuid, company_name, company_employees_count, company_industries,
--   company_keywords, company_address, company_annual_revenue, company_total_funding,
--   company_technologies, company_text_search, company_created_at, company_updated_at
--   Company metadata: company_metadata_linkedin_url, company_metadata_facebook_url,
--   company_metadata_twitter_url, company_metadata_website, company_metadata_company_name_for_emails,
--   company_metadata_phone_number, company_metadata_latest_funding, company_metadata_latest_funding_amount,
--   company_metadata_last_raised_at, company_metadata_city, company_metadata_state, company_metadata_country
--
-- Example Usage:
--   POST /api/v2/exports/companies/export
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "company_uuids": [
--       "abc123-def456-ghi789",
--       "xyz789-uvw456-rst123"
--     ]
--   }
-- ============================================================================

-- Step 1: Retrieve company data for export
-- The application layer queries companies and related data using the provided UUIDs
SELECT 
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count as company_employees_count,
    co.industries as company_industries,
    co.keywords as company_keywords,
    co.address as company_address,
    co.annual_revenue as company_annual_revenue,
    co.total_funding as company_total_funding,
    co.technologies as company_technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at,
    com.linkedin_url as company_metadata_linkedin_url,
    com.facebook_url as company_metadata_facebook_url,
    com.twitter_url as company_metadata_twitter_url,
    com.website as company_metadata_website,
    com.company_name_for_emails as company_metadata_company_name_for_emails,
    com.phone_number as company_metadata_phone_number,
    com.latest_funding as company_metadata_latest_funding,
    com.latest_funding_amount as company_metadata_latest_funding_amount,
    com.last_raised_at as company_metadata_last_raised_at,
    com.city as company_metadata_city,
    com.state as company_metadata_state,
    com.country as company_metadata_country
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.uuid = ANY($2::text[]);

-- Step 2: Insert export record into user_exports table
-- This is done in the application layer after CSV generation
INSERT INTO user_exports (
    export_id,
    user_id,
    export_type,
    company_count,
    company_uuids,
    status,
    created_at,
    expires_at,
    download_url,
    download_token
) VALUES (
    gen_random_uuid()::text,
    $1,
    'companies'::export_type,
    (SELECT COUNT(*) FROM companies WHERE uuid = ANY($2::text[])),
    $2,
    'completed'::export_status,
    NOW(),
    NOW() + INTERVAL '24 hours',
    $3,  -- Generated download URL
    $4   -- Generated download token
)
RETURNING 
    export_id,
    user_id,
    export_type,
    company_count,
    company_uuids,
    status,
    created_at,
    expires_at,
    download_url;

