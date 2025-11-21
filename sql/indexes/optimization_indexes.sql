-- Enable pg_trgm extension for trigram-based text search (required for GIN indexes with gin_trgm_ops)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_contacts_company_seniority_title
    ON public.contacts (company_id, seniority, title)
    WHERE company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_company_email_status
    ON public.contacts (company_id, email_status)
    WHERE company_id IS NOT NULL AND email_status IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_created_at_company
    ON public.contacts (created_at, company_id)
    WHERE company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_updated_at_company
    ON public.contacts (updated_at, company_id)
    WHERE company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_company_title
    ON public.contacts (company_id, title)
    WHERE company_id IS NOT NULL AND title IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_email_status_filter
    ON public.contacts (email, email_status)
    WHERE email IS NOT NULL AND email_status IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_city
    ON public.contacts_metadata (city)
    WHERE city IS NOT NULL AND city != '_';

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_state
    ON public.contacts_metadata (state)
    WHERE state IS NOT NULL AND state != '_';

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_country
    ON public.contacts_metadata (country)
    WHERE country IS NOT NULL AND country != '_';

CREATE INDEX IF NOT EXISTS idx_contacts_metadata_location
    ON public.contacts_metadata (city, state, country)
    WHERE city IS NOT NULL AND city != '_';

CREATE INDEX IF NOT EXISTS idx_companies_metadata_city
    ON companies_metadata (city)
    WHERE city IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_state
    ON companies_metadata (state)
    WHERE state IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_country
    ON companies_metadata (country)
    WHERE country IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_website
    ON companies_metadata (website)
    WHERE website IS NOT NULL;

-- Critical index for email finder: normalized_domain lookup
CREATE INDEX IF NOT EXISTS idx_companies_metadata_normalized_domain
    ON companies_metadata (normalized_domain)
    WHERE normalized_domain IS NOT NULL;

-- Composite index for faster company lookup by domain (Step 1 optimization)
CREATE INDEX IF NOT EXISTS idx_companies_metadata_normalized_domain_uuid
    ON companies_metadata (normalized_domain, uuid)
    WHERE normalized_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_location
    ON companies_metadata (city, state, country)
    WHERE city IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_metadata_funding_amount
    ON companies_metadata (latest_funding_amount)
    WHERE latest_funding_amount IS NOT NULL;

-- GIN index for contacts_metadata.linkedin_url (for ILIKE pattern matching with leading wildcards)
CREATE INDEX IF NOT EXISTS idx_contacts_metadata_linkedin_url_gin
    ON contacts_metadata USING gin (linkedin_url gin_trgm_ops)
    WHERE linkedin_url IS NOT NULL AND linkedin_url != '_';

-- GIN index for companies_metadata.linkedin_url (for ILIKE pattern matching with leading wildcards)
CREATE INDEX IF NOT EXISTS idx_companies_metadata_linkedin_url_gin
    ON companies_metadata USING gin (linkedin_url gin_trgm_ops)
    WHERE linkedin_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_company_id_not_null
    ON public.contacts (company_id)
    WHERE company_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_name_search_trgm
    ON public.contacts USING gin ((first_name || ' ' || COALESCE(last_name, '')) gin_trgm_ops);

-- Trigram indexes for individual name matching (for ILIKE queries with wildcards)
CREATE INDEX IF NOT EXISTS idx_contacts_first_name_trgm
    ON public.contacts USING gin (first_name gin_trgm_ops)
    WHERE first_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_last_name_trgm
    ON public.contacts USING gin (last_name gin_trgm_ops)
    WHERE last_name IS NOT NULL;

-- Composite index for email finder Step 3 optimization (company_id + names + email)
CREATE INDEX IF NOT EXISTS idx_contacts_company_name_email
    ON public.contacts (company_id, first_name, last_name, email)
    WHERE company_id IS NOT NULL 
        AND first_name IS NOT NULL 
        AND last_name IS NOT NULL 
        AND email IS NOT NULL 
        AND email != '';

CREATE INDEX IF NOT EXISTS idx_contacts_email_trgm
    ON public.contacts USING gin (email gin_trgm_ops)
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_address_trgm
    ON companies USING gin (address gin_trgm_ops)
    WHERE address IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_updated_at_desc
    ON public.contacts (updated_at DESC)
    WHERE updated_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_updated_at_desc
    ON companies (updated_at DESC)
    WHERE updated_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_employees_created
    ON companies (employees_count, created_at)
    WHERE employees_count IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_revenue_created
    ON companies (annual_revenue, created_at)
    WHERE annual_revenue IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_companies_name_asc
    ON companies (name ASC NULLS LAST)
    WHERE name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_created_at_id_desc
    ON public.contacts (created_at DESC NULLS LAST, id DESC);

CREATE INDEX IF NOT EXISTS idx_contacts_company_id_created_at
    ON public.contacts (company_id, created_at DESC)
    WHERE company_id IS NOT NULL;

-- Index for company text_search to optimize DISTINCT queries
-- This partial index filters out NULL and empty values, making DISTINCT operations faster
CREATE INDEX IF NOT EXISTS idx_companies_text_search_not_null
    ON companies (text_search)
    WHERE text_search IS NOT NULL AND text_search != '';

CREATE INDEX IF NOT EXISTS idx_companies_name_technologies
    ON companies (name)
    WHERE technologies IS NOT NULL AND name IS NOT NULL;
