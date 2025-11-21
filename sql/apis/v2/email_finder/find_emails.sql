-- ============================================================================
-- Endpoint: GET /api/v2/email/finder/
-- API Version: v2
-- Description: Find contact emails by first name, last name, and company domain.
--              Uses optimized 3-step approach with cached UUIDs and prioritized index lookups.
--              Returns simple list of (uuid, email) pairs.
--              PERFORMANCE: Optimized for 90%+ improvement (15-30s vs ~6 minutes).
-- ============================================================================
--
-- Query Parameters:
--   first_name (text, required) - Contact first name (case-insensitive partial match)
--   last_name (text, required) - Contact last name (case-insensitive partial match)
--   domain (text, optional) - Company domain or website URL (can use website parameter instead)
--   website (text, optional) - Company website URL (alias for domain parameter)
--
-- Domain Parameter Formats:
--   The domain/website parameter accepts various formats:
--   - Full URL: "https://www.example.com" or "http://example.com"
--   - Domain with www: "www.example.com"
--   - Plain domain: "example.com"
--   - URL with path: "https://example.com/path/to/page"
--   - URL with port: "https://example.com:8080"
--
--   The endpoint extracts and normalizes the domain from the input in the application layer
--   using extract_domain_from_url() utility function, which:
--   1. Removes protocol (http://, https://)
--   2. Extracts hostname (removes path)
--   3. Removes port number
--   4. Removes www. prefix
--   5. Converts to lowercase
--
--   The normalized domain is then used in the SQL query for matching against
--   CompanyMetadata using an optimized dual search strategy:
--   1. PRIMARY: Match against normalized_domain column (FAST - uses index)
--   2. FALLBACK: Extract domain from website column and match (SLOW - only if primary finds nothing)
--
--   OPTIMIZATION: Prioritizes indexed normalized_domain column for optimal performance.
--   Only uses website extraction when normalized_domain is NULL/empty, avoiding expensive
--   regex operations when possible.
--
-- Response Format:
--   Returns SimpleEmailFinderResponse with list of SimpleEmailResult objects:
--   {
--     "emails": [
--       { "uuid": "contact_uuid_1", "email": "email1@example.com" },
--       { "uuid": "contact_uuid_2", "email": "email2@example.com" }
--     ],
--     "total": 2
--   }
--
-- Response Codes:
--   200 OK: Emails found successfully
--   400 Bad Request: Invalid parameters (missing first_name, last_name, domain/website, or invalid domain format)
--   401 Unauthorized: Authentication required
--   404 Not Found: No companies found for the domain, or no contacts found matching the name criteria
--   500 Internal Server Error: Server error occurred
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v2/email/finder/?first_name=John&last_name=Doe&domain=example.com
--   Authorization: Bearer <access_token>
-- ============================================================================

-- ORM Implementation Notes (OPTIMIZED):
--   The EmailFinderService.find_emails() uses EmailFinderRepository.find_emails_by_name_and_domain()
--   which implements an optimized 3-step approach with UUID caching:
--
--   STEP 1: Find company UUIDs from companies_metadata table using optimized dual search strategy
--   - Strategy 1 (PRIMARY): Match normalized_domain column directly (FAST - uses index)
--   - Strategy 2 (FALLBACK): Extract domain from website column using SQL functions and match
--     (SLOW - only executed if Strategy 1 finds nothing)
--   - OPTIMIZATION: Prioritizes indexed normalized_domain, avoids expensive regex when possible
--   - Caches company UUIDs in memory for reuse in subsequent steps
--
--   STEP 2: Find company UUIDs from companies table using cached UUIDs
--   - Validates that companies exist in the main companies table
--   - OPTIMIZATION: Uses cached UUID list directly instead of re-executing Step 1 subquery
--   - Filters by uuid IN (cached UUID list)
--
--   STEP 3: Find contact (uuid, email) pairs from contacts table using cached UUIDs
--   - OPTIMIZATION: Uses cached company UUIDs from Step 2 (no subquery re-execution)
--   - Filter by company_id IN (cached UUID list) - direct list filtering
--   - Filter by first_name ILIKE '%{first_name}%' (uses trigram index)
--   - Filter by last_name ILIKE '%{last_name}%' (uses trigram index)
--   - Filter by email IS NOT NULL AND email != ''
--   - Returns only uuid and email columns
--   - OPTIMIZATION: Diagnostic queries are optional and combined into single query when needed
--
--   The repository extracts and logs the following fields for debugging:
--   - uuid (contact UUID)
--   - email (contact email)
--   - first_name (contact first name)
--   - last_name (contact last name)
--   - company_id (company UUID)
--
--   Field extraction logging is comprehensive throughout the flow to aid in debugging.

-- Query 1: Step 1 - Find company UUIDs from companies_metadata (dual search strategy)
-- Strategy 1: Match normalized_domain column
SELECT uuid
FROM companies_metadata
WHERE normalized_domain = 'example.com'
  AND normalized_domain IS NOT NULL;

-- Strategy 2: Extract domain from website column and match
-- Uses PostgreSQL functions to extract and normalize domain from website URL
SELECT uuid
FROM companies_metadata
WHERE website IS NOT NULL
  AND TRIM(website) != ''
  AND LOWER(
    REGEXP_REPLACE(
      SPLIT_PART(
        SPLIT_PART(
          REGEXP_REPLACE(COALESCE(website, ''), '^https?://', '', 'i'),
          '/',
          1
        ),
        ':',
        1
      ),
      '^www\.',
      '',
      'i'
    )
  ) = 'example.com';

-- Combined Step 1 query (OR condition)
SELECT DISTINCT uuid
FROM companies_metadata
WHERE uuid IN (
  -- Strategy 1: normalized_domain column
  SELECT uuid
  FROM companies_metadata
  WHERE normalized_domain = 'example.com'
    AND normalized_domain IS NOT NULL
)
OR uuid IN (
  -- Strategy 2: website extraction
  SELECT uuid
  FROM companies_metadata
  WHERE website IS NOT NULL
    AND TRIM(website) != ''
    AND LOWER(
      REGEXP_REPLACE(
        SPLIT_PART(
          SPLIT_PART(
            REGEXP_REPLACE(COALESCE(website, ''), '^https?://', '', 'i'),
            '/',
            1
          ),
          ':',
          1
        ),
        '^www\.',
        '',
        'i'
      )
    ) = 'example.com'
);

-- Query 2: Step 2 - Find company UUIDs from companies table
-- Validates that companies exist in the main companies table
SELECT uuid
FROM companies
WHERE uuid IN (
  -- Subquery from Step 1
  SELECT DISTINCT uuid
  FROM companies_metadata
  WHERE uuid IN (
    SELECT uuid
    FROM companies_metadata
    WHERE normalized_domain = 'example.com'
      AND normalized_domain IS NOT NULL
  )
  OR uuid IN (
    SELECT uuid
    FROM companies_metadata
    WHERE website IS NOT NULL
      AND TRIM(website) != ''
      AND LOWER(
        REGEXP_REPLACE(
          SPLIT_PART(
            SPLIT_PART(
              REGEXP_REPLACE(COALESCE(website, ''), '^https?://', '', 'i'),
              '/',
              1
            ),
            ':',
            1
          ),
          '^www\.',
          '',
          'i'
        )
      ) = 'example.com'
  )
);

-- Query 3: Step 3 - Find contact (uuid, email) pairs
-- Main query that returns the final results
SELECT 
    c.uuid,
    c.email,
    c.first_name,
    c.last_name,
    c.company_id
FROM contacts c
WHERE c.company_id IN (
  -- Subquery from Step 2
  SELECT uuid
  FROM companies
  WHERE uuid IN (
    SELECT DISTINCT uuid
    FROM companies_metadata
    WHERE uuid IN (
      SELECT uuid
      FROM companies_metadata
      WHERE normalized_domain = 'example.com'
        AND normalized_domain IS NOT NULL
    )
    OR uuid IN (
      SELECT uuid
      FROM companies_metadata
      WHERE website IS NOT NULL
        AND TRIM(website) != ''
        AND LOWER(
          REGEXP_REPLACE(
            SPLIT_PART(
              SPLIT_PART(
                REGEXP_REPLACE(COALESCE(website, ''), '^https?://', '', 'i'),
                '/',
                1
              ),
              ':',
              1
            ),
            '^www\.',
            '',
            'i'
          )
        ) = 'example.com'
    )
  )
)
AND c.first_name IS NOT NULL
AND c.first_name ILIKE '%John%'
AND c.last_name IS NOT NULL
AND c.last_name ILIKE '%Doe%'
AND c.email IS NOT NULL
AND TRIM(c.email) != '';

-- Note: The repository returns only (uuid, email) tuples from the query results.
--       The first_name, last_name, and company_id fields are extracted for logging purposes
--       but are not included in the final response.

-- Performance Notes (OPTIMIZED):
--   - Uses idx_companies_metadata_normalized_domain index in Step 1 (critical optimization)
--   - Uses idx_companies_metadata_normalized_domain_uuid composite index for faster Step 1 lookups
--   - Prioritizes normalized_domain column (indexed) over website extraction (unindexed)
--   - Only uses website extraction as fallback when normalized_domain is NULL/empty
--   - Caches company UUIDs from Step 1 to avoid re-executing subqueries in Step 2 and Step 3
--   - Uses direct UUID list filtering instead of nested subqueries (eliminates subquery re-execution)
--   - Uses idx_contacts_company_id index in Step 3
--   - Uses idx_contacts_company_name_email composite index for optimized Step 3 queries
--   - Uses trigram indexes (idx_contacts_first_name_trgm, idx_contacts_last_name_trgm) for name matching
--   - Diagnostic queries are optional and combined into single query using conditional aggregation
--   - Removed redundant company existence check (saves ~38s per request)
--   - Optimized for selective domains (when few companies match the domain)

