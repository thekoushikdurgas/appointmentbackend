# Apollo.io Integration Analysis

## Overview

The Apollo.io integration allows users to convert Apollo.io People Search URLs into contact filter parameters, enabling seamless replication of Apollo searches in the application's database. This document provides comprehensive analysis of the integration architecture, URL parsing, parameter mapping, and filter conversion.

## 1. Integration Architecture

### High-Level Flow

```
Apollo URL → ApolloAnalysisService.analyze_url()
    ↓
Extract Parameters → Categorize → Cache
    ↓
ApolloAnalysisService.map_to_contact_filters()
    ↓
Convert to ContactFilterParams → Handle Special Cases
    ↓
ContactRepository.list_contacts() → Execute Query
    ↓
Return Results with Mapping Metadata
```

### Components

**1. ApolloAnalysisService:**

- URL parsing and analysis
- Parameter categorization
- Filter mapping
- Caching

**2. ApolloPatternDetector:**

- Pattern detection for optimization
- Common filter pattern recognition

**3. Industry Mapping Utility:**

- Converts Apollo Tag IDs to industry names
- CSV-based mapping

**4. Domain Extraction Utility:**

- Extracts domains from URLs
- Handles various URL formats

## 2. URL Analysis

### URL Structure

**Apollo.io URLs:**

- Base URL: `https://app.apollo.io`
- Hash-based routing: `#/people?params`
- Query parameters in hash fragment

**Example:**
```
https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50
```

### URL Parsing Process

#### Step 1: Validation

- Check URL is not empty
- Verify contains "apollo.io" domain
- Validate URL format

#### Step 2: Parse Structure
```python
parsed_url = urlparse(url)
base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

if "#" in url:
    hash_part = url.split("#", 1)[1]
    if "?" in hash_part:
        path_part, query_part = hash_part.split("?", 1)
        # Parse query parameters
```

#### Step 3: Extract Parameters

- Parse query string with `parse_qs()`
- URL-decode parameter values
- Handle multi-value parameters (arrays)
- Preserve parameter order

#### Step 4: Categorize Parameters

- Map parameters to categories:
  - Pagination
  - Sorting
  - Person Filters
  - Organization Filters
  - Email Filters
  - Keyword Filters
  - Technology
  - Other

#### Step 5: Build Response

- Create parameter details with descriptions
- Generate statistics
- Build categorized structure
- Cache result (1 hour TTL)

### Parameter Categories

**Pagination:**

- `page`: Page number

**Sorting:**

- `sortByField`: Field to sort by
- `sortAscending`: Sort direction

**Person Filters:**

- `personTitles[]`: Job titles
- `personNotTitles[]`: Excluded titles
- `personLocations[]`: Person locations
- `personSeniorities[]`: Seniority levels
- `personDepartmentOrSubdepartments[]`: Departments

**Organization Filters:**

- `organizationNumEmployeesRanges[]`: Employee ranges
- `organizationLocations[]`: Company locations
- `organizationIndustryTagIds[]`: Industry Tag IDs
- `revenueRange[min/max]`: Revenue ranges

**Email Filters:**

- `contactEmailStatusV2[]`: Email verification status

**Keyword Filters:**

- `qOrganizationKeywordTags[]`: Keywords to include
- `qNotOrganizationKeywordTags[]`: Keywords to exclude
- `qKeywords`: General keyword search

**Technology:**

- `currentlyUsingAnyOfTechnologyUids[]`: Technology UIDs

**Other:**

- `includeSimilarTitles`: Title matching mode
- `uniqueUrlId`: Saved search ID
- Various Apollo-specific features

## 3. Parameter Mapping Logic

### Mapping Strategy

**Direct Mappings:**

- Simple one-to-one parameter conversion
- Example: `page` → `page`

**Combined Mappings:**

- Multiple Apollo parameters → single filter
- Example: `sortByField` + `sortAscending` → `ordering`

**Complex Mappings:**

- Parameter transformation required
- Example: `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`

**Special Handling:**

- Title normalization
- Industry Tag ID conversion
- Domain extraction

### Mapping Details

#### Pagination & Sorting

**Page:**

- `page` → `page` (integer)

**Sorting:**

- `sortByField` + `sortAscending` → `ordering`
- Field name mapping:
  - `contact_name` → `first_name`
  - `sanitized_organization_name_unanalyzed` → `company`
  - `employees` → `employees`
  - `revenue` → `annual_revenue`
  - `funding` → `total_funding`
- Descending: Prefix with `-` if `sortAscending=false`

#### Person Filters

**Titles:**

- `personTitles[]` → `title` (comma-separated, OR logic)
- Special handling based on `includeSimilarTitles`:
  - `true` → `jumble_title_words` (AND logic, individual words)
  - `false` → `normalize_title_column` (normalized matching)

**Locations:**

- `personLocations[]` → `contact_location` (comma-separated)
- `personNotLocations[]` → `exclude_contact_locations` (list)

**Seniority:**

- `personSeniorities[]` → `seniority` (comma-separated)

**Departments:**

- `personDepartmentOrSubdepartments[]` → `department` (comma-separated)

#### Organization Filters

**Employee Ranges:**

- `organizationNumEmployeesRanges[]` → `employees_min`, `employees_max`
- Parses ranges like "11,50" → min=11, max=50

**Locations:**

- `organizationLocations[]` → `company_location` (comma-separated)
- `organizationNotLocations[]` → `exclude_company_locations` (list)

**Industries:**

- `organizationIndustryTagIds[]` → `industries`
- Converts Tag IDs to industry names using `get_industry_names_from_ids()`
- Falls back to Tag IDs if conversion fails
- `organizationNotIndustryTagIds[]` → `exclude_industries`

**Revenue:**

- `revenueRange[min]` → `annual_revenue_min`
- `revenueRange[max]` → `annual_revenue_max`

**Funding:**

- Handled via company metadata filters
- `latest_funding_amount_min/max` if available

#### Email Filters

**Email Status:**

- `contactEmailStatusV2[]` → `email_status` (comma-separated)
- Common values: "verified", "unverified", "invalid"

#### Keyword Filters

**Keywords:**

- `qOrganizationKeywordTags[]` → `keywords` (comma-separated, OR logic)
- `qNotOrganizationKeywordTags[]` → `exclude_keywords` (list)
- `qAndedOrganizationKeywordTags[]` → `keywords_and` (AND logic)

**Field Control:**

- `includedOrganizationKeywordFields[]` → `keyword_search_fields`
- `excludedOrganizationKeywordFields[]` → `keyword_exclude_fields`
- `includedAndedOrganizationKeywordFields[]` → Used with `keywords_and`

**General Search:**

- `qKeywords` → `search` (multi-column search)

#### Technology Filters

**Technology UIDs:**

- `currentlyUsingAnyOfTechnologyUids[]` → `technologies_uids`
- Mapped to `technologies` field for substring matching

## 4. Special Handling

### Title Filtering

**Three Modes:**

**1. Standard (includeSimilarTitles not set):**

- Direct ILIKE matching
- `personTitles[]` → `title` filter

**2. Normalized (includeSimilarTitles=false):**

- Normalizes word order before comparison
- `personTitles[]` → `title` + `normalize_title_column=true`
- Uses `_normalize_title()`: Sorts words alphabetically

**3. Jumble (includeSimilarTitles=true):**

- Matches individual words (AND logic)
- `personTitles[]` → `jumble_title_words` (list of words)
- Uses `_jumble_title()`: Splits into words

**Example:**

- Apollo: `personTitles[]=Project Manager&includeSimilarTitles=true`
- Mapped to: `jumble_title_words=["project", "manager"]`
- Query: Both "project" AND "manager" must be in title

### Industry Tag ID Conversion

**Process:**

1. Extract Tag IDs from Apollo parameter
2. Load industry mapping CSV
3. Convert Tag IDs to industry names
4. Use industry names in filter
5. Fall back to Tag IDs if conversion fails

**Mapping File:**

- ~~`app/data/insdustryids.csv`~~ (REMOVED: File was unused and not referenced in codebase)
- Industry mapping is handled programmatically

**Example:**

- Apollo: `organizationIndustryTagIds[]=12345,67890`
- Converted: `industries=["Software", "Technology"]`
- Filter: Match companies in Software OR Technology industries

### Domain Extraction

**Process:**

1. Extract `include_domain_list` or `exclude_domain_list` from query params
2. Use `extract_domain_from_url()` utility
3. Extract domain from `CompanyMetadata.website`
4. Compare domains (case-insensitive)

**Domain Extraction Logic:**

- Handles various URL formats
- Extracts root domain
- Handles subdomains
- NULL-safe

## 5. Unmapped Parameters

### Tracking Unmapped Parameters

**Purpose:**

- Identify parameters that can't be mapped
- Provide feedback to users
- Track mapping coverage

**Reasons for Unmapping:**

**1. ID-Based Filters:**

- Industry Tag IDs (if conversion fails)
- Technology UIDs (mapped but tracked)
- Organization IDs
- Person Persona IDs

**2. Apollo-Specific Features:**

- Search Lists (`qOrganizationSearchListId`)
- Lookalike Organizations
- Intent Strengths
- Market Segments
- Prospecting Status

**3. Unsupported Features:**

- Job Posting Filters
- Trading Status
- Tour Mode
- Saved Search IDs

**Tracking:**

- Returns unmapped parameters in response
- Grouped by category
- Includes reason for unmapping

## 6. Caching Strategy

### URL Analysis Caching

**Cache Key:**

- MD5 hash of normalized URL
- Format: `apollo:url_analysis:{hash}`

**Cache TTL:**

- 1 hour (3600 seconds)
- Configurable via `analysis_cache_ttl`

**Normalization:**

- Sorts query parameters for consistent keys
- Handles encoding differences
- Ensures same URL produces same cache key

**Benefits:**

- Reduces redundant URL parsing
- Faster response for repeated URLs
- Reduces CPU usage

### Title Normalization Cache

**In-Memory Cache:**

- LRU-style cache (max 10,000 entries)
- Caches normalized title strings
- Reduces repeated normalization

**Common Titles:**

- Pre-cached common titles (CEO, CFO, etc.)
- Avoids normalization for frequent titles

## 7. Pattern Detection

### ApolloPatternDetector

**Purpose:**

- Detect common filter patterns
- Provide optimization hints
- Track usage patterns

**Common Patterns:**

**High Frequency Location:**

- `personLocations[]` (85% of queries)
- Most common filter

**High Frequency Employees:**

- `organizationNumEmployeesRanges[]` (82% of queries)
- Company size filtering

**High Frequency Titles:**

- `personTitles[]` (77% of queries)
- Job title filtering

**Combined Patterns:**

- Location + Employees (70% when both present)
- Executive Search (titles + seniority + email status)

**Usage:**

- Logging and monitoring
- Future optimization opportunities
- Query path selection

## 8. Error Handling

### Validation Errors

**URL Validation:**

- Empty URL → 400 Bad Request
- Not Apollo.io domain → 400 Bad Request
- Invalid URL format → 400 Bad Request

**Parameter Validation:**

- Invalid parameter values → 400 Bad Request
- Missing required parameters → 400 Bad Request

### Mapping Errors

**Graceful Degradation:**

- Unmapped parameters logged but don't fail
- Partial mapping supported
- Returns mapping summary with unmapped details

**Industry Conversion Errors:**

- Falls back to Tag IDs if conversion fails
- Logs warning
- Continues with available data

## 9. Response Structure

### ApolloContactsSearchResponse

**Structure:**
```json
{
    "next": "url",
    "previous": "url",
    "results": [...],
    "apollo_url": "original url",
    "mapping_summary": {
        "total_apollo_parameters": 10,
        "mapped_parameters": 8,
        "unmapped_parameters": 2,
        "mapped_parameter_names": [...],
        "unmapped_parameter_names": [...]
    },
    "unmapped_categories": [...]
}
```

**Mapping Summary:**

- Total parameters in Apollo URL
- Successfully mapped count
- Unmapped count
- Lists of mapped/unmapped parameter names

**Unmapped Categories:**

- Grouped by Apollo category
- Includes reason for unmapping
- Detailed parameter information

## 10. Integration with Repository

### Filter Application

**Flow:**

1. Apollo URL → ContactFilterParams
2. ContactFilterParams → Repository filters
3. Repository applies conditional JOINs
4. Query executes with optimized JOINs

**Benefits:**

- Reuses existing filter logic
- Leverages conditional JOIN optimization
- Consistent query patterns

### Query Optimization

**Conditional JOINs:**

- Only joins tables when Apollo filters require them
- Minimal queries when possible
- Same optimization as standard contact queries

**Example:**

- Apollo URL with only `personTitles[]` → No company join needed
- Apollo URL with `organizationNumEmployeesRanges[]` → Company join required

## 11. WebSocket Support

### Apollo WebSocket Endpoint

**Purpose:**

- Real-time Apollo URL analysis
- Streaming search results
- Progress updates for long-running queries

**Message Format:**
```json
{
    "action": "search_contacts",
    "request_id": "unique-id",
    "data": {
        "url": "apollo url",
        "limit": 100
    }
}
```

**Response Format:**
```json
{
    "request_id": "unique-id",
    "action": "search_contacts",
    "status": "success",
    "data": {
        "count": 1234,
        "results": [...]
    }
}
```

## 12. Industry Mapping

### Industry Tag ID Conversion

**Process:**

1. Load CSV mapping file
2. Create lookup dictionary
3. Convert Tag IDs to names
4. Return industry names or fallback to IDs

**Mapping File:**

- ~~`app/data/insdustryids.csv`~~ (REMOVED: File was unused and not referenced in codebase)
- Industry mapping is handled programmatically

**Utility Function:**

- `get_industry_names_from_ids(tag_ids: list[str]) -> list[str]`
- Returns industry names for Tag IDs
- Returns empty list if no matches

## 13. Domain Extraction

### Domain Extraction Utility

**Purpose:**

- Extract root domain from URLs
- Handle various URL formats
- Case-insensitive comparison

**Supported Formats:**

- `https://example.com`
- `http://www.example.com`
- `https://subdomain.example.com/path`
- `example.com` (no protocol)

**Logic:**

- Parses URL
- Extracts hostname
- Removes subdomain (optional)
- Returns root domain

**Usage:**

- Domain list filters
- Company website domain matching
- Case-insensitive comparison

## 14. Performance Considerations

### Caching

**URL Analysis:**

- 1 hour TTL
- Reduces parsing overhead
- MD5 hash for fast lookup

**Title Normalization:**

- In-memory cache
- Reduces repeated normalization
- Common titles pre-cached

### Query Optimization

**Conditional JOINs:**

- Only joins when Apollo filters require
- Minimal queries for simple Apollo URLs
- Same optimization as standard queries

### Batch Processing

**Large Result Sets:**

- Uses QueryBatcher for large limits
- Processes in chunks
- Prevents timeout

## Summary

The Apollo.io integration demonstrates:

1. **Comprehensive Mapping**: 50+ Apollo parameters mapped
2. **Special Handling**: Title normalization, industry conversion, domain extraction
3. **Unmapped Tracking**: Clear feedback on unmapped parameters
4. **Performance**: Caching, conditional JOINs, batch processing
5. **Error Handling**: Graceful degradation, validation
6. **Real-time Support**: WebSocket integration
7. **Pattern Detection**: Optimization hints and monitoring

The integration provides a seamless way to replicate Apollo.io searches while maintaining query performance through conditional JOIN optimization.

