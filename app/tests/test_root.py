import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_api_root_metadata(async_client):
    settings = get_settings()

    response = await async_client.get("/api/v1/")

    assert response.status_code == 200
    payload = response.json()
    expected = {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": settings.DOCS_URL or "/docs",
    }

    assert payload == expected
    assert set(payload.keys()) == {"name", "version", "docs"}

