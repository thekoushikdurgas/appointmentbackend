-- ============================================================================
-- Endpoint: GET /api/v1/companies/company/{company_uuid}/contacts/
-- API Version: v1
-- Description: Return a paginated list of contacts for a specific company using contact-specific filters.
-- ============================================================================
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--
-- Query Parameters (All optional):
--   Pagination:
--     limit (integer, >=1) - Number of contacts per page
--     offset (integer, >=0) - Zero-based offset into the result set
--     cursor (text) - Opaque cursor token for pagination
--     page (integer, >=1) - Optional 1-indexed page number
--     page_size (integer, >=1) - Explicit page size override
--     distinct (boolean, default: false) - Return distinct contacts
--
--   Contact Identity Filters:
--     first_name (text) - Case-insensitive substring match against Contact.first_name
--     last_name (text) - Case-insensitive substring match against Contact.last_name
--     title (text) - Case-insensitive substring match against Contact.title
--     seniority (text) - Case-insensitive substring match against Contact.seniority
--     department (text) - Substring match against Contact.departments array
--     email_status (text) - Case-insensitive substring match against Contact.email_status
--     email (text) - Case-insensitive substring match against Contact.email
--     contact_location (text) - Contact text-search column
--
--   Contact Metadata Filters:
--     work_direct_phone (text) - Substring match against ContactMetadata.work_direct_phone
--     home_phone (text) - Substring match against ContactMetadata.home_phone
--     mobile_phone (text) - Substring match against Contact.mobile_phone
--     other_phone (text) - Substring match against ContactMetadata.other_phone
--     city (text) - Substring match against ContactMetadata.city
--     state (text) - Substring match against ContactMetadata.state
--     country (text) - Substring match against ContactMetadata.country
--     person_linkedin_url (text) - Substring match against ContactMetadata.linkedin_url
--     website (text) - Substring match against ContactMetadata.website
--     facebook_url (text) - Substring match against ContactMetadata.facebook_url
--     twitter_url (text) - Substring match against ContactMetadata.twitter_url
--     stage (text) - Substring match against ContactMetadata.stage
--
--   Exclusion Filters:
--     exclude_titles (text[]) - Exclude contacts whose title matches any value
--     exclude_contact_locations (text[]) - Exclude contacts whose location matches
--     exclude_seniorities (text[]) - Exclude contacts whose seniority matches
--     exclude_departments (text[]) - Exclude contacts whose departments include any value
--
--   Temporal Filters:
--     created_at_after (timestamp) - Filter contacts created after timestamp
--     created_at_before (timestamp) - Filter contacts created before timestamp
--     updated_at_after (timestamp) - Filter contacts updated after timestamp
--     updated_at_before (timestamp) - Filter contacts updated before timestamp
--
--   Search and Ordering:
--     search (text) - General-purpose search term
--     ordering (text) - Sort field (e.g., 'first_name', '-created_at')
--
-- Response Structure:
--   Returns CursorPage[ContactListItem] with nested company and metadata objects.
--
-- Example Usage:
--   SELECT co.*, comp.*, com.*, comp_meta.*
--   FROM contacts co
--   LEFT JOIN companies comp ON co.company_id = comp.uuid
--   LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
--   LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
--   WHERE co.company_id = $1
--     AND co.title ILIKE '%engineer%'
--     AND co.seniority = 'senior'
--   ORDER BY co.created_at DESC
--   LIMIT 25 OFFSET 0;
-- ============================================================================

SELECT 
    co.id,
    co.uuid,
    co.first_name,
    co.last_name,
    co.email,
    co.title,
    co.seniority,
    co.departments,
    co.email_status,
    co.mobile_phone,
    co.text_search as contact_location,
    co.created_at,
    co.updated_at,
    -- Company summary
    comp.uuid as company_uuid,
    comp.name as company_name,
    -- Contact metadata
    com.work_direct_phone,
    com.home_phone,
    com.other_phone,
    com.city,
    com.state,
    com.country,
    com.linkedin_url as person_linkedin_url,
    com.website,
    com.facebook_url,
    com.twitter_url,
    com.stage
FROM contacts co
LEFT JOIN companies comp ON co.company_id = comp.uuid
LEFT JOIN contacts_metadata com ON co.uuid = com.uuid
LEFT JOIN companies_metadata comp_meta ON comp.uuid = comp_meta.uuid
WHERE co.company_id = $1
    -- Add filter conditions here based on query parameters
    -- Example filters:
    -- AND co.title ILIKE '%engineer%'
    -- AND co.seniority = 'senior'
    -- AND co.created_at >= '2024-01-01'
ORDER BY co.created_at DESC
LIMIT 25 OFFSET 0;

