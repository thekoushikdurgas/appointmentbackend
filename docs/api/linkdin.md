# LinkedIn CRUD API Documentation

Complete API documentation for LinkedIn URL-based CRUD operations, including searching and creating/updating contacts and companies by LinkedIn URL.

**Related Documentation:**

- [Contacts API](./contacts.md) - For general contact management endpoints
- [Companies API](./company.md) - For general company management endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [LinkedIn Endpoints](#linkedin-endpoints)
  - [GET /api/v2/linkedin/](#get-apiv2linkedin---search-by-linkedin-url)
  - [POST /api/v2/linkedin/](#post-apiv2linkedin---create-or-update-by-linkedin-url)
  - [POST /api/v2/linkedin/export](#post-apiv2linkedinexport---export-contacts-and-companies-by-linkedin-urls)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All LinkedIn endpoints are under `/api/v2/linkedin/`

## Authentication

All LinkedIn endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## LinkedIn Endpoints

### GET /api/v2/linkedin/ - Search by LinkedIn URL

Search for contacts and companies by LinkedIn URL. This endpoint searches both person LinkedIn URLs (from `ContactMetadata.linkedin_url`) and company LinkedIn URLs (from `CompanyMetadata.linkedin_url`), returning all matching records with their related data.

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
GET /api/v2/linkedin/
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
        "website": "https://johndoe.com",
        "city": "San Francisco",
        "state": "CA",
        "country": "US",
        "work_direct_phone": "+1234567890",
        "home_phone": null,
        "other_phone": null,
        "stage": "active"
      },
      "company": {
        "uuid": "company-uuid-123",
        "name": "Tech Corp",
        "employees_count": 500,
        "industries": ["Technology"],
        "annual_revenue": 10000000,
        "total_funding": 5000000,
        "technologies": ["Python", "JavaScript"],
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-15T10:00:00"
      },
      "company_metadata": {
        "uuid": "company-uuid-123",
        "linkedin_url": "https://www.linkedin.com/company/tech-corp",
        "website": "https://techcorp.com",
        "city": "San Francisco",
        "state": "CA",
        "country": "US",
        "phone_number": "+1234567890"
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
        "annual_revenue": 5000000,
        "total_funding": 2000000,
        "technologies": ["Java", "Spring"],
        "created_at": "2024-01-05T00:00:00",
        "updated_at": "2024-01-10T10:00:00"
      },
      "metadata": {
        "uuid": "company-uuid-456",
        "linkedin_url": "https://www.linkedin.com/company/another-company",
        "website": "https://anothercompany.com",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "phone_number": "+1987654321"
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

### POST /api/v2/linkedin/ - Create or Update by LinkedIn URL

Create or update contacts and companies based on LinkedIn URL. If a record with the LinkedIn URL already exists, it will be updated. Otherwise, new records will be created.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "url": "https://www.linkedin.com/in/jane-smith",
  "contact_data": {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@example.com",
    "title": "Product Manager",
    "seniority": "manager",
    "departments": ["Product"],
    "mobile_phone": "+1987654321"
  },
  "contact_metadata": {
    "website": "https://janesmith.com",
    "city": "New York",
    "state": "NY",
    "country": "US",
    "work_direct_phone": "+1987654321"
  },
  "company_data": {
    "name": "Product Corp",
    "employees_count": 300,
    "industries": ["Technology", "Product"],
    "annual_revenue": 15000000
  },
  "company_metadata": {
    "website": "https://productcorp.com",
    "city": "New York",
    "state": "NY",
    "country": "US"
  }
}
```

**Request Body Fields:**

- `url` (string, required): LinkedIn URL. Will be set as `linkedin_url` in the appropriate metadata table.
- `contact_data` (object, optional): Contact fields to create/update. All standard contact fields are supported.
- `contact_metadata` (object, optional): Contact metadata fields. The `linkedin_url` will automatically be set to the `url` value.
- `company_data` (object, optional): Company fields to create/update. All standard company fields are supported.
- `company_metadata` (object, optional): Company metadata fields. The `linkedin_url` will automatically be set to the `url` value.

**Example Request:**

```bash
POST /api/v2/linkedin/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "url": "https://www.linkedin.com/in/jane-smith",
  "contact_data": {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@example.com",
    "title": "Product Manager"
  },
  "contact_metadata": {
    "city": "New York",
    "state": "NY",
    "country": "US"
  }
}
```

**Response:**

**Success (200 OK):**

```json
{
  "created": true,
  "updated": false,
  "contacts": [
    {
      "contact": {
        "uuid": "new-contact-uuid",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "title": "Product Manager",
        "seniority": "_",
        "departments": null,
        "created_at": "2024-01-25T12:00:00",
        "updated_at": "2024-01-25T12:00:00"
      },
      "metadata": {
        "uuid": "new-contact-uuid",
        "linkedin_url": "https://www.linkedin.com/in/jane-smith",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "website": null,
        "work_direct_phone": null,
        "home_phone": null,
        "other_phone": null,
        "stage": null
      },
      "company": null,
      "company_metadata": null
    }
  ],
  "companies": []
}
```

**Response Fields:**

- `created` (boolean): Whether new records were created
- `updated` (boolean): Whether existing records were updated
- `contacts` (array): List of created/updated contacts with their metadata and related company data
- `companies` (array): List of created/updated companies with their metadata and related contacts

**Error Responses:**

- `400 Bad Request`: LinkedIn URL is empty or invalid, or request body is malformed
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Server error during create/update operation

---

### POST /api/v2/linkedin/export - Export Contacts and Companies by LinkedIn URLs

Create a CSV export of contacts and companies by multiple LinkedIn URLs. Accepts a list of LinkedIn URLs, searches for matching contacts and companies, and generates a combined CSV file containing all matches plus unmatched URLs marked as "not_found". The export is processed asynchronously in the background using Celery. Returns immediately with an export ID and job ID for tracking.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "urls": [
    "https://www.linkedin.com/in/john-doe",
    "https://www.linkedin.com/company/tech-corp",
    "https://www.linkedin.com/in/jane-smith"
  ]
}
```

**Request Body Fields:**

- `urls` (array[string], required, min: 1): List of LinkedIn URLs to search and export. At least one URL is required. Can be person LinkedIn URLs or company LinkedIn URLs.

**Example Request:**

```bash
POST /api/v2/linkedin/export
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "urls": [
    "https://www.linkedin.com/in/john-doe",
    "https://www.linkedin.com/company/tech-corp"
  ]
}
```

**Response:**

**Success (201 Created):**

```json
{
  "export_id": "f4b8c3f5-2222-4f9b-bbbb-123456789abc",
  "download_url": "http://54.87.173.234:8000/api/v2/exports/f4b8c3f5-2222-4f9b-bbbb-123456789abc/download?token=...",
  "expires_at": "2024-12-20T10:30:00Z",
  "contact_count": 0,
  "company_count": 0,
  "status": "pending",
  "job_id": "abc123-def456-ghi789"
}
```

**Response Fields:**

- `export_id` (string, UUID): Unique identifier for the export
- `download_url` (string): Signed URL for downloading the CSV file (will be updated when export completes)
- `expires_at` (datetime, ISO 8601): Timestamp when the download URL expires (24 hours from creation)
- `contact_count` (integer): Number of contacts included in the export (initially 0, updated when export completes)
- `company_count` (integer): Number of companies included in the export (initially 0, updated when export completes)
- `status` (string): Export status. Possible values: `pending`, `processing`, `completed`, `failed`, `cancelled`
- `job_id` (string, optional): Celery task ID for tracking the background job

**Error Responses:**

- `400 Bad Request`: At least one LinkedIn URL is required, or all URLs are empty/invalid
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Server error during export creation

**CSV Structure:**

The generated CSV file includes a `record_type` column that can have three values:
- `contact`: Row represents a contact found from the LinkedIn URLs
- `company`: Row represents a company found from the LinkedIn URLs
- `not_found`: Row represents a LinkedIn URL that didn't match any contacts or companies

**CSV Fields Included:**

The CSV includes all contact, company, and metadata fields:

**Contact Fields (populated for `contact` rows):**
- `contact_uuid`, `contact_first_name`, `contact_last_name`, `contact_company_id`, `contact_email`, `contact_title`, `contact_departments`, `contact_mobile_phone`, `contact_email_status`, `contact_text_search`, `contact_seniority`, `contact_created_at`, `contact_updated_at`

**Contact Metadata Fields (populated for `contact` rows):**
- `contact_metadata_linkedin_url`, `contact_metadata_facebook_url`, `contact_metadata_twitter_url`, `contact_metadata_website`, `contact_metadata_work_direct_phone`, `contact_metadata_home_phone`, `contact_metadata_city`, `contact_metadata_state`, `contact_metadata_country`, `contact_metadata_other_phone`, `contact_metadata_stage`

**Company Fields (populated for `company` rows and related companies in `contact` rows):**
- `company_uuid`, `company_name`, `company_employees_count`, `company_industries`, `company_keywords`, `company_address`, `company_annual_revenue`, `company_total_funding`, `company_technologies`, `company_text_search`, `company_created_at`, `company_updated_at`

**Company Metadata Fields (populated for `company` rows and related companies in `contact` rows):**
- `company_metadata_linkedin_url`, `company_metadata_facebook_url`, `company_metadata_twitter_url`, `company_metadata_website`, `company_metadata_company_name_for_emails`, `company_metadata_phone_number`, `company_metadata_latest_funding`, `company_metadata_latest_funding_amount`, `company_metadata_last_raised_at`, `company_metadata_city`, `company_metadata_state`, `company_metadata_country`

**For `not_found` rows:**
- Only `record_type` and `linkedin_url` fields are populated
- All other fields are empty

**Export Processing:**

1. The export is queued as a background job immediately upon request
2. The background job searches all provided LinkedIn URLs in parallel
3. Collects unique contact and company UUIDs from matches
4. Generates a combined CSV with all contacts, companies, and unmatched URLs
5. Uploads CSV to S3 (if configured) or saves locally
6. Updates export status to `completed` and generates signed download URL
7. The download URL expires 24 hours after creation

**Tracking Export Progress:**

Use the export status endpoint to track progress:

```bash
GET /api/v2/exports/{export_id}/status
Authorization: Bearer <access_token>
```

**Viewing Export Details:**

The original LinkedIn URLs used for the export are stored in the export record and can be viewed when listing exports:

```bash
GET /api/v2/exports/
Authorization: Bearer <access_token>
```

The response includes a `linkedin_urls` field in each export record (only populated for LinkedIn exports):

```json
{
  "exports": [
    {
      "export_id": "f4b8c3f5-2222-4f9b-bbbb-123456789abc",
      "linkedin_urls": [
        "https://www.linkedin.com/in/john-doe",
        "https://www.linkedin.com/company/tech-corp",
        "https://www.linkedin.com/in/jane-smith"
      ],
      "contact_count": 2,
      "company_count": 1,
      "status": "completed",
      ...
    }
  ]
}
```

**Downloading the Export:**

Once the export status is `completed`, download the CSV using the signed URL:

```bash
GET /api/v2/exports/{export_id}/download?token={download_token}
Authorization: Bearer <access_token>
```

---

## Response Schemas

### ContactWithRelations

```json
{
  "contact": {
    "uuid": "string",
    "first_name": "string | null",
    "last_name": "string | null",
    "email": "string | null",
    "title": "string | null",
    "company_id": "string | null",
    "seniority": "string | null",
    "departments": ["string"] | null,
    "mobile_phone": "string | null",
    "email_status": "string | null",
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
    "work_direct_phone": "string | null",
    "home_phone": "string | null",
    "other_phone": "string | null",
    "stage": "string | null"
  } | null,
  "company": {
    "uuid": "string",
    "name": "string | null",
    "employees_count": "integer | null",
    "industries": ["string"] | null,
    "annual_revenue": "integer | null",
    "total_funding": "integer | null",
    "technologies": ["string"] | null,
    "created_at": "datetime | null",
    "updated_at": "datetime | null"
  } | null,
  "company_metadata": {
    "uuid": "string",
    "linkedin_url": "string | null",
    "website": "string | null",
    "city": "string | null",
    "state": "string | null",
    "country": "string | null",
    "phone_number": "string | null"
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
    "annual_revenue": "integer | null",
    "total_funding": "integer | null",
    "technologies": ["string"] | null,
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

Use the GET endpoint to find all contacts with a specific LinkedIn URL:

```bash
GET /api/v2/linkedin/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://www.linkedin.com/in/john-doe"
}
```

This will return all contacts whose `ContactMetadata.linkedin_url` matches the provided URL (case-insensitive partial match).

### 2. Search for a Company by LinkedIn URL

Use the GET endpoint to find all companies with a specific LinkedIn URL:

```bash
GET /api/v2/linkedin/
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "url": "https://www.linkedin.com/company/tech-corp"
}
```

This will return all companies whose `CompanyMetadata.linkedin_url` matches the provided URL.

### 3. Create a New Contact from LinkedIn URL

Use the POST endpoint to create a new contact with LinkedIn metadata:

```bash
POST /api/v2/linkedin/
{
  "url": "https://www.linkedin.com/in/new-person",
  "contact_data": {
    "first_name": "New",
    "last_name": "Person",
    "email": "new.person@example.com",
    "title": "Developer"
  },
  "contact_metadata": {
    "city": "San Francisco",
    "state": "CA"
  }
}
```

### 4. Update Existing Contact by LinkedIn URL

If a contact with the LinkedIn URL already exists, the POST endpoint will update it:

```bash
POST /api/v2/linkedin/
{
  "url": "https://www.linkedin.com/in/existing-person",
  "contact_data": {
    "title": "Senior Developer",
    "email": "updated.email@example.com"
  }
}
```

### 5. Create Company with LinkedIn URL

Use the POST endpoint to create a new company:

```bash
POST /api/v2/linkedin/
{
  "url": "https://www.linkedin.com/company/new-company",
  "company_data": {
    "name": "New Company Inc",
    "employees_count": 100,
    "industries": ["Technology"]
  },
  "company_metadata": {
    "website": "https://newcompany.com",
    "city": "San Francisco",
    "state": "CA",
    "country": "US"
  }
}
```

### 6. Export Contacts and Companies by Multiple LinkedIn URLs

Use the export endpoint to generate a CSV file containing contacts and companies found from multiple LinkedIn URLs:

```bash
POST /api/v2/linkedin/export
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "urls": [
    "https://www.linkedin.com/in/john-doe",
    "https://www.linkedin.com/company/tech-corp",
    "https://www.linkedin.com/in/jane-smith"
  ]
}
```

This will:
1. Search all provided LinkedIn URLs in parallel
2. Collect all matching contacts and companies
3. Generate a combined CSV with contacts, companies, and unmatched URLs
4. Return an export ID and job ID for tracking
5. Process the export asynchronously in the background

Check export status:

```bash
GET /api/v2/exports/{export_id}/status
Authorization: Bearer <access_token>
```

Download the CSV once completed:

```bash
GET /api/v2/exports/{export_id}/download?token={download_token}
Authorization: Bearer <access_token>
```

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
- When creating records, if a UUID is not provided, one will be automatically generated
- The `linkedin_url` in metadata is automatically set to the provided `url` value in POST requests
- All timestamps are in UTC format
- Empty arrays are returned when no matches are found (not an error condition)
- Export endpoints process requests asynchronously via background jobs (Celery)
- Export CSV files include a `record_type` column to distinguish contacts, companies, and unmatched URLs
- Unmatched LinkedIn URLs are included in the export CSV with `record_type="not_found"` for visibility

