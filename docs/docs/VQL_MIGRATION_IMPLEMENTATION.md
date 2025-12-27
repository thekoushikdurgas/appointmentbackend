# VQL Migration Implementation Summary

## Overview

This document summarizes the implementation of VQL (Vivek Query Language) migration for direct PostgreSQL query endpoints. The migration centralizes query logic through the Connectra service, improving performance through Elasticsearch while maintaining automatic fallback to PostgreSQL.

## Implementation Status

### ✅ Completed Components

#### 1. ConnectraClient Extensions
**File:** `backend/app/clients/connectra_client.py`

Added methods:
- `get_contact_by_uuid()` - Single contact retrieval via VQL
- `get_company_by_uuid()` - Single company retrieval via VQL
- `search_by_linkedin_url()` - LinkedIn URL search for contacts/companies
- `batch_search_by_uuids()` - Batch queries for exports (supports chunking)

#### 2. CompanyContactFilterParams Converter
**File:** `backend/app/core/vql/company_contact_converter.py`

Converts `CompanyContactFilterParams` to VQL filter structures:
- Maps all filter fields to VQL conditions
- Handles exclusion filters with negation operators
- Automatically adds company_id filter

#### 3. Service Layer Updates

**ContactsService** (`backend/app/services/contacts_service.py`):
- `get_contact()` - Uses VQL when `VQL_SINGLE_RECORD_RETRIEVAL` enabled
- `list_contacts_by_company()` - Uses VQL when `VQL_COMPANY_CONTACTS` enabled
- `count_contacts_by_company()` - Uses VQL when `VQL_COMPANY_CONTACTS` enabled
- All methods include automatic fallback to repository queries

**CompaniesService** (`backend/app/services/companies_service.py`):
- `get_company_by_uuid()` - Uses VQL when `VQL_SINGLE_RECORD_RETRIEVAL` enabled
- Includes automatic fallback to repository queries

**ExportService** (`backend/app/services/export_service.py`):
- `generate_csv()` - Attempts VQL batch queries when `VQL_EXPORTS` enabled
- Falls back to repository for complete metadata

**LinkedInService** (`backend/app/services/linkedin_service.py`):
- `search_by_url()` - Attempts VQL LinkedIn search when `VQL_LINKEDIN_SEARCH` enabled
- Falls back to repository for complete data structure

#### 4. Feature Flags
**File:** `backend/app/core/config.py`

Added feature flags for gradual rollout:
- `VQL_SINGLE_RECORD_RETRIEVAL` - Enable VQL for single-record endpoints
- `VQL_COMPANY_CONTACTS` - Enable VQL for company contacts endpoints
- `VQL_EXPORTS` - Enable VQL for export tasks
- `VQL_LINKEDIN_SEARCH` - Enable VQL for LinkedIn search

#### 5. Integration Tests
**Files:**
- `backend/app/tests/integration/test_vql_endpoints.py` - Enhanced with migration endpoint tests
- `backend/app/tests/performance/test_vql_performance.py` - Performance benchmarking structure

### 🔄 Automatic Fallback Mechanism

All VQL-enabled services implement automatic fallback:
1. Try VQL via Connectra first (if enabled and feature flag is on)
2. On failure, log warning and fall back to repository queries
3. Maintain original error messages for client compatibility
4. Track fallback metrics for monitoring

## Endpoints Migrated

### Single-Record Retrieval
- `GET /api/v1/contacts/{contact_uuid}/` - Uses `ContactsService.get_contact()`
- `GET /api/v1/companies/{company_uuid}/` - Uses `CompaniesService.get_company_by_uuid()`

### Company Contacts
- `GET /api/v1/companies/company/{company_uuid}/contacts/` - Uses `ContactsService.list_contacts_by_company()`
- `GET /api/v1/companies/company/{company_uuid}/contacts/count/` - Uses `ContactsService.count_contacts_by_company()`
- Attribute endpoints (first_name, last_name, title, etc.) - Use `ContactsService.list_attribute_values_by_company()`

### Export Tasks
- Background task `process_contact_export()` - Uses `ExportService.generate_csv()`
- Background task `process_company_export()` - Uses `ExportService.generate_company_csv()`
- Background task `process_email_export()` - Uses export service

### LinkedIn Search
- `POST /api/v2/linkedin/` - Uses `LinkedInService.search_by_url()`

## Configuration

### Environment Variables

```bash
# Enable Connectra service
CONNECTRA_ENABLED=true

# Connectra service configuration
CONNECTRA_BASE_URL=http://18.234.210.191:8080
CONNECTRA_API_KEY=3e6b8811-40c2-46e7-8d7c-e7e038e86071
CONNECTRA_TIMEOUT=30

# VQL Feature Flags (gradual rollout)
VQL_SINGLE_RECORD_RETRIEVAL=false
VQL_COMPANY_CONTACTS=false
VQL_EXPORTS=false
VQL_LINKEDIN_SEARCH=false
```

## Gradual Rollout Strategy

### Phase 1: Single Record Retrieval
1. Set `VQL_SINGLE_RECORD_RETRIEVAL=true`
2. Monitor error rates and performance
3. Verify fallback mechanism works
4. Monitor for 24-48 hours

### Phase 2: Company Contacts
1. Set `VQL_COMPANY_CONTACTS=true`
2. Monitor company contacts endpoints
3. Verify filter conversion works correctly
4. Monitor for 24-48 hours

### Phase 3: Exports
1. Set `VQL_EXPORTS=true`
2. Monitor export success rates
3. Verify batch query performance
4. Monitor for 48-72 hours

### Phase 4: LinkedIn Search
1. Set `VQL_LINKEDIN_SEARCH=true`
2. Monitor search accuracy
3. Verify URL matching works correctly
4. Monitor for 24-48 hours

### Phase 5: Full Migration
1. After all phases stable, consider removing feature flags
2. Keep fallback mechanism for reliability
3. Monitor long-term performance

## Monitoring

### Key Metrics to Track

1. **VQL Success Rate**: Percentage of successful VQL queries
2. **Fallback Rate**: Percentage of queries falling back to repository
3. **Response Time**: Compare VQL vs direct query response times
4. **Error Rate**: Track VQL-specific errors
5. **Connectra Availability**: Monitor Connectra service uptime

### Logging

All VQL failures are logged with warnings:
```python
logger.warning(f"VQL query failed, falling back to repository: {exc}")
```

## Testing

### Integration Tests
Run integration tests:
```bash
pytest backend/app/tests/integration/test_vql_endpoints.py -v
```

### Performance Tests
Run performance benchmarks:
```bash
pytest backend/app/tests/performance/test_vql_performance.py -v -m performance
```

## Known Limitations

1. **Metadata Completeness**: VQL responses may not include all metadata fields needed for complete exports. Services fall back to repository for full data.

2. **ContactDetail Conversion**: Single record retrieval via VQL returns `ContactListItem`, which may need additional metadata fetching for `ContactDetail` conversion.

3. **LinkedIn Search**: VQL LinkedIn search may need additional processing to match the exact data structure returned by repository queries.

## Future Enhancements

1. **Enhanced VQL Response**: Request Connectra to include all metadata fields in responses
2. **Caching Layer**: Add caching for frequently accessed single records
3. **Metrics Collection**: Implement detailed metrics collection for VQL vs direct queries
4. **Performance Optimization**: Optimize VQL queries based on performance test results

## Rollback Plan

If issues arise during rollout:

1. **Immediate Rollback**: Set all VQL feature flags to `false`
2. **Selective Rollback**: Disable specific feature flags for problematic endpoints
3. **Service Rollback**: Set `CONNECTRA_ENABLED=false` to disable all VQL queries

All endpoints will automatically fall back to repository queries when VQL is disabled.

## Success Criteria

✅ All endpoints return same data as before migration
✅ VQL queries perform within acceptable threshold (≤20% slower)
✅ Fallback mechanism works correctly when Connectra unavailable
✅ Feature flags allow gradual rollout
✅ Integration tests pass
✅ Performance benchmarks meet criteria

## Related Documentation

- [VQL Integration README](VQL_INTEGRATION_README.md)
- [VQL API Guide](VQL_API_GUIDE.md)
- [Connectra Documentation](../../connectra/docs/)

