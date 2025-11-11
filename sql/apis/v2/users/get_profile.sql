-- ============================================================================
-- Endpoint: GET /api/v2/users/profile/
-- API Version: v2
-- Description: Get the profile information for the currently authenticated user. If a profile doesn't exist, it will be automatically created with default values.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--
-- Response Structure:
-- {
--   "id": "uuid",
--   "name": "John Doe",
--   "email": "user@example.com",
--   "role": "Member",
--   "avatar_url": "https://...",
--   "is_active": true,
--   "job_title": "Software Engineer",
--   "bio": "Bio text",
--   "timezone": "America/New_York",
--   "notifications": {
--     "weeklyReports": true,
--     "newLeadAlerts": true
--   },
--   "created_at": "2024-01-15T10:30:00Z",
--   "updated_at": "2024-01-15T10:30:00Z"
-- }
--
-- Example Usage:
--   SELECT u.id, u.email, u.name, u.is_active, u.created_at, u.updated_at,
--          up.id as profile_id, up.job_title, up.bio, up.timezone, up.avatar_url,
--          up.notifications, up.role, up.created_at as profile_created_at, up.updated_at as profile_updated_at
--   FROM users u
--   LEFT JOIN user_profiles up ON u.id = up.user_id
--   WHERE u.id = $1;
--
--   -- If profile doesn't exist, create it:
--   INSERT INTO user_profiles (user_id, role, notifications, created_at)
--   VALUES ($1, 'Member', '{}'::jsonb, NOW())
--   RETURNING *;
-- ============================================================================

-- Step 1: Retrieve user and profile
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

-- Step 2: If profile doesn't exist (up.id IS NULL), create it:
-- This is handled in the application layer, but the SQL would be:
INSERT INTO user_profiles (user_id, role, notifications, created_at)
VALUES ($1, 'Member', '{}'::jsonb, NOW())
ON CONFLICT (user_id) DO NOTHING
RETURNING id, user_id, job_title, bio, timezone, avatar_url, notifications, role, created_at, updated_at;

