-- ============================================================================
-- Endpoint: POST /api/v2/auth/refresh/
-- API Version: v2
-- Description: Refresh an expired access token using a refresh token. Returns new access and refresh tokens (token rotation).
-- ============================================================================
--
-- Parameters:
--   $1: refresh_token (text, required) - Valid refresh token
--
-- Request Body:
--   {
--     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
--   }
--
-- Response Codes:
--   200 OK: Token refresh successful
--   400 Bad Request: Invalid or expired refresh token
--
-- Note: Token validation and user lookup is performed in the application layer.
-- The refresh token is decoded to extract the user ID, then a new token pair is generated.
-- This SQL shows the user lookup that would occur after token validation.
--
-- Example Usage:
--   -- After decoding refresh token to get user_id:
--   SELECT id, email, is_active
--   FROM users
--   WHERE id = $2;  -- $2 is user_id extracted from token
-- ============================================================================

-- Note: Token validation happens in application layer (JWT decoding)
-- After validation, retrieve user by ID extracted from token
SELECT id, email, is_active, last_sign_in_at, created_at, updated_at
FROM users
WHERE id = $2;  -- $2 is user_id extracted from decoded refresh token

