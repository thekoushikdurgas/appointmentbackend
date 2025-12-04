# Data Models and Schemas Analysis

## Overview

This document analyzes the SQLAlchemy models (database layer) and Pydantic schemas (API layer) used throughout the application. Models define database structure, while schemas handle validation and serialization.

## 1. SQLAlchemy Models Architecture

### Base Class

**Base (`app/db/base.py`):**

```python
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
```

**Features:**

- Uses SQLAlchemy 2.0 declarative base
- Auto-discovers models on import
- Provides foundation for all models

### Model Patterns

**Common Structure:**

- `id`: BigInteger primary key (auto-increment)
- `uuid`: Text unique identifier (indexed)
- `created_at`: DateTime timestamp
- `updated_at`: DateTime timestamp (optional)
- Relationships defined with `relationship()`

## 2. Contact Models

### Contact Model

**Table:** `contacts`

**Key Fields:**

- `id`: BigInteger primary key
- `uuid`: Text unique identifier (indexed)
- `first_name`, `last_name`: Text (indexed)
- `company_id`: Text foreign key to companies.uuid (indexed)
- `email`: Text (indexed)
- `title`: Text (indexed, trigram index)
- `departments`: StringList (array of strings, GIN index)
- `mobile_phone`: Text (indexed)
- `email_status`: Text (indexed)
- `text_search`: Text (trigram index for search)
- `seniority`: Text (indexed)
- `created_at`, `updated_at`: DateTime

**Indexes:**

- Individual column indexes (first_name, last_name, email, etc.)
- Composite indexes (email+company_id, name+company_id)
- GIN indexes for arrays (departments)
- Trigram indexes for text search (title, text_search)
- Composite indexes for common queries (seniority+company_id)

**Relationships:**

- `company`: Optional Company (many-to-one)
- `metadata_`: Optional ContactMetadata (one-to-one)

### ContactMetadata Model

**Table:** `contacts_metadata`

**Key Fields:**

- `id`: BigInteger primary key
- `uuid`: Text unique identifier (matches Contact.uuid)
- `linkedin_url`, `facebook_url`, `twitter_url`: Text
- `website`: Text
- `work_direct_phone`, `home_phone`, `other_phone`: Text
- `city`, `state`, `country`: Text (indexed)
- `stage`: Text

**Indexes:**

- Individual indexes on city, state, country

**Relationships:**

- `contact`: Optional Contact (one-to-one)

**Purpose:**

- Stores enriched metadata from external sources
- Separated from main Contact table for performance
- Optional (not all contacts have metadata)

## 3. Company Models

### Company Model

**Table:** `companies`

**Key Fields:**

- `id`: BigInteger primary key
- `uuid`: Text unique identifier (indexed)
- `name`: Text (indexed, trigram index)
- `employees_count`: BigInteger (indexed)
- `industries`: StringList (GIN index)
- `keywords`: StringList (GIN index)
- `technologies`: StringList (GIN index)
- `address`: Text
- `annual_revenue`: BigInteger (indexed)
- `total_funding`: BigInteger (indexed)
- `text_search`: Text (trigram index)
- `created_at`, `updated_at`: DateTime

**Indexes:**

- Individual column indexes
- GIN indexes for arrays (industries, keywords, technologies)
- Trigram indexes for text search (name, text_search)
- Composite indexes (annual_revenue+industries)

**Relationships:**

- `metadata_`: Optional CompanyMetadata (one-to-one)
- `contacts`: List of Contact (one-to-many)

### CompanyMetadata Model

**Table:** `companies_metadata`

**Key Fields:**

- `id`: BigInteger primary key
- `uuid`: Text unique identifier (matches Company.uuid)
- `linkedin_url`, `facebook_url`, `twitter_url`: Text
- `website`: Text (used for domain extraction)
- `company_name_for_emails`: Text (indexed)
- `phone_number`: Text
- `latest_funding`: Text
- `latest_funding_amount`: BigInteger
- `last_raised_at`: Text
- `city`, `state`, `country`: Text (indexed)

**Indexes:**

- Indexes on company_name_for_emails, city, state, country

**Relationships:**

- `company`: Optional Company (one-to-one)

**Purpose:**

- Stores enriched company metadata
- Website field used for domain filtering
- Separated for performance

## 4. User Models

### User Model

**Table:** `users`

**Key Fields:**

- `id`: Text primary key (UUID string)
- `email`: String(255) unique (indexed)
- `hashed_password`: Text
- `name`: String(255) optional
- `is_active`: Boolean (default True)
- `last_sign_in_at`: DateTime (timezone-aware)
- `created_at`: DateTime (timezone-aware, server default)
- `updated_at`: DateTime (timezone-aware, on update)

**Indexes:**

- Index on email
- Index on id

**Relationships:**

- `profile`: Optional UserProfile (one-to-one, cascade delete)

**Features:**

- UUID as string (not PostgreSQL UUID type)
- Timezone-aware timestamps
- Active flag for account management

### UserProfile Model

**Table:** `user_profiles`

**Key Fields:**

- `id`: Integer primary key
- `user_id`: Text foreign key to users.id (unique, indexed)
- `job_title`: String(255) optional
- `bio`: Text optional
- `timezone`: String(100) optional
- `avatar_url`: Text optional
- `notifications`: JSON (default empty dict)
- `role`: String(50) default "Member"
- `created_at`, `updated_at`: DateTime (timezone-aware)

**Indexes:**

- Index on user_id

**Relationships:**

- `user`: User (many-to-one)

**Purpose:**

- Extends user with profile information
- Stores role for authorization
- JSON field for flexible notification preferences

## 5. Import Models

### ContactImportJob Model

**Table:** `contact_import_jobs`

**Key Fields:**

- `id`: BigInteger primary key
- `job_id`: Text unique identifier (indexed)
- `file_name`: Text
- `file_path`: Text
- `total_rows`: Integer (default 0)
- `processed_rows`: Integer (default 0)
- `status`: ImportJobStatus enum (indexed)
- `error_count`: Integer (default 0)
- `message`: Text optional
- `created_at`, `updated_at`, `completed_at`: DateTime

**Relationships:**

- `errors`: List of ContactImportError (one-to-many, cascade delete)

**Status Enum:**

- `pending`: Job created, not started
- `processing`: Currently processing
- `completed`: Successfully completed
- `failed`: Failed with errors

### ContactImportError Model

**Table:** `contact_import_errors`

**Key Fields:**

- `id`: BigInteger primary key
- `job_id`: BigInteger foreign key (indexed)
- `row_number`: Integer
- `error_message`: Text
- `payload`: Text optional (stores row data)
- `created_at`: DateTime

**Relationships:**

- `job`: ContactImportJob (many-to-one)

**Purpose:**

- Tracks row-level import errors
- Stores error details for debugging
- Links to import job

## 6. Custom Types

### StringList Type

**Implementation (`app/db/types.py`):**

**Purpose:** Store arrays of strings in PostgreSQL

**Features:**

- PostgreSQL: Uses native ARRAY(Text) type
- Other dialects: JSON-encoded TEXT
- Automatic serialization/deserialization
- Handles NULL values

**Usage:**

- `departments`, `industries`, `keywords`, `technologies` columns
- Enables array operations in queries
- GIN indexes for performance

## 7. Pydantic Schemas Architecture

### Schema Categories

**1. Request Schemas:**

- Input validation
- Used in endpoint parameters
- Example: `ContactCreate`, `UserRegister`

**2. Response Schemas:**

- Output serialization
- Used in endpoint responses
- Example: `ContactDetail`, `ContactListItem`

**3. Filter Schemas:**

- Query parameter validation
- Complex filter logic
- Example: `ContactFilterParams`, `ApolloFilterParams`

**4. Common Schemas:**

- Shared structures
- Generic types
- Example: `CursorPage`, `CountResponse`

## 8. Contact Schemas

### ContactCreate

**Purpose:** Create new contact

**Fields:**

- All contact fields (optional)
- UUID optional (generated if not provided)
- No timestamps (set by service)

### ContactDetail

**Purpose:** Full contact information

**Fields:**

- All contact fields
- Company summary (if exists)
- Contact metadata (if exists)
- Company metadata (if exists)
- Timestamps

**Features:**

- Includes related data
- Handles NULL relationships
- Comprehensive contact view

### ContactListItem

**Purpose:** Contact in list view

**Fields:**

- Core contact fields
- Flattened company/metadata fields
- Optimized for list display

**Features:**

- Flattened structure (no nested objects)
- Includes commonly used fields
- Efficient serialization

### ContactSimpleItem

**Purpose:** Minimal contact information

**Fields:**

- Only essential fields (uuid, name, email, title)
- Used for simple list views

## 9. Filter Schemas

### ContactFilterParams

**Purpose:** Comprehensive filter parameter validation

**Key Features:**

- 100+ filter fields
- Field aliases (e.g., `company` = `name`)
- Validation rules (ge=0 for numeric fields)
- Optional fields (all filters optional)
- Field descriptions for API docs

**Filter Categories:**

**Contact Filters:**

- `first_name`, `last_name`, `title`, `seniority`
- `email`, `email_status`, `mobile_phone`
- `department`, `contact_location`

**Company Filters:**

- `company`, `include_company_name`, `exclude_company_name`
- `employees_count`, `employees_min`, `employees_max`
- `annual_revenue`, `total_funding` (with min/max)
- `technologies`, `keywords`, `industries`
- `company_location`, `company_address`

**Metadata Filters:**

- ContactMetadata: `work_direct_phone`, `city`, `state`, `country`
- CompanyMetadata: `company_name_for_emails`, `corporate_phone`, `company_city`

**Special Filters:**

- `include_domain_list`, `exclude_domain_list`
- `keyword_search_fields`, `keyword_exclude_fields`
- `search` (multi-column)

**Pagination:**

- `page`, `page_size`, `cursor`
- `distinct` (for unique results)
- `ordering` (sort field)

**Title Filtering:**

- `title`: Standard ILIKE matching
- `normalize_title_column`: Normalize word order
- `jumble_title_words`: Match individual words (AND logic)

### ApolloFilterParams

**Purpose:** Extends ContactFilterParams with Apollo-specific fields

**Additional Fields:**

- Apollo URL analysis metadata
- Unmapped parameter tracking
- Mapping statistics

## 10. Common Schemas

### CursorPage

**Purpose:** Paginated response wrapper

**Fields:**

- `next`: Optional URL for next page
- `previous`: Optional URL for previous page
- `results`: List of items (generic type)

**Usage:**

- Generic type parameter for item type
- Used across all list endpoints
- Supports cursor and offset pagination

### CountResponse

**Purpose:** Simple count response

**Fields:**

- `count`: Integer count

**Usage:**

- Count endpoints
- Simple aggregation responses

### UuidListResponse

**Purpose:** UUID list response

**Fields:**

- `count`: Integer count
- `uuids`: List of UUID strings

**Usage:**

- UUID retrieval endpoints
- Bulk operations

### MessageResponse

**Purpose:** Simple message response

**Fields:**

- `message`: String message

**Usage:**

- Status messages
- Success/error responses

## 11. Apollo Schemas

### ApolloUrlAnalysisRequest

**Purpose:** Request Apollo URL analysis

**Fields:**

- `url`: String (Apollo.io URL)

### ApolloUrlAnalysisResponse

**Purpose:** Apollo URL analysis result

**Fields:**

- `url`: Original URL
- `url_structure`: URL breakdown
- `categories`: Categorized parameters
- `statistics`: Analysis statistics
- `raw_parameters`: Raw parameter dict

### ApolloContactsSearchResponse

**Purpose:** Apollo search results with mapping metadata

**Fields:**

- `next`, `previous`: Pagination links
- `results`: List of contacts (generic)
- `apollo_url`: Original Apollo URL
- `mapping_summary`: Mapping statistics
- `unmapped_categories`: Unmapped parameters

**Features:**

- Includes mapping metadata
- Tracks unmapped parameters
- Generic type for contact items

## 12. Schema Validation Patterns

### Field Validation

**Numeric Fields:**

```python
employees_min: Optional[int] = Field(ge=0)
```

- `ge=0`: Greater than or equal to 0
- Prevents negative values

**String Fields:**

```python
title: Optional[str] = Field(description="Job title")
```

- Optional by default
- Descriptions for API docs

**List Fields:**

```python
exclude_titles: Optional[list[str]] = Field(default=None)
```

- Optional lists
- Default None (not empty list)

### Field Aliases

**Multiple Names:**

```python
company: Optional[str] = Field(
    validation_alias=AliasChoices("company", "name")
)
```

- Accepts multiple parameter names
- Maps to same field

### Model Configuration

**Common Config:**

```python
model_config = ConfigDict(
    from_attributes=True,  # Allow ORM model conversion
    extra="ignore"  # Ignore extra fields
)
```

## 13. Schema Inheritance

### Base Schemas

**ContactBase:**

- Shared contact fields
- Used as base for other schemas

**TimestampedModel:**

- `created_at`, `updated_at` fields
- Used across multiple schemas

### Schema Composition

**ContactDetail:**

- Extends ContactBase
- Adds related data (company, metadata)
- Includes timestamps

## 14. Index Strategy

### Index Types

**B-Tree Indexes:**

- Standard indexes for equality/range queries
- Used on: uuid, email, name, etc.

**GIN Indexes:**

- For array columns (departments, industries, keywords, technologies)
- Enables efficient array operations

**Trigram Indexes:**

- For text search columns (title, text_search, name)
- Enables fast ILIKE queries
- Uses PostgreSQL pg_trgm extension

**Composite Indexes:**

- Multiple columns (email+company_id, seniority+company_id)
- Optimizes common query patterns

### Index Selection Criteria

**High Cardinality Fields:**

- UUID, email (unique indexes)

**Frequently Filtered:**

- Name, title, email_status (standard indexes)

**Text Search:**

- Title, text_search (trigram indexes)

**Array Operations:**

- Departments, industries, keywords (GIN indexes)

**Common Joins:**

- company_id (indexed for JOIN performance)

## 15. Relationship Patterns

### One-to-One Relationships

**Contact ↔ ContactMetadata:**

- Linked by UUID
- Optional (not all contacts have metadata)
- One-to-one with `uselist=False`

**Company ↔ CompanyMetadata:**

- Linked by UUID
- Optional
- One-to-one

**User ↔ UserProfile:**

- Linked by user_id
- Optional (created on registration)
- Cascade delete

### One-to-Many Relationships

**Company ↔ Contacts:**

- Company has many contacts
- Contact has one company (optional)
- Foreign key: `Contact.company_id → Company.uuid`

**ContactImportJob ↔ ContactImportError:**

- Job has many errors
- Error belongs to one job
- Cascade delete errors when job deleted

## 16. Data Type Patterns

### Text vs String

**Text:**

- Unlimited length
- Used for: names, addresses, descriptions, UUIDs

**String:**

- Fixed length (e.g., String(255))
- Used for: email, short fields

### BigInteger

**Usage:**

- Primary keys (id)
- Large integers (employees_count, revenue, funding)
- Prevents integer overflow

### DateTime

**Patterns:**

- `timezone=False`: Legacy timestamps (contacts, companies)
- `timezone=True`: Timezone-aware (users, imports)
- `server_default=func.now()`: Auto-set on insert
- `onupdate=func.now()`: Auto-update on change

## 17. Model Validation

### Database Constraints

**Unique Constraints:**

- `uuid`: Unique across table
- `email`: Unique in users table

**Foreign Key Constraints:**

- `Contact.company_id → Company.uuid`
- `ContactMetadata.uuid → Contact.uuid`
- `UserProfile.user_id → User.id`

**Cascade Behavior:**

- `ondelete="SET NULL"`: Set foreign key to NULL on delete
- `ondelete="CASCADE"`: Delete related records
- `cascade="all, delete-orphan"`: Delete orphaned records

## Summary

The models and schemas demonstrate:

1. **Clear Separation**: Models for database, schemas for API
2. **Performance Focus**: Strategic indexes (B-tree, GIN, trigram)
3. **Flexible Filtering**: Comprehensive filter schemas
4. **Type Safety**: Pydantic validation, SQLAlchemy types
5. **Relationship Management**: Proper foreign keys and cascades
6. **Optional Metadata**: Separate metadata tables for performance
7. **Generic Patterns**: Reusable schema patterns (CursorPage, etc.)

The architecture supports both simple queries (minimal models) and complex queries (with metadata joins), with schemas providing validation and clear API contracts.

