# Contacts API Endpoints - Query Building Logic Analysis

This document analyzes all Contacts API endpoints to determine which ones use the same 8-step query building process and documents any variations.

## 8-Step Query Building Process Reference

The standard 8-step process (as implemented in `GET /api/v1/contacts/`):

1. **Parameter Analysis and Join Determination** - Analyze filters to determine which tables need joins
2. **Base Query Construction** - Build query with conditional joins (minimal, company, or full metadata)
3. **Apply Contact Table Filters** - Filter Contact table and ContactMetadata (if joined)
4. **Apply Company Table Filters** - Filter Company table and CompanyMetadata (if joined)
5. **Apply Special Filters** - Domain filters and keyword field control on joined result
6. **Apply Search Parameter** - Multi-column full-text search across all available columns
7. **Apply Ordering** - Build dynamic ordering map and apply ordering
8. **Execute Query and Normalize Results** - Execute with pagination and normalize results

---

## Endpoint Analysis

### 1. GET /api/v1/contacts/ - List Contacts

**Status:** ✅ **Uses Full 8-Step Process**

**Implementation:** 
- Endpoint: `app/api/v1/endpoints/contacts.py` (line 118)
- Repository: `ContactRepository.list_contacts()` (lines 895-1134)

**Steps Used:**
- ✅ Step 1: Parameter analysis (lines 915-941)
- ✅ Step 2: Base query construction (lines 945-958)
- ✅ Step 3: Apply contact filters (lines 964-970)
- ✅ Step 4: Apply company filters (lines 972-979)
- ✅ Step 5: Apply special filters (lines 981-988)
- ✅ Step 6: Apply search (lines 990-998)
- ✅ Step 7: Apply ordering (lines 1005-1075)
- ✅ Step 8: Execute and normalize (lines 1091-1134)

**Notes:** This is the reference implementation with all 8 steps fully implemented.

---

### 2. GET /api/v1/contacts/{contact_uuid}/ - Retrieve Contact

**Status:** ⚠️ **Simplified Process (No Filtering)**

**Implementation:**
- Endpoint: `app/api/v1/endpoints/contacts.py` (line 670)
- Repository: `ContactRepository.get_contact_with_relations()` (line 2738)

**Steps Used:**
- ✅ Step 2: Base query construction (uses `base_query_with_metadata()` - line 2745)
- ❌ Step 1: No parameter analysis (single UUID lookup)
- ❌ Steps 3-6: No filtering (direct UUID match)
- ❌ Step 7: No ordering (single result)
- ✅ Step 8: Execute query (line 2747)

**Code Reference:**
```python
async def get_contact_with_relations(
    self,
    session: AsyncSession,
    contact_uuid: str,
) -> Optional[tuple[Contact, Company, ContactMetadata, CompanyMetadata]]:
    stmt, _, _, _ = self.base_query()  # Step 2: Build query with all joins
    stmt = stmt.where(Contact.uuid == contact_uuid)  # Direct UUID filter
    result = await session.execute(stmt)  # Step 8: Execute
    return result.first()
```

**Notes:** 
- Always uses full metadata query (all joins) since it needs complete contact data
- No filtering logic needed - direct UUID lookup
- Returns single row or None

---

### 3. GET /api/v1/contacts/count/ - Get Contact Count

**Status:** ✅ **Uses Steps 1-6, Variation in Steps 7-8**

**Implementation:**
- Endpoint: `app/api/v1/endpoints/contacts.py` (line 253)
- Repository: `ContactRepository.count_contacts()` (lines 1451-1584)

**Steps Used:**
- ✅ Step 1: Parameter analysis (lines 1487-1500)
- ✅ Step 2: Base query construction (lines 1505-1518)
- ✅ Step 3: Apply contact filters (lines 1522-1528)
- ✅ Step 4: Apply company filters (lines 1530-1537)
- ✅ Step 5: Apply special filters (lines 1539-1546)
- ✅ Step 6: Apply search (lines 1548-1556)
- ⚠️ Step 7: **Variation** - Convert to COUNT query instead of ordering (line 1562)
- ⚠️ Step 8: **Variation** - Execute and return scalar count (lines 1581-1583)

**Code Reference:**
```python
# Steps 1-6: Same as list_contacts
# Step 7 Variation: Convert to COUNT
stmt = base_stmt.with_only_columns(func.count(distinct(Contact.id)))

# Step 8 Variation: Return scalar
result = await session.execute(stmt)
total = result.scalar_one() or 0
return total
```

**Notes:**
- Uses same filtering logic as `list_contacts` (Steps 1-6)
- Step 7: Replaces SELECT + ORDERING with `COUNT(DISTINCT Contact.id)`
- Step 8: Returns integer count instead of normalized rows
- Supports approximate count for very large unfiltered queries (PostgreSQL `pg_class`)

---

### 4. GET /api/v1/contacts/count/uuids/ - Get Contact UUIDs

**Status:** ✅ **Uses Steps 1-6, Variation in Steps 7-8**

**Implementation:**
- Endpoint: `app/api/v1/endpoints/contacts.py` (line 267)
- Repository: `ContactRepository.get_uuids_by_filters()` (lines 1904-2008)

**Steps Used:**
- ✅ Step 1: Parameter analysis (lines 1921-1934)
- ✅ Step 2: Base query construction (lines 1938-1952)
- ✅ Step 3: Apply contact filters (lines 1956-1962)
- ✅ Step 4: Apply company filters (lines 1964-1971)
- ✅ Step 5: Apply special filters (lines 1973-1980)
- ✅ Step 6: Apply search (lines 1982-1990)
- ⚠️ Step 7: **Variation** - Convert to UUID-only SELECT, no ordering (line 1993)
- ⚠️ Step 8: **Variation** - Execute and return list of UUIDs (lines 2005-2007)

**Code Reference:**
```python
# Steps 1-6: Same as list_contacts
# Step 7 Variation: Select UUID only, no ordering
stmt = base_stmt.with_only_columns(Contact.uuid)
stmt = stmt.where(Contact.uuid.isnot(None))
if limit is not None:
    stmt = stmt.limit(limit)

# Step 8 Variation: Return UUID list
result = await session.execute(stmt)
uuids = [uuid for (uuid,) in result.fetchall() if uuid]
return uuids
```

**Notes:**
- Uses same filtering logic as `list_contacts` (Steps 1-6)
- Step 7: Replaces SELECT + ORDERING with `SELECT Contact.uuid` only
- Step 8: Returns list of UUID strings instead of normalized rows
- Supports optional limit parameter

---

### 5. POST /api/v1/contacts/ - Create Contact

**Status:** ❌ **No Query Building (Write Operation)**

**Implementation:**
- Endpoint: `app/api/v1/endpoints/contacts.py` (line 282)
- Repository: `ContactRepository.create_contact()` (line 1136)

**Steps Used:**
- ❌ None - This is a write operation

**Code Reference:**
```python
async def create_contact(self, session: AsyncSession, data: dict[str, Any]) -> Contact:
    contact = Contact(**data)
    session.add(contact)
    await session.flush()
    await session.refresh(contact)
    return contact
```

**Notes:**
- Creates new Contact record
- No query building or filtering involved
- After creation, calls `get_contact()` which uses the simplified process (endpoint #2)

---

### 6. Field-Specific Endpoints (13 endpoints)

**Status:** ✅ **Uses Steps 1-6, Variation in Steps 7-8**

**Endpoints:**
1. `GET /api/v1/contacts/title/`
2. `GET /api/v1/contacts/company/`
3. `GET /api/v1/contacts/industry/`
4. `GET /api/v1/contacts/keywords/`
5. `GET /api/v1/contacts/technologies/`
6. `GET /api/v1/contacts/company_address/`
7. `GET /api/v1/contacts/contact_address/`
8. `GET /api/v1/contacts/city/`
9. `GET /api/v1/contacts/state/`
10. `GET /api/v1/contacts/country/`
11. `GET /api/v1/contacts/company_city/`
12. `GET /api/v1/contacts/company_state/`
13. `GET /api/v1/contacts/company_country/`

**Implementation:**
- Endpoints: `app/api/v1/endpoints/contacts.py` (lines 383-667)
- Repository: `ContactRepository.list_attribute_values()` (lines 1676-1807)
- Array Optimization: `ContactRepository._list_array_attribute_values()` (lines 1809-1902)

**Steps Used:**
- ✅ Step 1: Parameter analysis (lines 1709-1712)
- ✅ Step 2: Base query construction (lines 1714-1735) - Always joins Company, conditionally joins metadata
- ✅ Step 3: Apply contact filters (lines 1741-1747)
- ✅ Step 4: Apply company filters (lines 1749-1756)
- ✅ Step 5: Apply special filters (lines 1758-1765)
- ✅ Step 6: Apply search (lines 1767-1775)
- ⚠️ Step 7: **Variation** - Order by selected column only, distinct handling (lines 1779-1793)
- ⚠️ Step 8: **Variation** - Execute and return list of attribute values (lines 1795-1807)

**Code Reference:**
```python
# Steps 1-6: Same as list_contacts
# Step 7 Variation: Order by selected column, handle distinct
column_expression = column_factory(Contact, company_alias, contact_meta_alias, company_meta_alias)
stmt = select(column_expression).select_from(Contact)
# ... apply filters (Steps 3-6) ...
stmt = stmt.where(column_expression.isnot(None))

if params.distinct:
    stmt = stmt.distinct()

ordering_map = {"value": column_expression}
stmt = apply_ordering(stmt, params.ordering, ordering_map)

# Step 8 Variation: Return attribute values
stmt = stmt.offset(params.offset)
if params.limit is not None:
    stmt = stmt.limit(params.limit)
result = await session.execute(stmt)
values = [value for (value,) in result.fetchall() if value]
return values
```

**Array Mode Optimization:**
For array columns (industries, keywords, technologies) with `separated=true`:
- Uses `_list_array_attribute_values()` method
- Applies Steps 1-6 to filter contacts
- Then uses PostgreSQL `unnest()` to expand array values
- Applies search and ordering to individual array elements

**Notes:**
- All 13 endpoints use the same `list_attribute_values()` method
- Each endpoint provides a different `column_factory` lambda to select the specific column
- Supports `distinct`, `search`, `limit`, `offset`, and `ordering` parameters
- Array endpoints (industry, keywords, technologies) support `separated=true` for expansion

---

### 7. Import Endpoints (4 endpoints)

**Status:** ❌ **No Query Building (File Upload/Job Management)**

**Endpoints:**
1. `GET /api/v1/contacts/import/` - Get import information
2. `POST /api/v1/contacts/import/` - Upload CSV file
3. `GET /api/v1/contacts/import/{job_id}/` - Get import job status
4. `GET /api/v1/contacts/import/{job_id}/errors/` - Get import errors

**Implementation:**
- Endpoints: `app/api/v1/endpoints/imports.py`

**Steps Used:**
- ❌ None - These are file upload and job management endpoints

**Notes:**
- `GET /api/v1/contacts/import/` - Returns informational message
- `POST /api/v1/contacts/import/` - Uploads CSV file, creates background job
- `GET /api/v1/contacts/import/{job_id}/` - Queries `ImportJob` table (different from contacts query building)
- `GET /api/v1/contacts/import/{job_id}/errors/` - Returns error records from import job

**Query Building:**
- Import endpoints query the `ImportJob` and related tables, not the Contact/Company tables
- Uses standard SQLAlchemy queries, not the 8-step contact query building process
- Job status queries are simple SELECT queries by job_id

---

## Summary Matrix

| Endpoint | Steps 1-6 | Step 7 | Step 8 | Notes |
|----------|-----------|--------|--------|-------|
| `GET /contacts/` | ✅ Full | ✅ Ordering | ✅ Normalize rows | Reference implementation |
| `GET /contacts/{uuid}/` | ⚠️ Step 2 only | ❌ None | ✅ Execute | Single UUID lookup |
| `GET /contacts/count/` | ✅ Full | ⚠️ COUNT | ⚠️ Scalar result | Same filtering, count output |
| `GET /contacts/count/uuids/` | ✅ Full | ⚠️ SELECT uuid | ⚠️ UUID list | Same filtering, UUID output |
| `POST /contacts/` | ❌ None | ❌ None | ❌ None | Write operation |
| Field endpoints (13) | ✅ Full | ⚠️ Column ordering | ⚠️ Value list | Same filtering, attribute output |
| Import endpoints (4) | ❌ None | ❌ None | ❌ None | File/job management |

---

## Key Findings

### Endpoints Using Full 8-Step Process (Steps 1-6)
1. ✅ `GET /api/v1/contacts/` - Full implementation
2. ✅ `GET /api/v1/contacts/count/` - Steps 1-6, COUNT in Step 7
3. ✅ `GET /api/v1/contacts/count/uuids/` - Steps 1-6, UUID SELECT in Step 7
4. ✅ All 13 field-specific endpoints - Steps 1-6, column SELECT in Step 7

### Endpoints Using Simplified Process
1. ⚠️ `GET /api/v1/contacts/{contact_uuid}/` - Only Step 2 (base query) and Step 8 (execute)

### Endpoints With No Query Building
1. ❌ `POST /api/v1/contacts/` - Write operation
2. ❌ All 4 import endpoints - File upload/job management

### Common Pattern
All endpoints that use filtering (Steps 1-6) follow the same pattern:
- **Steps 1-6:** Identical across all filtering endpoints
- **Step 7:** Varies based on output type (ordering, COUNT, SELECT column)
- **Step 8:** Varies based on output format (rows, scalar, list)

This design ensures:
- **Consistency:** All filtering logic is centralized and reusable
- **Performance:** Same optimizations (conditional joins, trigram indexes) apply everywhere
- **Maintainability:** Changes to filtering logic automatically apply to all endpoints

---

## Code References

### Repository Methods
- `list_contacts()` - Lines 895-1134 in `app/repositories/contacts.py`
- `count_contacts()` - Lines 1451-1584 in `app/repositories/contacts.py`
- `get_uuids_by_filters()` - Lines 1904-2008 in `app/repositories/contacts.py`
- `list_attribute_values()` - Lines 1676-1807 in `app/repositories/contacts.py`
- `_list_array_attribute_values()` - Lines 1809-1902 in `app/repositories/contacts.py`
- `get_contact_with_relations()` - Line 2738 in `app/repositories/contacts.py`
- `create_contact()` - Line 1136 in `app/repositories/contacts.py`

### Shared Filter Methods
- `_apply_contact_filters()` - Lines 560-664 in `app/repositories/contacts.py`
- `_apply_company_filters()` - Lines 666-790 in `app/repositories/contacts.py`
- `_apply_special_filters()` - Lines 799-870 in `app/repositories/contacts.py`
- `apply_search_terms()` - Lines 505-558 in `app/repositories/contacts.py`

### Join Determination Methods
- `_needs_company_join()` - Lines 39-53 in `app/repositories/contacts.py`
- `_needs_contact_metadata_join()` - Lines 55-63 in `app/repositories/contacts.py`
- `_needs_company_metadata_join()` - Lines 65-75 in `app/repositories/contacts.py`

