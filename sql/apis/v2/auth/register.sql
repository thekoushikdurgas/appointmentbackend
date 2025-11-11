-- ============================================================================
-- Endpoint: POST /api/v2/auth/register/
-- API Version: v2
-- Description: Register a new user account and receive access tokens. A user profile is automatically created upon registration.
-- ============================================================================
--
-- Parameters:
--   $1: name (text, required) - User's full name (max 255 characters)
--   $2: email (text, required) - Valid email address (must be unique)
--   $3: hashed_password (text, required) - Bcrypt hashed password
--   $4: user_id (text, required) - UUID for the user (generated in application)
--
-- Response Codes:
--   201 Created: Registration successful
--   400 Bad Request: Invalid request data, email already exists, or password validation failed
--
-- Example Usage:
--   INSERT INTO users (id, email, hashed_password, name, is_active, created_at)
--   VALUES ($4, $2, $3, $1, true, NOW())
--   RETURNING id, email, name, is_active, created_at;
--
--   INSERT INTO user_profiles (user_id, role, created_at)
--   VALUES ($4, 'Member', NOW())
--   RETURNING id, user_id, role, created_at;
-- ============================================================================

-- Step 1: Check if email already exists
SELECT id, email 
FROM users 
WHERE email = $2;

-- Step 2: If email doesn't exist, insert new user
-- Note: user_id ($4) should be a UUID generated in the application
INSERT INTO users (id, email, hashed_password, name, is_active, created_at)
VALUES ($4, $2, $3, $1, true, NOW())
RETURNING id, email, name, is_active, created_at, updated_at, last_sign_in_at;

-- Step 3: Create user profile automatically
INSERT INTO user_profiles (user_id, role, notifications, created_at)
VALUES ($4, 'Member', '{}'::jsonb, NOW())
RETURNING id, user_id, job_title, bio, timezone, avatar_url, notifications, role, created_at, updated_at;

