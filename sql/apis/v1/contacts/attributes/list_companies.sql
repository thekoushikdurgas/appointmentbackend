-- ============================================================================
-- Endpoint: GET /api/v1/contacts/company/
-- API Version: v1
-- Description: Return company names directly from Company table.
--              This endpoint queries ONLY the Company table and ignores all contact filters.
--              Only uses: distinct, limit, offset, ordering, search parameters.
-- ============================================================================
--
-- Parameters:
--   Query Parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term
--
--   Note: ContactFilterParams are NOT supported - this endpoint queries only Company table.
--
-- Response Structure:
--   Returns array of strings: ["Company A", "Company B", ...]
--
-- Response Codes:
--   200 OK: Companies retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying companies
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- ORM Implementation Notes:
--   The ContactRepository.list_company_names_simple() queries ONLY the Company table:
--   - No contact filters are supported (ignores ContactFilterParams)
--   - Queries Company.name directly: SELECT Company.name FROM companies
--   - Filters out NULL and empty names
--   - Applies search, distinct, ordering, pagination
--   - Default ordering: Company.name ASC (not created_at)
--
--   This is different from other attribute endpoints that support contact filters.
--   The endpoint does NOT accept ContactFilterParams - only AttributeListParams.

-- Example Usage:
--   GET /api/v1/contacts/company/
--   GET /api/v1/contacts/company/?search=Tech&limit=50
--   GET /api/v1/contacts/company/?ordering=-value&offset=25
-- ============================================================================

-- Query 1: Basic query - Get all distinct companies (queries Company table directly)
-- GET /api/v1/contacts/company/
-- Note: Queries ONLY Company table - no contact joins, no contact filters
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 2: With search parameter
-- GET /api/v1/contacts/company/?search=Tech&distinct=true
-- Note: Search is applied to Company.name column only
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
    AND co.name ILIKE '%Tech%'
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false (allows duplicates)
-- GET /api/v1/contacts/company/?distinct=false
-- Note: When distinct=false, returns all company names including duplicates
SELECT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending, explicit)
-- GET /api/v1/contacts/company/?ordering=value
-- Note: Default ordering is Company.name ASC when no ordering specified
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/company/?ordering=-value
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name DESC
LIMIT 25
OFFSET 0;

-- Query 6: With limit parameter
-- GET /api/v1/contacts/company/?limit=50
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 50
OFFSET 0;

-- Query 7: With offset parameter
-- GET /api/v1/contacts/company/?offset=25
SELECT DISTINCT co.name as value
FROM companies co
WHERE co.name IS NOT NULL
    AND TRIM(co.name) != ''
ORDER BY co.name ASC
LIMIT 25
OFFSET 25;

-- ============================================================================
-- IMPORTANT: Contact Filters Are NOT Supported
-- ============================================================================
-- This endpoint uses list_company_names_simple() which queries ONLY the Company table.
-- Contact filters (ContactFilterParams) are IGNORED by this endpoint.
-- 
-- The endpoint accepts only AttributeListParams:
--   - distinct (boolean)
--   - limit (integer)
--   - offset (integer)
--   - ordering (text: 'value' or '-value')
--   - search (text: searches Company.name only)
--
-- All queries shown above (Queries 1-7) demonstrate the correct implementation.
-- Any queries that show contact joins or contact filters are incorrect and have been removed.
-- ============================================================================
