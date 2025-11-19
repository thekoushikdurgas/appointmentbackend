# Apollo URL Analysis API Documentation

Complete API documentation for Apollo.io URL analysis endpoints, including parsing and categorizing Apollo search URL parameters.

**Related Documentation:**
- [Contacts API](./contacts.md) - For contact search and filtering endpoints
- [User API](./user.md) - For authentication endpoints
- [Export API](./export.md) - For exporting contacts matching Apollo criteria

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [CORS Testing](#cors-testing)
- [Apollo Endpoints](#apollo-endpoints)
  - [POST /api/v2/apollo/analyze](#post-apiv2apolloanalyze---analyze-apollo-url)
  - [POST /api/v2/apollo/analyze/count](#post-apiv2apolloanalyzecount---analyze-apollo-url-with-contact-counts)
  - [POST /api/v2/apollo/contacts](#post-apiv2apollocontacts---search-contacts-from-apollo-url)
  - [POST /api/v2/apollo/contacts/count](#post-apiv2apollocontactscount---count-contacts-from-apollo-url)
  - [POST /api/v2/apollo/contacts/count/uuids](#post-apiv2apollocontactscountuuids---get-contact-uuids-from-apollo-url)
- [Response Schema](#response-schema)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All Apollo endpoints are under `/api/v2/apollo/`

## Authentication

All Apollo endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## CORS Testing

All endpoints support CORS (Cross-Origin Resource Sharing) for browser-based requests. For testing CORS headers, you can include an optional `Origin` header in your requests:

**Optional Header:**

- `Origin: http://localhost:3000` (or your frontend origin)

**Expected CORS Response Headers:**

- `Access-Control-Allow-Origin: http://localhost:3000` (matches the Origin header)
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH`
- `Access-Control-Allow-Headers: *`
- `Access-Control-Max-Age: 3600`

**Note:** The Origin header is optional and only needed when testing CORS behavior. The API automatically handles CORS preflight (OPTIONS) requests.

---

## Apollo Endpoints

### POST /api/v2/apollo/analyze - Analyze Apollo URL

Analyze an Apollo.io URL and return structured parameter breakdown. This endpoint parses Apollo.io search URLs (typically from the People Search page) and extracts all query parameters, categorizing them into logical groups.

**Note:** Industry Tag IDs (`organizationIndustryTagIds[]`, `organizationNotIndustryTagIds[]`) are automatically converted to readable industry names in the API response for better usability.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false"
}
```

**Request Body Fields:**

- `url` (string, required): Apollo.io URL to analyze. Must be from the `apollo.io` domain.

**Response:**

**Success (200 OK):**

```json
{
  "url": "https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false",
  "url_structure": {
    "base_url": "https://app.apollo.io",
    "hash_path": "/people",
    "query_string": "contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false",
    "has_query_params": true
  },
  "categories": [
    {
      "name": "Pagination",
      "parameters": [
        {
          "name": "page",
          "values": ["1"],
          "description": "Page number for pagination",
          "category": "Pagination"
        }
      ],
      "total_parameters": 1
    },
    {
      "name": "Sorting",
      "parameters": [
        {
          "name": "sortByField",
          "values": ["recommendations_score"],
          "description": "Field to sort results by",
          "category": "Sorting"
        },
        {
          "name": "sortAscending",
          "values": ["false"],
          "description": "Sort direction (true/false)",
          "category": "Sorting"
        }
      ],
      "total_parameters": 2
    },
    {
      "name": "Person Filters",
      "parameters": [
        {
          "name": "personTitles[]",
          "values": ["CEO"],
          "description": "Job titles to include",
          "category": "Person Filters"
        },
        {
          "name": "personLocations[]",
          "values": ["california"],
          "description": "Person locations to include",
          "category": "Person Filters"
        }
      ],
      "total_parameters": 2
    },
    {
      "name": "Email Filters",
      "parameters": [
        {
          "name": "contactEmailStatusV2[]",
          "values": ["verified"],
          "description": "Email verification status",
          "category": "Email Filters"
        }
      ],
      "total_parameters": 1
    },
    {
      "name": "Organization Filters",
      "parameters": [
        {
          "name": "organizationNumEmployeesRanges[]",
          "values": ["11,50"],
          "description": "Company size ranges",
          "category": "Organization Filters"
        }
      ],
      "total_parameters": 1
    }
  ],
  "statistics": {
    "total_parameters": 7,
    "total_parameter_values": 7,
    "categories_used": 5,
    "categories": ["Pagination", "Sorting", "Person Filters", "Email Filters", "Organization Filters"]
  },
  "raw_parameters": {
    "contactEmailStatusV2[]": ["verified"],
    "personLocations[]": ["california"],
    "personTitles[]": ["CEO"],
    "organizationNumEmployeesRanges[]": ["11,50"],
    "page": ["1"],
    "sortByField": ["recommendations_score"],
    "sortAscending": ["false"]
  }
}
```

**Error (400 Bad Request) - Invalid URL:**

```json
{
  "detail": "URL is required and must be a string"
}
```

**Error (400 Bad Request) - Not Apollo.io Domain:**

```json
{
  "detail": "URL must be from apollo.io domain"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while analyzing the URL"
}
```

**Status Codes:**

- `200 OK`: URL analyzed successfully
- `400 Bad Request`: Invalid URL, not from Apollo.io domain, or missing URL field
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error occurred while analyzing the URL

**Example Requests:**

```txt
POST /api/v2/apollo/analyze
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=United States&page=1"
}
```

**Parameter Categories:**

The endpoint categorizes parameters into the following groups:

1. **Pagination**
   - `page`: Page number for pagination

2. **Sorting**
   - `sortByField`: Field to sort results by
   - `sortAscending`: Sort direction (true/false)

3. **Person Filters**
   - `personTitles[]`: Job titles to include
   - `personNotTitles[]`: Job titles to exclude
   - `personLocations[]`: Person locations to include
   - `personNotLocations[]`: Person locations to exclude
   - `personSeniorities[]`: Seniority levels to include
   - `personDepartmentOrSubdepartments[]`: Departments to include

4. **Organization Filters**
   - `organizationNumEmployeesRanges[]`: Company size ranges
   - `organizationLocations[]`: Organization locations to include
   - `organizationNotLocations[]`: Organization locations to exclude
   - `organizationIndustryTagIds[]`: Industry tag IDs to include (displayed as industry names in response)
   - `organizationNotIndustryTagIds[]`: Industry tag IDs to exclude (displayed as industry names in response)
   - `organizationJobLocations[]`: Job posting locations
   - `organizationNumJobsRange[min]`: Minimum number of job postings
   - `organizationJobPostedAtRange[min]`: Job posting date range
   - `revenueRange[min]`: Minimum revenue
   - `revenueRange[max]`: Maximum revenue
   - `organizationTradingStatus[]`: Company trading status

5. **Email Filters**
   - `contactEmailStatusV2[]`: Email verification status
   - `contactEmailExcludeCatchAll`: Exclude catch-all emails

6. **Keyword Filters**
   - `qOrganizationKeywordTags[]`: Organization keywords to include
   - `qNotOrganizationKeywordTags[]`: Organization keywords to exclude
   - `qAndedOrganizationKeywordTags[]`: Organization keywords to include (ALL must match)
   - `includedOrganizationKeywordFields[]`: Fields to search for keywords
   - `excludedOrganizationKeywordFields[]`: Fields to exclude from keyword search
   - `includedAndedOrganizationKeywordFields[]`: Fields to search for ANDed keywords

7. **Search Lists**
   - `qOrganizationSearchListId`: Saved organization list ID
   - `qNotOrganizationSearchListId`: Excluded organization list ID
   - `qPersonPersonaIds[]`: Person persona IDs

8. **Technology**
   - `currentlyUsingAnyOfTechnologyUids[]`: Technology stack filters

9. **Market Segments**
   - `marketSegments[]`: Market segment filters

10. **Intent**
    - `intentStrengths[]`: Buying intent levels

11. **Lookalike**
    - `lookalikeOrganizationIds[]`: Similar organization IDs

12. **Prospecting**
    - `prospectedByCurrentTeam[]`: Prospecting status

13. **Other**
    - `uniqueUrlId`: Unique identifier for saved searches
    - `tour`: Tour mode flag
    - `includeSimilarTitles`: Include similar titles
    - `existFields[]`: Required fields
    - `notOrganizationIds[]`: Excluded organization IDs
    - `organizationIds[]`: Organization IDs to include
    - `qKeywords`: Keyword search in profiles or organizations

**Notes:**

- Apollo.io URLs use hash-based routing (`#/people?params`)
- Parameters are URL-encoded (spaces become `%20`, etc.)
- Array parameters use `[]` notation (e.g., `personTitles[]`)
- Multiple values for the same parameter are repeated in the URL
- All parameter values are automatically URL-decoded in the response
- The analysis includes both categorized parameters and raw parameter dictionary
- Statistics provide summary information about the search criteria
- The endpoint validates that the URL is from the `apollo.io` domain

**URL Structure:**

Apollo.io URLs follow this structure:

```txt
https://app.apollo.io/#/people?[query_parameters]
```

Components:

- **Base URL**: `https://app.apollo.io`
- **Hash Route**: `#/people` (indicates People Search page)
- **Query Parameters**: Filter and search criteria (URL encoded)

**Example Apollo URLs:**

```txt
# Simple search with location and title
https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=United States&page=1

# Complex search with multiple filters
https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personTitles[]=CEO&personTitles[]=Founder&organizationNumEmployeesRanges[]=11,50&organizationNumEmployeesRanges[]=51,100&qOrganizationKeywordTags[]=saas&page=1&sortByField=recommendations_score&sortAscending=false

# Search with keyword filters and exclusions
https://app.apollo.io/#/people?qOrganizationKeywordTags[]=marketing&qNotOrganizationKeywordTags[]=retail&includedOrganizationKeywordFields[]=tags&includedOrganizationKeywordFields[]=name&personLocations[]=California&page=1

# Search with AND logic keywords and field control
https://app.apollo.io/#/people?qAndedOrganizationKeywordTags[]=saas&qAndedOrganizationKeywordTags[]=cloud&includedAndedOrganizationKeywordFields[]=keywords&includedAndedOrganizationKeywordFields[]=company&personLocations[]=California&page=1

# Search with technology UIDs
https://app.apollo.io/#/people?currentlyUsingAnyOfTechnologyUids[]=uid123&currentlyUsingAnyOfTechnologyUids[]=uid456&organizationNumEmployeesRanges[]=11,50&page=1

# Search with industry tag IDs (automatically converted to industry names)
https://app.apollo.io/#/people?organizationIndustryTagIds[]=5567cd4773696439b10b0000&organizationIndustryTagIds[]=5567cd4e7369643b70010000&personTitles[]=CEO&page=1
```

---

### POST /api/v2/apollo/analyze/count - Analyze Apollo URL with Contact Counts

Analyze an Apollo.io URL and return structured parameter breakdown with contact counts. This endpoint extends `/apollo/analyze` by adding contact counts for each parameter and each value within parameters, helping users understand the impact of each filter on their contact database.

**Note:** Industry Tag IDs (`organizationIndustryTagIds[]`, `organizationNotIndustryTagIds[]`) are automatically converted to readable industry names in the API response for better usability.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false"
}
```

**Request Body Fields:**

- `url` (string, required): Apollo.io URL to analyze. Must be from the `apollo.io` domain.

**Response:**

**Success (200 OK):**

```json
{
  "url": "https://app.apollo.io/#/people?contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false",
  "url_structure": {
    "base_url": "https://app.apollo.io",
    "hash_path": "/people",
    "query_string": "contactEmailStatusV2[]=verified&personLocations[]=california&personTitles[]=CEO&organizationNumEmployeesRanges[]=11,50&page=1&sortByField=recommendations_score&sortAscending=false",
    "has_query_params": true
  },
  "categories": [
    {
      "name": "Pagination",
      "count": 0,
      "parameters": [
        {
          "name": "page",
          "count": 0,
          "values": [
            {
              "value": "1",
              "count": 0
            }
          ],
          "description": "Page number for pagination",
          "category": "Pagination"
        }
      ],
      "total_parameters": 1
    },
    {
      "name": "Sorting",
      "count": 0,
      "parameters": [
        {
          "name": "sortByField",
          "count": 0,
          "values": [
            {
              "value": "recommendations_score",
              "count": 0
            }
          ],
          "description": "Field to sort results by",
          "category": "Sorting"
        },
        {
          "name": "sortAscending",
          "count": 0,
          "values": [
            {
              "value": "false",
              "count": 0
            }
          ],
          "description": "Sort direction (true/false)",
          "category": "Sorting"
        }
      ],
      "total_parameters": 2
    },
    {
      "name": "Person Filters",
      "count": 850,
      "parameters": [
        {
          "name": "personTitles[]",
          "count": 500,
          "values": [
            {
              "value": "CEO",
              "count": 500
            }
          ],
          "description": "Job titles to include",
          "category": "Person Filters"
        },
        {
          "name": "personLocations[]",
          "count": 350,
          "values": [
            {
              "value": "california",
              "count": 350
            }
          ],
          "description": "Person locations to include",
          "category": "Person Filters"
        }
      ],
      "total_parameters": 2
    },
    {
      "name": "Email Filters",
      "count": 1200,
      "parameters": [
        {
          "name": "contactEmailStatusV2[]",
          "count": 1200,
          "values": [
            {
              "value": "verified",
              "count": 1200
            }
          ],
          "description": "Email verification status",
          "category": "Email Filters"
        }
      ],
      "total_parameters": 1
    },
    {
      "name": "Organization Filters",
      "count": 600,
      "parameters": [
        {
          "name": "organizationNumEmployeesRanges[]",
          "count": 600,
          "values": [
            {
              "value": "11,50",
              "count": 600
            }
          ],
          "description": "Company size ranges",
          "category": "Organization Filters"
        }
      ],
      "total_parameters": 1
    }
  ],
  "statistics": {
    "total_parameters": 7,
    "total_parameter_values": 7,
    "categories_used": 5,
    "categories": ["Pagination", "Sorting", "Person Filters", "Email Filters", "Organization Filters"]
  },
  "raw_parameters": {
    "contactEmailStatusV2[]": ["verified"],
    "personLocations[]": ["california"],
    "personTitles[]": ["CEO"],
    "organizationNumEmployeesRanges[]": ["11,50"],
    "page": ["1"],
    "sortByField": ["recommendations_score"],
    "sortAscending": ["false"]
  }
}
```

**Response Fields:**

The response structure is identical to `/apollo/analyze`, but with the following additions:

- **`categories[].count`** (integer): Total number of contacts matching any parameter in this category (uses maximum parameter count to avoid overcounting)
- **`categories[].parameters[].count`** (integer): Total number of contacts matching this parameter (all values combined)
- **`categories[].parameters[].values[]`**: Array of objects instead of strings, where each object contains:
  - **`value`** (string): Parameter value (same as before)
  - **`count`** (integer): Number of contacts matching this specific value

**Notes:**

- Pagination and sorting parameters (`page`, `sortByField`, `sortAscending`) always return count 0 as they don't filter contacts
- Unmapped parameters return count 0 (expected behavior)
- Counts are calculated independently for each parameter and value
- Category counts use the maximum parameter count to avoid overcounting when parameters overlap
- The counts reflect how many contacts in your database match each filter criterion

**Error (400 Bad Request) - Invalid URL:**

```json
{
  "detail": "URL is required and must be a string"
}
```

**Error (400 Bad Request) - Not Apollo.io Domain:**

```json
{
  "detail": "URL must be from apollo.io domain"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "An error occurred while analyzing the URL with counts"
}
```

**Status Codes:**

- `200 OK`: URL analyzed successfully with counts
- `400 Bad Request`: Invalid URL, not from Apollo.io domain, or missing URL field
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error occurred while analyzing the URL with counts

**Example Requests:**

```txt
POST /api/v2/apollo/analyze/count
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=United States&page=1"
}
```

**Use Cases:**

1. **Filter Impact Analysis**: Understand how many contacts match each filter criterion before applying them
2. **Search Optimization**: Identify which filters narrow down results most effectively
3. **Data Exploration**: Explore your contact database by seeing counts for different parameter combinations
4. **Filter Validation**: Verify that your Apollo URL filters are working as expected with actual counts

**Performance Notes:**

- This endpoint performs multiple database queries (one per parameter and one per value)
- Response time may be longer than `/apollo/analyze` for URLs with many parameters
- Counts are calculated in real-time from your current database state

---

### POST /api/v2/apollo/contacts - Search Contacts from Apollo URL

Search contacts using Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns matching contacts from your database. It provides a seamless way to replicate Apollo.io searches in your own contact database.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified&page=1&sortByField=employees&sortAscending=false"
}
```

**Request Body Fields:**

- `url` (string, required): Apollo.io URL to analyze and convert. Must be from the `apollo.io` domain.

**Query Parameters:**

- `limit` (integer, optional, >=1): Maximum number of results per page. **If not provided, returns all matching contacts (no pagination limit).** When provided, limits results to the specified number (capped at MAX_PAGE_SIZE).
- `offset` (integer, optional, >=0): Starting offset for results (default: 0)
- `cursor` (string, optional): Opaque cursor token for pagination
- `view` (string, optional): When set to `"simple"`, returns simplified contact data. Omit for full contact details.
- `include_company_name` (string, optional): Include contacts whose company name matches this value (case-insensitive substring match). Supports comma-separated values for OR logic.
- `exclude_company_name` (array of strings, optional): Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times or as comma-separated values.
- `include_domain_list` (array of strings, optional): Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`
- `exclude_domain_list` (array of strings, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`

**Response:**

Returns an extended response format that includes:

- Contact results (`CursorPage` with `ContactListItem` or `ContactSimpleItem` objects)
- Apollo URL mapping metadata
- Summary of mapped and unmapped parameters
- Detailed information about parameters that were not mapped

**Success (200 OK):**

```json
{
  "next": "http://54.87.173.234:8000/api/v2/apollo/contacts?limit=25&offset=25",
  "previous": null,
  "results": [
    {
      "id": 123,
      "first_name": "John",
      "last_name": "Doe",
      "title": "CEO",
      "company": "Tech Corp",
      "email": "john@techcorp.com",
      "email_status": "verified",
      "seniority": "C-Level",
      "employees": 45,
      "city": "San Francisco",
      "state": "California",
      "country": "United States",
      "person_linkedin_url": "https://linkedin.com/in/johndoe",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
    }
  ],
  "apollo_url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified",
  "mapping_summary": {
    "total_apollo_parameters": 8,
    "mapped_parameters": 4,
    "unmapped_parameters": 4,
    "mapped_parameter_names": ["contactEmailStatusV2[]", "organizationNumEmployeesRanges[]", "personLocations[]", "personTitles[]"],
    "unmapped_parameter_names": ["organizationIndustryTagIds[]", "qOrganizationSearchListId", "sortByField", "tour"]
  },
  "unmapped_categories": [
    {
      "name": "Organization Filters",
      "total_parameters": 1,
      "parameters": [
        {
          "name": "organizationIndustryTagIds[]",
          "values": ["5567cd4773696439b10b0000"],
          "category": "Organization Filters",
          "reason": "ID-based filter (no name mapping available)"
        }
      ]
    },
    {
      "name": "Search Lists",
      "total_parameters": 1,
      "parameters": [
        {
          "name": "qOrganizationSearchListId",
          "values": ["abc123"],
          "category": "Search Lists",
          "reason": "Apollo-specific feature (search lists, personas)"
        }
      ]
    },
    {
      "name": "Other",
      "total_parameters": 2,
      "parameters": [
        {
          "name": "sortByField",
          "values": ["recommendations_score"],
          "category": "Sorting",
          "reason": "Unknown parameter (no mapping defined)"
        },
        {
          "name": "tour",
          "values": ["true"],
          "category": "Other",
          "reason": "UI flag or advanced filter (not applicable)"
        }
      ]
    }
  ]
}
```

**Error (400 Bad Request) - Invalid URL:**

```json
{
  "detail": "URL is required and must be a string"
}
```

**Error (400 Bad Request) - Invalid Filter Parameters:**

```json
{
  "detail": "Invalid filter parameters: validation error message"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `200 OK`: Contacts retrieved successfully
- `400 Bad Request`: Invalid URL, not from Apollo.io domain, or invalid filter parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error occurred while searching contacts

**Parameter Mappings:**

The endpoint maps Apollo.io parameters to contact filter parameters as follows:

| Apollo Parameter | Contact Filter | Mapping Notes |
|-----------------|----------------|---------------|
| `page` | `page` | Direct mapping |
| `sortByField` + `sortAscending` | `ordering` | Combined; prepend `-` for descending |
| `personTitles[]` | `title` | Multiple values joined with comma (OR logic). **Title Mapping**: When `includeSimilarTitles=false` (or absent), titles are normalized by sorting words alphabetically (e.g., "Project Manager" → "manager project"). When `includeSimilarTitles=true`, uses **jumble mapping**: splits titles into individual words (e.g., "Project Manager" → "project,manager"), allowing each word to be searched separately. |
| `personNotTitles[]` | `exclude_titles` | List of titles to exclude. **Title Mapping**: Always uses exact mapping (normalize by sorting words alphabetically), regardless of `includeSimilarTitles` flag. This parameter is NOT dependent on `includeSimilarTitles`. |
| `includeSimilarTitles` | (influences `personTitles[]` only) | When `true`, `personTitles[]` uses jumble mapping (splits into words). When `false` or absent, `personTitles[]` uses exact mapping (normalize). **Note**: This flag does NOT affect `personNotTitles[]`, which always uses exact mapping. |
| `personSeniorities[]` | `seniority` | Multiple values joined with comma |
| `personDepartmentOrSubdepartments[]` | `department` | Multiple values joined with comma |
| `personLocations[]` | `contact_location` | Multiple values joined with comma |
| `personNotLocations[]` | `exclude_contact_locations` | List of locations to exclude |
| `organizationNumEmployeesRanges[]` | `employees_min`, `employees_max` | Parses ranges like "11,50" |
| `organizationLocations[]` | `company_location` | Multiple values joined with comma |
| `organizationNotLocations[]` | `exclude_company_locations` | List of locations to exclude |
| `revenueRange[min]` | `annual_revenue_min` | Direct mapping |
| `revenueRange[max]` | `annual_revenue_max` | Direct mapping |
| `contactEmailStatusV2[]` | `email_status` | Multiple values joined with comma |
| `organizationIndustryTagIds[]` | `industries` | Tag IDs converted to industry names from CSV mapping |
| `organizationNotIndustryTagIds[]` | `exclude_industries` | Tag IDs converted to industry names from CSV mapping |
| `qOrganizationKeywordTags[]` | `keywords` | Multiple values joined with comma (OR logic) |
| `qNotOrganizationKeywordTags[]` | `exclude_keywords` | List of keywords to exclude |
| `qAndedOrganizationKeywordTags[]` | `keywords_and` | Multiple values joined with comma (AND logic - all must match) |
| `includedOrganizationKeywordFields[]` | `keyword_search_fields` | Fields to include in keyword search: 'company', 'industries', 'keywords' |
| `excludedOrganizationKeywordFields[]` | `keyword_exclude_fields` | Fields to exclude from keyword search: 'company', 'industries', 'keywords' |
| `includedAndedOrganizationKeywordFields[]` | `keywords_and` + `keyword_search_fields` | AND logic keywords with field control (combines both) |
| `currentlyUsingAnyOfTechnologyUids[]` | `technologies_uids` | Technology UIDs joined with comma (substring matching) |
| `qKeywords` | `search` | Direct mapping |

**Skipped Parameters:**

The following Apollo parameters are not mapped (no equivalent in contacts database):

- **Apollo-specific features**: `qOrganizationSearchListId`, `qNotOrganizationSearchListId`, `qPersonPersonaIds[]`, `marketSegments[]`, `intentStrengths[]`, `lookalikeOrganizationIds[]`, `prospectedByCurrentTeam[]`
- **Unmapped filters**: `organizationJobLocations[]`, `organizationNumJobsRange[min]`, `organizationJobPostedAtRange[min]`, `organizationTradingStatus[]`, `contactEmailExcludeCatchAll`
- **UI flags**: `uniqueUrlId`, `tour`, `existFields[]`, `notOrganizationIds[]`, `organizationIds[]`

**Note:** `includeSimilarTitles` is now mapped and influences how `personTitles[]` is processed (see Title Mapping above). **Important**: `personNotTitles[]` is NOT affected by `includeSimilarTitles` and always uses exact mapping (normalize).

**Note:** Industry tag IDs (`organizationIndustryTagIds[]`, `organizationNotIndustryTagIds[]`) ARE now successfully mapped to industry names using a CSV-based lookup table with 147 industry mappings.

**Title Mapping Examples:**

**personTitles[] with includeSimilarTitles=false** (exact mapping - normalize):
```
Apollo URL: personTitles[]=Project Manager&personTitles[]=Senior Developer
Normalized search terms: "manager project", "developer senior"
Database normalization: Both search terms AND database titles are normalized before comparison
Result: Matches contacts with "Project Manager", "Manager Project", "Senior Developer", "Developer Senior"
Does NOT match: "Account Manager Project" (normalizes to "account manager project" ≠ "manager project")
```

**personTitles[] with includeSimilarTitles=true** (jumble mapping - split into words):
```
Apollo URL: personTitles[]=Project Manager&includeSimilarTitles=true
Jumbled: "project,manager" (split into individual words)
Result: Matches contacts with titles containing "project" OR "manager" (e.g., "Project Manager", "Project Lead", "Product Manager", "Manager of Engineering")
```

**personNotTitles[]** (always exact mapping - normalize, ignores includeSimilarTitles):
```
Apollo URL: personNotTitles[]=Project Manager&includeSimilarTitles=true
Normalized: "manager project" (always normalized, regardless of includeSimilarTitles)
Result: Excludes contacts with "Project Manager" or "Manager Project" (case-insensitive)
```

**Example Requests:**

```txt
POST /api/v2/apollo/contacts
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50"
}
```

With view parameter for simplified results:

```txt
POST /api/v2/apollo/contacts?view=simple
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&contactEmailStatusV2[]=verified"
}
```

With pagination:

```txt
POST /api/v2/apollo/contacts?limit=50&offset=0
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?qKeywords=technology&personLocations[]=United States"
}
```

**Response Fields:**

In addition to the standard pagination fields (`next`, `previous`, `results`), the response includes:

- **apollo_url** (string): The original Apollo.io URL that was converted
- **mapping_summary** (object): Summary statistics about parameter mapping:
  - `total_apollo_parameters`: Total number of parameters found in the Apollo URL
  - `mapped_parameters`: Number of parameters successfully mapped to contact filters
  - `unmapped_parameters`: Number of parameters that could not be mapped
  - `mapped_parameter_names`: Array of parameter names that were successfully mapped
  - `unmapped_parameter_names`: Array of parameter names that were not mapped
- **unmapped_categories** (array): Detailed information about unmapped parameters, grouped by category:
  - `name`: Category name (e.g., "Organization Filters", "Search Lists", "Other")
  - `total_parameters`: Number of unmapped parameters in this category
  - `parameters`: Array of unmapped parameter details:
    - `name`: Parameter name from Apollo URL
    - `values`: Parameter values from Apollo URL
    - `category`: Apollo parameter category
    - `reason`: Explanation of why this parameter was not mapped (e.g., "ID-based filter (no name mapping available)", "Apollo-specific feature", "UI flag or advanced filter")

**Unmapped Parameter Reasons:**

- **ID-based filter (no name mapping available)**: Parameters that use IDs which cannot be mapped to names (e.g., `currentlyUsingAnyOfTechnologyUids[]`)
  - Note: `organizationIndustryTagIds[]` and `organizationNotIndustryTagIds[]` are now successfully mapped using a CSV-based industry name lookup
- **Apollo-specific feature**: Features specific to Apollo.io that don't have equivalents in the contact database (e.g., search lists, personas, intent signals, lookalike)
- **Unmapped filter**: Filters that don't have corresponding fields in the contact database (e.g., job postings, trading status)
- **Keyword field control**: Parameters that control which fields to search for keywords (not applicable in the contacts database)
- **UI flag or advanced filter**: User interface flags and advanced filters that don't affect the query (e.g., `tour`, `uniqueUrlId`)

**Note:** `includeSimilarTitles` is now mapped and controls title normalization behavior (see Title Normalization in parameter mappings).
- **Unknown parameter**: Parameters not recognized or not yet mapped

**Notes:**

- Multiple values for the same parameter are combined with OR logic (comma-separated for text filters)
- Exclusion filters accept lists and exclude contacts matching any value
- Employee ranges (e.g., "11,50", "51,100") are parsed into min/max values
- Sorting fields from Apollo are mapped to contact database fields where possible
- The endpoint provides transparency about which parameters were used and which were skipped
- All text searches are case-insensitive
- **Default behavior**: When `limit` is not provided, the endpoint returns all matching contacts (no pagination limit). This is useful for exporting or processing all results.
- **Limited behavior**: When `limit` is provided, results are paginated and limited to the specified number (capped at MAX_PAGE_SIZE).
- Results can be filtered further using additional query parameters (limit, offset, cursor, view, include_company_name, exclude_company_name, include_domain_list, exclude_domain_list)
- Company name filters (`include_company_name`, `exclude_company_name`) and domain filters (`include_domain_list`, `exclude_domain_list`) can be combined with Apollo URL filters
- Use the `mapping_summary` to understand how many of your Apollo filters were applied
- Use the `unmapped_categories` to see which filters were not applied and why

**Use Cases:**

1. **Apollo to Database Migration**: Convert Apollo searches to your database queries seamlessly
2. **Search Replication**: Replicate Apollo.io searches in your own system without manual parameter mapping
3. **Workflow Integration**: Integrate Apollo URLs directly into your workflow to search your contact database
4. **Search Preservation**: Save and reuse Apollo search URLs to query your contact database with consistent criteria

---

### POST /api/v2/apollo/contacts/count - Count Contacts from Apollo URL

Count contacts matching Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns the total count of matching contacts from your database.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified"
}
```

**Request Body Fields:**

- `url` (string, required): Apollo.io URL to analyze and convert. Must be from the `apollo.io` domain.

**Query Parameters:**

- `include_company_name` (string, optional): Include contacts whose company name matches this value (case-insensitive substring match). Supports comma-separated values for OR logic.
- `exclude_company_name` (array of strings, optional): Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times or as comma-separated values.
- `include_domain_list` (array of strings, optional): Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`
- `exclude_domain_list` (array of strings, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`

**Response:**

Returns a simple count response with the total number of matching contacts.

**Success (200 OK):**

```json
{
  "count": 1234
}
```

**Error (400 Bad Request) - Invalid URL:**

```json
{
  "detail": "URL is required and must be a string"
}
```

**Error (400 Bad Request) - Invalid Filter Parameters:**

```json
{
  "detail": "Invalid filter parameters: validation error message"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `200 OK`: Count retrieved successfully
- `400 Bad Request`: Invalid URL, not from Apollo.io domain, or invalid filter parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error occurred while counting contacts

**Parameter Mappings:**

The endpoint uses the same parameter mappings as `/api/v2/apollo/contacts`. See that endpoint's documentation for complete mapping details.

**Example Requests:**

```txt
POST /api/v2/apollo/contacts/count
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50"
}
```

With company name inclusion filter:

```txt
POST /api/v2/apollo/contacts/count?include_company_name=Tech
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&contactEmailStatusV2[]=verified"
}
```

With domain inclusion filter:

```txt
POST /api/v2/apollo/contacts/count?include_domain_list=example.com&include_domain_list=test.com
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&contactEmailStatusV2[]=verified"
}
```

With company name exclusion filter:

```txt
POST /api/v2/apollo/contacts/count?exclude_company_name=Test&exclude_company_name=Demo

POST /api/v2/apollo/contacts/count?exclude_domain_list=spam.com
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?qKeywords=technology&personLocations[]=United States"
}
```

**Notes:**

- The count endpoint uses the same filter mapping logic as the search endpoint
- Company name filters can be combined with Apollo URL filters
- All text searches are case-insensitive
- The count reflects the total number of contacts matching all applied filters

**Use Cases:**

1. **Quick Count Check**: Get the total number of contacts matching an Apollo search before fetching results
2. **Progress Tracking**: Monitor how many contacts match specific criteria
3. **Filter Validation**: Verify that your Apollo URL filters are working as expected
4. **Resource Planning**: Estimate data volume before processing large result sets

---

### POST /api/v2/apollo/contacts/count/uuids - Get Contact UUIDs from Apollo URL

Get a list of contact UUIDs matching Apollo.io URL parameters. This endpoint converts an Apollo.io People Search URL into contact filter parameters and returns matching contact UUIDs from your database.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50&contactEmailStatusV2[]=verified"
}
```

**Request Body Fields:**

- `url` (string, required): Apollo.io URL to analyze and convert. Must be from the `apollo.io` domain.

**Query Parameters:**

**This endpoint accepts the same request body and query parameters as `/api/v2/apollo/contacts/count` endpoint, plus an additional parameter:**

- `include_company_name` (string, optional): Include contacts whose company name matches this value (case-insensitive substring match). Supports comma-separated values for OR logic.
- `exclude_company_name` (array of strings, optional): Exclude contacts whose company name matches any provided value (case-insensitive). Can be provided multiple times or as comma-separated values.
- `include_domain_list` (array of strings, optional): Include contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`
- `exclude_domain_list` (array of strings, optional): Exclude contacts whose company website domain matches any provided domain (case-insensitive). Domains are extracted from `CompanyMetadata.website` column. Can be provided multiple times. Example: `["example.com", "test.com"]`
- `limit` (integer, optional): Maximum number of UUIDs to return. **If not provided, returns all matching UUIDs (unlimited).** When provided, limits results to the specified number.

**Response:**

Returns count and list of UUIDs.

**Success (200 OK):**

```json
{
  "count": 1234,
  "uuids": [
    "398cce44-233d-5f7c-aea1-e4a6a79df10c",
    "498cce44-233d-5f7c-aea1-e4a6a79df10d",
    "598cce44-233d-5f7c-aea1-e4a6a79df10e"
  ]
}
```

**Error (400 Bad Request) - Invalid URL:**

```json
{
  "detail": "URL is required and must be a string"
}
```

**Error (400 Bad Request) - Invalid Filter Parameters:**

```json
{
  "detail": "Invalid filter parameters: validation error message"
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Status Codes:**

- `200 OK`: UUIDs retrieved successfully
- `400 Bad Request`: Invalid URL, not from Apollo.io domain, or invalid filter parameters
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Error occurred while retrieving UUIDs

**Parameter Mappings:**

The endpoint uses the same parameter mappings as `/api/v2/apollo/contacts`. See that endpoint's documentation for complete mapping details.

**Example Requests:**

```txt
POST /api/v2/apollo/contacts/count/uuids
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&personLocations[]=California&organizationNumEmployeesRanges[]=11,50"
}
```

With company name inclusion filter and limit:

```txt
POST /api/v2/apollo/contacts/count/uuids?include_company_name=Tech&limit=1000
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://app.apollo.io/#/people?personTitles[]=CEO&contactEmailStatusV2[]=verified"
}
```

**Notes:**

- Returns only UUIDs, not full contact data (efficient for bulk operations)
- **Accepts the same request body and query parameters as `/api/v2/apollo/contacts/count` endpoint, plus an additional `limit` parameter**
- Useful for exporting specific contact sets or bulk updates
- When `limit` is not provided, returns all matching UUIDs (unlimited)
- Company name filters can be combined with Apollo URL filters
- All text searches are case-insensitive

**Use Cases:**

1. **Bulk Operations**: Get UUIDs for bulk updates or exports
2. **Efficient Filtering**: Retrieve only UUIDs without full contact data
3. **Export Preparation**: Get UUID list before exporting specific contact sets
4. **Integration**: Use UUIDs for downstream processing or API calls

---

## Response Schema

### Important: Tag ID to Industry Name Conversion

**All API responses automatically convert industry Tag IDs to human-readable industry names:**

- **Affected Parameters**: `organizationIndustryTagIds[]`, `organizationNotIndustryTagIds[]`
- **Conversion Source**: CSV mapping file with 147 industry name mappings
- **Where Applied**:
  - `raw_parameters` dictionary in `/apollo/analyze` response
  - Categorized parameter `values` in `/apollo/analyze` response
  - Unmapped parameter `values` in `/apollo/contacts` response (if any)

**Example Conversion:**
- **Input (Apollo URL)**: `organizationIndustryTagIds[]=5567cd4773696439dd350000`
- **Output (API Response)**: `organizationIndustryTagIds[]=["construction"]`

This conversion makes API responses more readable and user-friendly without requiring clients to perform Tag ID lookups.

### ApolloUrlAnalysisResponse

```json
{
  "url": "string",
  "url_structure": {
    "base_url": "string",
    "hash_path": "string | null",
    "query_string": "string | null",
    "has_query_params": "boolean"
  },
  "categories": [
    {
      "name": "string",
      "parameters": [
        {
          "name": "string",
          "values": ["string"],
          "description": "string",
          "category": "string"
        }
      ],
      "total_parameters": "integer"
    }
  ],
  "statistics": {
    "total_parameters": "integer",
    "total_parameter_values": "integer",
    "categories_used": "integer",
    "categories": ["string"]
  },
  "raw_parameters": {
    "parameter_name": ["value1", "value2"]
  }
}
```

### Field Descriptions

- `url`: Original URL that was analyzed
- `url_structure.base_url`: Base URL (e.g., https://app.apollo.io)
- `url_structure.hash_path`: Hash path (e.g., /people)
- `url_structure.query_string`: Full query string
- `url_structure.has_query_params`: Whether the URL has query parameters
- `categories`: Array of parameter categories, each containing:
  - `name`: Category name
  - `parameters`: Array of parameter details
  - `total_parameters`: Number of parameters in this category
- `statistics.total_parameters`: Total number of unique parameters found
- `statistics.total_parameter_values`: Total number of parameter values (including duplicates)
- `statistics.categories_used`: Number of parameter categories used
- `statistics.categories`: List of category names found
- `raw_parameters`: Raw parameter dictionary (parameter name -> list of values)

---

## Use Cases

### 1. Understanding Search Criteria

Use this endpoint to understand what search criteria are embedded in an Apollo.io URL, making it easier to:

- Replicate searches in your own system
- Document search parameters
- Analyze search patterns

### 2. URL Migration

When migrating from Apollo.io to another system, use this endpoint to:

- Extract all filter parameters
- Map Apollo parameters to your database schema
- Preserve search criteria during migration

### 3. Search Analysis

Analyze Apollo search URLs to:

- Understand which filters are most commonly used
- Identify search patterns
- Optimize your own search interface

### 4. Integration

Integrate Apollo URL analysis into your workflow to:

- Automatically parse and categorize search URLs
- Extract structured data from Apollo URLs
- Build search queries based on Apollo parameters

---

## Error Handling

The endpoint provides detailed error messages for common issues:

1. **Invalid URL Format**: URL is missing or not a string
2. **Wrong Domain**: URL is not from apollo.io domain
3. **Authentication Required**: Missing or invalid JWT token
4. **Server Error**: Internal error during URL parsing or analysis

Always check the response status code and error message to handle errors appropriately in your application.


