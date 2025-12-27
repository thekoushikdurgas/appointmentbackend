# VQL Integration Deployment Checklist

## Prerequisites

- [ ] Elasticsearch 8.x installed and running
- [ ] Connectra Go service deployed and accessible
- [ ] PostgreSQL database with contacts and companies data
- [ ] Environment variables configured

## Environment Configuration

Update `.env` file with:

```bash
# Connectra VQL Service
CONNECTRA_BASE_URL=http://localhost:8000
CONNECTRA_API_KEY=your-secret-api-key
CONNECTRA_TIMEOUT=30
CONNECTRA_ENABLED=false  # Start disabled
CONNECTRA_RETRY_ATTEMPTS=3
CONNECTRA_RETRY_DELAY=1.0

# Elasticsearch Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_USE_SSL=false
ELASTICSEARCH_VERIFY_CERTS=true
```

## Step-by-Step Deployment

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Create Elasticsearch Indices

```bash
python -m app.scripts.create_elasticsearch_indices
```

Verify indices were created:
```bash
curl http://localhost:9200/_cat/indices
```

### 3. Initial Data Sync

Sync contacts:
```bash
python -m app.cli.elasticsearch_sync sync-contacts --limit 10000
```

Sync companies:
```bash
python -m app.cli.elasticsearch_sync sync-companies --limit 10000
```

Verify sync:
```bash
python -m app.cli.elasticsearch_sync verify-sync
```

### 4. Deploy Connectra Service

Ensure Connectra Go service is running and accessible at `CONNECTRA_BASE_URL`.

Test connection:
```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:8000/health
```

### 5. Enable VQL Feature Flag

Update `.env`:
```bash
CONNECTRA_ENABLED=true
```

Restart the backend service.

### 6. Monitor and Validate

- Check application logs for VQL query success/failure rates
- Monitor fallback frequency
- Compare query performance (VQL vs Direct DB)
- Verify data consistency between ES and PostgreSQL

### 7. Rollback Plan

If issues occur, immediately disable VQL:
```bash
CONNECTRA_ENABLED=false
```

Restart the backend service. All endpoints will automatically fallback to direct DB queries.

## Verification Tests

1. **Basic Query Test**:
   ```bash
   curl -H "X-API-Key: your-key" \
        -H "Authorization: Bearer your-token" \
        "http://localhost:8000/api/v1/contacts/?first_name=John&limit=10"
   ```

2. **Count Test**:
   ```bash
   curl -H "X-API-Key: your-key" \
        -H "Authorization: Bearer your-token" \
        "http://localhost:8000/api/v1/contacts/count/?seniority=Senior"
   ```

3. **Complex Filter Test**:
   ```bash
   curl -H "X-API-Key: your-key" \
        -H "Authorization: Bearer your-token" \
        "http://localhost:8000/api/v1/contacts/?employees_min=100&employees_max=1000&industries=Technology"
   ```

## Success Criteria

- ✅ All endpoints respond successfully
- ✅ Query results match between VQL and Direct DB
- ✅ Fallback rate < 5%
- ✅ Query performance improved (50%+ faster)
- ✅ No data inconsistencies

## Troubleshooting

### Issue: VQL queries failing

**Solution**: Check Connectra service logs, verify API key, check network connectivity.

### Issue: Elasticsearch sync lag

**Solution**: Increase sync batch size, run sync more frequently, check ES cluster health.

### Issue: Data inconsistencies

**Solution**: Re-run bulk sync, verify ES index mappings match Connectra specs.

### Issue: High fallback rate

**Solution**: Review VQL converter logic, check filter mapping, verify ES data completeness.

