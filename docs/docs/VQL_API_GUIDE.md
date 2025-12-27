# VQL (Vivek Query Language) API Guide

## Overview

The Appointment360 backend now uses VQL (Vivek Query Language) for flexible, powerful querying of contacts and companies. VQL provides a unified query interface that supports complex filtering, field selection, and related entity population.

## VQL Query Structure

A VQL query is a JSON object with the following structure:

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"},
      {"field": "seniority", "operator": "eq", "value": "Senior"}
    ],
    "or": [
      {"field": "email_status", "operator": "eq", "value": "verified"}
    ]
  },
  "select_columns": ["id", "first_name", "last_name", "email"],
  "company_config": {
    "populate": true,
    "select_columns": ["id", "name", "domain"]
  },
  "limit": 10,
  "offset": 0,
  "sort_by": "created_at",
  "sort_direction": "desc"
}
```

## Endpoints

### Contact Endpoints

#### POST `/api/v1/contacts/query`

Query contacts using VQL.

**Request Body:**
```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  },
  "limit": 20,
  "offset": 0
}
```

**Response:** `CursorPage[ContactListItem]`

#### POST `/api/v1/contacts/count`

Count contacts matching VQL query.

**Request Body:**
```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  }
}
```

**Response:** `{"count": 123}`

#### POST `/api/v1/contacts/count/uuids`

Get contact UUIDs matching VQL query.

**Request Body:**
```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  }
}
```

**Query Parameters:**
- `limit` (optional): Maximum number of UUIDs to return

**Response:** `{"count": 10, "uuids": ["uuid1", "uuid2", ...]}`

#### POST `/api/v1/contacts/stream`

Stream contacts matching VQL query.

**Request Body:**
```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  }
}
```

**Query Parameters:**
- `format`: "jsonl" or "csv" (default: "jsonl")
- `max_results` (optional): Maximum results to stream

**Response:** Streaming response (JSONL or CSV)

### Company Endpoints

Similar endpoints are available for companies:
- `POST /api/v1/companies/query`
- `POST /api/v1/companies/count`
- `POST /api/v1/companies/count/uuids`
- `POST /api/v1/companies/stream`

## Operators

VQL supports the following operators:

- `eq` - Equal
- `ne` - Not equal
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `in` - In list (value must be an array)
- `nin` - Not in list (value must be an array)
- `contains` - Array contains or string contains (case-insensitive)
- `ncontains` - Array doesn't contain or string doesn't contain
- `exists` - Field exists (not null)
- `nexists` - Field doesn't exist (is null)

## Field Names

### Contact Fields

- `id` / `uuid` - Contact UUID
- `first_name` - First name
- `last_name` - Last name
- `title` - Job title
- `email` - Email address
- `company_id` - Company UUID
- `seniority` - Seniority level
- `departments` - Array of departments
- `mobile_phone` - Mobile phone
- `email_status` - Email status
- `status` - Contact status
- `text_search` / `contact_location` - Contact location text search
- `person_linkedin_url` / `linkedin_url` - LinkedIn URL (from ContactMetadata)
- `city`, `state`, `country` - Location (from ContactMetadata)
- `work_direct_phone`, `home_phone`, `other_phone` - Phone numbers (from ContactMetadata)

### Company Fields (for Contact Queries)

- `company.name` - Company name
- `company.employees_count` / `employees_count` - Employee count
- `company.annual_revenue` - Annual revenue
- `company.total_funding` - Total funding
- `company.industries` / `industries` - Array of industries
- `company.keywords` / `keywords` - Array of keywords
- `company.technologies` / `technologies` - Array of technologies
- `company.text_search` / `company_location` - Company location text search
- `company.domain` - Company domain (from CompanyMetadata.website)
- `company.city`, `company.state`, `company.country` - Company location (from CompanyMetadata)

## Examples

### Simple Filter

Find all contacts with "engineer" in their title:

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  },
  "limit": 10
}
```

### Complex Filter with AND/OR

Find senior engineers or managers:

```json
{
  "filters": {
    "and": [
      {
        "or": [
          {"field": "title", "operator": "contains", "value": "engineer"},
          {"field": "title", "operator": "contains", "value": "manager"}
        ]
      },
      {"field": "seniority", "operator": "eq", "value": "Senior"}
    ]
  },
  "limit": 20
}
```

### Filter with Company Data

Find contacts at companies with 100+ employees:

```json
{
  "filters": {
    "and": [
      {"field": "employees_count", "operator": "gte", "value": 100}
    ]
  },
  "company_config": {
    "populate": true,
    "select_columns": ["id", "name", "employees_count"]
  },
  "limit": 50
}
```

### Field Selection

Get only specific fields:

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  },
  "select_columns": ["id", "first_name", "last_name", "email", "title"],
  "limit": 10
}
```

### Array Field Filtering

Find contacts in specific departments:

```json
{
  "filters": {
    "and": [
      {"field": "departments", "operator": "contains", "value": "Engineering"}
    ]
  },
  "limit": 20
}
```

### Sorting

Sort by creation date (newest first):

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  },
  "sort_by": "created_at",
  "sort_direction": "desc",
  "limit": 10
}
```

## Migration from Old Endpoints

### Old: GET `/api/v1/contacts/?title=engineer&limit=10`

### New: POST `/api/v1/contacts/query`

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  },
  "limit": 10
}
```

### Old: GET `/api/v1/contacts/count/?title=engineer`

### New: POST `/api/v1/contacts/count`

```json
{
  "filters": {
    "and": [
      {"field": "title", "operator": "contains", "value": "engineer"}
    ]
  }
}
```

## Notes

- All VQL endpoints use POST method to support complex query structures
- Field names are case-sensitive
- Array operators (`contains`, `ncontains`) work on both array fields and string fields
- The `company_config.populate` option allows you to include related company data in responses
- Pagination uses `limit` and `offset` parameters
- Sorting is optional and defaults to ascending order

