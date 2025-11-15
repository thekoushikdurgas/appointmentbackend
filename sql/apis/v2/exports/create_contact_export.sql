-- ============================================================================
-- Endpoint: POST /api/v2/exports/contacts/export
-- API Version: v2
-- Description: Create a CSV export of selected contacts. Accepts a list of contact UUIDs and generates a CSV file containing all contact, company, contact metadata, and company metadata fields. Returns a signed temporary download URL that expires after 24 hours.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--   $2: contact_uuids (text[], required, min: 1) - List of contact UUIDs to export
--
-- Request Body Fields:
--   contact_uuids (array[string], required, min: 1) - List of contact UUIDs to export. At least one UUID is required.
--
-- Response Structure:
-- {
--   "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
--   "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=...",
--   "expires_at": "2024-12-20T10:30:00Z",
--   "contact_count": 2,
--   "status": "completed"
-- }
--
-- Response Codes:
--   201 Created: Export created successfully
--   400 Bad Request: No contact UUIDs provided or invalid request data
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: CSV generation failed or export creation failed
--
-- Note: The CSV file is generated in the application layer using the contact data.
-- The export record is stored in the user_exports table with status='completed'.
-- The download URL includes a signed token that expires after 24 hours.
--
-- CSV Fields Included:
--   Contact fields: contact_uuid, contact_first_name, contact_last_name, contact_company_id,
--   contact_email, contact_title, contact_departments, contact_mobile_phone, contact_email_status,
--   contact_text_search, contact_seniority, contact_created_at, contact_updated_at
--   Contact metadata: contact_metadata_linkedin_url, contact_metadata_facebook_url,
--   contact_metadata_twitter_url, contact_metadata_website, contact_metadata_work_direct_phone,
--   contact_metadata_home_phone, contact_metadata_other_phone, contact_metadata_city,
--   contact_metadata_state, contact_metadata_country, contact_metadata_stage
--   Company fields: company_uuid, company_name, company_employees_count, company_industries,
--   company_keywords, company_address, company_annual_revenue, company_total_funding,
--   company_technologies, company_text_search, company_created_at, company_updated_at
--   Company metadata: company_metadata_linkedin_url, company_metadata_facebook_url,
--   company_metadata_twitter_url, company_metadata_website, company_metadata_company_name_for_emails,
--   company_metadata_phone_number, company_metadata_latest_funding, company_metadata_latest_funding_amount,
--   company_metadata_last_raised_at, company_metadata_city, company_metadata_state, company_metadata_country
--
-- Example Usage:
--   POST /api/v2/exports/contacts/export
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "contact_uuids": [
--       "abc123-def456-ghi789",
--       "xyz789-uvw456-rst123"
--     ]
--   }
-- ============================================================================

-- Step 1: Retrieve contact data for export
-- The application layer queries contacts and related data using the provided UUIDs
SELECT 
    c.uuid as contact_uuid,
    c.first_name as contact_first_name,
    c.last_name as contact_last_name,
    c.company_id as contact_company_id,
    c.email as contact_email,
    c.title as contact_title,
    c.departments as contact_departments,
    c.mobile_phone as contact_mobile_phone,
    c.email_status as contact_email_status,
    c.text_search as contact_text_search,
    c.seniority as contact_seniority,
    c.created_at as contact_created_at,
    c.updated_at as contact_updated_at,
    cm.linkedin_url as contact_metadata_linkedin_url,
    cm.facebook_url as contact_metadata_facebook_url,
    cm.twitter_url as contact_metadata_twitter_url,
    cm.website as contact_metadata_website,
    cm.work_direct_phone as contact_metadata_work_direct_phone,
    cm.home_phone as contact_metadata_home_phone,
    cm.other_phone as contact_metadata_other_phone,
    cm.city as contact_metadata_city,
    cm.state as contact_metadata_state,
    cm.country as contact_metadata_country,
    cm.stage as contact_metadata_stage,
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
FROM contacts c
LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT JOIN companies co ON c.company_id = co.uuid
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.uuid = ANY($2::text[]);

-- Step 2: Insert export record into user_exports table
-- This is done in the application layer after CSV generation
INSERT INTO user_exports (
    export_id,
    user_id,
    export_type,
    contact_count,
    contact_uuids,
    status,
    created_at,
    expires_at,
    download_url,
    download_token
) VALUES (
    gen_random_uuid()::text,
    $1,
    'contacts'::export_type,
    (SELECT COUNT(*) FROM contacts WHERE uuid = ANY($2::text[])),
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
    contact_count,
    contact_uuids,
    status,
    created_at,
    expires_at,
    download_url;

