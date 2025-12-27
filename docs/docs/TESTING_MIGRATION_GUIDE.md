# Testing Guide for Connectra Write Migration

## Overview

This guide explains how to update tests after the Connectra write migration. All tests that interact with contacts or companies need to be updated to mock the `ConnectraClient` instead of repository classes.

## Changes Required

### Before Migration

Tests mocked repository methods:

```python
@pytest.mark.asyncio
async def test_create_contact(mocker):
    # Old: Mock repository
    mock_repo = mocker.Mock()
    mock_repo.create_contact.return_value = Contact(uuid="test-uuid", ...)
    
    service = ContactsService(repository=mock_repo)
    result = await service.create_contact(session, contact_data)
    
    assert result.uuid == "test-uuid"
    mock_repo.create_contact.assert_called_once()
```

### After Migration

Tests should mock `ConnectraClient`:

```python
@pytest.mark.asyncio
async def test_create_contact(mocker):
    # New: Mock ConnectraClient
    mock_client = mocker.patch('app.clients.connectra_client.ConnectraClient')
    mock_client.return_value.__aenter__.return_value.create_contact = AsyncMock(
        return_value={"data": {"uuid": "test-uuid", "first_name": "John", ...}, "success": true}
    )
    
    service = ContactsService()
    result = await service.create_contact(session, contact_data)
    
    assert result.uuid == "test-uuid"
    mock_client.return_value.__aenter__.return_value.create_contact.assert_called_once()
```

## Files Requiring Updates

### High Priority

1. **backend/app/tests/test_contacts.py**
   - Update all contact creation/update tests
   - Mock `ConnectraClient` instead of `ContactRepository`
   - Update assertion expectations (Connectra returns dict, not ORM model)

2. **backend/app/tests/test_companies.py** (if exists)
   - Update all company CRUD tests
   - Mock `ConnectraClient` instead of `CompanyRepository`

3. **backend/app/tests/test_sales_navigator.py** (if exists)
   - Update bulk operation tests
   - Mock `ConnectraClient.bulk_upsert_contacts()` and `bulk_upsert_companies()`

### Medium Priority

4. **backend/app/tests/test_api_contacts.py** (if exists)
   - API endpoint tests should still work if they test through the service layer
   - May need to update mock setup

5. **backend/app/tests/integration/** (if exists)
   - Integration tests may need real Connectra instance
   - Consider using VCR.py to record/replay Connectra API responses

## Test Patterns

### 1. Mocking ConnectraClient Context Manager

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_connectra_client(mocker):
    """Fixture to mock ConnectraClient for all tests."""
    mock_client = mocker.patch('app.clients.connectra_client.ConnectraClient')
    mock_instance = AsyncMock()
    mock_client.return_value.__aenter__.return_value = mock_instance
    mock_client.return_value.__aexit__.return_value = None
    return mock_instance

@pytest.mark.asyncio
async def test_create_contact(mock_connectra_client):
    mock_connectra_client.create_contact.return_value = {
        "data": {"uuid": "test-123", "first_name": "John"},
        "success": True
    }
    
    service = ContactsService()
    # ... rest of test
```

### 2. Testing Error Handling

```python
@pytest.mark.asyncio
async def test_create_contact_api_error(mock_connectra_client):
    # Simulate Connectra API error
    mock_connectra_client.create_contact.side_effect = Exception("API unavailable")
    
    service = ContactsService()
    
    with pytest.raises(Exception, match="API unavailable"):
        await service.create_contact(session, contact_data)
```

### 3. Testing Bulk Operations

```python
@pytest.mark.asyncio
async def test_bulk_upsert_contacts(mock_connectra_client):
    mock_connectra_client.bulk_upsert_contacts.return_value = {
        "data": {
            "created": 10,
            "updated": 5,
            "total": 15
        },
        "success": True
    }
    
    service = SalesNavigatorService()
    result = await service.save_profiles_to_database(session, profiles)
    
    assert result['summary']['contacts_created'] == 10
    assert result['summary']['contacts_updated'] == 5
```

## Integration Testing

For integration tests that need real Connectra:

### Option 1: Docker Compose Test Environment

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
  
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
  
  connectra:
    build: ../connectra
    depends_on:
      - postgres
      - elasticsearch
    environment:
      DATABASE_URL: postgresql://test_user:test_pass@postgres:5432/test_db
      ELASTICSEARCH_URL: http://elasticsearch:9200
```

Run integration tests:
```bash
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/
docker-compose -f docker-compose.test.yml down
```

### Option 2: VCR.py for Recording API Responses

```python
import vcr
import pytest

@pytest.mark.vcr()
async def test_create_contact_integration():
    """This test records Connectra API responses on first run."""
    service = ContactsService()
    result = await service.create_contact(session, contact_data)
    assert result.uuid
```

Configure VCR in `conftest.py`:
```python
import vcr

@pytest.fixture(scope='module')
def vcr_config():
    return {
        'filter_headers': ['X-API-Key'],  # Don't record API keys
        'record_mode': 'once',  # Record once, then replay
        'match_on': ['uri', 'method', 'body'],
    }
```

## Running Tests

### Unit Tests (with mocks)

```bash
pytest tests/unit/ -v
```

### Integration Tests (requires Connectra)

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Wait for services
sleep 10

# Run integration tests
pytest tests/integration/ -v

# Cleanup
docker-compose -f docker-compose.test.yml down
```

### Coverage Report

```bash
pytest --cov=app --cov-report=html --cov-report=term
```

## Common Issues

### Issue 1: AsyncMock not found

**Solution:** Upgrade to Python 3.8+ or use `asynctest` library:
```bash
pip install asynctest
```

### Issue 2: Mock not being used

**Solution:** Ensure patch path is correct:
```python
# Correct: Patch where it's imported
mocker.patch('app.services.contacts_service.ConnectraClient')

# Not correct: Patching the definition location
mocker.patch('app.clients.connectra_client.ConnectraClient')
```

### Issue 3: Context manager not working

**Solution:** Mock both `__aenter__` and `__aexit__`:
```python
mock_client = mocker.patch('app.clients.connectra_client.ConnectraClient')
mock_instance = AsyncMock()
mock_client.return_value.__aenter__.return_value = mock_instance
mock_client.return_value.__aexit__.return_value = None
```

## Checklist

- [ ] Update `test_contacts.py` to mock ConnectraClient
- [ ] Update `test_companies.py` to mock ConnectraClient
- [ ] Update `test_sales_navigator.py` for bulk operations
- [ ] Create integration test suite for Connectra
- [ ] Set up Docker Compose for integration testing
- [ ] Add VCR.py for recording API responses
- [ ] Update CI/CD pipeline to run tests
- [ ] Document test coverage requirements
- [ ] Create test data fixtures for Connectra responses

## Resources

- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [VCR.py Documentation](https://vcrpy.readthedocs.io/)
- [unittest.mock AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)

---

**Note:** Tests are not included in the initial migration due to time constraints. This guide provides the framework for updating tests when resources are available.

