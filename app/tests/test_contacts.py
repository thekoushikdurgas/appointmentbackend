import pytest


@pytest.mark.asyncio
async def test_contacts_list_empty(async_client):
    response = await async_client.get("/api/v1/contacts/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["next"] is None
    assert payload["previous"] is None


@pytest.mark.asyncio
async def test_contacts_count_empty(async_client):
    response = await async_client.get("/api/v1/contacts/count/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0

