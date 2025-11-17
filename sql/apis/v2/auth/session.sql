-- ============================================================================
-- Endpoint: GET /api/v2/auth/session/
-- API Version: v2
-- Description: Get the current authenticated user's session information. Useful for checking token validity.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID extracted from JWT token
--
-- Response Structure:
-- {
--   "user": {
--     "id": "uuid",
--     "email": "user@example.com"
--   },
--   "last_sign_in_at": "2024-01-15T10:30:00Z"
-- }
--
-- Example Usage:
--   SELECT id, email, last_sign_in_at
--   FROM users
--   WHERE id = $1;
-- ============================================================================

SELECT id, email, last_sign_in_at, created_at, updated_at, is_active
FROM users
WHERE id = $1;

