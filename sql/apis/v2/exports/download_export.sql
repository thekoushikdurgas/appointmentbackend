-- ============================================================================
-- Endpoint: GET /api/v2/exports/{export_id}/download
-- API Version: v2
-- Description: Download a CSV export file using a signed URL. The token must be valid and the export must belong to the requesting user. The export must not have expired. Returns the CSV file as a file download.
-- ============================================================================
--
-- Path Parameters:
--   $1: export_id (text, required) - Export UUID identifier
--
-- Query Parameters:
--   token (text, required) - Signed URL token for authentication (validated in application layer)
--
-- Parameters:
--   $2: user_id (text, required) - User ID from authenticated session (for ownership verification)
--
-- Response:
--   Returns the CSV file as a file download with Content-Type: text/csv
--   The file is streamed from the file_path stored in the user_exports table
--
-- Response Codes:
--   200 OK: File downloaded successfully
--   401 Unauthorized: Invalid or expired download token, or authentication required
--   403 Forbidden: User does not own this export
--   404 Not Found: Export not found
--   410 Gone: Export has expired
--   500 Internal Server Error: File not found or read error
--
-- Note: The signed URL token is validated in the application layer using verify_signed_url().
-- The token must contain the export_id and user_id, and must not be expired.
-- The export must have status='completed' to be downloadable.
-- The file is served from the file_path stored in the user_exports table.
--
-- Example Usage:
--   GET /api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
--   Authorization: Bearer <access_token>
-- ============================================================================

-- Query 1: Retrieve export record for download with ownership verification
-- GET /api/v2/exports/{export_id}/download?token=...
SELECT 
    export_id,
    user_id,
    export_type,
    file_path,
    file_name,
    status,
    expires_at,
    download_token
FROM user_exports
WHERE export_id = $1
    AND user_id = $2  -- Verify ownership
    AND status = 'completed'::export_status
    AND expires_at > NOW();  -- Verify not expired

-- Note: The application layer performs additional validation:
-- 1. Verifies the signed URL token matches the export_id and user_id
-- 2. Checks that the file_path exists and is readable
-- 3. Streams the CSV file to the client with appropriate headers
-- If the query returns no rows, the export either doesn't exist, doesn't belong to the user,
-- is not completed, or has expired. The application layer handles the appropriate error response.

