-- ============================================================================
-- Endpoint: GET /api/v1/contacts/import/{job_id}/errors/
-- API Version: v1
-- Description: Retrieve recorded row-level import errors for the specified job.
-- ============================================================================
--
-- Parameters:
--   Path Parameters:
--     job_id (text, required) - Import job identifier
--
-- Response Structure:
--   Returns array of ImportError objects:
--   [
--     {
--       "row_number": 1,
--       "error_message": "Invalid email format",
--       "payload": "{\"first_name\": \"John\", \"email\": \"invalid\"}",
--       "created_at": "2024-01-15T10:30:00Z"
--     },
--     ...
--   ]
--
-- Response Codes:
--   200 OK: Errors retrieved successfully
--   401 Unauthorized: Authentication required
--   404 Not Found: Import job not found
--   500 Internal Server Error: Error occurred while querying errors
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/import/{job_id}/errors/
-- ============================================================================

SELECT 
    e.row_number,
    e.error_message,
    e.payload,
    e.created_at
FROM contact_import_errors e
INNER JOIN contact_import_jobs j ON e.job_id = j.id
WHERE j.job_id = $1
ORDER BY e.row_number ASC;

