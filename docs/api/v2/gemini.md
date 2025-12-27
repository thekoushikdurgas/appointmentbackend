# Gemini AI API Documentation

Complete API documentation for Gemini AI-powered endpoints, including email risk analysis and company summary generation.

**Related Documentation:**

- [Email API](./email.md) - For email finder and verification endpoints
- [User API](./user.md) - For authentication endpoints

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Gemini AI Endpoints](#gemini-ai-endpoints)
  - [POST /api/v2/gemini/email/analyze](#post-apiv2geminemailanalyze---analyze-email-risk)
  - [POST /api/v2/gemini/company/summary](#post-apiv2geminicompanysummary---generate-company-summary)
  - [POST /api/v2/gemini/parse-filters](#post-apiv2geminiparse-filters---parse-natural-language-filters)
- [Response Schemas](#response-schemas)
- [Use Cases](#use-cases)
- [Error Handling](#error-handling)

---

## Base URL

For production, use:

```txt
http://34.229.94.175:8000
```

**API Version:** All Gemini AI endpoints are under `/api/v2/gemini/`

## Authentication

All Gemini AI endpoints require JWT authentication via the `Authorization` header:

```txt
Authorization: Bearer <access_token>
```

Tokens are obtained through the login or register endpoints.

## Role-Based Access Control

All Gemini AI endpoints are accessible to all authenticated users regardless of role:

- **Free Users (`FreeUser`)**: ✅ Full access to all Gemini AI endpoints
- **Pro Users (`ProUser`)**: ✅ Full access to all Gemini AI endpoints
- **Admin (`Admin`)**: ✅ Full access to all Gemini AI endpoints
- **Super Admin (`SuperAdmin`)**: ✅ Full access to all Gemini AI endpoints

**Note:** There are no role-based restrictions on Gemini AI functionality. All authenticated users can use email risk analysis and company summary generation.

---

## Gemini AI Endpoints

### POST /api/v2/gemini/email/analyze - Analyze Email Risk

Analyze an email address for potential risk factors using Gemini AI. This endpoint evaluates email addresses to identify risk indicators such as role-based emails, disposable email addresses, and provides a risk score with detailed analysis.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Request Body Fields:**

- `email` (string, required): Email address to analyze. Must be a valid email format (EmailStr).

**Response:**

**Success (200 OK):**

```json
{
  "riskScore": 75,
  "analysis": "This email appears to be a role-based email address (e.g., info@, support@) which may have lower deliverability rates.",
  "isRoleBased": true,
  "isDisposable": false
}
```

**Response Fields:**

- `riskScore` (integer): Risk score from 0-100, where higher scores indicate higher risk
- `analysis` (string): Detailed text analysis of the email address risk factors
- `isRoleBased` (boolean): Whether the email is a role-based email (e.g., info@, support@, admin@)
- `isDisposable` (boolean): Whether the email is from a disposable email service

**Error (400 Bad Request) - Invalid Email Format:**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "input": "invalid-email"
    }
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to analyze email risk"
}
```

**Status Codes:**

- `200 OK`: Email risk analysis completed successfully
- `400 Bad Request`: Invalid email format
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to analyze email risk (Gemini AI service error)

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v2/gemini/email/analyze" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "info@example.com"
  }'
```

**Notes:**

- The analysis is performed using Google Gemini AI
- Risk scores are calculated based on multiple factors including email patterns, domain reputation, and disposable email detection
- Role-based emails typically have higher risk scores due to lower engagement rates
- Disposable emails are flagged as high risk

---

### POST /api/v2/gemini/company/summary - Generate Company Summary

Generate an AI-powered company summary using Gemini AI. This endpoint creates a comprehensive summary of a company based on its name and industry, providing insights and context.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "company_name": "Example Company Inc.",
  "industry": "Technology"
}
```

**Request Body Fields:**

- `company_name` (string, required): Name of the company to generate a summary for
- `industry` (string, required): Industry or sector the company operates in

**Response:**

**Success (200 OK):**

```json
{
  "summary": "Example Company Inc. is a technology company operating in the Technology sector. The company focuses on innovative solutions and digital transformation services for businesses across various industries."
}
```

**Response Fields:**

- `summary` (string): AI-generated company summary providing insights and context about the company

**Error (400 Bad Request) - Missing Fields:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "company_name"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to generate company summary"
}
```

**Status Codes:**

- `200 OK`: Company summary generated successfully
- `400 Bad Request`: Missing required fields (company_name or industry)
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to generate company summary (Gemini AI service error)

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v2/gemini/company/summary" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corporation",
    "industry": "Software"
  }'
```

**Notes:**

- The summary is generated using Google Gemini AI
- Summaries are context-aware and provide relevant insights based on the company name and industry
- The quality of the summary depends on the specificity of the industry provided
- Summaries are generated in real-time and may vary slightly between requests

---

### POST /api/v2/gemini/parse-filters - Parse Natural Language Filters

Parse a natural language query into structured contact filter parameters using Gemini AI. This endpoint extracts job titles, company names, industries, locations, employee counts, and seniority levels from natural language queries to enable intelligent contact search.

**Headers:**

- `Authorization: Bearer <access_token>` (required)
- `Content-Type: application/json`

**Request Body:**

```json
{
  "query": "VP of Engineering at tech companies in San Francisco with 100-500 employees"
}
```

**Request Body Fields:**

- `query` (string, required): Natural language query describing the contact filters you want to extract

**Response:**

**Success (200 OK):**

```json
{
  "job_titles": ["VP", "Engineering"],
  "company_names": null,
  "industry": ["Technology"],
  "location": ["San Francisco"],
  "employees": [100, 500],
  "seniority": ["VP"]
}
```

**Response Fields:**

- `job_titles` (array[string], optional): List of extracted job titles (e.g., "VP", "CEO", "Director", "Engineer")
- `company_names` (array[string], optional): List of extracted company names
- `industry` (array[string], optional): List of extracted industry sectors
- `location` (array[string], optional): List of extracted locations (city, state, country)
- `employees` (tuple[integer, integer], optional): Employee count range as [min, max]. Returns null if no range specified
- `seniority` (array[string], optional): List of extracted seniority levels (e.g., "CXO", "VP", "Director", "Manager")

**Error (400 Bad Request) - Missing Query:**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "query"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**Error (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

**Error (500 Internal Server Error):**

```json
{
  "detail": "Failed to parse filters: <error_message>"
}
```

**Status Codes:**

- `200 OK`: Filter parsing completed successfully
- `400 Bad Request`: Missing required query field
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Failed to parse filters (Gemini AI service error or fallback failure)

**Example Request:**

```bash
curl -X POST "http://34.229.94.175:8000/api/v2/gemini/parse-filters" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "VP of Engineering at tech companies in San Francisco"
  }'
```

**Example Queries:**

```bash
# Extract job titles and industry
{
  "query": "CEOs and CTOs in the finance industry"
}

# Extract location and employee count
{
  "query": "Directors in New York at companies with 200-1000 employees"
}

# Extract seniority and company names
{
  "query": "VPs and Directors at Google and Microsoft"
}
```

**Notes:**

- The parsing is performed using Google Gemini AI
- If Gemini AI is unavailable, the endpoint falls back to basic pattern matching
- Only fields that are successfully extracted from the query are included in the response (others are null)
- Employee count ranges are returned as a tuple [min, max] if both values are found
- The endpoint is designed to extract structured filter parameters from natural language for use in contact search queries
- All extracted values are returned as arrays to support multiple matches (e.g., multiple job titles)

---

## Response Schemas

### EmailRiskAnalysisRequest

```json
{
  "email": "string"
}
```

**Field Descriptions:**

- `email` (string, required): Email address to analyze. Must be a valid email format (EmailStr).

### EmailRiskAnalysisResponse

```json
{
  "riskScore": 0,
  "analysis": "string",
  "isRoleBased": false,
  "isDisposable": false
}
```

**Field Descriptions:**

- `riskScore` (integer): Risk score from 0-100, where higher scores indicate higher risk
- `analysis` (string): Detailed text analysis of the email address risk factors
- `isRoleBased` (boolean): Whether the email is a role-based email (e.g., info@, support@, admin@)
- `isDisposable` (boolean): Whether the email is from a disposable email service

### CompanySummaryRequest

```json
{
  "company_name": "string",
  "industry": "string"
}
```

**Field Descriptions:**

- `company_name` (string, required): Name of the company to generate a summary for
- `industry` (string, required): Industry or sector the company operates in

### CompanySummaryResponse

```json
{
  "summary": "string"
}
```

**Field Descriptions:**

- `summary` (string): AI-generated company summary providing insights and context about the company

### ParseFiltersRequest

```json
{
  "query": "string"
}
```

**Field Descriptions:**

- `query` (string, required): Natural language query describing the contact filters to extract

### ParseFiltersResponse

```json
{
  "job_titles": ["string"] | null,
  "company_names": ["string"] | null,
  "industry": ["string"] | null,
  "location": ["string"] | null,
  "employees": [integer, integer] | null,
  "seniority": ["string"] | null
}
```

**Field Descriptions:**

- `job_titles` (array[string], optional): List of extracted job titles
- `company_names` (array[string], optional): List of extracted company names
- `industry` (array[string], optional): List of extracted industry sectors
- `location` (array[string], optional): List of extracted locations
- `employees` (tuple[integer, integer], optional): Employee count range as [min, max]. Returns null if no range specified
- `seniority` (array[string], optional): List of extracted seniority levels

---

## Use Cases

### 1. Analyze Email Risk Before Sending

Before sending marketing emails or important communications, analyze email addresses to identify high-risk recipients:

```bash
POST /api/v2/gemini/email/analyze
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "info@example.com"
}
```

### 2. Generate Company Intelligence

Generate AI-powered summaries for companies in your database to enrich contact records:

```bash
POST /api/v2/gemini/company/summary
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "company_name": "Tech Innovations Inc.",
  "industry": "Software Development"
}
```

### 3. Bulk Email Risk Analysis

Analyze multiple email addresses to identify high-risk contacts:

```bash
# Analyze each email individually
for email in email_list:
    POST /api/v2/gemini/email/analyze
    {
      "email": email
    }
```

### 4. Parse Natural Language Query into Filters

Convert a natural language query into structured filter parameters for contact search:

```bash
POST /api/v2/gemini/parse-filters
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "query": "VP of Engineering at tech companies in San Francisco with 100-500 employees"
}
```

**Use Case:** Intelligent contact search, query understanding, natural language interface for contact filtering

---

## Error Handling

### Invalid Email Format

**Request:**

```bash
POST /api/v2/gemini/email/analyze
{
  "email": "not-an-email"
}
```

**Response (400 Bad Request):**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "input": "not-an-email"
    }
  ]
}
```

### Missing Required Fields

**Request:**

```bash
POST /api/v2/gemini/company/summary
{
  "company_name": "Example Corp"
  // Missing industry field
}
```

**Response (400 Bad Request):**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "industry"],
      "msg": "Field required",
      "input": {"company_name": "Example Corp"}
    }
  ]
}
```

### Unauthorized Access

**Request:**

```bash
POST /api/v2/gemini/email/analyze
# Missing Authorization header
```

**Response (401 Unauthorized):**

```json
{
  "detail": "Not authenticated"
}
```

### Service Error

**Response (500 Internal Server Error):**

```json
{
  "detail": "Failed to analyze email risk"
}
```

or

```json
{
  "detail": "Failed to generate company summary"
}
```

---

## Notes

- All Gemini AI endpoints require JWT authentication
- Email risk analysis uses Google Gemini AI to evaluate email addresses
- Company summaries are generated in real-time using Gemini AI
- Filter parsing uses Google Gemini AI to extract structured parameters from natural language
- If Gemini AI is unavailable, the parse-filters endpoint falls back to basic pattern matching
- Risk scores are calculated on a scale of 0-100
- Role-based emails (info@, support@, admin@) typically have higher risk scores
- Disposable email addresses are automatically flagged as high risk
- Company summaries are context-aware and provide relevant insights
- Filter parsing extracts only fields that are present in the query (others return null)
- All endpoints are accessible to all authenticated users regardless of role
- No credits are deducted for using Gemini AI endpoints (unlimited usage)

