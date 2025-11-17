-- ============================================================================
-- Endpoint: GET /api/v1/companies/{company_id}/
-- API Version: v1
-- Description: Fetch details for a single company by primary key.
-- ============================================================================
--
-- Parameters:
--   $1: company_id (integer, required) - Company primary key (id)
--
-- Response Structure:
--   Returns CompanyDetail schema with nested metadata object.
--
-- Example Usage:
--   SELECT co.*, com.*
--   FROM companies co
--   LEFT JOIN companies_metadata com ON co.uuid = com.uuid
--   WHERE co.id = $1;
-- ============================================================================

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
    -- Company metadata fields
    com.id as metadata_id,
    com.uuid as metadata_uuid,
    com.linkedin_url,
    com.facebook_url,
    com.twitter_url,
    com.website,
    com.company_name_for_emails,
    com.phone_number,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city,
    com.state,
    com.country
FROM companies co
LEFT JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.id = $1;

