# ContactRepository Refactoring Plan

## Current State
- **File**: `backend/app/repositories/contacts.py`
- **Size**: ~5,111 lines
- **Methods**: 99 methods in a single class

## Proposed Structure

The `ContactRepository` class can be logically split into multiple files using Python mixins or separate modules. Here's the proposed organization:

### 1. `contacts.py` (Main Repository - ~800 lines)
**Core CRUD and orchestration methods:**
- `__init__`
- `list_contacts`
- `create_contact`
- `count_contacts`
- `get_contact_with_relations`
- `base_query_minimal`
- `apply_filters` (legacy, may be deprecated)
- `apply_search_terms` (legacy, may be deprecated)

### 2. `contacts_filters.py` (Filter Logic - ~1,500 lines)
**Filter detection and application:**
- Filter detection methods:
  - `_needs_company_exists_subquery`
  - `_needs_contact_metadata_exists_subquery`
  - `_needs_company_metadata_exists_subquery`
  - `_needs_company_exists_subquery_for_search`
  - `_detect_column_table`
  - `_get_contact_only_filters`
  - `_get_company_only_filters`
  - `_get_contact_metadata_filters`
  - `_get_company_metadata_filters`
  - `_get_special_filters`

- Filter application methods:
  - `_apply_contact_filters_direct`
  - `_build_company_exists_subquery`
  - `_build_company_metadata_exists_subquery`
  - `_build_contact_metadata_exists_subquery`
  - `_apply_filters_with_exists`
  - `_apply_contact_filters` (legacy)
  - `_apply_company_filters` (legacy)
  - `_apply_special_filters` (legacy)

### 3. `contacts_filter_helpers.py` (Filter Utilities - ~800 lines)
**Low-level filter helper methods:**
- `_apply_multi_value_filter`
- `_apply_trigram_similarity_filter`
- `_apply_values_join_filter`
- `_apply_batched_filter`
- `_apply_array_text_filter`
- `_apply_multi_value_exclusion`
- `_apply_array_text_exclusion`
- `_apply_domain_filter`
- `_apply_domain_exclusion`
- `_apply_array_text_filter_and`
- `_apply_keyword_search_with_fields`
- `_extract_domain_from_url_sql`
- `_array_column_as_text`
- `_split_filter_values`

### 4. `contacts_title_filters.py` (Title Filtering - ~300 lines)
**Specialized title filtering logic:**
- `_normalize_title_in_sql`
- `_apply_normalized_title_filter`
- `_apply_normalized_title_exclusion`
- `_apply_jumble_title_filter`

### 5. `contacts_ordering.py` (Ordering Logic - ~300 lines)
**Ordering and sorting:**
- `_build_company_ordering_subqueries`
- `_build_company_metadata_ordering_subqueries`
- `_build_contact_metadata_ordering_subqueries`
- `_build_ordering_map_with_subqueries`

### 6. `contacts_search.py` (Search Logic - ~200 lines)
**Search functionality:**
- `_apply_search_terms_with_exists`
- `_apply_company_contact_search`

### 7. `contacts_attributes.py` (Attribute Listing - ~1,500 lines)
**Attribute value listing methods:**
- `_can_optimize_company_query`
- `_clean_company_column_expression`
- `_apply_company_table_filters_optimized`
- `_apply_company_metadata_filters_optimized`
- `_apply_keyword_filters_optimized`
- `_list_company_attribute_values_optimized`
- `list_attribute_values`
- `list_company_names_simple`
- `list_company_domains_simple`
- `list_industries_simple`
- `list_keywords_simple`
- `list_technologies_simple`
- `list_departments_simple`
- `_list_array_attribute_values`

### 8. `contacts_company.py` (Company-Specific - ~600 lines)
**Company-related operations:**
- `list_contacts_by_company`
- `count_contacts_by_company`
- `list_attribute_values_by_company`
- `_convert_company_contact_filters_to_contact_filters`
- `_build_department_attribute_query_by_company`
- `_build_scalar_attribute_query_by_company`
- `_apply_company_contact_filters`
- `_apply_company_contact_search`

### 9. `contacts_utils.py` (Utility Methods - ~200 lines)
**Utility and helper methods:**
- `get_uuids_by_filters`
- `get_uuids_by_company`

## Implementation Strategy

### Option 1: Mixin Pattern (Recommended)
Create mixin classes that can be inherited by `ContactRepository`:

```python
# contacts_filters.py
class ContactFilterMixin:
    """Mixin for filter-related methods."""
    # ... filter methods ...

# contacts.py
from .contacts_filters import ContactFilterMixin
from .contacts_ordering import ContactOrderingMixin
# ... other mixins ...

class ContactRepository(AsyncRepository[Contact], 
                       ContactFilterMixin,
                       ContactOrderingMixin,
                       ContactAttributeMixin,
                       ...):
    """Main repository class."""
    # Core methods only
```

**Pros:**
- Maintains single class interface
- Easy to import: `from app.repositories.contacts import ContactRepository`
- No breaking changes to existing code
- Methods remain accessible as `repo.method_name()`

**Cons:**
- Multiple inheritance complexity
- Need to ensure no method name conflicts

### Option 2: Composition Pattern
Create separate classes and compose them:

```python
# contacts_filters.py
class ContactFilterBuilder:
    """Handles filter building logic."""
    # ... filter methods ...

# contacts.py
class ContactRepository(AsyncRepository[Contact]):
    def __init__(self):
        super().__init__(Contact)
        self._filter_builder = ContactFilterBuilder()
        self._ordering_builder = ContactOrderingBuilder()
        # ...
    
    def list_contacts(self, ...):
        # Use self._filter_builder.apply_filters(...)
```

**Pros:**
- Clear separation of concerns
- Easier to test individual components
- No multiple inheritance

**Cons:**
- Breaking change: method calls become `repo._filter_builder.method()`
- More verbose
- Requires refactoring all call sites

### Option 3: Module Functions
Extract methods as module-level functions:

```python
# contacts_filters.py
def apply_filters_with_exists(stmt, filters, ...):
    """Apply filters using EXISTS subqueries."""
    # ...

# contacts.py
from .contacts_filters import apply_filters_with_exists

class ContactRepository(AsyncRepository[Contact]):
    def list_contacts(self, ...):
        stmt = apply_filters_with_exists(stmt, filters, ...)
```

**Pros:**
- Simple, no inheritance complexity
- Functions can be reused independently
- Easy to test

**Cons:**
- Breaking change: methods become functions
- Need to pass `self` explicitly if accessing instance state
- Less object-oriented

## Recommended Approach

**Use Option 1 (Mixin Pattern)** because:
1. Maintains backward compatibility
2. Keeps the familiar `ContactRepository` interface
3. Allows logical grouping without breaking changes
4. Python's MRO handles method resolution cleanly

## Migration Steps

1. **Phase 1: Create mixin files** (non-breaking)
   - Create new files with mixin classes
   - Move methods to appropriate mixins
   - Keep original file working

2. **Phase 2: Update main class** (non-breaking)
   - Update `ContactRepository` to inherit from mixins
   - Remove duplicate method definitions
   - Test thoroughly

3. **Phase 3: Cleanup** (non-breaking)
   - Remove any unused legacy methods
   - Update documentation
   - Add type hints where missing

## Testing Strategy

1. Run existing test suite to ensure no regressions
2. Test each mixin independently
3. Integration tests for main repository methods
4. Performance benchmarks to ensure no degradation

## Estimated Impact

- **Files created**: 8 new files
- **Lines per file**: 200-1,500 (much more manageable)
- **Breaking changes**: None (if using mixin pattern)
- **Testing effort**: Medium (comprehensive test suite needed)

## Notes

- The `list_attribute_values` method (344 lines) is complex and handles multiple optimization paths. Consider further splitting during this refactoring.
- Some legacy methods (`apply_filters`, `apply_search_terms`, `_apply_contact_filters`, etc.) may be candidates for deprecation.
- Consider creating a `contacts_base.py` for shared utilities and constants.

## Future Considerations

- Consider extracting query building logic into a separate query builder pattern
- Evaluate if some attribute listing methods can be further consolidated
- Review if filter helper methods can be simplified or consolidated

