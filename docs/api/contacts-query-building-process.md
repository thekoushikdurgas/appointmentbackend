# Contacts API Query Building Process

This document provides a detailed breakdown of how the `/contacts/` API builds queries, maps parameters to table columns, and joins tables to retrieve contact data.

## Overview

The Contacts API uses a multi-stage query building process that:

1. Analyzes parameters to determine which tables need to be joined
2. Builds a base query with conditional joins
3. Applies filters sequentially to each table
4. Performs special operations on joined results
5. Applies search and ordering
6. Executes the query and normalizes results

## Step 1: Parameter Analysis and Join Determination

**Location:** `app/repositories/contacts.py` (lines 39-75, 915-941)

Before building the query, the system analyzes which parameters are provided to determine which table joins are necessary. This optimization ensures we only join tables that are actually needed.

### Contact Table Parameters

These parameters map directly to the `Contact` table and don't require additional joins:

| Parameter | Column | Match Type |
|-----------|--------|------------|
| `first_name` | `Contact.first_name` | Case-insensitive substring (ILIKE) |
| `last_name` | `Contact.last_name` | Case-insensitive substring (ILIKE) |
| `title` | `Contact.title` | Case-insensitive substring (trigram optimized) |
| `email` | `Contact.email` | Case-insensitive substring (ILIKE) |
| `email_status` | `Contact.email_status` | Case-insensitive exact match |
| `seniority` | `Contact.seniority` | Case-insensitive substring (ILIKE) |
| `departments` | `Contact.departments` | Array text search |
| `mobile_phone` | `Contact.mobile_phone` | Substring match |
| `contact_location` | `Contact.text_search` | Case-insensitive substring |
| `exclude_titles` | `Contact.title` | Exclusion list (case-insensitive) |
| `exclude_seniorities` | `Contact.seniority` | Exclusion list |
| `exclude_departments` | `Contact.departments` | Exclusion list |
| `exclude_company_ids` | `Contact.company_id` | Exclusion list (NOT IN) |
| `exclude_contact_locations` | `Contact.text_search` | Exclusion list |
| `created_at_after` | `Contact.created_at` | >= (inclusive) |
| `created_at_before` | `Contact.created_at` | <= (inclusive) |
| `updated_at_after` | `Contact.updated_at` | >= (inclusive) |
| `updated_at_before` | `Contact.updated_at` | <= (inclusive) |

**Method:** `_needs_company_join()` returns `False` for these - Contact table is always available.

### Company Table Parameters

These parameters require joining the `Company` table:

| Parameter | Column | Match Type |
|-----------|--------|------------|
| `company` (alias: `name`) | `Company.name` | Case-insensitive substring |
| `include_company_name` | `Company.name` | Case-insensitive substring (inclusion) |
| `company_location` | `Company.text_search` | Case-insensitive substring |
| `company_address` | `Company.text_search` | Case-insensitive substring |
| `employees_count` | `Company.employees_count` | Exact match |
| `employees_min` | `Company.employees_count` | >= (minimum) |
| `employees_max` | `Company.employees_count` | <= (maximum) |
| `annual_revenue` | `Company.annual_revenue` | Exact match (integer dollars) |
| `annual_revenue_min` | `Company.annual_revenue` | >= (minimum) |
| `annual_revenue_max` | `Company.annual_revenue` | <= (maximum) |
| `total_funding` | `Company.total_funding` | Exact match |
| `total_funding_min` | `Company.total_funding` | >= (minimum) |
| `total_funding_max` | `Company.total_funding` | <= (maximum) |
| `technologies` | `Company.technologies` | Array text search |
| `technologies_uids` | `Company.technologies` | Array text search (UID-based) |
| `keywords` | `Company.keywords` | Array text search (OR logic) |
| `keywords_and` | `Company.keywords` | Array text search (AND logic) |
| `industries` (alias: `industry`) | `Company.industries` | Array text search |
| `exclude_company_locations` | `Company.text_search` | Exclusion list |
| `exclude_company_name` | `Company.name` | Exclusion list |
| `exclude_technologies` | `Company.technologies` | Exclusion list |
| `exclude_keywords` | `Company.keywords` | Exclusion list |
| `exclude_industries` | `Company.industries` | Exclusion list |

**Method:** `_needs_company_join()` checks if any of these parameters are provided.

**Join Condition:** `Contact.company_id = Company.uuid` (OUTER JOIN)

### ContactMetadata Table Parameters

These parameters require joining the `ContactMetadata` table:

| Parameter | Column | Match Type |
|-----------|--------|------------|
| `work_direct_phone` | `ContactMetadata.work_direct_phone` | Substring match |
| `home_phone` | `ContactMetadata.home_phone` | Substring match |
| `other_phone` | `ContactMetadata.other_phone` | Substring match |
| `city` | `ContactMetadata.city` | Substring match |
| `state` | `ContactMetadata.state` | Substring match |
| `country` | `ContactMetadata.country` | Substring match |
| `person_linkedin_url` | `ContactMetadata.linkedin_url` | Substring match |
| `website` | `ContactMetadata.website` | Substring match |
| `stage` | `ContactMetadata.stage` | Substring match |
| `facebook_url` | `ContactMetadata.facebook_url` | Substring match (OR with CompanyMetadata) |
| `twitter_url` | `ContactMetadata.twitter_url` | Substring match (OR with CompanyMetadata) |

**Method:** `_needs_contact_metadata_join()` checks if any of these parameters are provided.

**Join Condition:** `Contact.uuid = ContactMetadata.uuid` (OUTER JOIN)

### CompanyMetadata Table Parameters

These parameters require joining the `CompanyMetadata` table:

| Parameter | Column | Match Type |
|-----------|--------|------------|
| `company_name_for_emails` | `CompanyMetadata.company_name_for_emails` | Case-insensitive substring |
| `corporate_phone` | `CompanyMetadata.phone_number` | Substring match |
| `company_phone` | `CompanyMetadata.phone_number` | Substring match |
| `company_city` | `CompanyMetadata.city` | Substring match |
| `company_state` | `CompanyMetadata.state` | Substring match |
| `company_country` | `CompanyMetadata.country` | Substring match |
| `company_linkedin_url` | `CompanyMetadata.linkedin_url` | Substring match |
| `latest_funding_amount_min` | `CompanyMetadata.latest_funding_amount` | >= (minimum) |
| `latest_funding_amount_max` | `CompanyMetadata.latest_funding_amount` | <= (maximum) |
| `include_domain_list` | `CompanyMetadata.website` | Domain extraction and matching |
| `exclude_domain_list` | `CompanyMetadata.website` | Domain extraction and exclusion |
| `facebook_url` | `CompanyMetadata.facebook_url` | Substring match (OR with ContactMetadata) |
| `twitter_url` | `CompanyMetadata.twitter_url` | Substring match (OR with ContactMetadata) |

**Method:** `_needs_company_metadata_join()` checks if any of these parameters are provided.

**Join Condition:** `Company.uuid = CompanyMetadata.uuid` (OUTER JOIN)

**Note:** `CompanyMetadata` join requires `Company` join to be present first.

### Special Parameters

These parameters require special handling and may affect join requirements:

| Parameter | Description | Join Requirements |
|-----------|-------------|-------------------|
| `search` | Full-text search across multiple columns | Requires Company join if search includes company fields |
| `keyword_search_fields` | Controls which fields to search in keyword queries | Requires Company join |
| `keyword_exclude_fields` | Excludes specific fields from keyword search | Requires Company join |
| `ordering` | Ordering field name | May require joins based on field (checked via `_needs_joins_for_ordering()`) |

## Step 2: Base Query Construction with Conditional Joins

**Location:** `app/repositories/contacts.py` (lines 181-224, 945-958)

Based on the join requirements determined in Step 1, one of three base queries is constructed:

### Option 1: Minimal Query (No Joins)

**Method:** `base_query_minimal()`

```python
stmt: Select = select(Contact)
```

**Used when:**

- No company, ContactMetadata, or CompanyMetadata filters are provided
- No search parameter is provided
- No ordering requires joins

**Result:** Returns only Contact rows

### Option 2: Company Query (Contact + Company)

**Method:** `base_query_with_company()`

```python
company_alias = aliased(Company, name="company")
stmt: Select = (
    select(Contact, company_alias)
    .select_from(Contact)
    .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
)
```

**Used when:**

- Company table filters are provided
- Search parameter is provided (may include company fields)
- Ordering requires company fields
- But ContactMetadata and CompanyMetadata are not needed

**Result:** Returns Contact and Company rows (ContactMetadata and CompanyMetadata are None)

### Option 3: Full Metadata Query (All Tables)

**Method:** `base_query_with_metadata()`

```python
company_alias = aliased(Company, name="company")
contact_meta_alias = aliased(ContactMetadata, name="contact_metadata")
company_meta_alias = aliased(CompanyMetadata, name="company_metadata")

stmt: Select = (
    select(Contact, company_alias, contact_meta_alias, company_meta_alias)
    .select_from(Contact)
    .outerjoin(company_alias, Contact.company_id == company_alias.uuid)
    .outerjoin(contact_meta_alias, Contact.uuid == contact_meta_alias.uuid)
    .outerjoin(company_meta_alias, company_alias.uuid == company_meta_alias.uuid)
)
```

**Used when:**

- ContactMetadata filters are provided, OR
- CompanyMetadata filters are provided, OR
- Both metadata tables are needed

**Result:** Returns Contact, Company, ContactMetadata, and CompanyMetadata rows

**Join Relationships:**

- `Contact.company_id = Company.uuid` (OUTER JOIN)
- `Contact.uuid = ContactMetadata.uuid` (OUTER JOIN)
- `Company.uuid = CompanyMetadata.uuid` (OUTER JOIN)

**Important:** All joins are OUTER JOINs, meaning contacts without companies or metadata will still be returned (with NULL values for missing relationships).

## Step 3: Apply Contact Table Filters

**Location:** `app/repositories/contacts.py` (lines 560-664, 965-970)

**Method:** `_apply_contact_filters()`

Filters are applied to the Contact table columns. This method handles:

### Direct Contact Column Filters

```python
# Text filters (case-insensitive substring matching)
stmt = self._apply_multi_value_filter(stmt, Contact.first_name, filters.first_name)
stmt = self._apply_multi_value_filter(stmt, Contact.last_name, filters.last_name)
stmt = self._apply_multi_value_filter(stmt, Contact.title, filters.title, use_trigram_optimization=True)
stmt = self._apply_multi_value_filter(stmt, Contact.email, filters.email)
stmt = apply_ilike_filter(stmt, Contact.email_status, filters.email_status)
stmt = self._apply_multi_value_filter(stmt, Contact.seniority, filters.seniority)
stmt = self._apply_multi_value_filter(stmt, Contact.text_search, filters.contact_location)
stmt = self._apply_multi_value_filter(stmt, Contact.mobile_phone, filters.mobile_phone)
```

### Array Column Filters

```python
# Departments array search
if filters.department:
    stmt = self._apply_array_text_filter(
        stmt,
        Contact.departments,
        filters.department,
        dialect=dialect,
    )
```

### Exclusion Filters

```python
# Exclude titles (case-insensitive)
if filters.exclude_titles:
    lowered_titles = tuple(title.lower() for title in filters.exclude_titles if title)
    if lowered_titles:
        stmt = stmt.where(
            or_(
                Contact.title.is_(None),
                func.lower(Contact.title).notin_(lowered_titles),
            )
        )

# Exclude company IDs
if filters.exclude_company_ids:
    exclusion_values = tuple(filters.exclude_company_ids)
    exclusion_condition = ~Contact.company_id.in_(exclusion_values)
    stmt = stmt.where(or_(Contact.company_id.is_(None), exclusion_condition))

# Exclude contact locations, seniorities, departments
if filters.exclude_contact_locations:
    stmt = self._apply_multi_value_exclusion(stmt, Contact.text_search, filters.exclude_contact_locations)
if filters.exclude_seniorities:
    stmt = self._apply_multi_value_exclusion(stmt, Contact.seniority, filters.exclude_seniorities)
if filters.exclude_departments:
    stmt = self._apply_array_text_exclusion(stmt, Contact.departments, filters.exclude_departments)
```

### Date Range Filters

```python
if filters.created_at_after is not None:
    stmt = stmt.where(Contact.created_at >= filters.created_at_after)
if filters.created_at_before is not None:
    stmt = stmt.where(Contact.created_at <= filters.created_at_before)
if filters.updated_at_after is not None:
    stmt = stmt.where(Contact.updated_at >= filters.updated_at_after)
if filters.updated_at_before is not None:
    stmt = stmt.where(Contact.updated_at <= filters.updated_at_before)
```

### ContactMetadata Filters (if joined)

If `contact_meta_alias` is not None, additional filters are applied:

```python
if contact_meta is not None:
    stmt = self._apply_multi_value_filter(stmt, contact_meta.work_direct_phone, filters.work_direct_phone)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.home_phone, filters.home_phone)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.other_phone, filters.other_phone)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.city, filters.city)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.state, filters.state)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.country, filters.country)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.linkedin_url, filters.person_linkedin_url)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.website, filters.website)
    stmt = self._apply_multi_value_filter(stmt, contact_meta.stage, filters.stage)
    
    # Facebook and Twitter URLs can match either ContactMetadata or CompanyMetadata
    if filters.facebook_url:
        # Creates OR condition between contact_meta.facebook_url and company_meta.facebook_url
        # (handled in apply_filters method)
```

## Step 4: Apply Company Table Filters

**Location:** `app/repositories/contacts.py` (lines 666-790, 972-979)

**Method:** `_apply_company_filters()`

Filters are applied to the Company table columns. This method only runs if `company_alias` is not None.

### Company Name Filters

```python
stmt = self._apply_multi_value_filter(stmt, company.name, filters.company)
stmt = self._apply_multi_value_filter(stmt, company.name, filters.include_company_name)
```

### Company Location Filters

```python
stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_location)
stmt = self._apply_multi_value_filter(stmt, company.text_search, filters.company_address)
```

### Numeric Filters

```python
# Exact match
if filters.employees_count is not None:
    stmt = stmt.where(company.employees_count == filters.employees_count)

# Range filters
stmt = apply_numeric_range_filter(
    stmt,
    company.employees_count,
    filters.employees_min,
    filters.employees_max,
)

if filters.annual_revenue is not None:
    stmt = stmt.where(company.annual_revenue == filters.annual_revenue)
stmt = apply_numeric_range_filter(
    stmt,
    company.annual_revenue,
    filters.annual_revenue_min,
    filters.annual_revenue_max,
)

if filters.total_funding is not None:
    stmt = stmt.where(company.total_funding == filters.total_funding)
stmt = apply_numeric_range_filter(
    stmt,
    company.total_funding,
    filters.total_funding_min,
    filters.total_funding_max,
)
```

### Array Column Filters

```python
# Technologies
if filters.technologies:
    stmt = self._apply_array_text_filter(
        stmt,
        company.technologies,
        filters.technologies,
        dialect=dialect,
    )

# Keywords (OR logic)
if filters.keywords:
    stmt = self._apply_array_text_filter(
        stmt,
        company.keywords,
        filters.keywords,
        dialect=dialect,
    )

# Keywords (AND logic)
if filters.keywords_and:
    stmt = self._apply_array_text_filter_and(
        stmt,
        company.keywords,
        filters.keywords_and,
        dialect=dialect,
    )

# Industries
if filters.industries:
    stmt = self._apply_array_text_filter(
        stmt,
        company.industries,
        filters.industries,
        dialect=dialect,
    )
```

### Exclusion Filters

```python
if filters.exclude_company_locations:
    stmt = self._apply_multi_value_exclusion(stmt, company.text_search, filters.exclude_company_locations)
if filters.exclude_company_name:
    stmt = self._apply_multi_value_exclusion(stmt, company.name, filters.exclude_company_name)
if filters.exclude_technologies:
    stmt = self._apply_array_text_exclusion(stmt, company.technologies, filters.exclude_technologies)
if filters.exclude_keywords:
    stmt = self._apply_array_text_exclusion(stmt, company.keywords, filters.exclude_keywords)
if filters.exclude_industries:
    stmt = self._apply_array_text_exclusion(stmt, company.industries, filters.exclude_industries)
```

### CompanyMetadata Filters (if joined)

If `company_meta_alias` is not None, additional filters are applied:

```python
if company_meta is not None:
    stmt = self._apply_multi_value_filter(
        stmt,
        company_meta.company_name_for_emails,
        filters.company_name_for_emails,
    )
    stmt = self._apply_multi_value_filter(stmt, company_meta.phone_number, filters.corporate_phone)
    stmt = self._apply_multi_value_filter(stmt, company_meta.phone_number, filters.company_phone)
    stmt = self._apply_multi_value_filter(stmt, company_meta.city, filters.company_city)
    stmt = self._apply_multi_value_filter(stmt, company_meta.state, filters.company_state)
    stmt = self._apply_multi_value_filter(stmt, company_meta.country, filters.company_country)
    stmt = self._apply_multi_value_filter(stmt, company_meta.linkedin_url, filters.company_linkedin_url)
    
    # Latest funding amount range
    if filters.latest_funding_amount_min is not None:
        stmt = stmt.where(company_meta.latest_funding_amount >= filters.latest_funding_amount_min)
    if filters.latest_funding_amount_max is not None:
        stmt = stmt.where(company_meta.latest_funding_amount <= filters.latest_funding_amount_max)
```

## Step 5: Apply Special Filters on Joined Tables

**Location:** `app/repositories/contacts.py` (lines 799-870, 981-988)

**Method:** `_apply_special_filters()`

Special filters that require joined tables are applied after the basic filters. These filters operate on the joined result set.

### Domain Filters

Domain filters extract domains from website URLs and match them against provided domain lists. This requires the CompanyMetadata table to be joined.

```python
if company_meta is not None:
    if filters.include_domain_list:
        stmt = self._apply_domain_filter(
            stmt,
            company_meta.website,
            filters.include_domain_list,
            dialect=dialect,
        )
    if filters.exclude_domain_list:
        stmt = self._apply_domain_exclusion(
            stmt,
            company_meta.website,
            filters.exclude_domain_list,
            dialect=dialect,
        )
```

**How it works:**

1. Extracts domain from `CompanyMetadata.website` using `extract_domain_from_url()`
2. Compares extracted domain (case-insensitive) against provided domain list
3. Uses ILIKE matching for partial domain matches

**Example:**

- `CompanyMetadata.website = "https://www.example.com/path"`
- Extracted domain: `"example.com"`
- `include_domain_list = ["example.com"]` → Match
- `include_domain_list = ["example"]` → Match (partial)

### Keyword Field Control

Keyword filters can be controlled to search specific fields or exclude certain fields. This requires the Company table to be joined.

```python
if filters.keywords:
    if filters.keyword_search_fields or filters.keyword_exclude_fields:
        stmt = self._apply_keyword_search_with_fields(
            stmt,
            filters.keywords,
            company,
            filters.keyword_search_fields,
            filters.keyword_exclude_fields,
            dialect=dialect,
        )
    else:
        # Standard keyword filter (OR logic)
        stmt = self._apply_array_text_filter(
            stmt,
            company.keywords,
            filters.keywords,
            dialect=dialect,
        )

if filters.keywords_and:
    if filters.keyword_search_fields or filters.keyword_exclude_fields:
        stmt = self._apply_keyword_search_with_fields(
            stmt,
            filters.keywords_and,
            company,
            filters.keyword_search_fields,
            filters.keyword_exclude_fields,
            dialect=dialect,
            use_and_logic=True,
        )
```

**Field Control Options:**

- `keyword_search_fields`: List of fields to include in search (`['company', 'industries', 'keywords']`)
- `keyword_exclude_fields`: List of fields to exclude from search

**Example:**

- `keywords = "technology"`
- `keyword_search_fields = ['company', 'keywords']`
- Searches only `Company.name` and `Company.keywords`, excludes `Company.industries`

## Step 6: Apply Search Parameter (Multi-Column Search)

**Location:** `app/repositories/contacts.py` (lines 505-558, 990-998)

**Method:** `apply_search_terms()`

The `search` parameter performs full-text search across multiple columns from all joined tables. This is applied after all other filters.

### Search Columns

The search includes columns from all available tables:

```python
columns: list[Any] = [
    # Contact table columns
    Contact.first_name,
    Contact.last_name,
    Contact.email,
    Contact.title,
    Contact.seniority,
    Contact.text_search,
    
    # Company table columns
    company.name,
    company.address,
    self._array_column_as_text(company.industries, dialect),
    self._array_column_as_text(company.keywords, dialect),
]

# Add CompanyMetadata columns if joined
if company_meta is not None:
    columns.extend([
        company_meta.city,
        company_meta.state,
        company_meta.country,
        company_meta.phone_number,
        company_meta.website,
    ])

# Add ContactMetadata columns if joined
if contact_meta is not None:
    columns.extend([
        contact_meta.city,
        contact_meta.state,
        contact_meta.country,
        contact_meta.linkedin_url,
        contact_meta.twitter_url,
    ])
```

### Search Logic

The search uses OR logic - a contact matches if **any** of the columns contain the search term:

```python
stmt = apply_search(stmt, search, columns)
```

**Implementation:** Creates an OR condition where each column is checked with ILIKE:
```sql
WHERE (
    Contact.first_name ILIKE '%search_term%' OR
    Contact.last_name ILIKE '%search_term%' OR
    Contact.email ILIKE '%search_term%' OR
    ...
)
```

**Case-insensitive:** All searches are case-insensitive.

**Array columns:** Array columns (`industries`, `keywords`) are converted to text using `_array_column_as_text()` before searching.

## Step 7: Apply Ordering

**Location:** `app/repositories/contacts.py` (lines 1005-1075)

The ordering map is built dynamically based on which tables are joined. This ensures we only reference columns from available tables.

### Base Ordering Map (Always Available)

```python
ordering_map = {
    "created_at": Contact.created_at,
    "updated_at": Contact.updated_at,
    "first_name": Contact.first_name,
    "last_name": Contact.last_name,
    "title": Contact.title,
    "email": Contact.email,
    "email_status": Contact.email_status,
    "seniority": Contact.seniority,
    "departments": cast(Contact.departments, Text),
    "mobile_phone": Contact.mobile_phone,
}
```

### Company Ordering Map (if Company joined)

```python
if company_alias is not None:
    ordering_map.update({
        "employees": company_alias.employees_count,
        "annual_revenue": company_alias.annual_revenue,
        "total_funding": company_alias.total_funding,
        "company": company_alias.name,
        "industry": cast(company_alias.industries, Text),
        "keywords": cast(company_alias.keywords, Text),
        "technologies": cast(company_alias.technologies, Text),
        "company_address": company_alias.address,
    })
```

### CompanyMetadata Ordering Map (if CompanyMetadata joined)

```python
if company_meta_alias is not None:
    ordering_map.update({
        "latest_funding_amount": company_meta_alias.latest_funding_amount,
        "company_name_for_emails": company_meta_alias.company_name_for_emails,
        "corporate_phone": company_meta_alias.phone_number,
        "company_phone": company_meta_alias.phone_number,
        "company_city": company_meta_alias.city,
        "company_state": company_meta_alias.state,
        "company_country": company_meta_alias.country,
        "company_linkedin_url": company_meta_alias.linkedin_url,
        "latest_funding": company_meta_alias.latest_funding,
        "last_raised_at": company_meta_alias.last_raised_at,
    })
```

### ContactMetadata Ordering Map (if ContactMetadata joined)

```python
if contact_meta_alias is not None:
    ordering_map.update({
        "work_direct_phone": contact_meta_alias.work_direct_phone,
        "home_phone": contact_meta_alias.home_phone,
        "other_phone": contact_meta_alias.other_phone,
        "stage": contact_meta_alias.stage,
        "person_linkedin_url": contact_meta_alias.linkedin_url,
        "website": contact_meta_alias.website,
        "city": contact_meta_alias.city,
        "state": contact_meta_alias.state,
        "country": contact_meta_alias.country,
    })
    
    # Special handling for facebook_url and twitter_url
    if company_meta_alias is not None:
        # Use COALESCE to prefer ContactMetadata, fallback to CompanyMetadata
        ordering_map.update({
            "facebook_url": func.coalesce(
                contact_meta_alias.facebook_url, company_meta_alias.facebook_url
            ),
            "twitter_url": func.coalesce(
                contact_meta_alias.twitter_url, company_meta_alias.twitter_url
            ),
        })
    else:
        ordering_map.update({
            "facebook_url": contact_meta_alias.facebook_url,
            "twitter_url": contact_meta_alias.twitter_url,
        })
```

### Default Ordering

If no ordering is specified, default ordering is applied:

```python
if not filters.ordering:
    if company_alias is not None:
        # Order by company name (ascending), then contact id for tie-breaking
        stmt = stmt.order_by(company_alias.name.asc().nulls_last(), Contact.id.asc())
    else:
        # Fallback to created_at if company join is not available
        stmt = stmt.order_by(Contact.created_at.desc().nulls_last(), Contact.id.desc())
```

**Rationale:** Default ordering ensures consistent pagination results, especially with OFFSET-based pagination.

## Step 8: Execute Query and Normalize Results

**Location:** `app/repositories/contacts.py` (lines 1091-1134)

### Apply Pagination

```python
stmt = stmt.offset(offset)
if limit is not None:
    stmt = stmt.limit(limit)
```

### Execute Query

For large result sets (>10,000 rows), batching is used to reduce memory usage:

```python
if limit and limit > 10000:
    logger.debug("Using batched query for large result set limit=%d", limit)
    batcher = QueryBatcher(session, stmt, batch_size=5000)
    rows = await batcher.fetch_all()
else:
    result = await session.execute(stmt)
    rows = result.fetchall()
```

### Normalize Results

Results are normalized to always return a 4-tuple format `(Contact, Company, ContactMetadata, CompanyMetadata)` for compatibility:

```python
normalized_rows = []
for row in rows:
    if isinstance(row, tuple) and len(row) == 4:
        # Already in correct format
        normalized_rows.append(row)
    elif isinstance(row, tuple) and len(row) == 2:
        # Only Contact and Company
        contact, company = row
        normalized_rows.append((contact, company, None, None))
    elif isinstance(row, Contact):
        # Only Contact
        normalized_rows.append((row, None, None, None))
    else:
        # Fallback
        normalized_rows.append((row, None, None, None))
```

**Why normalize?** The service layer expects a consistent 4-tuple format regardless of which tables were joined. Missing tables are represented as `None`.

## Optimization Strategies

### 1. Conditional Joins

Only join tables that are actually needed based on provided filters. This reduces query complexity and improves performance.

### 2. Trigram Optimization

The `title` column uses trigram GIN index optimization for faster substring searches:

```python
stmt = self._apply_multi_value_filter(
    stmt, Contact.title, filters.title, 
    dialect_name=dialect_name, 
    use_trigram_optimization=True
)
```

### 3. Query Batching

For large result sets (>10,000 rows), queries are executed in batches to reduce memory usage.

### 4. EXISTS Subqueries (Fallback)

When joins aren't needed (e.g., for count queries), EXISTS subqueries can be used instead:

```python
def _apply_filters_with_exists(
    self,
    stmt: Select,
    filters: ContactFilterParams,
    *,
    dialect_name: str | None = None,
) -> Select:
    """Apply filters using EXISTS subqueries instead of joins for better performance."""
```

## Summary

The Contacts API query building process follows this sequence:

1. **Analyze parameters** → Determine which tables need to be joined
2. **Build base query** → Create query with conditional joins (minimal, company, or full metadata)
3. **Apply Contact filters** → Filter Contact table and ContactMetadata (if joined)
4. **Apply Company filters** → Filter Company table and CompanyMetadata (if joined)
5. **Apply special filters** → Domain filters and keyword field control on joined result
6. **Apply search** → Multi-column full-text search across all available columns
7. **Apply ordering** → Build dynamic ordering map and apply ordering
8. **Execute and normalize** → Execute query with pagination and normalize results to 4-tuple format

This process ensures optimal performance by only joining necessary tables and applying filters in the most efficient order.

