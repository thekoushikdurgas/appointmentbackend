-- ============================================================================
-- Endpoint: PUT /api/v1/companies/{company_uuid}/
-- API Version: v1
-- Description: Update an existing company record. All fields are optional (partial update). Requires admin authentication and X-Companies-Write-Key header.
-- ============================================================================
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--
-- Request Body Parameters (All optional):
--   $2: name (text, optional) - Company name
--   $3: employees_count (integer, optional) - Number of employees
--   $4: industries (text[], optional) - List of industries
--   $5: keywords (text[], optional) - List of keywords
--   $6: address (text, optional) - Company address
--   $7: annual_revenue (integer, optional) - Annual revenue in dollars
--   $8: total_funding (integer, optional) - Total funding in dollars
--   $9: technologies (text[], optional) - List of technologies
--   $10: text_search (text, optional) - Free-form search text, e.g., location information
--
-- Metadata Parameters (All optional):
--   $11: city (text, optional) - Company city
--   $12: state (text, optional) - Company state
--   $13: country (text, optional) - Company country
--   $14: phone_number (text, optional) - Company phone number
--   $15: website (text, optional) - Company website
--   $16: linkedin_url (text, optional) - Company LinkedIn URL
--   $17: facebook_url (text, optional) - Company Facebook URL
--   $18: twitter_url (text, optional) - Company Twitter URL
--   $19: company_name_for_emails (text, optional) - Company name for emails
--   $20: latest_funding (text, optional) - Latest funding round
--   $21: latest_funding_amount (integer, optional) - Latest funding amount
--   $22: last_raised_at (text, optional) - Last raised date
--
-- Response Structure:
--   Returns CompanyDetail schema with nested metadata object.
--
-- Response Codes:
--   200 OK: Company updated successfully
--   400 Bad Request: Invalid request data
--   401 Unauthorized: Authentication required
--   403 Forbidden: Admin access or write key required
--   404 Not Found: Company not found
--
-- Authentication:
--   Requires admin authentication and X-Companies-Write-Key header.
-- ============================================================================

-- Step 1: Update companies table (only non-NULL values are updated)
UPDATE companies
SET 
    name = COALESCE($2, name),
    employees_count = COALESCE($3, employees_count),
    industries = COALESCE($4, industries),
    keywords = COALESCE($5, keywords),
    address = COALESCE($6, address),
    annual_revenue = COALESCE($7, annual_revenue),
    total_funding = COALESCE($8, total_funding),
    technologies = COALESCE($9, technologies),
    text_search = COALESCE($10, text_search),
    updated_at = NOW()
WHERE uuid = $1
RETURNING *;

-- Step 2: Update or insert companies_metadata (only non-NULL values are updated)
INSERT INTO companies_metadata (
    uuid,
    city,
    state,
    country,
    phone_number,
    website,
    linkedin_url,
    facebook_url,
    twitter_url,
    company_name_for_emails,
    latest_funding,
    latest_funding_amount,
    last_raised_at
) VALUES (
    $1,
    $11,
    $12,
    $13,
    $14,
    $15,
    $16,
    $17,
    $18,
    $19,
    $20,
    $21,
    $22
)
ON CONFLICT (uuid) DO UPDATE SET
    city = COALESCE(EXCLUDED.city, companies_metadata.city),
    state = COALESCE(EXCLUDED.state, companies_metadata.state),
    country = COALESCE(EXCLUDED.country, companies_metadata.country),
    phone_number = COALESCE(EXCLUDED.phone_number, companies_metadata.phone_number),
    website = COALESCE(EXCLUDED.website, companies_metadata.website),
    linkedin_url = COALESCE(EXCLUDED.linkedin_url, companies_metadata.linkedin_url),
    facebook_url = COALESCE(EXCLUDED.facebook_url, companies_metadata.facebook_url),
    twitter_url = COALESCE(EXCLUDED.twitter_url, companies_metadata.twitter_url),
    company_name_for_emails = COALESCE(EXCLUDED.company_name_for_emails, companies_metadata.company_name_for_emails),
    latest_funding = COALESCE(EXCLUDED.latest_funding, companies_metadata.latest_funding),
    latest_funding_amount = COALESCE(EXCLUDED.latest_funding_amount, companies_metadata.latest_funding_amount),
    last_raised_at = COALESCE(EXCLUDED.last_raised_at, companies_metadata.last_raised_at)
RETURNING *;

-- Step 3: Retrieve the complete updated company record with metadata
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
WHERE co.uuid = $1;

