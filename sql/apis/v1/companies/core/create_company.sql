-- ============================================================================
-- Endpoint: POST /api/v1/companies/
-- API Version: v1
-- Description: Create a new company record using the CompanyCreate schema.
-- ============================================================================
--
-- Parameters: (All optional)
--   $1: uuid (text, optional) - Company UUID. If not provided, one will be generated.
--   $2: name (text, optional) - Company name
--   $3: employees_count (integer, optional) - Number of employees
--   $4: industries (text[], optional) - List of industries
--   $5: keywords (text[], optional) - List of keywords
--   $6: address (text, optional) - Company address
--   $7: annual_revenue (integer, optional) - Annual revenue in dollars
--   $8: total_funding (integer, optional) - Total funding in dollars
--   $9: technologies (text[], optional) - List of technologies
--   $10: text_search (text, optional) - Free-form search text, e.g., location information
--   $11: created_at (timestamp, optional) - Creation timestamp (defaults to NOW())
--   $12: updated_at (timestamp, optional) - Update timestamp (defaults to NOW())
--
-- Metadata Parameters: (All optional)
--   $13: city (text, optional) - Company city
--   $14: state (text, optional) - Company state
--   $15: country (text, optional) - Company country
--   $16: phone_number (text, optional) - Company phone number
--   $17: website (text, optional) - Company website
--   $18: linkedin_url (text, optional) - Company LinkedIn URL
--   $19: facebook_url (text, optional) - Company Facebook URL
--   $20: twitter_url (text, optional) - Company Twitter URL
--   $21: company_name_for_emails (text, optional) - Company name for emails
--   $22: latest_funding (text, optional) - Latest funding round
--   $23: latest_funding_amount (integer, optional) - Latest funding amount
--   $24: last_raised_at (text, optional) - Last raised date
--
-- Response Structure:
--   Returns CompanyDetail schema with nested metadata object.
--
-- Authentication:
--   Requires admin authentication and X-Companies-Write-Key header.
-- ============================================================================

-- Step 1: Insert into companies table
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
    COALESCE($1, gen_random_uuid()::text),
    $2,
    $3,
    $4,
    $5,
    $6,
    $7,
    $8,
    $9,
    $10,
    COALESCE($11, NOW()),
    COALESCE($12, NOW())
)
RETURNING *;

-- Step 2: Insert into companies_metadata table (if metadata provided)
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
    $1,  -- Use the same UUID from companies table
    $13,
    $14,
    $15,
    $16,
    $17,
    $18,
    $19,
    $20,
    $21,
    $22,
    $23,
    $24
)
ON CONFLICT (uuid) DO UPDATE SET
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    country = EXCLUDED.country,
    phone_number = EXCLUDED.phone_number,
    website = EXCLUDED.website,
    linkedin_url = EXCLUDED.linkedin_url,
    facebook_url = EXCLUDED.facebook_url,
    twitter_url = EXCLUDED.twitter_url,
    company_name_for_emails = EXCLUDED.company_name_for_emails,
    latest_funding = EXCLUDED.latest_funding,
    latest_funding_amount = EXCLUDED.latest_funding_amount,
    last_raised_at = EXCLUDED.last_raised_at
RETURNING *;

-- Step 3: Retrieve the complete company record with metadata
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

