-- ============================================================================
-- Endpoint: GET /api/v1/contacts/company/domain/
-- API Version: v1
-- Description: Return distinct company domains extracted from CompanyMetadata.website using AttributeListParams.
-- ============================================================================
--
-- Parameters:
--   Query Parameters:
--     distinct (boolean, default: true) - Return unique values
--     limit (integer, default: 25) - Maximum number of results
--     offset (integer, default: 0) - Offset applied before fetching values
--     ordering (text, default: 'value') - Sort alphabetically ('value' or '-value')
--     search (text, optional) - Optional case-insensitive search term
--
--   Note: ContactFilterParams are NOT supported - this endpoint queries only CompanyMetadata table.
--
-- Response Structure:
--   Returns array of strings: ["example.com", "company.com", ...]
--   Domains are extracted from CompanyMetadata.website field.
--
-- Response Codes:
--   200 OK: Company domains retrieved successfully
--   400 Bad Request: Invalid query parameters
--   401 Unauthorized: Authentication required
--   500 Internal Server Error: Error occurred while querying company domains
--
-- Authentication:
--   Required - Bearer token in Authorization header
--
-- Example Usage:
--   GET /api/v1/contacts/company/domain/
--   GET /api/v1/contacts/company/domain/?search=example&limit=50
--   GET /api/v1/contacts/company/domain/?ordering=-value
-- ============================================================================

-- ORM Implementation Notes:
--   The ContactRepository.list_company_domains_simple() queries ONLY CompanyMetadata table:
--   - No contact filters are supported (ignores ContactFilterParams)
--   - Queries CompanyMetadata.website directly and extracts domain using PostgreSQL regex
--   - Domain extraction: removes protocol, www. prefix, port numbers, converts to lowercase
--   - Filters out NULL and placeholder "_" values
--   - Only uses AttributeListParams: distinct, limit, offset, ordering, search

-- Query 1: Basic query - Get all distinct company domains
-- GET /api/v1/contacts/company/domain/
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 2: With distinct=true
-- GET /api/v1/contacts/company/domain/?distinct=true
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 3: With distinct=false
-- GET /api/v1/contacts/company/domain/?distinct=false
SELECT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 4: With ordering=value (ascending)
-- GET /api/v1/contacts/company/domain/?ordering=value
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 5: With ordering=-value (descending)
-- GET /api/v1/contacts/company/domain/?ordering=-value
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 6: With search parameter
-- GET /api/v1/contacts/company/domain/?search=example
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
    AND LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) ILIKE '%example%'
ORDER BY value ASC
LIMIT 25
OFFSET 0;

-- Query 7: With limit parameter
-- GET /api/v1/contacts/company/domain/?limit=50
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 8: With offset parameter
-- GET /api/v1/contacts/company/domain/?offset=25
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 25
OFFSET 25;

-- Query 9: With limit and offset
-- GET /api/v1/contacts/company/domain/?limit=10&offset=20
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
ORDER BY value ASC
LIMIT 10
OFFSET 20;

-- Query 10: With search and ordering
-- GET /api/v1/contacts/company/domain/?search=example&ordering=-value
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
    AND LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) ILIKE '%example%'
ORDER BY value DESC
LIMIT 25
OFFSET 0;

-- Query 11: With all attribute parameters
-- GET /api/v1/contacts/company/domain/?distinct=true&limit=50&offset=0&ordering=value&search=example
SELECT DISTINCT 
    LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) as value
FROM companies_metadata com
WHERE com.website IS NOT NULL
    AND TRIM(com.website) != ''
    AND com.website != '_'
    AND TRIM(com.website) != '_'
    AND LOWER(
        REGEXP_REPLACE(
            SPLIT_PART(
                SPLIT_PART(
                    REGEXP_REPLACE(COALESCE(com.website, ''), '^https?://', '', 'i'),
                    '/', 1
                ),
                ':', 1
            ),
            '^www\.', '', 'i'
        )
    ) ILIKE '%example%'
ORDER BY value ASC
LIMIT 50
OFFSET 0;

-- Query 12: Domain extraction examples
-- The domain extraction handles various URL formats:
-- https://www.example.com -> example.com
-- http://example.com/path -> example.com
-- https://example.com:8080 -> example.com
-- www.example.com -> example.com
-- example.com -> example.com

