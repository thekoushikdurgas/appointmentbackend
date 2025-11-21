# Email Finder API Documentation

Complete API documentation for email finder operations, including searching for contact emails by first name, last name, and company domain.

**Related Documentation:**

- [Contacts API](./contacts.md) - For general contact management endpoints
- [Companies API](./company.md) - For general company management endpoints
- [LinkedIn API](./linkdin.md) - For LinkedIn URL-based operations
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Email Finder Endpoints](#email-finder-endpoints)
  - [GET /api/v2/email/finder/](#get-apiv2emailfinder---find-emails-by-name-and-domain)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://54.87.173.234:8000
```

**API Version:** All email finder endpoints are under `/api/v2/email/`

## Authentication

All email finder endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

---

## Email Finder Endpoints

### GET /api/v2/email/finder/ - Find Emails by Name and Domain

Find contact emails by first name, last name, and company domain. This endpoint searches for contacts matching the provided name criteria whose company website domain matches the provided domain/website. Only returns contacts that have email addresses.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Accept: application/json`

**Query Parameters:**

- `first_name` (string, required): Contact first name (case-insensitive partial match)
- `last_name` (string, required): Contact last name (case-insensitive partial match)
- `domain` (string, optional): Company domain or website URL. Can use `website` parameter instead.
- `website` (string, optional): Company website URL (alias for `domain` parameter)

**Domain Parameter Formats:**

The `domain` or `website` parameter accepts various formats:

- Full URL: `https://www.example.com` or `http://example.com`
- Domain with www: `www.example.com`
- Plain domain: `example.com`

The endpoint automatically extracts and normalizes the domain from the input, removing:

- Protocols (`http://`, `https://`)
- `www.` prefix
- Port numbers
- Paths and query strings

**Example Requests:**

```bash
# Using domain parameter
GET /api/v2/email/finder/?first_name=John&last_name=Doe&domain=example.com
Authorization: Bearer <access_token>

# Using website parameter with full URL
GET /api/v2/email/finder/?first_name=John&last_name=Doe&website=https://www.example.com
Authorization: Bearer <access_token>

# Using domain parameter with www
GET /api/v2/email/finder/?first_name=John&last_name=Doe&domain=www.example.com
Authorization: Bearer <access_token>
```

**Response:**

**Success (200 OK):**

```json
{
  "emails": [
    {
      "uuid": "abc123",
      "email": "john.doe@example.com"
    },
    {
      "uuid": "def456",
      "email": "jane.smith@example.com"
    }
  ],
  "total": 2
}
```

The response contains a simple list of email results, each with:
- `uuid` (string): Contact UUID
- `email` (string): Email address from Contact.email

**Error Responses:**

**400 Bad Request - Missing first_name:**

```json
{
  "detail": "first_name is required and cannot be empty"
}
```

**400 Bad Request - Missing last_name:**

```json
{
  "detail": "last_name is required and cannot be empty"
}
```

**400 Bad Request - Missing domain/website:**

```json
{
  "detail": "Either domain or website parameter is required"
}
```

**400 Bad Request - Invalid domain:**

```json
{
  "detail": "Could not extract valid domain from: invalid-domain"
}
```

**401 Unauthorized:**

```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found - Company not found:**

```json
{
  "detail": "No companies found with domain: example.com"
}
```

This error occurs when no companies in the database match the provided domain. The domain has been successfully extracted and validated, but no companies exist with that domain in the `companies_metadata` table.

**404 Not Found - Contact not found:**

```json
{
  "detail": "No contacts found with name 'John Doe' for companies with domain: example.com"
}
```

This error occurs when companies exist for the domain, but no contacts match the provided first name and last name criteria. The search was performed across all companies with the matching domain, but no contacts were found.

**500 Internal Server Error - General error:**

```json
{
  "detail": "Failed to find emails"
}
```

**Status Codes:**

- `200 OK`: Emails found successfully
- `400 Bad Request`: Invalid parameters (missing first_name, last_name, domain/website, or invalid domain format)
- `401 Unauthorized`: Authentication required
- `404 Not Found`: No companies found for the domain, or no contacts found matching the name criteria
- `500 Internal Server Error`: Server error occurred

---

## Response Schemas

### SimpleEmailFinderResponse

```json
{
  "emails": [
    {
      "uuid": "string",
      "email": "string"
    }
  ],
  "total": 0
}
```

**Field Descriptions:**

- `emails` (array): List of email results, each containing:
  - `uuid` (string): Contact UUID
  - `email` (string): Email address from `Contact.email`
- `total` (integer): Total number of emails found

---

## Use Cases

### 1. Find Email by Contact Name and Company Domain

**Scenario:** You know a contact's first name, last name, and their company's website, and want to find their email address.

**Example:**

```bash
GET /api/v2/email/finder/?first_name=John&last_name=Smith&domain=acme.com
```

**Use Case:** Sales prospecting, lead enrichment, contact verification

### 2. Find Multiple Emails for Same Name at Different Companies

**Scenario:** You want to find all contacts named "John Doe" across different companies with specific domains.

**Example:**

```bash
# Search for John Doe at example.com
GET /api/v2/email/finder/?first_name=John&last_name=Doe&domain=example.com

# Search for John Doe at another company
GET /api/v2/email/finder/?first_name=John&last_name=Doe&domain=another-company.com
```

**Use Case:** Contact discovery, email verification across multiple companies

### 3. Domain Extraction from Full URLs

**Scenario:** You have a full company website URL and want to find contacts.

**Example:**

```bash
# Full URL with protocol and path
GET /api/v2/email/finder/?first_name=Jane&last_name=Smith&website=https://www.example.com/about-us
```

The endpoint automatically extracts `example.com` from the URL.

**Use Case:** Integration with external systems that provide full URLs

### 4. Partial Name Matching

**Scenario:** You know part of a contact's name and want to find matching emails.

**Example:**

```bash
# Partial first name match
GET /api/v2/email/finder/?first_name=John&last_name=Smith&domain=example.com
# This will match "John", "Johnny", "Johnson", etc.
```

**Use Case:** Flexible name searching when exact spelling is unknown

---

## Error Handling

### Validation Errors

All validation errors return `400 Bad Request` with descriptive error messages:

- **Missing first_name:** `"first_name is required and cannot be empty"`
- **Missing last_name:** `"last_name is required and cannot be empty"`
- **Missing domain/website:** `"Either domain or website parameter is required"`
- **Empty domain/website:** `"Domain or website cannot be empty"`
- **Invalid domain format:** `"Could not extract valid domain from: <input>"`

### Authentication Errors

- **401 Unauthorized:** Missing or invalid authentication token

### Not Found Errors

The endpoint returns `404 Not Found` in two scenarios:

1. **Company not found:** When no companies in the database match the provided domain
   - Error message: `"No companies found with domain: {domain}"`
   - This occurs after domain extraction and validation, but before searching for contacts
   - Indicates the domain is valid but no companies exist with that domain

2. **Contact not found:** When companies exist for the domain, but no contacts match the name criteria
   - Error message: `"No contacts found with name '{first_name} {last_name}' for companies with domain: {domain}"`
   - This occurs after confirming companies exist, but the contact search returns no results
   - Indicates the domain has companies, but no contacts match the provided first and last name

### Server Errors

- **500 Internal Server Error - General error:** Unexpected server error occurred during email search
  - Error message: `"Failed to find emails"`

---

## Implementation Details

### Domain Extraction

The endpoint uses the same domain extraction logic as the company domain listing endpoint:

1. Removes protocol (`http://`, `https://`)
2. Extracts hostname (everything before first `/`)
3. Removes port numbers
4. Removes `www.` prefix
5. Converts to lowercase

**Examples:**

- `` `https://www.example.com` `` → `` `example.com` ``
- `` `http://example.com:8080/path` `` → `` `example.com` ``
- `www.example.com` → `example.com`
- `example.com` → `example.com`

### Name Matching

- **Case-insensitive:** Matches are case-insensitive
- **Partial matching:** Uses `ILIKE` with `%name%` pattern
- **Both names required:** Both first_name and last_name must match

### Email Filtering

- Only contacts with non-empty email addresses are returned
- Filters out contacts where `Contact.email IS NULL` or empty string

### Database Queries

The endpoint uses a 3-step subquery approach for optimal performance:

**Step 1: Find company UUIDs from companies_metadata table**
- Uses optimized dual search strategy:
  - **Strategy 1 (Primary):** Match against `normalized_domain` column (FAST - uses index)
  - **Strategy 2 (Fallback):** Extract domain from `website` column using SQL functions and match (SLOW - only if Strategy 1 finds nothing)
- Prioritizes indexed `normalized_domain` column for optimal performance
- Only uses website extraction when `normalized_domain` is NULL/empty

**Step 2: Find company UUIDs from companies table**
- Validates that companies exist in the main companies table
- Uses cached company UUIDs from Step 1 (no subquery re-execution)
- Filters by `uuid IN (cached UUID list)`

**Step 3: Find contact (uuid, email) pairs from contacts table**
- Uses cached company UUIDs from Step 2 (no subquery re-execution)
- Filters by `company_id IN (cached UUID list)` - uses direct list filtering instead of nested subqueries
- Filters by `first_name ILIKE '%{first_name}%'` (case-insensitive partial match)
- Filters by `last_name ILIKE '%{last_name}%'` (case-insensitive partial match)
- Filters by `email IS NOT NULL AND email != ''`
- Returns only `uuid` and `email` columns
- Diagnostic queries are optional and combined into single query when no results found

**Field Extraction:**
The repository extracts and logs the following fields for debugging:
- `uuid` (contact UUID)
- `email` (contact email)
- `first_name` (contact first name)
- `last_name` (contact last name)
- `company_id` (company UUID)

**Performance Optimizations (Updated):**
- **Index Optimizations:**
  - Uses `idx_companies_metadata_normalized_domain` index in Step 1 (critical optimization)
  - Uses `idx_companies_metadata_normalized_domain_uuid` composite index for faster Step 1 lookups
  - Uses `idx_contacts_company_id` index in Step 3
  - Uses `idx_contacts_company_name_email` composite index for optimized Step 3 queries
  - Uses trigram indexes (`idx_contacts_first_name_trgm`, `idx_contacts_last_name_trgm`) for name matching
- **Query Optimizations:**
  - Prioritizes `normalized_domain` column (indexed) over website extraction (unindexed)
  - Only uses website extraction as fallback when `normalized_domain` is NULL/empty
  - Caches company UUIDs from Step 1 to avoid re-executing subqueries in Step 2 and Step 3
  - Uses direct UUID list filtering instead of nested subqueries (eliminates subquery re-execution)
  - Removed redundant company existence check (saves significant query time)
  - Diagnostic queries are optional and combined into single query using conditional aggregation
- **Expected Performance:**
  - Response time improved from ~6 minutes to ~15-30 seconds (90%+ improvement)
  - Optimized for selective domains (when few companies match the domain)

---

## Related Endpoints

- **GET /api/v1/contacts/company/domain/**: List all company domains
- **GET /api/v1/contacts/**: Search contacts with filters
- **GET /api/v2/linkedin/**: Search by LinkedIn URL

---

## Notes

- The endpoint only returns contacts that have email addresses in the database
- Domain matching is case-insensitive
- Name matching uses partial matching (substring search)
- The endpoint extracts domains from `CompanyMetadata.website` field using dual search strategy
- The endpoint requires both first_name and last_name to be provided
- Returns simple (uuid, email) pairs for efficient data transfer
- Comprehensive logging is included throughout the flow for debugging purposes
