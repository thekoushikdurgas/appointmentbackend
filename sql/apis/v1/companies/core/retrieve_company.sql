-- ============================================================================
-- Endpoint: GET /api/v1/companies/{company_uuid}/
-- API Version: v1
-- Description: Fetch details for a single company by UUID with all related metadata information.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     company_uuid (text, required) - Company UUID (not the integer ID)
--
-- Response Structure:
--   Returns CompanyDetail schema with nested metadata object.
--   All fields from companies and companies_metadata tables.
--
-- Response Codes:
--   200 OK: Company retrieved successfully
--   401 Unauthorized: Authentication required
--   404 Not Found: Company with specified UUID not found
--   500 Internal Server Error: Error occurred while retrieving company
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/companies/550e8400-e29b-41d4-a716-446655440000/
-- ============================================================================

-- ORM Implementation Notes:
--   The CompanyRepository.get_company_with_relations() always uses base_query_with_metadata():
--   - Always joins CompanyMetadata table (LEFT JOIN)
--   - Returns 2-tuple: (Company, CompanyMetadata)
--   - Service layer builds CompanyDetail from the 2-tuple
--   - Unlike list_companies, this endpoint always performs metadata join (no conditional logic)

-- Query: Retrieve company by UUID with metadata
-- GET /api/v1/companies/{company_uuid}/
-- Note: Always uses LEFT JOIN to CompanyMetadata (unlike list_companies which uses conditional logic)
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
WHERE co.uuid = $1;

