# VQL Gradual Rollout Guide

## Overview

This guide provides step-by-step instructions for gradually rolling out VQL migration endpoints in production. The rollout uses feature flags to enable endpoints incrementally, allowing for monitoring and quick rollback if issues arise.

## Prerequisites

Before starting the rollout:

- [ ] Connectra service is deployed and healthy
- [ ] Elasticsearch indices are synced with PostgreSQL data
- [ ] Monitoring and alerting are configured
- [ ] Rollback procedures are documented and tested
- [ ] Team is available for monitoring during rollout

## Rollout Phases

### Phase 0: Pre-Rollout Verification

**Duration:** 1-2 hours

1. **Verify Connectra Service Health**
   ```bash
   curl -H "X-API-Key: $CONNECTRA_API_KEY" $CONNECTRA_BASE_URL/health
   ```
   Expected: `{"status": "healthy"}`

2. **Verify Elasticsearch Sync**
   ```bash
   # Check contact count in ES vs PostgreSQL
   curl "$ELASTICSEARCH_HOST:9200/contacts_index/_count"
   ```

3. **Test VQL Queries Manually**
   ```bash
   # Test single contact retrieval
   curl -X POST "$CONNECTRA_BASE_URL/contacts" \
     -H "X-API-Key: $CONNECTRA_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"filters": {"and": [{"field": "uuid", "operator": "eq", "value": "test-uuid"}]}, "limit": 1}'
   ```

4. **Enable Monitoring**
   - Ensure VQL monitoring middleware is active
   - Set up alerts for high fallback rates (>10%)
   - Set up alerts for VQL error rates (>5%)

### Phase 1: Single Record Retrieval

**Duration:** 24-48 hours  
**Feature Flag:** `VQL_SINGLE_RECORD_RETRIEVAL`

**Endpoints Affected:**
- `GET /api/v1/contacts/{contact_uuid}/`
- `GET /api/v1/companies/{company_uuid}/`

**Steps:**

1. **Enable Feature Flag**
   ```bash
   # In .env or environment variables
   VQL_SINGLE_RECORD_RETRIEVAL=true
   CONNECTRA_ENABLED=true
   ```

2. **Deploy and Monitor**
   - Deploy backend with feature flag enabled
   - Monitor for first 2 hours:
     - Error rates
     - Response times
     - Fallback frequency
   - Check logs for VQL warnings

3. **Validation Checks**
   - [ ] Single contact retrieval works correctly
   - [ ] Single company retrieval works correctly
   - [ ] Response times are acceptable (≤20% slower than direct queries)
   - [ ] Fallback rate < 5%
   - [ ] No data inconsistencies

4. **Success Criteria**
   - ✅ Error rate < 1%
   - ✅ Fallback rate < 5%
   - ✅ Response time within acceptable threshold
   - ✅ No customer complaints

5. **If Issues Occur**
   - Immediately set `VQL_SINGLE_RECORD_RETRIEVAL=false`
   - Investigate logs and Connectra service
   - Fix issues before proceeding

### Phase 2: Company Contacts

**Duration:** 24-48 hours  
**Feature Flag:** `VQL_COMPANY_CONTACTS`

**Endpoints Affected:**
- `GET /api/v1/companies/company/{company_uuid}/contacts/`
- `GET /api/v1/companies/company/{company_uuid}/contacts/count/`
- `GET /api/v1/companies/company/{company_uuid}/contacts/{attribute}/`

**Steps:**

1. **Enable Feature Flag**
   ```bash
   VQL_COMPANY_CONTACTS=true
   # Keep VQL_SINGLE_RECORD_RETRIEVAL=true
   ```

2. **Deploy and Monitor**
   - Deploy backend with feature flag enabled
   - Monitor for first 4 hours:
     - Company contacts listing performance
     - Filter conversion accuracy
     - Count accuracy
   - Test with various filter combinations

3. **Validation Checks**
   - [ ] Company contacts listing works correctly
   - [ ] Filters are applied correctly
   - [ ] Counts match direct query results
   - [ ] Attribute endpoints work correctly
   - [ ] Pagination works correctly

4. **Success Criteria**
   - ✅ Filter conversion accuracy 100%
   - ✅ Count accuracy matches direct queries
   - ✅ Response time acceptable
   - ✅ No data inconsistencies

### Phase 3: Exports

**Duration:** 48-72 hours  
**Feature Flag:** `VQL_EXPORTS`

**Endpoints Affected:**
- Background task: `process_contact_export()`
- Background task: `process_company_export()`
- Background task: `process_email_export()`

**Steps:**

1. **Enable Feature Flag**
   ```bash
   VQL_EXPORTS=true
   # Keep previous flags enabled
   ```

2. **Deploy and Monitor**
   - Deploy backend with feature flag enabled
   - Monitor for first 24 hours:
     - Export success rates
     - Export processing times
     - Memory usage for large exports
     - Batch query performance

3. **Validation Checks**
   - [ ] Small exports (< 100 records) work correctly
   - [ ] Medium exports (100-1000 records) work correctly
   - [ ] Large exports (1000+ records) work correctly
   - [ ] Export CSV data matches direct query results
   - [ ] Progress tracking works correctly

4. **Success Criteria**
   - ✅ Export success rate > 99%
   - ✅ Export processing time acceptable
   - ✅ Memory usage within limits
   - ✅ No data loss in exports

### Phase 4: LinkedIn Search

**Duration:** 24-48 hours  
**Feature Flag:** `VQL_LINKEDIN_SEARCH`

**Endpoints Affected:**
- `POST /api/v2/linkedin/`

**Steps:**

1. **Enable Feature Flag**
   ```bash
   VQL_LINKEDIN_SEARCH=true
   # Keep all previous flags enabled
   ```

2. **Deploy and Monitor**
   - Deploy backend with feature flag enabled
   - Monitor for first 4 hours:
     - LinkedIn URL search accuracy
     - Search result completeness
     - Response times

3. **Validation Checks**
   - [ ] LinkedIn URL search finds correct contacts
   - [ ] LinkedIn URL search finds correct companies
   - [ ] Results match direct query results
   - [ ] Parallel/sequential execution works

4. **Success Criteria**
   - ✅ Search accuracy 100%
   - ✅ Results match direct queries
   - ✅ Response time acceptable

### Phase 5: Full Migration Complete

**Duration:** Ongoing monitoring

After all phases are stable:

1. **Monitor for 1-2 weeks**
   - Track all metrics
   - Monitor for edge cases
   - Collect performance data

2. **Optimize Based on Data**
   - Tune batch sizes
   - Optimize queries
   - Adjust timeouts

3. **Consider Removing Feature Flags**
   - After 2+ weeks of stable operation
   - Keep fallback mechanism
   - Document final configuration

## Monitoring Dashboard

### Key Metrics to Track

1. **VQL Success Rate**
   - Target: > 95%
   - Alert if: < 90%

2. **Fallback Rate**
   - Target: < 5%
   - Alert if: > 10%

3. **Response Time**
   - Target: ≤ 20% slower than direct queries
   - Alert if: > 50% slower

4. **Error Rate**
   - Target: < 1%
   - Alert if: > 5%

5. **Connectra Service Availability**
   - Target: > 99.9%
   - Alert if: < 99%

### Monitoring Queries

**VQL Query Success Rate:**
```sql
-- Count VQL successes vs failures from logs
SELECT 
  COUNT(*) FILTER (WHERE message LIKE '%VQL query failed%') as failures,
  COUNT(*) FILTER (WHERE message LIKE '%VQL query succeeded%') as successes
FROM logs
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

**Fallback Rate:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE message LIKE '%falling back to repository%') as fallbacks,
  COUNT(*) as total_queries
FROM logs
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

## Rollback Procedures

### Immediate Rollback (All Endpoints)

1. **Disable All Feature Flags**
   ```bash
   VQL_SINGLE_RECORD_RETRIEVAL=false
   VQL_COMPANY_CONTACTS=false
   VQL_EXPORTS=false
   VQL_LINKEDIN_SEARCH=false
   CONNECTRA_ENABLED=false
   ```

2. **Restart Backend Service**
   ```bash
   systemctl restart contact360-backend
   # or
   docker-compose restart backend
   ```

3. **Verify Rollback**
   - All endpoints should use direct repository queries
   - Check logs to confirm no VQL queries
   - Monitor for stability

### Selective Rollback (Single Endpoint)

1. **Disable Specific Feature Flag**
   ```bash
   # Example: Disable only company contacts
   VQL_COMPANY_CONTACTS=false
   ```

2. **Restart Backend Service**

3. **Verify Specific Endpoint**
   - Only affected endpoint should use repository
   - Other endpoints continue using VQL

## Troubleshooting

### High Fallback Rate

**Symptoms:** > 10% of queries falling back to repository

**Possible Causes:**
- Connectra service unavailable
- Elasticsearch sync lag
- VQL query syntax errors
- Network connectivity issues

**Solutions:**
1. Check Connectra service health
2. Verify Elasticsearch sync status
3. Review VQL query logs
4. Check network connectivity

### Slow Response Times

**Symptoms:** VQL queries significantly slower than direct queries

**Possible Causes:**
- Elasticsearch performance issues
- Network latency to Connectra
- Large result sets
- Complex filter queries

**Solutions:**
1. Optimize Elasticsearch indices
2. Check network latency
3. Review query complexity
4. Consider increasing batch sizes

### Data Inconsistencies

**Symptoms:** VQL results don't match direct query results

**Possible Causes:**
- Elasticsearch sync lag
- Missing data in Elasticsearch
- Filter conversion errors
- Field mapping issues

**Solutions:**
1. Re-sync Elasticsearch data
2. Review filter converter logic
3. Verify field mappings
4. Check Connectra field definitions

## Success Metrics

After full rollout, track these metrics for 2 weeks:

- **Overall VQL Success Rate:** > 95%
- **Average Fallback Rate:** < 5%
- **Response Time Improvement:** 20-50% faster
- **Error Rate:** < 1%
- **Customer Satisfaction:** No complaints related to VQL

## Post-Rollout

After successful rollout:

1. **Document Learnings**
   - Performance improvements
   - Issues encountered
   - Solutions applied

2. **Optimize Configuration**
   - Tune batch sizes
   - Adjust timeouts
   - Optimize queries

3. **Plan Next Steps**
   - Additional endpoint migrations
   - Performance optimizations
   - Feature enhancements

## Support Contacts

- **Technical Lead:** [Name/Email]
- **DevOps Team:** [Name/Email]
- **On-Call Engineer:** [Name/Email]

## Related Documentation

- [VQL Migration Implementation](VQL_MIGRATION_IMPLEMENTATION.md)
- [VQL Deployment Checklist](VQL_DEPLOYMENT_CHECKLIST.md)
- [VQL Integration README](../VQL_INTEGRATION_README.md)

