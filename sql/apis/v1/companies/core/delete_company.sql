-- ============================================================================
-- Endpoint: DELETE /api/v1/companies/{company_uuid}/
-- API Version: v1
-- Description: Delete a company record. Requires admin authentication and X-Companies-Write-Key header.
-- ============================================================================
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--
-- Response Codes:
--   204 No Content: Company deleted successfully (no response body)
--   401 Unauthorized: Authentication required
--   403 Forbidden: Admin access or write key required
--   404 Not Found: Company not found
--
-- Authentication:
--   Requires admin authentication and X-Companies-Write-Key header.
--
-- Note: This operation deletes the company record and associated metadata.
-- Related contacts may have their company_id set to NULL or may be handled
-- by application-level cascade rules.
-- ============================================================================

-- Step 1: Delete company metadata (if exists)
DELETE FROM companies_metadata
WHERE uuid = $1;

-- Step 2: Delete company record
DELETE FROM companies
WHERE uuid = $1
RETURNING uuid;

-- Note: The endpoint returns 204 No Content on success, so no data is returned.
-- The application layer verifies the company exists before deletion.

