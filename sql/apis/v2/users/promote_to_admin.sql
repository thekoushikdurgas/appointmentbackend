-- ============================================================================
-- Endpoint: POST /api/v2/users/promote-to-admin/
-- API Version: v2
-- Description: Promote the currently authenticated user to admin role. This endpoint allows authenticated users to change their role to "Admin". The operation is logged for audit purposes.
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--
-- Response Structure:
-- {
--   "id": "user-uuid",
--   "email": "user@example.com",
--   "name": "User Name",
--   "is_active": true,
--   "is_admin": true,
--   "profile": {
--     "id": "profile-id",
--     "user_id": "user-uuid",
--     "job_title": "Software Engineer",
--     "bio": "User biography",
--     "timezone": "America/New_York",
--     "avatar_url": "https://example.com/avatar.jpg",
--     "notifications": {...},
--     "role": "Admin",
--     "created_at": "2024-01-15T10:30:00Z",
--     "updated_at": "2024-01-15T11:45:00Z"
--   },
--   "created_at": "2024-01-15T10:30:00Z",
--   "updated_at": "2024-01-15T11:45:00Z"
-- }
--
-- Response Codes:
--   200 OK: User promoted to admin successfully
--   401 Unauthorized: Authentication required
--   404 Not Found: User profile not found (default profile will be created)
--   500 Internal Server Error: Failed to promote user to admin
--
-- Note: This endpoint updates the user's role in the user_profiles table.
-- If the user doesn't have a profile, a default profile is created first.
-- The is_admin field in the users table may also be updated depending on implementation.
--
-- Example Usage:
--   POST /api/v2/users/promote-to-admin/
--   Authorization: Bearer <access_token>
-- ============================================================================

-- Step 1: Update user_profiles table to set role to 'Admin'
-- If profile doesn't exist, it will be created in the application layer first
UPDATE user_profiles
SET 
    role = 'Admin',
    updated_at = NOW()
WHERE user_id = $1
RETURNING 
    id,
    user_id,
    job_title,
    bio,
    timezone,
    avatar_url,
    notifications,
    role,
    created_at,
    updated_at;

-- Step 2: Retrieve updated user and profile
SELECT 
    u.id,
    u.email,
    u.name,
    u.is_active,
    u.is_admin,
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

-- Note: If the user doesn't have a profile, the application layer creates
-- a default profile first before updating the role. The is_admin field
-- in the users table may also be updated depending on the implementation.

