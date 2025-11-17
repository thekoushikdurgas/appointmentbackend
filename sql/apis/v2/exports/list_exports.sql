-- ============================================================================
-- Endpoint: GET /api/v2/exports/
-- API Version: v2
-- Description: Get a list of all export jobs for the current user. Returns exports sorted by creation date (newest first). Only returns exports owned by the authenticated user.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--
-- Response Structure:
-- {
--   "exports": [
--     {
--       "export_id": "f4b8c3f5-1111-4f9b-aaaa-123456789abc",
--       "export_type": "contacts",
--       "contact_count": 2,
--       "company_count": 0,
--       "status": "completed",
--       "created_at": "2024-12-19T10:30:00Z",
--       "expires_at": "2024-12-20T10:30:00Z",
--       "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-1111-4f9b-aaaa-123456789abc/download?token=..."
--     },
--     {
--       "export_id": "a1b2c3d4-2222-4f9b-bbbb-987654321def",
--       "export_type": "companies",
--       "contact_count": 0,
--       "company_count": 5,
--       "status": "completed",
--       "created_at": "2024-12-18T15:45:00Z",
--       "expires_at": "2024-12-19T15:45:00Z",
--       "download_url": "http://54.87.173.234:8000/api/v2/exports/a1b2c3d4-2222-4f9b-bbbb-987654321def/download?token=..."
--     }
--   ]
-- }
--
-- Response Codes:
--   200 OK: Exports retrieved successfully
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: An error occurred while processing the request
--
-- Example Usage:
--   GET /api/v2/exports/
--   Authorization: Bearer <access_token>
-- ============================================================================

-- Query 1: List all exports for user, sorted by creation date (newest first)
-- GET /api/v2/exports/
SELECT 
    export_id,
    export_type,
    contact_count,
    company_count,
    status,
    created_at,
    expires_at,
    download_url
FROM user_exports
WHERE user_id = $1
ORDER BY created_at DESC NULLS LAST;

-- Query 2: List only completed exports
-- GET /api/v2/exports/?status=completed
SELECT 
    export_id,
    export_type,
    contact_count,
    company_count,
    status,
    created_at,
    expires_at,
    download_url
FROM user_exports
WHERE user_id = $1
    AND status = 'completed'::export_status
ORDER BY created_at DESC NULLS LAST;

-- Query 3: List only contact exports
-- GET /api/v2/exports/?type=contacts
SELECT 
    export_id,
    export_type,
    contact_count,
    company_count,
    status,
    created_at,
    expires_at,
    download_url
FROM user_exports
WHERE user_id = $1
    AND export_type = 'contacts'::export_type
ORDER BY created_at DESC NULLS LAST;

-- Query 4: List only company exports
-- GET /api/v2/exports/?type=companies
SELECT 
    export_id,
    export_type,
    contact_count,
    company_count,
    status,
    created_at,
    expires_at,
    download_url
FROM user_exports
WHERE user_id = $1
    AND export_type = 'companies'::export_type
ORDER BY created_at DESC NULLS LAST;

