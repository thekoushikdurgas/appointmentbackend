-- ============================================================================
-- Endpoint: GET /api/v1/contacts/import/{job_id}/
-- API Version: v1
-- Description: Fetch the status of a queued import job with optional embedded error payloads.
-- ============================================================================
--
-- Parameters:
--   $1: job_id (text, required) - Import job identifier
--   $2: include_errors (boolean, optional, default: false) - Whether to include error details
--
-- Query Parameters:
--   include_errors (boolean, optional, default: false): When false, returns ImportJobDetail. When true, returns ImportJobWithErrors with embedded error payloads.
--
-- Response Codes:
--   200 OK: Job details retrieved
--   401 Unauthorized: Authentication required
--   404 Not Found: Import job not found
--
-- Example Usage (without errors):
--   SELECT id, job_id, file_name, file_path, total_rows, processed_rows, status, error_count, message, created_at, updated_at, completed_at
--   FROM contact_import_jobs
--   WHERE job_id = $1;
--
-- Example Usage (with errors):
--   SELECT j.id, j.job_id, j.file_name, j.file_path, j.total_rows, j.processed_rows, j.status, j.error_count, j.message, j.created_at, j.updated_at, j.completed_at,
--          json_agg(json_build_object('row_number', e.row_number, 'error_message', e.error_message, 'payload', e.payload)) FILTER (WHERE e.id IS NOT NULL) as errors
--   FROM contact_import_jobs j
--   LEFT JOIN contact_import_errors e ON j.id = e.job_id
--   WHERE j.job_id = $1
--   GROUP BY j.id, j.job_id, j.file_name, j.file_path, j.total_rows, j.processed_rows, j.status, j.error_count, j.message, j.created_at, j.updated_at, j.completed_at;
-- ============================================================================

-- Query without errors (include_errors = false)
SELECT 
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
    completed_at
FROM contact_import_jobs
WHERE job_id = $1;

-- Query with errors (include_errors = true)
-- Note: This query aggregates errors as a JSON array
SELECT 
    j.id,
    j.job_id,
    j.file_name,
    j.file_path,
    j.total_rows,
    j.processed_rows,
    j.status,
    j.error_count,
    j.message,
    j.created_at,
    j.updated_at,
    j.completed_at,
    COALESCE(
        json_agg(
            json_build_object(
                'row_number', e.row_number,
                'error_message', e.error_message,
                'payload', e.payload,
                'created_at', e.created_at
            )
            ORDER BY e.row_number
        ) FILTER (WHERE e.id IS NOT NULL),
        '[]'::json
    ) as errors
FROM contact_import_jobs j
LEFT JOIN contact_import_errors e ON j.id = e.job_id
WHERE j.job_id = $1
GROUP BY j.id, j.job_id, j.file_name, j.file_path, j.total_rows, j.processed_rows, j.status, j.error_count, j.message, j.created_at, j.updated_at, j.completed_at;

