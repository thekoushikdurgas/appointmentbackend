-- ============================================================================
-- Endpoint: POST /api/v2/auth/login/
-- API Version: v2
-- Description: Authenticate a user and receive access tokens. Updates the user's last_sign_in_at timestamp upon successful login.
-- ============================================================================
--
-- Parameters:
--   $1: email (text, required) - User's email address (must be valid email format)
--   $2: password (text, required) - User's password (verified against hashed_password in application)
--
-- Response Codes:
--   200 OK: Login successful
--   400 Bad Request: Invalid credentials, missing fields, or account disabled
--
-- Example Usage:
--   SELECT id, email, hashed_password, name, is_active, last_sign_in_at, created_at
--   FROM users
--   WHERE email = $1;
--
--   UPDATE users
--   SET last_sign_in_at = NOW()
--   WHERE id = $3;  -- $3 is the user ID from the SELECT query
-- ============================================================================

-- Step 1: Retrieve user by email
SELECT id, email, hashed_password, name, is_active, last_sign_in_at, created_at, updated_at
FROM users
WHERE email = $1;

-- Step 2: Update last_sign_in_at timestamp (after password verification in application)
-- Note: $3 should be the user ID from the SELECT query above
UPDATE users
SET last_sign_in_at = NOW(), updated_at = NOW()
WHERE id = $3
RETURNING id, email, name, is_active, last_sign_in_at, created_at, updated_at;

