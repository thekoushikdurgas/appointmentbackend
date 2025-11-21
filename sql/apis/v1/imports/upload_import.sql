-- ============================================================================
-- Endpoint: POST /api/v1/contacts/import/
-- API Version: v1
-- Description: Start a background contacts import using a CSV file.
-- ============================================================================
--
-- Parameters:
--   Body Parameters:
--     $1: job_id (text, required) - Unique job identifier (UUID hex string)
--     $2: file_name (text, required) - Original filename of the uploaded CSV
--     $3: file_path (text, required) - Path where the file is stored on the server
--     $4: total_rows (integer, optional, default: 0) - Total number of rows in the CSV
--
-- File Requirements:
--   - Format: CSV (Comma-Separated Values)
--   - File must not be empty
--   - File name is required
--
-- Response Structure:
--   Returns ImportJobDetail with job_id, file_name, file_path, total_rows, status, timestamps.
--
-- Response Codes:
--   202 Accepted: Import job created and queued
--   400 Bad Request: Empty file or missing filename
--   401 Unauthorized: Authentication required
--   403 Forbidden: Admin access required
--   422 Unprocessable Entity: File name is required
--   500 Internal Server Error: Failed to store file or create job
--
-- Authentication:
--   Required - Bearer token (admin) in Authorization header
--
-- Example Usage:
--   POST /api/v1/contacts/import/
--   Content-Type: multipart/form-data
--   Authorization: Bearer <admin_token>
--   
--   Form data:
--     file: <CSV file>
-- ============================================================================

INSERT INTO contact_import_jobs (
    job_id,
    file_name,
    file_path,
    total_rows,
    processed_rows,
    status,
    error_count,
    message,
    created_at,
    updated_at
)
VALUES (
    $1,
    $2,
    $3,
    COALESCE($4, 0),
    0,
    'pending',
    0,
    NULL,
    NOW(),
    NOW()
)
RETURNING 
    id,
    job_id,
    file_name,
    file_path,
    total_rows,
    processed_rows,
    status,
    error_count,
    message,
    created_at,
    updated_at,
    completed_at;

