-- ============================================================================
-- Endpoint: POST /api/v1/contacts/
-- API Version: v1
-- Description: Create a new contact record using the ContactCreate schema.
-- ============================================================================
--
-- Parameters:
--   $1: uuid (text, optional) - Contact UUID. If not provided, one will be generated.
--   $2: first_name (text, optional) - Contact's first name
--   $3: last_name (text, optional) - Contact's last name
--   $4: company_id (text, optional) - UUID of the related company
--   $5: email (text, optional) - Contact's email address
--   $6: title (text, optional) - Contact's job title
--   $7: departments (text[], optional) - Array of department names
--   $8: mobile_phone (text, optional) - Contact's mobile phone number
--   $9: email_status (text, optional) - Email verification status
--   $10: text_search (text, optional) - Free-form search text, e.g., location information
--   $11: seniority (text, optional) - Contact's seniority level
--
-- All body fields are optional. Requires admin authentication and X-Contacts-Write-Key header.
--
-- Response Codes:
--   201 Created: Contact created successfully
--   400 Bad Request: Invalid request data
--   401 Unauthorized: Authentication required
--   403 Forbidden: Admin access or write key required
--
-- Example Usage:
--   INSERT INTO contacts (uuid, first_name, last_name, company_id, email, title, departments, mobile_phone, email_status, text_search, seniority, created_at, updated_at)
--   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
--   RETURNING *;
-- ============================================================================

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
)
VALUES (
    COALESCE($1, uuid_generate_v4()::text),
    $2,
    $3,
    $4,
    $5,
    $6,
    $7,
    $8,
    $9,
    $10,
    COALESCE($11, '_'),
    NOW(),
    NOW()
)
RETURNING 
    id,
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
    updated_at;

