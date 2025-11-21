-- ============================================================================
-- Endpoint: POST /api/v2/linkedin/
-- API Version: v2
-- Description: Create or update contacts and companies based on LinkedIn URL. If a record with the LinkedIn URL already exists, it will be updated. Otherwise, new records will be created. The endpoint automatically determines whether the LinkedIn URL belongs to a person (ContactMetadata) or company (CompanyMetadata) by checking existing records.
-- ============================================================================
--
-- Request Body Parameters:
--   url (text, required) - LinkedIn URL. Will be set as linkedin_url in the appropriate metadata table.
--   contact_data (object, optional) - Contact fields to create/update. All standard contact fields are supported.
--   contact_metadata (object, optional) - Contact metadata fields. The linkedin_url will automatically be set to the url value.
--   company_data (object, optional) - Company fields to create/update. All standard company fields are supported.
--   company_metadata (object, optional) - Company metadata fields. The linkedin_url will automatically be set to the url value.
--
-- Response Structure:
--   Returns LinkedInUpsertResponse containing:
--   - created: boolean - Whether new records were created
--   - updated: boolean - Whether existing records were updated
--   - contacts: List of ContactWithRelations (Contact, ContactMetadata, Company, CompanyMetadata)
--   - companies: List of CompanyWithRelations (Company, CompanyMetadata, and related contacts)
--
-- Response Codes:
--   200 OK: Records created/updated successfully
--   400 Bad Request: LinkedIn URL is empty or invalid, or request body is malformed
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred during create/update operation
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   POST /api/v2/linkedin/
--   Content-Type: application/json
--   Authorization: Bearer <access_token>
--   
--   {
--     "url": "https://www.linkedin.com/in/jane-smith",
--     "contact_data": {
--       "first_name": "Jane",
--       "last_name": "Smith",
--       "email": "jane.smith@example.com",
--       "title": "Product Manager"
--     },
--     "contact_metadata": {
--       "city": "New York",
--       "state": "NY",
--       "country": "US"
--     }
--   }
-- ============================================================================

-- ORM Implementation Notes:
--   The LinkedInService.upsert_by_url() performs the following steps:
--   1. Normalize the LinkedIn URL (trim whitespace, validate)
--   2. Check if contact exists with exact LinkedIn URL match (find_contact_by_exact_linkedin_url)
--   3. Check if company exists with exact LinkedIn URL match (find_company_by_exact_linkedin_url)
--   4. Handle contact upsert:
--      - If contact exists: UPDATE contacts and contacts_metadata tables
--      - If contact doesn't exist: INSERT into contacts and contacts_metadata tables
--   5. Handle company upsert:
--      - If company exists: UPDATE companies and companies_metadata tables
--      - If company doesn't exist: INSERT into companies and companies_metadata tables
--   6. Fetch updated/created records with all relations
--   7. Commit transaction
--
--   The service layer handles:
--   - UUID generation if not provided
--   - Timestamp management (created_at, updated_at)
--   - Data normalization (empty strings, placeholder values)
--   - Setting linkedin_url in metadata automatically

-- ============================================================================
-- Query 1: Check if Contact Exists by Exact LinkedIn URL
-- ============================================================================
-- POST /api/v2/linkedin/ - Check for existing contact
-- Note: Uses exact match (ILIKE without wildcards) to find existing contact
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
    -- Contact metadata
    cm.id as contact_metadata_id,
    cm.uuid as contact_metadata_uuid,
    cm.linkedin_url,
    cm.facebook_url,
    cm.twitter_url,
    cm.website,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.stage,
    -- Company (if exists)
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries,
    co.keywords,
    co.address,
    co.annual_revenue,
    co.total_funding,
    co.technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at,
    -- Company metadata (if exists)
    com.id as company_metadata_id,
    com.uuid as company_metadata_uuid,
    com.linkedin_url as company_linkedin_url,
    com.facebook_url as company_facebook_url,
    com.twitter_url as company_twitter_url,
    com.website as company_website,
    com.company_name_for_emails,
    com.phone_number,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country
FROM contacts c
LEFT OUTER JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT OUTER JOIN companies co ON c.company_id = co.uuid
LEFT OUTER JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 
    cm.linkedin_url IS NOT NULL
    AND cm.linkedin_url != '_'
    AND cm.linkedin_url ILIKE $1  -- $1 is the normalized linkedin_url (exact match)
LIMIT 1;

-- ============================================================================
-- Query 2: Check if Company Exists by Exact LinkedIn URL
-- ============================================================================
-- POST /api/v2/linkedin/ - Check for existing company
-- Note: Uses exact match (ILIKE without wildcards) to find existing company
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
    -- Company metadata
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
LEFT OUTER JOIN companies_metadata com ON co.uuid = com.uuid
WHERE 
    com.linkedin_url IS NOT NULL
    AND com.linkedin_url ILIKE $1  -- $1 is the normalized linkedin_url (exact match)
LIMIT 1;

-- ============================================================================
-- Query 3: UPDATE Existing Contact
-- ============================================================================
-- POST /api/v2/linkedin/ - Update contact fields
-- Note: The ORM updates fields individually using setattr(). This shows the equivalent SQL.
--       Only non-None fields from contact_data are updated.
UPDATE contacts
SET 
    first_name = COALESCE($2, first_name),  -- $2 from contact_data
    last_name = COALESCE($3, last_name),
    company_id = COALESCE($4, company_id),
    email = COALESCE($5, email),
    title = COALESCE($6, title),
    departments = COALESCE($7, departments),
    mobile_phone = COALESCE($8, mobile_phone),
    email_status = COALESCE($9, email_status),
    text_search = COALESCE($10, text_search),
    seniority = COALESCE($11, seniority),
    updated_at = NOW()
WHERE uuid = $1;  -- $1 is the contact UUID

-- ============================================================================
-- Query 4: UPDATE Existing Contact Metadata
-- ============================================================================
-- POST /api/v2/linkedin/ - Update contact metadata
-- Note: linkedin_url is always updated to the normalized URL value
UPDATE contacts_metadata
SET 
    linkedin_url = $2,  -- Always set to normalized URL
    facebook_url = COALESCE($3, facebook_url),  -- $3 from contact_metadata
    twitter_url = COALESCE($4, twitter_url),
    website = COALESCE($5, website),
    work_direct_phone = COALESCE($6, work_direct_phone),
    home_phone = COALESCE($7, home_phone),
    other_phone = COALESCE($8, other_phone),
    city = COALESCE($9, city),
    state = COALESCE($10, state),
    country = COALESCE($11, country),
    stage = COALESCE($12, stage)
WHERE uuid = $1;  -- $1 is the contact UUID

-- ============================================================================
-- Query 5: INSERT New Contact
-- ============================================================================
-- POST /api/v2/linkedin/ - Create new contact
-- Note: UUID is generated by service layer if not provided (uuid4().hex)
--       created_at and updated_at are set to current timestamp
--       seniority defaults to '_' (PLACEHOLDER_VALUE) if not provided
INSERT INTO contacts (
    uuid,
    first_name,
    last_name,
    company_id,
    email,
    title,
    departments,
    mobile_phone,
    email_status,
    text_search,
    seniority,
    created_at,
    updated_at
) VALUES (
    $1,   -- uuid (generated or provided)
    $2,   -- first_name from contact_data
    $3,   -- last_name from contact_data
    $4,   -- company_id from contact_data
    $5,   -- email from contact_data
    $6,   -- title from contact_data
    $7,   -- departments from contact_data (array)
    $8,   -- mobile_phone from contact_data
    $9,   -- email_status from contact_data
    $10,  -- text_search from contact_data
    COALESCE($11, '_'),  -- seniority from contact_data (defaults to '_')
    NOW(),  -- created_at
    NOW()   -- updated_at
);

-- ============================================================================
-- Query 6: INSERT New Contact Metadata
-- ============================================================================
-- POST /api/v2/linkedin/ - Create new contact metadata
-- Note: linkedin_url is always set to the normalized URL value
--       uuid must match the contact UUID
INSERT INTO contacts_metadata (
    uuid,
    linkedin_url,
    facebook_url,
    twitter_url,
    website,
    work_direct_phone,
    home_phone,
    other_phone,
    city,
    state,
    country,
    stage
) VALUES (
    $1,   -- uuid (must match contact UUID)
    $2,   -- linkedin_url (normalized URL)
    $3,   -- facebook_url from contact_metadata
    $4,   -- twitter_url from contact_metadata
    $5,   -- website from contact_metadata
    $6,   -- work_direct_phone from contact_metadata
    $7,   -- home_phone from contact_metadata
    $8,   -- other_phone from contact_metadata
    $9,   -- city from contact_metadata
    $10,  -- state from contact_metadata
    $11,  -- country from contact_metadata
    $12   -- stage from contact_metadata
);

-- ============================================================================
-- Query 7: UPDATE Existing Company
-- ============================================================================
-- POST /api/v2/linkedin/ - Update company fields
-- Note: The ORM updates fields individually using setattr(). This shows the equivalent SQL.
--       Only non-None fields from company_data are updated.
UPDATE companies
SET 
    name = COALESCE($2, name),  -- $2 from company_data
    employees_count = COALESCE($3, employees_count),
    industries = COALESCE($4, industries),  -- array
    keywords = COALESCE($5, keywords),  -- array
    address = COALESCE($6, address),
    annual_revenue = COALESCE($7, annual_revenue),
    total_funding = COALESCE($8, total_funding),
    technologies = COALESCE($9, technologies),  -- array
    text_search = COALESCE($10, text_search),
    updated_at = NOW()
WHERE uuid = $1;  -- $1 is the company UUID

-- ============================================================================
-- Query 8: UPDATE Existing Company Metadata
-- ============================================================================
-- POST /api/v2/linkedin/ - Update company metadata
-- Note: linkedin_url is always updated to the normalized URL value
UPDATE companies_metadata
SET 
    linkedin_url = $2,  -- Always set to normalized URL
    facebook_url = COALESCE($3, facebook_url),  -- $3 from company_metadata
    twitter_url = COALESCE($4, twitter_url),
    website = COALESCE($5, website),
    company_name_for_emails = COALESCE($6, company_name_for_emails),
    phone_number = COALESCE($7, phone_number),
    latest_funding = COALESCE($8, latest_funding),
    latest_funding_amount = COALESCE($9, latest_funding_amount),
    last_raised_at = COALESCE($10, last_raised_at),
    city = COALESCE($11, city),
    state = COALESCE($12, state),
    country = COALESCE($13, country)
WHERE uuid = $1;  -- $1 is the company UUID

-- ============================================================================
-- Query 9: INSERT New Company
-- ============================================================================
-- POST /api/v2/linkedin/ - Create new company
-- Note: UUID is generated by service layer if not provided (uuid4().hex)
--       created_at and updated_at are set to current timestamp
INSERT INTO companies (
    uuid,
    name,
    employees_count,
    industries,
    keywords,
    address,
    annual_revenue,
    total_funding,
    technologies,
    text_search,
    created_at,
    updated_at
) VALUES (
    $1,   -- uuid (generated or provided)
    $2,   -- name from company_data
    $3,   -- employees_count from company_data
    $4,   -- industries from company_data (array)
    $5,   -- keywords from company_data (array)
    $6,   -- address from company_data
    $7,   -- annual_revenue from company_data
    $8,   -- total_funding from company_data
    $9,   -- technologies from company_data (array)
    $10,  -- text_search from company_data
    NOW(),  -- created_at
    NOW()   -- updated_at
);

-- ============================================================================
-- Query 10: INSERT New Company Metadata
-- ============================================================================
-- POST /api/v2/linkedin/ - Create new company metadata
-- Note: linkedin_url is always set to the normalized URL value
--       uuid must match the company UUID
INSERT INTO companies_metadata (
    uuid,
    linkedin_url,
    facebook_url,
    twitter_url,
    website,
    company_name_for_emails,
    phone_number,
    latest_funding,
    latest_funding_amount,
    last_raised_at,
    city,
    state,
    country
) VALUES (
    $1,   -- uuid (must match company UUID)
    $2,   -- linkedin_url (normalized URL)
    $3,   -- facebook_url from company_metadata
    $4,   -- twitter_url from company_metadata
    $5,   -- website from company_metadata
    $6,   -- company_name_for_emails from company_metadata
    $7,   -- phone_number from company_metadata
    $8,   -- latest_funding from company_metadata
    $9,   -- latest_funding_amount from company_metadata
    $10,  -- last_raised_at from company_metadata
    $11,  -- city from company_metadata
    $12,  -- state from company_metadata
    $13   -- country from company_metadata
);

-- ============================================================================
-- Query 11: Fetch Updated/Created Contact with Relations (after upsert)
-- ============================================================================
-- POST /api/v2/linkedin/ - Retrieve contact after upsert
-- Note: Same query structure as Query 1, used to fetch the updated/created contact
--       with all related data for the response
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
    -- Contact metadata
    cm.id as contact_metadata_id,
    cm.uuid as contact_metadata_uuid,
    cm.linkedin_url,
    cm.facebook_url,
    cm.twitter_url,
    cm.website,
    cm.work_direct_phone,
    cm.home_phone,
    cm.other_phone,
    cm.city,
    cm.state,
    cm.country,
    cm.stage,
    -- Company (if exists)
    co.id as company_id_db,
    co.uuid as company_uuid,
    co.name as company_name,
    co.employees_count,
    co.industries,
    co.keywords,
    co.address,
    co.annual_revenue,
    co.total_funding,
    co.technologies,
    co.text_search as company_text_search,
    co.created_at as company_created_at,
    co.updated_at as company_updated_at,
    -- Company metadata (if exists)
    com.id as company_metadata_id,
    com.uuid as company_metadata_uuid,
    com.linkedin_url as company_linkedin_url,
    com.facebook_url as company_facebook_url,
    com.twitter_url as company_twitter_url,
    com.website as company_website,
    com.company_name_for_emails,
    com.phone_number,
    com.latest_funding,
    com.latest_funding_amount,
    com.last_raised_at,
    com.city as company_city,
    com.state as company_state,
    com.country as company_country
FROM contacts c
LEFT OUTER JOIN contacts_metadata cm ON c.uuid = cm.uuid
LEFT OUTER JOIN companies co ON c.company_id = co.uuid
LEFT OUTER JOIN companies_metadata com ON co.uuid = com.uuid
WHERE c.uuid = $1;  -- $1 is the contact UUID

-- ============================================================================
-- Query 12: Fetch Updated/Created Company with Relations (after upsert)
-- ============================================================================
-- POST /api/v2/linkedin/ - Retrieve company after upsert
-- Note: Same query structure as Query 2, used to fetch the updated/created company
--       with all related data for the response
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
    -- Company metadata
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
LEFT OUTER JOIN companies_metadata com ON co.uuid = com.uuid
WHERE co.uuid = $1;  -- $1 is the company UUID

-- ============================================================================
-- Example Upsert Scenarios
-- ============================================================================

-- Example 1: Create New Contact
-- Request: { "url": "https://www.linkedin.com/in/new-person", "contact_data": {...}, "contact_metadata": {...} }
-- 
-- Flow:
--   1. Query 1: Check if contact exists → No match
--   2. Query 5: INSERT new contact
--   3. Query 6: INSERT new contact metadata (with linkedin_url)
--   4. Query 11: Fetch created contact with relations
--   5. Response: { "created": true, "updated": false, "contacts": [...], "companies": [] }

-- Example 2: Update Existing Contact
-- Request: { "url": "https://www.linkedin.com/in/existing-person", "contact_data": {...} }
-- 
-- Flow:
--   1. Query 1: Check if contact exists → Match found
--   2. Query 3: UPDATE existing contact
--   3. Query 4: UPDATE existing contact metadata (linkedin_url always updated)
--   4. Query 11: Fetch updated contact with relations
--   5. Response: { "created": false, "updated": true, "contacts": [...], "companies": [] }

-- Example 3: Create New Company
-- Request: { "url": "https://www.linkedin.com/company/new-company", "company_data": {...}, "company_metadata": {...} }
-- 
-- Flow:
--   1. Query 2: Check if company exists → No match
--   2. Query 9: INSERT new company
--   3. Query 10: INSERT new company metadata (with linkedin_url)
--   4. Query 12: Fetch created company with relations
--   5. Query 3 (from search_by_url.sql): Fetch related contacts for company
--   6. Response: { "created": true, "updated": false, "contacts": [], "companies": [...] }

-- Example 4: Update Existing Company
-- Request: { "url": "https://www.linkedin.com/company/existing-company", "company_data": {...} }
-- 
-- Flow:
--   1. Query 2: Check if company exists → Match found
--   2. Query 7: UPDATE existing company
--   3. Query 8: UPDATE existing company metadata (linkedin_url always updated)
--   4. Query 12: Fetch updated company with relations
--   5. Query 3 (from search_by_url.sql): Fetch related contacts for company
--   6. Response: { "created": false, "updated": true, "contacts": [], "companies": [...] }

-- ============================================================================
-- Transaction Notes
-- ============================================================================
--
-- All queries are executed within a single database transaction:
--   - session.begin() - Start transaction
--   - Multiple INSERT/UPDATE queries
--   - session.commit() - Commit transaction (or rollback on error)
--
-- This ensures atomicity: either all changes succeed or all are rolled back.

-- ============================================================================
-- Data Normalization
-- ============================================================================
--
-- The service layer performs data normalization before database operations:
--   - Empty strings are converted to None (NULL)
--   - Placeholder values ('_') are converted to None for most fields
--   - LinkedIn URL is trimmed and validated
--   - UUIDs are generated if not provided (uuid4().hex)
--   - Timestamps are set to current UTC time
--
-- This normalization ensures data consistency and prevents placeholder values
-- from being stored in the database.

