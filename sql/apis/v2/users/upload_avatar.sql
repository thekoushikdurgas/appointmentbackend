-- ============================================================================
-- Endpoint: POST /api/v2/users/profile/avatar/
-- API Version: v2
-- Description: Upload an avatar image file for the currently authenticated user.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--   $2: avatar_url (text, required) - URL/path to the uploaded avatar file
--
-- File Requirements:
--   - File Types: JPEG, PNG, GIF, or WebP
--   - Maximum Size: 5MB
--   - Validation: Both file extension and file content (magic bytes) are validated
--
-- Response Codes:
--   200 OK: Avatar uploaded successfully
--   400 Bad Request: Invalid file type or size
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error saving file
--
-- Example Usage:
--   UPDATE user_profiles
--   SET avatar_url = $2, updated_at = NOW()
--   WHERE user_id = $1
--   RETURNING *;
-- ============================================================================

-- Update avatar URL in user profile
UPDATE user_profiles
SET 
    avatar_url = $2,
    updated_at = NOW()
WHERE user_id = $1
RETURNING id, user_id, job_title, bio, timezone, avatar_url, notifications, role, created_at, updated_at;

-- Retrieve updated profile with user info
SELECT 
    u.id,
    u.email,
    u.name,
    u.is_active,
    u.created_at,
    u.updated_at,
    up.id as profile_id,
    up.job_title,
    up.bio,
    up.timezone,
    up.avatar_url,
    up.notifications,
    up.role,
    up.created_at as profile_created_at,
    up.updated_at as profile_updated_at
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
WHERE u.id = $1;

