# Apollo URL Analysis API Documentation

Complete API documentation for Apollo.io URL analysis endpoints, including parsing and categorizing Apollo search URL parameters.

## Base URL

```txt
http://localhost:8000
```

For production, use:

```txt
http://107.21.188.21:8000
```

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
   - `organizationIndustryTagIds[]`: Industry tag IDs to include
   - `organizationNotIndustryTagIds[]`: Industry tag IDs to exclude
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

```
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
```

---

## Response Schema

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

