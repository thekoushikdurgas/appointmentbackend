-- ============================================================================
-- Query Optimization Indexes for Large Tables (50M Contacts, 5M Companies)
-- ============================================================================
-- This file contains indexes to optimize query performance for large datasets
-- Run these indexes after the base table creation
-- ============================================================================

-- ============================================================================
-- Phase 1: Composite Indexes for Common Filter Combinations
-- ============================================================================

-- Task 1.1: Composite indexes for contacts table
-- Optimize company contact queries with seniority and title filters
CREATE INDEX IF NOT EXISTS idx_contacts_company_seniority_title 
    ON public.contacts (company_id, seniority, title) 
    WHERE company_id IS NOT NULL;

-- Optimize email filtering by company
CREATE INDEX IF NOT EXISTS idx_contacts_company_email_status 
    ON public.contacts (company_id, email_status) 
    WHERE company_id IS NOT NULL AND email_status IS NOT NULL;

-- Optimize date-range queries with company filter
CREATE INDEX IF NOT EXISTS idx_contacts_created_at_company 
    ON public.contacts (created_at, company_id) 
    WHERE company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_updated_at_company 
    ON public.contacts (updated_at, company_id) 
    WHERE company_id IS NOT NULL;

-- Composite index for company + title filtering (common pattern)
CREATE INDEX IF NOT EXISTS idx_contacts_company_title 
    ON public.contacts (company_id, title) 
    WHERE company_id IS NOT NULL AND title IS NOT NULL;

-- Composite index for email + email_status filtering
CREATE INDEX IF NOT EXISTS idx_contacts_email_status_filter 
    ON public.contacts (email, email_status) 
    WHERE email IS NOT NULL AND email_status IS NOT NULL;

-- ============================================================================
-- Task 1.2: Metadata Table Indexes
-- ============================================================================

-- Contacts metadata indexes
CREATE INDEX IF NOT EXISTS idx_contacts_metadata_city 
    ON public.contacts_metadata (city) 
    WHERE city IS NOT NULL AND city != '_';

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_state 
    ON public.contacts_metadata (state) 
    WHERE state IS NOT NULL AND state != '_';

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_country 
    ON public.contacts_metadata (country) 
    WHERE country IS NOT NULL AND country != '_';

-- Composite index for location filtering
CREATE INDEX IF NOT EXISTS idx_contacts_metadata_location 
    ON public.contacts_metadata (city, state, country) 
    WHERE city IS NOT NULL AND city != '_';

-- Companies metadata indexes
CREATE INDEX IF NOT EXISTS idx_companies_metadata_city 
    ON companies_metadata (city) 
    WHERE city IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_state 
    ON companies_metadata (state) 
    WHERE state IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_country 
    ON companies_metadata (country) 
    WHERE country IS NOT NULL;

-- Index for website domain filtering (using expression for domain extraction)
CREATE INDEX IF NOT EXISTS idx_companies_metadata_website 
    ON companies_metadata (website) 
    WHERE website IS NOT NULL;

-- Composite index for company location filtering
CREATE INDEX IF NOT EXISTS idx_companies_metadata_location 
    ON companies_metadata (city, state, country) 
    WHERE city IS NOT NULL;

-- Index for funding amount filtering
CREATE INDEX IF NOT EXISTS idx_companies_metadata_funding_amount 
    ON companies_metadata (latest_funding_amount) 
    WHERE latest_funding_amount IS NOT NULL;

-- ============================================================================
-- Task 1.3: Foreign Key Index Optimization
-- ============================================================================

-- Verify company_id index exists (already exists, but ensure it's optimal)
-- The existing idx_contacts_company_id should be sufficient
-- Add partial index for non-null company_id (if beneficial)
CREATE INDEX IF NOT EXISTS idx_contacts_company_id_not_null 
    ON public.contacts (company_id) 
    WHERE company_id IS NOT NULL;

-- ============================================================================
-- Task 1.4: Text Search Indexes
-- ============================================================================

-- Verify GIN indexes exist (already exist for text_search)
-- Add additional trigram indexes for commonly searched columns

-- Index for first_name + last_name search
CREATE INDEX IF NOT EXISTS idx_contacts_name_search_trgm 
    ON public.contacts USING gin ((first_name || ' ' || COALESCE(last_name, '')) gin_trgm_ops);

-- Index for email search (if not already covered)
CREATE INDEX IF NOT EXISTS idx_contacts_email_trgm 
    ON public.contacts USING gin (email gin_trgm_ops) 
    WHERE email IS NOT NULL;

-- Index for company name search (already exists as idx_companies_name_trgm)
-- Add index for company address search
CREATE INDEX IF NOT EXISTS idx_companies_address_trgm 
    ON companies USING gin (address gin_trgm_ops) 
    WHERE address IS NOT NULL;

-- ============================================================================
-- Additional Performance Indexes
-- ============================================================================

-- Index for contacts by updated_at (for recent updates queries)
CREATE INDEX IF NOT EXISTS idx_contacts_updated_at_desc 
    ON public.contacts (updated_at DESC) 
    WHERE updated_at IS NOT NULL;

-- Index for companies by updated_at
CREATE INDEX IF NOT EXISTS idx_companies_updated_at_desc 
    ON companies (updated_at DESC) 
    WHERE updated_at IS NOT NULL;

-- Composite index for company filtering with employees count
CREATE INDEX IF NOT EXISTS idx_companies_employees_created 
    ON companies (employees_count, created_at) 
    WHERE employees_count IS NOT NULL;

-- Index for company filtering with revenue
CREATE INDEX IF NOT EXISTS idx_companies_revenue_created 
    ON companies (annual_revenue, created_at) 
    WHERE annual_revenue IS NOT NULL;

-- ============================================================================
-- Index Maintenance Notes
-- ============================================================================
-- After creating these indexes:
-- 1. Run ANALYZE on all tables to update statistics
-- 2. Monitor index usage with: 
--    SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
-- 3. Consider REINDEX for GIN indexes periodically
-- 4. Monitor index size and bloat
-- ============================================================================

