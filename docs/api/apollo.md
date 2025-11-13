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

- `limit` (integer, optional, >=1): Maximum number of results per page
- `offset` (integer, optional, >=0): Starting offset for results (default: 0)
- `cursor` (string, optional): Opaque cursor token for pagination
- `view` (string, optional): When set to `"simple"`, returns simplified contact data. Omit for full contact details.

**Response:**

Returns an extended response format that includes:
- Contact results (`CursorPage` with `ContactListItem` or `ContactSimpleItem` objects)
- Apollo URL mapping metadata
- Summary of mapped and unmapped parameters
- Detailed information about parameters that were not mapped

**Success (200 OK):**

```json
{
  "next": "http://localhost:8000/api/v2/apollo/contacts?limit=25&offset=25",
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
| `personTitles[]` | `title` | Multiple values joined with comma (OR logic) |
| `personNotTitles[]` | `exclude_titles` | List of titles to exclude |
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
| `qOrganizationKeywordTags[]` | `keywords` | Multiple values joined with comma |
| `qNotOrganizationKeywordTags[]` | `exclude_keywords` | List of keywords to exclude |
| `qKeywords` | `search` | Direct mapping |

**Skipped Parameters:**

The following Apollo parameters are not mapped (no equivalent in contacts database):

- **ID-based filters**: `organizationIndustryTagIds[]`, `currentlyUsingAnyOfTechnologyUids[]`, `organizationNotIndustryTagIds[]` (no ID-to-name mapping available)
- **Apollo-specific features**: `qOrganizationSearchListId`, `qNotOrganizationSearchListId`, `qPersonPersonaIds[]`, `marketSegments[]`, `intentStrengths[]`, `lookalikeOrganizationIds[]`, `prospectedByCurrentTeam[]`
- **Unmapped filters**: `organizationJobLocations[]`, `organizationNumJobsRange[min]`, `organizationJobPostedAtRange[min]`, `organizationTradingStatus[]`, `contactEmailExcludeCatchAll`
- **Keyword field controls**: `includedOrganizationKeywordFields[]`, `excludedOrganizationKeywordFields[]`, `includedAndedOrganizationKeywordFields[]`
- **UI flags**: `uniqueUrlId`, `tour`, `includeSimilarTitles`, `existFields[]`

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

- **ID-based filter (no name mapping available)**: Parameters that use IDs which cannot be mapped to names (e.g., `organizationIndustryTagIds[]`, `currentlyUsingAnyOfTechnologyUids[]`)
- **Apollo-specific feature**: Features specific to Apollo.io that don't have equivalents in the contact database (e.g., search lists, personas, intent signals, lookalike)
- **Unmapped filter**: Filters that don't have corresponding fields in the contact database (e.g., job postings, trading status)
- **Keyword field control**: Parameters that control which fields to search for keywords (not applicable in the contacts database)
- **UI flag or advanced filter**: User interface flags and advanced filters that don't affect the query (e.g., `tour`, `uniqueUrlId`, `includeSimilarTitles`)
- **Unknown parameter**: Parameters not recognized or not yet mapped

**Notes:**

- Multiple values for the same parameter are combined with OR logic (comma-separated for text filters)
- Exclusion filters accept lists and exclude contacts matching any value
- Employee ranges (e.g., "11,50", "51,100") are parsed into min/max values
- Sorting fields from Apollo are mapped to contact database fields where possible
- The endpoint provides transparency about which parameters were used and which were skipped
- All text searches are case-insensitive
- Results can be filtered further using additional query parameters (limit, offset, cursor, view)
- Use the `mapping_summary` to understand how many of your Apollo filters were applied
- Use the `unmapped_categories` to see which filters were not applied and why

**Use Cases:**

1. **Apollo to Database Migration**: Convert Apollo searches to your database queries seamlessly
2. **Search Replication**: Replicate Apollo.io searches in your own system without manual parameter mapping
3. **Workflow Integration**: Integrate Apollo URLs directly into your workflow to search your contact database
4. **Search Preservation**: Save and reuse Apollo search URLs to query your contact database with consistent criteria

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

