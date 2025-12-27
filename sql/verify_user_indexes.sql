-- ============================================================================
-- Verify User Table Indexes
-- ============================================================================
-- This script verifies that all required indexes exist for user-related tables
-- Run this to check if indexes need to be created

-- Check existing indexes on users table
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('users', 'user_profiles', 'user_history')
ORDER BY tablename, indexname;

-- Verify specific indexes exist
-- Users table indexes
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'users' AND indexname = 'idx_users_email'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_users_email_status;

SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'users' AND indexname = 'idx_users_uuid'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_users_uuid_status;

-- User profiles table indexes
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'user_profiles' AND indexname = 'idx_user_profiles_user_id'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_user_profiles_user_id_status;

-- User history table indexes
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'user_history' AND indexname = 'idx_user_history_user_id'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_user_history_user_id_status;

SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'user_history' AND indexname = 'idx_user_history_event_type'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_user_history_event_type_status;

SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'user_history' AND indexname = 'idx_user_history_created_at'
        ) THEN 'EXISTS'
        ELSE 'MISSING'
    END as idx_user_history_created_at_status;

-- ============================================================================
-- Create Missing Indexes (if needed)
-- ============================================================================
-- Uncomment and run these if indexes are missing:

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_uuid ON public.users(uuid);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_history_user_id ON public.user_history(user_id);
CREATE INDEX IF NOT EXISTS idx_user_history_event_type ON public.user_history(event_type);
CREATE INDEX IF NOT EXISTS idx_user_history_created_at ON public.user_history(created_at);

-- After creating indexes, analyze tables to update statistics
ANALYZE public.users;
ANALYZE public.user_profiles;
ANALYZE public.user_history;

