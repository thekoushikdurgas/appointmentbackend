-- ============================================================================
-- Migration: Add linkedin_urls column to user_exports table
-- Date: 2024
-- Description: Adds linkedin_urls text[] column to track original LinkedIn URLs
--              used for LinkedIn exports. This allows users to see what URLs
--              they originally requested when viewing export records.
-- ============================================================================

-- Add linkedin_urls column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'user_exports'
        AND column_name = 'linkedin_urls'
    ) THEN
        ALTER TABLE public.user_exports
        ADD COLUMN linkedin_urls text[];
        
        COMMENT ON COLUMN public.user_exports.linkedin_urls IS 
            'LinkedIn URLs used for LinkedIn exports. Only populated for exports created via POST /api/v2/linkedin/export.';
        
        RAISE NOTICE 'Column linkedin_urls added to user_exports table';
    ELSE
        RAISE NOTICE 'Column linkedin_urls already exists in user_exports table';
    END IF;
END $$;

