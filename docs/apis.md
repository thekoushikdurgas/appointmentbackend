# Appointment360 API Reference

The Appointment360 backend exposes a RESTful API implemented with FastAPI. This document describes every public endpoint that ships with the repository, the query/body parameters each endpoint accepts, expected responses, and known error semantics. All paths listed below assume the default versioned prefix `API_V1_PREFIX = "/api/v1"` defined in `app/core/config.py`.

## Base URLs

| Environment | Example |
| ----------- | ------- |
| Server origin | `http://localhost:8000` |
| Versioned API root | `http://localhost:8000/api/v1` |

## Authentication & Headers

- **Read endpoints** (`GET`) are currently unauthenticated.
- **Contact creation** requires the header `X-Contacts-Write-Key` to match the configured `CONTACTS_WRITE_KEY` setting. Missing or incorrect keys return `403 Forbidden`.
- All endpoints expect `Accept: application/json`. The `POST /contacts/` endpoint also requires `Content-Type: application/json`.

## Error Handling

| HTTP Status | When Returned |
| ----------- | ------------- |
| `400 Bad Request` | Validation failures (invalid query/body data, malformed cursor tokens, negative pagination values, unsupported file uploads). |
| `403 Forbidden` | Missing/invalid `X-Contacts-Write-Key` for contact creation or when write access is disabled. |
| `404 Not Found` | Contact or import job identifiers that cannot be resolved, or malformed paths such as `/contacts//`. |
| `422 Unprocessable Entity` | File upload without a filename. |
| `500 Internal Server Error` | Unhandled persistence or background task failures during import workflows. |

All error payloads follow FastAPI's default schema: `{"detail": "message"}` unless otherwise noted.

## System Endpoints

| Method | Path | Description | Success Response |
| ------ | ---- | ----------- | ---------------- |
| `GET` | `/api/v1/` | Returns project metadata: name, version, docs URL. | `200 OK` → `{"name": str, "version": str, "docs": str}` |
| `GET` | `/api/v1/health/` | Lightweight health probe. | `200 OK` → `{"status": "healthy", "environment": str}` |

The unversioned `GET /health` endpoint defined in `app/main.py` is also available for infrastructure probes.

## Contacts API

All contacts endpoints are defined in `app/api/v1/endpoints/contacts.py`. They rely on the schemas in `app/schemas/contacts.py`, `app/schemas/common.py`, and `app/schemas/filters.py`.

### Common Query Parameters

Contacts list, count, and lookup endpoints share a rich set of filters derived from `ContactFilterParams`. Unless otherwise stated, parameters are optional and perform case-insensitive substring matching.

- **Pagination & cursors**
  - `limit` (query): Maximum items per page (default resolves to `settings.DEFAULT_PAGE_SIZE`, capped by `settings.MAX_PAGE_SIZE`).
  - `offset` (query): Zero-based offset into the result set.
  - `cursor` (query): Base64 cursor token (`encode_offset_cursor`) that supersedes `offset` when supplied.
  - `page` (query): 1-indexed page number; converted to an offset when provided.
  - `page_size` (query/body via filters): Overrides default page size (bounded by `MAX_PAGE_SIZE`).
  - `distinct` (query/body via filters): `true/false` expression enabling distinct contacts.

- **Contact identity filters** (`first_name`, `last_name`, `title`, `seniority`, `email`, `email_status`, `uuid` via `exclude_company_ids`).
- **Department & seniority**: `department`/`departments`, `exclude_departments`, `exclude_seniorities`.
- **Location**: `contact_location` (`text_search` alias), `company_location` (`company_text_search` alias), `city`, `state`, `country`, `company_city`, `company_state`, `company_country`, `company_address`.
- **Company profile**: `company`, `company_name_for_emails`, `employees_count` (`employees` alias), `employees_min`, `employees_max`, `annual_revenue`, `annual_revenue_min`, `annual_revenue_max`, `total_funding`, `total_funding_min`, `total_funding_max`, `stage`.
- **Array/keyword filters**: `technologies`, `keywords`, `industries`, plus exclusion counterparts (`exclude_technologies`, `exclude_keywords`, `exclude_industries`).
- **Funding metadata**: `latest_funding_amount_min`, `latest_funding_amount_max`, `latest_funding`, `last_raised_at`.
- **Phone & contact details**: `mobile_phone`, `work_direct_phone`, `home_phone`, `other_phone`, `corporate_phone`, `company_phone`.
- **Web & social**: `website`, `person_linkedin_url`, `company_linkedin_url`, `facebook_url`, `twitter_url`.
- **Temporal filters**: `created_at_after`, `created_at_before`, `updated_at_after`, `updated_at_before` (ISO timestamps coerced to UTC naive).
- **Exclusion lists** accept comma-delimited strings, JSON arrays, or repeated query params depending on the caller. Empty strings are ignored.
- **Free-text search**: `search` applies case-insensitive matching across contact and company columns.
- **Ordering**: `ordering` accepts any key from `ContactRepository.ordering_map` (e.g., `last_name`, `company`, `created_at`).

Validation errors for any of the above parameters return `400 Bad Request`.

### Attribute List Parameters

Attribute lookup endpoints use `AttributeListParams`:

| Parameter | Type | Default | Notes |
| --------- | ---- | ------- | ----- |
| `search` | `str` | `null` | Optional substring filter. |
| `distinct` | `bool` | `false` | Normalized from truthy/falsey strings. |
| `limit` | `int` | `25` | Must be positive. |
| `offset` | `int` | `0` | Must be ≥ 0. |
| `ordering` | `str` | `null` | `value` sorts alphabetically. |

Additional flags:

- `separated` (query, `bool`): Available on `/industry/`, `/keywords/`, `/technologies/`. When `true`, array columns are split, deduplicated, and the `limit` applies after splitting.

### Endpoints

| Method | Path | Description | Success Response | Additional Notes |
| ------ | ---- | ----------- | ---------------- | ---------------- |
| `GET` | `/api/v1/contacts/` | Paginated contact list. | `200 OK` → `CursorPage[ContactListItem]` | Accepts all `ContactFilterParams` fields, pagination params, and cursor tokens. Invalid cursor tokens return `400 Bad Request`. |
| `GET` | `/api/v1/contacts/count/` | Count contacts matching filters. | `200 OK` → `{"count": int}` | Shares the same filter contract as list. |
| `POST` | `/api/v1/contacts/` | Create a contact record. | `201 Created` → `ContactDetail` | Requires `X-Contacts-Write-Key`. Body schema aligns with `ContactCreate`; unspecified fields default to `null`. Empty/placeholder text is normalized. |
| `GET` | `/api/v1/contacts/{contact_id}/` | Retrieve contact detail. | `200 OK` → `ContactDetail` | Trailing slash variant documented; non-existent IDs return `404`. |

#### ContactCreate Body Fields

All properties are optional unless business rules dictate otherwise.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `uuid` | `str` | Custom UUID (generated if omitted). |
| `first_name`, `last_name` | `str` | Basic identity fields. |
| `company_id` | `str` | Company UUID (links to `companies` table). |
| `email`, `email_status` | `str` | Email address and deliverability status. |
| `title`, `seniority`, `departments` | `str` / `list[str]` | Role information; departments stored as array of strings. |
| `mobile_phone` | `str` | Stored in `Contact.mobile_phone`. |
| `text_search` | `str` | Free-form location text used for search. |

The service normalizes empty strings, trims whitespace, and collapses placeholder values (`"_"`) to `null`. Departments arrays are deduplicated and stored as comma-delimited strings for list responses.

#### Attribute Lookup Suite

All endpoints below return `200 OK` with a JSON array of strings. They accept both `ContactFilterParams` and `AttributeListParams`, with `separated` supported where noted.

| Path | Supports `separated`? | Column Source |
| ---- | --------------------- | ------------- |
| `/api/v1/contacts/title/` | No | `Contact.title` |
| `/api/v1/contacts/company/` | No | `Company.name` |
| `/api/v1/contacts/industry/` | Yes | `Company.industries` (array) |
| `/api/v1/contacts/keywords/` | Yes | `Company.keywords` (array) |
| `/api/v1/contacts/technologies/` | Yes | `Company.technologies` (array) |
| `/api/v1/contacts/company_address/` | No | `Company.text_search` |
| `/api/v1/contacts/contact_address/` | No | `Contact.text_search` |
| `/api/v1/contacts/city/` | No | `ContactMetadata.city` |
| `/api/v1/contacts/state/` | No | `ContactMetadata.state` |
| `/api/v1/contacts/country/` | No | `ContactMetadata.country` |
| `/api/v1/contacts/company_city/` | No | `CompanyMetadata.city` |
| `/api/v1/contacts/company_state/` | No | `CompanyMetadata.state` |
| `/api/v1/contacts/company_country/` | No | `CompanyMetadata.country` |

Error semantics:

- `400 Bad Request` for non-positive limits, negative offsets, or validation issues.
- `200 OK` returns an empty array when no values match.

### Response Models

- `CursorPage[ContactListItem]`: `{ "next": str|null, "previous": str|null, "results": [ContactListItem, ...] }`.
- `ContactListItem`: flattened view combining contact, company, and metadata columns (see `app/schemas/contacts.py` for full field list).
- `ContactDetail`: Extends `ContactListItem` with nested `company_detail` (`CompanySummary`) and `metadata` (`ContactMetadataOut`).
- All timestamps are serialized as ISO8601 strings.

## Import Workflow API

Import endpoints (in `app/api/v1/endpoints/imports.py`) support uploading contacts CSV files processed by background Celery tasks.

| Method | Path | Description | Success Response | Error Cases |
| ------ | ---- | ----------- | ---------------- | ----------- |
| `GET` | `/api/v1/contacts/import/` | Returns guidance on how to trigger an import. | `200 OK` → `{"message": str}` | — |
| `POST` | `/api/v1/contacts/import/` | Upload a CSV file and enqueue background processing. | `202 Accepted` → `ImportJobDetail` | `400` empty file, `422` missing filename, `500` storage/task failures. |
| `GET` | `/api/v1/contacts/import/{job_id}/` | Retrieve import job status. | `200 OK` → `ImportJobDetail` or `ImportJobWithErrors` when `include_errors=true`. | `404` unknown job ID. |
| `GET` | `/api/v1/contacts/import/{job_id}/errors/` | Fetch recorded row-level errors. | `200 OK` → `[ImportErrorRecord, ...]` | `404` unknown job ID or no errors recorded. |

### Upload Requirements

- Accepts multipart form-data with a single `file` field (`UploadFile`).
- Files are persisted under `settings.UPLOAD_DIR`. Zero-byte files are rejected with `400 Bad Request`.
- On success, the background task `process_contacts_import.delay(job_id, path)` is queued. Failures to enqueue mark the job as `failed`.

### Import Schemas

- `ImportJobDetail`: Metadata including `job_id`, `file_name`, `status`, `total_rows`, `processed_rows`, `error_count`, `message`, timestamps, and the stored `file_path`.
- `ImportJobWithErrors`: Extends `ImportJobDetail` with an `errors` array of `ImportErrorRecord` (`row_number`, `error_message`, `payload`).

### Query Parameters

- `include_errors` (`bool`, default `false`) on `/contacts/import/{job_id}/` toggles embedding error records in the response. Errors are still available separately via `/errors/`.

### Typical Status Lifecycle

`ImportJobStatus` (see `app/models/imports.py`) can be `pending`, `processing`, `completed`, or `failed`. Client UIs should poll the job detail endpoint until `status` transitions away from `pending/processing`.
