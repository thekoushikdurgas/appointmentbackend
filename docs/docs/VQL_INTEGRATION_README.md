# VQL Integration Documentation

## Overview

This backend now supports VQL (Vivek Query Language) integration through the Connectra Go service. VQL provides powerful Elasticsearch-based filtering and search capabilities while maintaining PostgreSQL as the primary data store.

## Architecture

```
FastAPI Backend → VQL Client → Connectra Go Service → Elasticsearch
                                      ↓
                                  PostgreSQL
```

## Key Components

### 1. VQL Client (`app/clients/connectra_client.py`)
- HTTP client for Connectra API
- Handles authentication, retries, and error handling
- Methods: `search_contacts()`, `search_companies()`, `count_contacts()`, `count_companies()`

### 2. VQL Converter (`app/services/vql_converter.py`)
- Converts existing filter parameters to VQL format
- Maps backend filters to VQL query structure
- Handles text matches, keyword matches, and range queries

### 3. VQL Transformer (`app/services/vql_transformer.py`)
- Transforms VQL responses back to backend schema formats
- Handles pagination and cursor conversion
- Maps VQL response fields to `ContactListItem` and `CompanyListItem`

### 4. Elasticsearch Sync Service (`app/services/elasticsearch_sync_service.py`)
- Synchronizes PostgreSQL data to Elasticsearch
- Handles individual and bulk sync operations
- Maintains data consistency between systems

## Configuration

### Environment Variables

```bash
# Connectra VQL Service
CONNECTRA_BASE_URL=http://localhost:8000
CONNECTRA_API_KEY=your-secret-api-key
CONNECTRA_TIMEOUT=30
CONNECTRA_ENABLED=false  # Feature flag
CONNECTRA_RETRY_ATTEMPTS=3
CONNECTRA_RETRY_DELAY=1.0

# Elasticsearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_USE_SSL=false
ELASTICSEARCH_VERIFY_CERTS=true
```

## Usage

### Enabling VQL

1. Set `CONNECTRA_ENABLED=true` in `.env`
2. Ensure Connectra service is running
3. Ensure Elasticsearch indices are created and synced
4. Restart the backend service

### Automatic Fallback

All VQL-enabled endpoints automatically fallback to direct PostgreSQL queries if:
- `CONNECTRA_ENABLED=false`
- Connectra service is unavailable
- VQL query fails for any reason

### Endpoints Using VQL

When `CONNECTRA_ENABLED=true`, the following endpoints use VQL:

**Contact Endpoints:**
- `GET /api/v1/contacts/` - List contacts
- `GET /api/v1/contacts/count/` - Count contacts
- `GET /api/v1/contacts/stream/` - Stream contacts (future)

**Company Endpoints:**
- `GET /api/v1/companies/` - List companies
- `GET /api/v1/companies/count/` - Count companies
- `GET /api/v1/companies/stream/` - Stream companies (future)

## Data Synchronization

### Initial Sync

```bash
# Sync contacts
python -m app.cli.elasticsearch_sync sync-contacts --limit 10000

# Sync companies
python -m app.cli.elasticsearch_sync sync-companies --limit 10000

# Verify sync
python -m app.cli.elasticsearch_sync verify-sync
```

### Real-time Sync

When contacts or companies are created/updated/deleted, they should be synced to Elasticsearch. This can be done by:

1. Hooking into repository create/update/delete methods
2. Calling `sync_contact_to_elasticsearch()` or `sync_company_to_elasticsearch()`
3. Or using background tasks for async sync

## Filter Mapping

### Contact Filters → VQL

| Backend Filter | VQL Field | Type |
|---------------|-----------|------|
| `first_name` | `first_name` | text_match |
| `last_name` | `last_name` | text_match |
| `title` | `title` | text_match |
| `seniority` | `seniority` | keyword_match |
| `email_status` | `email_status` | keyword_match |
| `departments` | `departments` | keyword_match |
| `employees_min/max` | `company_employees_count` | range_query |
| `annual_revenue_min/max` | `company_annual_revenue` | range_query |
| `industries` | `company_industries` | keyword_match |

### Company Filters → VQL

| Backend Filter | VQL Field | Type |
|---------------|-----------|------|
| `name` | `name` | text_match |
| `address` | `address` | text_match |
| `industries` | `industries` | keyword_match |
| `technologies` | `technologies` | keyword_match |
| `employees_min/max` | `employees_count` | range_query |
| `annual_revenue_min/max` | `annual_revenue` | range_query |

## Testing

### Unit Tests

```bash
pytest app/tests/unit/test_vql_converter.py
pytest app/tests/unit/test_vql_transformer.py
pytest app/tests/unit/test_connectra_client.py
```

### Integration Tests

```bash
pytest app/tests/integration/test_vql_endpoints.py
```

## Monitoring

VQL query metrics are tracked via `VQLMonitoringMiddleware`:
- Total VQL queries
- Success/failure rates
- Average response times
- Fallback frequency

## Troubleshooting

### VQL queries always falling back

1. Check `CONNECTRA_ENABLED` is `true`
2. Verify Connectra service is running
3. Check API key is correct
4. Review application logs for errors

### Data inconsistencies

1. Re-run bulk sync
2. Verify ES index mappings match Connectra specs
3. Check sync service logs

### Performance issues

1. Monitor Elasticsearch cluster health
2. Check index shard/replica configuration
3. Review query complexity
4. Consider increasing ES resources

## Future Enhancements

- [ ] Real-time sync hooks in repositories
- [ ] Background sync tasks
- [ ] Advanced monitoring dashboard
- [ ] Query performance analytics
- [ ] Automatic index optimization

