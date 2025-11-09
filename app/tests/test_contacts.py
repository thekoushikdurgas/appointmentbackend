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


@pytest.mark.asyncio
async def test_create_contact_minimal(async_client):
    response = await async_client.post("/api/v1/contacts/", json={})
    assert response.status_code == 201
    payload = response.json()
    assert isinstance(payload["id"], int)
    assert payload["seniority"] == "_"
    assert payload["first_name"] is None
    assert payload["departments"] is None

    list_response = await async_client.get("/api/v1/contacts/")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload["results"]) == 1
    assert list_payload["results"][0]["id"] == payload["id"]


@pytest.mark.asyncio
async def test_create_contact_with_optional_fields(async_client):
    request_body = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "title": "Director of Sales",
        "departments": ["Sales", "Marketing"],
        "mobile_phone": "+1234567890",
        "email_status": "valid",
        "text_search": "Austin, TX",
        "seniority": "Director",
    }
    response = await async_client.post("/api/v1/contacts/", json=request_body)
    assert response.status_code == 201
    payload = response.json()
    assert payload["first_name"] == request_body["first_name"]
    assert payload["last_name"] == request_body["last_name"]
    assert payload["email"] == request_body["email"]
    assert payload["title"] == request_body["title"]
    assert payload["mobile_phone"] == request_body["mobile_phone"]
    assert payload["email_status"] == request_body["email_status"]
    assert payload["seniority"] == request_body["seniority"]
    assert payload["departments"] == "Sales, Marketing"

    detail_response = await async_client.get(f"/api/v1/contacts/{payload['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["first_name"] == request_body["first_name"]
    assert detail["departments"] == "Sales, Marketing"
