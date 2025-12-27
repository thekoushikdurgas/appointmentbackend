# LinkedIn API Documentation

Complete API documentation for LinkedIn URL-based search operations, including searching for contacts and companies by LinkedIn URL.

**Related Documentation:**

- [Contacts API](./contacts.md) - For general contact management endpoints
- [Companies API](./company.md) - For general company management endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [LinkedIn Endpoints](#linkedin-endpoints)
  - [POST /api/v3/linkedin/](#post-apiv3linkedin---search-by-linkedin-url)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All LinkedIn endpoints are under `/api/v3/linkedin/`

## Authentication

All LinkedIn endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All LinkedIn endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to all LinkedIn endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all LinkedIn endpoints
- **Admin (`Admin`)**: ✅ Full access to all LinkedIn endpoints (unlimited credits)
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all LinkedIn endpoints (unlimited credits)

**Note:** There are no role-based restrictions on LinkedIn functionality. All authenticated users can search for contacts/companies by LinkedIn URL.

## Credit Deduction

Credits are automatically deducted after successful operations:

- **SuperAdmin & Admin**: Unlimited credits (no deduction)
- **FreeUser & ProUser**: Credits are deducted after successful operations:
  - **Search operations**: 1 credit per search request

**Important Notes:**

- Credits are deducted **after** successful operation completion
- Negative credit balances are allowed (credits can go below 0)
- Failed operations do not deduct credits

---

## LinkedIn Endpoints

### POST /api/v3/linkedin/ - Search by LinkedIn URL

Search for contacts and companies by LinkedIn URL. This endpoint searches both person LinkedIn URLs (from `ContactMetadata.linkedin_url`) and company LinkedIn URLs (from `CompanyMetadata.linkedin_url`), returning all matching records with their related data.

**Credit Deduction:** 1 credit is deducted after a successful search (FreeUser and ProUser only). SuperAdmin and Admin have unlimited credits.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://www.linkedin.com/in/john-doe"
}
```

**Request Body Fields:**

- `url` (string, required): LinkedIn URL to search for. Can be a person LinkedIn URL or company LinkedIn URL. Supports partial matching (case-insensitive).

**Example Request:**

```bash
POST /api/v3/linkedin/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "url": "https://www.linkedin.com/in/john-doe"
}
```

**Response:**

**Success (200 OK):**

```json
{
  "contacts": [
    {
      "contact": {
        "uuid": "abc123",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "title": "Software Engineer",
        "company_id": "company-uuid-123",
        "seniority": "individual_contributor",
        "departments": ["Engineering"],
        "mobile_phone": "+1234567890",
        "email_status": "verified",
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-20T14:45:00"
      },
      "metadata": {
        "uuid": "abc123",
        "linkedin_url": "https://www.linkedin.com/in/john-doe",
        "linkedin_sales_url": null,
        "facebook_url": null,
        "twitter_url": null,
        "website": "https://johndoe.com",
        "work_direct_phone": "+1234567890",
        "home_phone": null,
        "city": "San Francisco",
        "state": "CA",
        "country": "US",
        "other_phone": null,
        "stage": "active"
      },
      "company": {
        "uuid": "company-uuid-123",
        "name": "Tech Corp",
        "employees_count": 500,
        "industries": ["Technology"],
        "keywords": null,
        "address": null,
        "annual_revenue": 10000000,
        "total_funding": 5000000,
        "technologies": ["Python", "JavaScript"],
        "text_search": null,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-15T10:00:00"
      },
      "company_metadata": {
        "uuid": "company-uuid-123",
        "linkedin_url": "https://www.linkedin.com/company/tech-corp",
        "linkedin_sales_url": null,
        "facebook_url": null,
        "twitter_url": null,
        "website": "https://techcorp.com",
        "company_name_for_emails": null,
        "phone_number": "+1234567890",
        "latest_funding": null,
        "latest_funding_amount": null,
        "last_raised_at": null,
        "city": "San Francisco",
        "state": "CA",
        "country": "US"
      }
    }
  ],
  "companies": [
    {
      "company": {
        "uuid": "company-uuid-456",
        "name": "Another Company",
        "employees_count": 200,
        "industries": ["Finance"],
        "keywords": null,
        "address": null,
        "annual_revenue": 5000000,
        "total_funding": 2000000,
        "technologies": ["Java", "Spring"],
        "text_search": null,
        "created_at": "2024-01-05T00:00:00",
        "updated_at": "2024-01-10T10:00:00"
      },
      "metadata": {
        "uuid": "company-uuid-456",
        "linkedin_url": "https://www.linkedin.com/company/another-company",
        "linkedin_sales_url": null,
        "facebook_url": null,
        "twitter_url": null,
        "website": "https://anothercompany.com",
        "company_name_for_emails": null,
        "phone_number": "+1987654321",
        "latest_funding": null,
        "latest_funding_amount": null,
        "last_raised_at": null,
        "city": "New York",
        "state": "NY",
        "country": "US"
      },
      "contacts": []
    }
  ],
  "total_contacts": 1,
  "total_companies": 1
}
```

**Response Fields:**

- `contacts` (array): List of contacts matching the LinkedIn URL, each containing:
  - `contact`: Contact object with all contact fields
  - `metadata`: ContactMetadata object with LinkedIn URL and other metadata
  - `company`: Related Company object (if contact has a company_id)
  - `company_metadata`: Related CompanyMetadata object (if company exists)
- `companies` (array): List of companies matching the LinkedIn URL, each containing:
  - `company`: Company object with all company fields
  - `metadata`: CompanyMetadata object with LinkedIn URL and other metadata
  - `contacts`: List of related contacts for this company
- `total_contacts` (integer): Total number of contacts found
- `total_companies` (integer): Total number of companies found

**Error Responses:**

- `400 Bad Request`: LinkedIn URL is empty or invalid
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Server error during search

---

## Response Schemas

### ContactWithRelations

```json
{
  "contact": {
    "uuid": "string",
    "first_name": "string | null",
    "last_name": "string | null",
    "company_id": "string | null",
    "email": "string | null",
    "title": "string | null",
    "departments": ["string"] | null,
    "mobile_phone": "string | null",
    "email_status": "string | null",
    "text_search": "string | null",
    "seniority": "string | null",
    "created_at": "datetime | null",
    "updated_at": "datetime | null"
  },
  "metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "linkedin_sales_url": "string | null",
    "facebook_url": "string | null",
    "twitter_url": "string | null",
    "website": "string | null",
    "work_direct_phone": "string | null",
    "home_phone": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null",
    "other_phone": "string | null",
    "stage": "string | null"
  } | null,
  "company": {
    "uuid": "string",
    "name": "string | null",
    "employees_count": "integer | null",
    "industries": ["string"] | null,
    "keywords": ["string"] | null,
    "address": "string | null",
    "annual_revenue": "integer | null",
    "total_funding": "integer | null",
    "technologies": ["string"] | null,
    "text_search": "string | null",
    "created_at": "datetime | null",
    "updated_at": "datetime | null"
  } | null,
  "company_metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "linkedin_sales_url": "string | null",
    "facebook_url": "string | null",
    "twitter_url": "string | null",
    "website": "string | null",
    "company_name_for_emails": "string | null",
    "phone_number": "string | null",
    "latest_funding": "string | null",
    "latest_funding_amount": "integer | null",
    "last_raised_at": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null"
  } | null
}
```

### CompanyWithRelations

```json
{
  "company": {
    "uuid": "string",
    "name": "string | null",
    "employees_count": "integer | null",
    "industries": ["string"] | null,
    "keywords": ["string"] | null,
    "address": "string | null",
    "annual_revenue": "integer | null",
    "total_funding": "integer | null",
    "technologies": ["string"] | null,
    "text_search": "string | null",
    "created_at": "datetime | null",
    "updated_at": "datetime | null"
  },
  "metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "website": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null",
    "phone_number": "string | null"
  } | null,
  "contacts": [
    /* Array of ContactWithRelations */
  ]
}
```

---

## Use Cases

### 1. Search for a Person by LinkedIn URL

Use the POST endpoint to find all contacts with a specific LinkedIn URL:

```bash
POST /api/v3/linkedin/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://www.linkedin.com/in/john-doe"
}
```

This will return all contacts whose `ContactMetadata.linkedin_url` matches the provided URL (case-insensitive partial match).

### 2. Search for a Company by LinkedIn URL

Use the POST endpoint to find all companies with a specific LinkedIn URL:

```bash
POST /api/v3/linkedin/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://www.linkedin.com/company/tech-corp"
}
```

This will return all companies whose `CompanyMetadata.linkedin_url` matches the provided URL.

---

## Error Handling

### Common Error Responses

**400 Bad Request:**

```json
{
  "detail": "LinkedIn URL cannot be empty"
}
```

**401 Unauthorized:**

```json
{
  "detail": "Not authenticated"
}
```

**500 Internal Server Error:**

```json
{
  "detail": "Failed to search by LinkedIn URL"
}
```

### Error Handling Best Practices

1. Always validate the LinkedIn URL format before sending requests
2. Handle empty result sets gracefully (empty arrays are returned, not errors)
3. Check authentication token validity before making requests
4. Implement retry logic for 500 errors
5. Log errors for debugging purposes

---

## Notes

- LinkedIn URL matching is case-insensitive and supports partial matches
- The endpoint searches both person and company LinkedIn URLs simultaneously
- All timestamps are in UTC format
- Empty arrays are returned when no matches are found (not an error condition)

## Activity Tracking

All LinkedIn search operations are automatically tracked in the user activities system. Each operation creates an activity record with:

- **Service Type**: `linkedin`
- **Action Type**: `search`
- **Request Parameters**: Stored as JSON (e.g., `{"url": "https://linkedin.com/in/john-doe"}`)
- **Result Count**: Number of results returned (contacts + companies)
- **Result Summary**: Detailed summary (e.g., `{"contacts": 3, "companies": 2}`)
- **Status**: `success`, `failed`, or `partial`
- **IP Address**: User's IP address (extracted from request headers)
- **User Agent**: User's browser/device information

**Activity Tracking Endpoints:**

- **GET /api/v2/activities/**: View your activity history with filtering and pagination
- **GET /api/v2/activities/stats/**: Get activity statistics (counts by service type, action type, status, and recent activities)

**Example Activity Record (Search):**

```json
{
  "id": 1,
  "user_id": "user-uuid",
  "service_type": "linkedin",
  "action_type": "search",
  "status": "success",
  "request_params": {
    "url": "https://linkedin.com/in/john-doe"
  },
  "result_count": 5,
  "result_summary": {
    "contacts": 3,
    "companies": 2
  },
  "error_message": null,
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Notes:**

- Activities are logged automatically - no additional API calls required
- Failed operations are also logged with error messages
- All activities are tied to the authenticated user
