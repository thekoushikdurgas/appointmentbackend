-- ============================================================================
-- Endpoint: DELETE /api/v1/companies/{company_uuid}/
-- API Version: v1
-- Description: Delete a company record. Requires admin authentication and X-Companies-Write-Key header.
-- ============================================================================
--
-- Path Parameters:
--   $1: company_uuid (text, required) - Company UUID identifier
--
-- Response Structure:
--   Returns 204 No Content (no response body) on success.
--
-- Response Codes:
--   204 No Content: Company deleted successfully
--   401 Unauthorized: Authentication required
--   403 Forbidden: Admin access and X-Companies-Write-Key header required
--   404 Not Found: Company not found
--   500 Internal Server Error: Error occurred while deleting company
--
-- Authentication:
--   Required - Bearer token (admin) and X-Companies-Write-Key header
--
-- Example Usage:
--   DELETE /api/v1/companies/550e8400-e29b-41d4-a716-446655440000/
--   Authorization: Bearer <admin_token>
--   X-Companies-Write-Key: <write_key>
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

