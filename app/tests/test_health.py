import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    settings = get_settings()

    response = await async_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }
