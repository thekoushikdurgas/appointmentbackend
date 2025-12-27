# Sales Navigator Scraping API Documentation

Complete API documentation for Sales Navigator HTML scraping endpoint that extracts profile data from Sales Navigator search results pages.

**Related Documentation:**

- [LinkedIn API](./linkdin.md) - For LinkedIn URL-based operations
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Sales Navigator Endpoints](#sales-navigator-endpoints)
  - [POST /api/v3/sales-navigator/scrape](#post-apiv3sales-navigatorscrape---scrape-sales-navigator-html)
- [User Scraping Endpoints](#user-scraping-endpoints)
  - [GET /api/v1/users/sales-navigator/list](#get-apiv1userssales-navigatorlist---list-user-scraping-records)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All Sales Navigator endpoints are under `/api/v3/sales-navigator/`

## Authentication

All Sales Navigator endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All Sales Navigator endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to Sales Navigator scraping
- **Pro Users (`ProUser`)**: ✅ Full access to Sales Navigator scraping
- **Admin (`Admin`)**: ✅ Full access to Sales Navigator scraping (unlimited credits)
- **Super Admin (`SuperAdmin`)**: ✅ Full access to Sales Navigator scraping (unlimited credits)

**Note:** There are no role-based restrictions on Sales Navigator functionality. All authenticated users can scrape Sales Navigator HTML.

---

## Sales Navigator Endpoints

### POST /api/v3/sales-navigator/scrape - Scrape Sales Navigator HTML

Scrape Sales Navigator HTML content and extract all profile data into a structured JSON format. This endpoint accepts HTML content from a Sales Navigator search results page and extracts profile information including names, titles, companies, locations, connection degrees, and more.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "html": "<html>...</html>",
  "save": false
}
```

**Request Body Fields:**

- `html` (string, required): Sales Navigator HTML content to scrape. Must be valid HTML from a Sales Navigator search results page. Minimum length: 1 character. HTML is automatically trimmed of whitespace.
- `save` (boolean, optional, default: false): Whether to persist scraped profiles to the database. When `true`, profiles are saved as contacts and companies, and the response includes saved records and a save summary. When `false` (default), only extraction metadata, page metadata, and profiles are returned (faster response).

**Example Request:**

```bash
# Basic request (without saving to database)
curl -X POST "http://127.0.0.1:8000/api/v3/sales-navigator/scrape" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html><body>...</body></html>"
  }'

# Request with save=true (persists profiles to database)
curl -X POST "http://127.0.0.1:8000/api/v3/sales-navigator/scrape" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html><body>...</body></html>",
    "save": true
  }'
```

**Response Codes:**

- `200 OK`: Scraping completed successfully
- `400 Bad Request`: Invalid HTML content or HTML is empty
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to scrape HTML

**Example Response (save=false, default):**

```json
{
  "extraction_metadata": {
    "timestamp": "2025-01-15T10:30:00.123456+00:00",
    "version": "2.0",
    "source_file": "api_request"
  },
  "page_metadata": {
    "search_context": {
      "search_filters": {
        "current_title": "Software Engineer",
        "filter_id": 9,
        "selection_type": "INCLUDED"
      },
      "search_id": "5263824340",
      "session_id": "MZSayEwCQkaWxjmJ3Sz4Wg=="
    },
    "pagination": {
      "current_page": 1,
      "total_pages": 100,
      "results_per_page": 25
    },
    "user_info": {
      "user_member_urn": "urn:li:member:301118112",
      "user_name": null
    },
    "application_info": {
      "application_version": "2.0.5996",
      "client_page_instance_id": "3fd1fa6a-dc94-413b-9df7-ae3a1dcb503d",
      "request_ip_country": "in",
      "tracking_id": null,
      "tree_id": "AAZEG7qFXTcSYbM745ibpg=="
    }
  },
  "profiles": [
    {
      "name": "John Doe",
      "title": "Software Engineer",
      "company": "Tech Corp",
      "location": "San Francisco, California, United States",
      "profile_url": "https://www.linkedin.com/sales/lead/ACwAAAByMvQBweFnFh_2u0h3gM1sJHeWTItSn5M,NAME_SEARCH,z0xx",
      "image_url": "https://media.licdn.com/dms/image/...",
      "connection_degree": "3rd",
      "about": "Experienced software engineer...",
      "time_in_role": "1 year 8 months",
      "time_in_company": "1 year 8 months",
      "lead_id": "ACwAAAByMvQBweFnFh_2u0h3gM1sJHeWTItSn5M",
      "lead_urn": "urn:li:fs_salesProfile:(ACwAAAByMvQBweFnFh_2u0h3gM1sJHeWTItSn5M,NAME_SEARCH,z0xx)",
      "search_type": "NAME_SEARCH",
      "search_id": "z0xx",
      "company_id": 5221148,
      "company_url": "https://www.linkedin.com/sales/company/5221148",
      "is_premium_member": false,
      "is_reachable": true,
      "last_active": "Reachable",
      "is_viewed": false,
      "mutual_connections_count": 0,
      "mutual_connections": [],
      "is_recently_hired": false,
      "recently_hired_company_logo": null,
      "recent_posts_count": null,
      "shared_groups_details": [],
      "shared_groups": [],
      "data_quality_score": 94,
      "missing_fields": [
        "mutual_connections_count",
        "mutual_connections",
        "recent_posts_count"
      ]
    }
  ],
  "saved_contacts": [],
  "saved_contacts_metadata": [],
  "saved_companies": [],
  "saved_companies_metadata": [],
  "save_summary": {
    "total_profiles": 1,
    "contacts_created": 0,
    "contacts_updated": 0,
    "companies_created": 0,
    "companies_updated": 0,
    "errors": []
  }
}
```

**Example Response (save=true):**

When `save=true`, the response includes the same fields as above, plus populated `saved_contacts`, `saved_contacts_metadata`, `saved_companies`, `saved_companies_metadata`, and a detailed `save_summary`:

```json
{
  "extraction_metadata": { /* ... */ },
  "page_metadata": { /* ... */ },
  "profiles": [ /* ... */ ],
  "saved_contacts": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@techcorp.com",
      "title": "Software Engineer",
      /* ... other contact fields ... */
    }
  ],
  "saved_contacts_metadata": [
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "linkedin_url": "https://www.linkedin.com/in/john-doe",
      /* ... other metadata fields ... */
    }
  ],
  "saved_companies": [
    {
      "uuid": "223e4567-e89b-12d3-a456-426614174001",
      "name": "Tech Corp",
      "employees_count": 500,
      /* ... other company fields ... */
    }
  ],
  "saved_companies_metadata": [
    {
      "uuid": "223e4567-e89b-12d3-a456-426614174001",
      "linkedin_url": "https://www.linkedin.com/company/tech-corp",
      /* ... other metadata fields ... */
    }
  ],
  "save_summary": {
    "total_profiles": 25,
    "contacts_created": 20,
    "contacts_updated": 5,
    "companies_created": 15,
    "companies_updated": 3,
    "errors": []
  }
}
```

**Response Fields:**

- `extraction_metadata` (object): Metadata about the extraction process
  - `timestamp` (string): ISO 8601 timestamp of when extraction occurred
  - `version` (string): Version of the extraction logic (currently "2.0")
  - `source_file` (string): Source identifier (typically "api_request" for API calls)
- `page_metadata` (object): Page-level metadata extracted from the HTML
  - `search_context` (object): Search filters and context information
    - `search_filters` (object): Applied search filters (e.g., current_title, filter_id, selection_type)
    - `search_id` (string): Search identifier
    - `session_id` (string): Session identifier
  - `pagination` (object): Pagination information
    - `current_page` (integer): Current page number
    - `total_pages` (integer): Total number of pages
    - `results_per_page` (integer): Number of results per page
  - `user_info` (object): Information about the user who performed the search
    - `user_member_urn` (string): LinkedIn member URN
    - `user_name` (string|null): User's name if available
  - `application_info` (object): Application and tracking information
    - `application_version` (string): LinkedIn application version
    - `client_page_instance_id` (string): Client page instance ID
    - `request_ip_country` (string): Country code from request IP
    - `tracking_id` (string|null): Tracking identifier
    - `tree_id` (string): Tree identifier
- `profiles` (array): List of extracted profile objects, each containing:
  - `name` (string): Full name of the person
  - `title` (string): Job title
  - `company` (string): Company name
  - `location` (string): Location information
  - `profile_url` (string): Full LinkedIn Sales Navigator profile URL
  - `image_url` (string): Profile image URL
  - `connection_degree` (string): Connection degree (e.g., "1st", "2nd", "3rd")
  - `about` (string|null): About/bio text
  - `time_in_role` (string|null): Time in current role
  - `time_in_company` (string|null): Time in current company
  - `lead_id` (string): Sales Navigator lead identifier
  - `lead_urn` (string): Sales Navigator lead URN
  - `search_type` (string): Type of search (e.g., "NAME_SEARCH")
  - `search_id` (string): Search identifier
  - `company_id` (integer|null): LinkedIn company ID
  - `company_url` (string|null): LinkedIn company URL
  - `is_premium_member` (boolean): Whether the person has LinkedIn Premium
  - `is_reachable` (boolean): Whether the person is reachable
  - `last_active` (string|null): Last active status or timestamp
  - `is_viewed` (boolean): Whether the profile was previously viewed
  - `mutual_connections_count` (integer): Number of mutual connections
  - `mutual_connections` (array): List of mutual connection objects with image_url and name
  - `is_recently_hired` (boolean): Whether the person was recently hired
  - `recently_hired_company_logo` (string|null): Logo URL of recently hired company
  - `recent_posts_count` (integer|null): Number of recent posts
  - `shared_groups_details` (array): List of shared groups with group_name, group_logo_url, group_url
  - `shared_groups` (array): Legacy field for backward compatibility
  - `data_quality_score` (integer): Data quality score (0-100)
  - `missing_fields` (array): List of optional fields that are missing
- `saved_contacts` (array): List of saved contact records (ContactDB objects). Only populated when `save=true`. Empty array when `save=false`.
- `saved_contacts_metadata` (array): List of saved contact metadata records (ContactMetadataOut objects). Only populated when `save=true`. Empty array when `save=false`.
- `saved_companies` (array): List of saved company records (CompanyDB objects). Only populated when `save=true`. Empty array when `save=false`.
- `saved_companies_metadata` (array): List of saved company metadata records (CompanyMetadataOut objects). Only populated when `save=true`. Empty array when `save=false`.
- `save_summary` (object): Summary of save operation. Always present, but only contains meaningful data when `save=true`.
  - `total_profiles` (integer): Total number of profiles processed
  - `contacts_created` (integer): Number of contacts created
  - `contacts_updated` (integer): Number of contacts updated
  - `companies_created` (integer): Number of companies created
  - `companies_updated` (integer): Number of companies updated
  - `errors` (array): List of error messages if any errors occurred during saving

---

## Response Schemas

### SalesNavigatorScrapeRequest

```json
{
  "html": "string (required, min_length=1)",
  "save": "boolean (optional, default: false)"
}
```

**Field Descriptions:**

- `html` (string, required, min_length=1): Sales Navigator HTML content to scrape. HTML is automatically trimmed of whitespace.
- `save` (boolean, optional, default: false): Whether to persist scraped profiles to the database. When `true`, profiles are saved as contacts and companies.

### SalesNavigatorScrapeResponse

```json
{
  "extraction_metadata": {
    "timestamp": "string (ISO 8601)",
    "version": "string",
    "source_file": "string"
  },
  "page_metadata": {
    "search_context": {},
    "pagination": {},
    "user_info": {},
    "application_info": {}
  },
  "profiles": [
    {
      "name": "string",
      "title": "string",
      "company": "string",
      "location": "string",
      "profile_url": "string",
      "image_url": "string",
      "connection_degree": "string",
      "about": "string|null",
      "time_in_role": "string|null",
      "time_in_company": "string|null",
      "lead_id": "string",
      "lead_urn": "string",
      "search_type": "string",
      "search_id": "string",
      "company_id": "integer|null",
      "company_url": "string|null",
      "is_premium_member": "boolean",
      "is_reachable": "boolean",
      "last_active": "string|null",
      "is_viewed": "boolean",
      "mutual_connections_count": "integer",
      "mutual_connections": "array",
      "is_recently_hired": "boolean",
      "recently_hired_company_logo": "string|null",
      "recent_posts_count": "integer|null",
      "shared_groups_details": "array",
      "shared_groups": "array",
      "data_quality_score": "integer",
      "missing_fields": "array"
    }
  ],
  "saved_contacts": "array (ContactDB objects, empty when save=false)",
  "saved_contacts_metadata": "array (ContactMetadataOut objects, empty when save=false)",
  "saved_companies": "array (CompanyDB objects, empty when save=false)",
  "saved_companies_metadata": "array (CompanyMetadataOut objects, empty when save=false)",
  "save_summary": {
    "total_profiles": "integer",
    "contacts_created": "integer",
    "contacts_updated": "integer",
    "companies_created": "integer",
    "companies_updated": "integer",
    "errors": "array"
  }
}
```

**Field Descriptions:**

- `saved_contacts` (array): List of saved contact records. Only populated when `save=true`. See [Contacts API](./contacts.md) for ContactDB schema.
- `saved_contacts_metadata` (array): List of saved contact metadata records. Only populated when `save=true`. See [Contacts API](./contacts.md) for ContactMetadataOut schema.
- `saved_companies` (array): List of saved company records. Only populated when `save=true`. See [Companies API](./company.md) for CompanyDB schema.
- `saved_companies_metadata` (array): List of saved company metadata records. Only populated when `save=true`. See [Companies API](./company.md) for CompanyMetadataOut schema.
- `save_summary` (object): Summary of save operation with counts and errors. Always present, but only contains meaningful data when `save=true`.

---

## Use Cases

### 1. Extract Profiles from Sales Navigator Search Results

Use this endpoint to extract structured profile data from Sales Navigator HTML. This is particularly useful when:

- You have saved HTML from Sales Navigator search results
- You want to programmatically extract profile information
- You need to process multiple pages of search results
- You want to analyze search context and pagination information

### 2. Integration with Chrome Extension

The Chrome extension automatically detects Sales Navigator URLs and uses this endpoint to extract and display profile data in the URL Analysis Dashboard.

### 3. Batch Processing

You can process multiple HTML files by calling this endpoint multiple times with different HTML content.

### 4. Extract and Save Profiles

Extract profiles and automatically save them to the database:

```bash
POST /api/v3/sales-navigator/scrape
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "html": "<html>...</html>",
  "save": true
}
```

This will extract profiles and automatically create/update contacts and companies in the database. The response includes the saved records and a summary of the save operation.

---

## Error Handling

### 400 Bad Request

**Invalid HTML Content:**

```json
{
  "detail": "Invalid HTML content: Failed to parse HTML"
}
```

**Empty HTML:**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "html"],
      "msg": "HTML content cannot be empty",
      "input": ""
    }
  ]
}
```

**Note:** The exact error format may vary. The backend validates that HTML is not empty or just whitespace.

### 401 Unauthorized

**Missing or Invalid Token:**

```json
{
  "detail": "Not authenticated"
}
```

### 500 Internal Server Error

**Scraping Failure:**

```json
{
  "detail": "Failed to scrape HTML: <error_message>"
}
```

**Common Causes:**

- HTML is not from a valid Sales Navigator page
- HTML structure has changed and extraction logic needs updating
- Network or server errors during processing

---

## Notes

1. **HTML Size**: Large HTML content may take longer to process. Consider setting appropriate timeouts for your client.

2. **Data Quality**: Each profile includes a `data_quality_score` (0-100) indicating how complete the extracted data is. Higher scores indicate more complete profiles.

3. **Missing Fields**: The `missing_fields` array lists optional fields that were not found in the HTML for that profile.

4. **Profile Count**: The number of profiles extracted depends on the HTML content. Sales Navigator typically shows 25 profiles per page.

5. **Version**: The extraction logic version is included in `extraction_metadata.version`. This helps track which version of the scraper was used.

6. **Source File**: For API requests, `source_file` will be set to "api_request". For file-based scraping (using the Python script), it contains the file path.

7. **Save Parameter**: The `save` parameter defaults to `false` for fastest response. When set to `true`, scraped profiles are automatically saved as contacts and companies in the database. This is useful when you want to persist the data for later use. When `save=false`, only extraction metadata, page metadata, and profiles are returned (no database operations).

8. **Save Summary**: When `save=true`, the `save_summary` field provides detailed information about the save operation, including counts of created/updated contacts and companies, and any errors that occurred during saving.

9. **Saved Records**: When `save=true`, the response includes `saved_contacts`, `saved_contacts_metadata`, `saved_companies`, and `saved_companies_metadata` arrays containing the actual database records that were created or updated. These arrays are empty when `save=false`.

---

## User Scraping Endpoints

### GET /api/v1/users/sales-navigator/list - List User Scraping Records

List Sales Navigator scraping metadata records for the authenticated user. Returns paginated list of scraping records ordered by timestamp (newest first).

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `limit` (integer, optional, default: 100, min: 1, max: 1000): Maximum number of records to return
- `offset` (integer, optional, default: 0, min: 0): Number of records to skip (for pagination)

**Example Request:**

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/users/sales-navigator/list?limit=50&offset=0" \
  -H "Authorization: Bearer <access_token>" \
  -H "Accept: application/json"
```

**Response Codes:**

- `200 OK`: Records retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to retrieve records

**Example Response:**

```json
{
  "items": [
    {
      "id": 1,
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2025-12-01T21:51:46.519397+00:00",
      "version": "2.0",
      "source": "api_request",
      "search_context": {
        "search_filters": {
          "current_title": "Software Engineer",
          "filter_id": 9,
          "selection_type": "INCLUDED"
        },
        "search_id": "5277019068",
        "session_id": "CvIKeM+EScOxVolPwEtEUA=="
      },
      "pagination": {
        "current_page": 1,
        "total_pages": 100,
        "results_per_page": 25
      },
      "user_info": {
        "user_member_urn": "urn:li:member:301118112",
        "user_name": null
      },
      "application_info": {
        "application_version": "2.0.6065",
        "client_page_instance_id": "35b54fb2-eea1-41ce-9b98-efc1f98c9e37",
        "request_ip_country": "in",
        "tracking_id": null,
        "tree_id": "AAZE6qJjeLPSavp2BbjRrQ=="
      },
      "created_at": "2025-12-01T21:51:46.519397+00:00",
      "updated_at": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

**Response Fields:**

- `items` (array): List of scraping records, each containing:
  - `id` (integer): Scraping record ID
  - `user_id` (string, UUID): User ID who performed the scraping
  - `timestamp` (string): ISO 8601 timestamp of when scraping occurred
  - `version` (string): Version of the extraction logic (e.g., "2.0")
  - `source` (string): Source identifier (e.g., "api_request")
  - `search_context` (object): Search context metadata
    - `search_filters` (object): Applied search filters
    - `search_id` (string): Search identifier
    - `session_id` (string): Session identifier
  - `pagination` (object): Pagination metadata
    - `current_page` (integer): Current page number
    - `total_pages` (integer): Total number of pages
    - `results_per_page` (integer): Number of results per page
  - `user_info` (object): User info metadata
    - `user_member_urn` (string): LinkedIn member URN
    - `user_name` (string|null): User's name if available
  - `application_info` (object): Application info metadata
    - `application_version` (string): LinkedIn application version
    - `client_page_instance_id` (string): Client page instance ID
    - `request_ip_country` (string): Country code from request IP
    - `tracking_id` (string|null): Tracking identifier
    - `tree_id` (string): Tree identifier
  - `created_at` (string): ISO 8601 timestamp of when record was created
  - `updated_at` (string|null): ISO 8601 timestamp of when record was last updated
- `total` (integer): Total number of records for the user
- `limit` (integer): Maximum number of records per page
- `offset` (integer): Number of records skipped

**Notes:**

- Only returns scraping records for the currently authenticated user
- Records are ordered by timestamp in descending order (newest first)
- Supports pagination via `limit` and `offset` query parameters
- All authenticated users can access their own scraping records
