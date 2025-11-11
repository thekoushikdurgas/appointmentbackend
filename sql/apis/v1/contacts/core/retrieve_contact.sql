-- ============================================================================
-- Endpoint: GET /api/v1/contacts/{contact_id}/
-- API Version: v1
-- Description: Fetch details for a single contact by primary key.
-- ============================================================================
--
-- Parameters:
--   $1: contact_id (integer, required) - Contact primary key (id)
--
-- Response Structure:
--   Returns ContactDetail schema with nested company and metadata objects.
--
-- Example Usage:
--   SELECT c.*, co.*, cm.*, com.*
--   FROM contacts c
--   LEFT JOIN companies co ON c.company_id = co.uuid
--   LEFT JOIN contacts_metadata cm ON c.uuid = cm.uuid
--   LEFT JOIN companies_metadata com ON co.uuid = com.uuid
--   WHERE c.id = $1;
-- ============================================================================

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
    -- Company fields
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
    -- Contact metadata fields
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
    -- Company metadata fields
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
WHERE c.id = $1;

