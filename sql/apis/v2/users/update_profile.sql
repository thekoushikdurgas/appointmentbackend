-- ============================================================================
-- Endpoint: PUT /api/v2/users/profile/
-- API Version: v2
-- Description: Update the profile information for the currently authenticated user. All fields are optional - only provided fields will be updated (partial update).
-- ============================================================================
--
-- Parameters:
--   $1: user_id (text, required) - User ID from authenticated session
--   $2: name (text, optional, max 255 chars) - User's full name
--   $3: job_title (text, optional, max 255 chars) - User's job title
--   $4: bio (text, optional) - User's biography
--   $5: timezone (text, optional, max 100 chars) - User's timezone (e.g., "America/New_York")
--   $6: avatar_url (text, optional) - URL to user's avatar image
--   $7: notifications (jsonb, optional) - User notification preferences (merged with existing)
--   $8: role (text, optional, max 50 chars) - User's role
--
-- Response Codes:
--   200 OK: Profile updated successfully
--   400 Bad Request: Invalid data provided
--   401 Unauthorized: Authentication required
--
-- Note: Only non-NULL parameters should be included in the UPDATE statement.
-- The application layer handles merging notifications with existing preferences.
--
-- Example Usage:
--   UPDATE users
--   SET name = $2, updated_at = NOW()
--   WHERE id = $1;
--
--   UPDATE user_profiles
--   SET job_title = COALESCE($3, job_title),
--       bio = COALESCE($4, bio),
--       timezone = COALESCE($5, timezone),
--       avatar_url = COALESCE($6, avatar_url),
--       notifications = COALESCE($7, notifications),
--       role = COALESCE($8, role),
--       updated_at = NOW()
--   WHERE user_id = $1
--   RETURNING *;
-- ============================================================================

-- Step 1: Update user name if provided
UPDATE users
SET 
    name = COALESCE($2, name),
    updated_at = NOW()
WHERE id = $1;

-- Step 2: Update profile fields (only non-NULL values are updated)
UPDATE user_profiles
SET 
    job_title = COALESCE($3, job_title),
    bio = COALESCE($4, bio),
    timezone = COALESCE($5, timezone),
    avatar_url = COALESCE($6, avatar_url),
    notifications = COALESCE($7, notifications),
    role = COALESCE($8, role),
    updated_at = NOW()
WHERE user_id = $1
RETURNING id, user_id, job_title, bio, timezone, avatar_url, notifications, role, created_at, updated_at;

-- Step 3: Retrieve updated user and profile
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

