"""
Test cases for Apollo contacts pagination functionality.

This module tests the pagination behavior of the /api/v2/apollo/contacts endpoint,
including proper offset handling, cursor pagination, and next/previous links.
"""

from urllib.parse import parse_qs, urlparse

import pytest

from app.tests.factories import create_company, create_contact
from app.utils.cursor import encode_offset_cursor


@pytest.mark.asyncio
async def test_apollo_contacts_pagination_basic(async_client, db_session):
    """Test basic pagination with limit and offset parameters."""
    # Create 10 test contacts
    for i in range(10):
        await create_contact(
            db_session,
            first_name=f"Contact {i}",
            email=f"contact{i}@example.com",
            title=f"Title {i}",
        )
    
    await db_session.commit()
    
    # Test data: Apollo URL (doesn't matter for now, just needs to be valid)
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # First request: Get first 3 contacts
    response_page1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0}
    )
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    
    # Verify first page results
    assert len(data_page1["results"]) == 3
    assert data_page1["next"] is not None
    assert data_page1["previous"] is None
    
    # Get UUIDs from first page
    page1_ids = [contact["uuid"] for contact in data_page1["results"]]
    
    # Second request: Get next 3 contacts using offset
    response_page2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 3}
    )
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    
    # Verify second page results
    assert len(data_page2["results"]) == 3
    assert data_page2["next"] is not None
    assert data_page2["previous"] is not None
    
    # Get UUIDs from second page
    page2_ids = [contact["uuid"] for contact in data_page2["results"]]
    
    # Critical assertion: Pages should have different contacts
    assert set(page1_ids).isdisjoint(set(page2_ids)), (
        f"Pagination bug detected: Same contacts returned on different pages!\n"
        f"Page 1 IDs: {page1_ids}\n"
        f"Page 2 IDs: {page2_ids}\n"
        f"Overlap: {set(page1_ids) & set(page2_ids)}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_pagination_using_next_url(async_client, db_session):
    """Test pagination by following the 'next' URL - this should expose the bug."""
    # Create 10 test contacts
    contacts_created = []
    for i in range(10):
        contact = await create_contact(
            db_session,
            first_name=f"Person {i}",
            email=f"person{i}@test.com",
            title=f"Role {i}",
        )
        contacts_created.append(contact)
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # First request
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    assert len(data1["results"]) == 3
    assert data1["next"] is not None, "Next link should be present"
    
    page1_results = data1["results"]
    page1_uuids = [c["uuid"] for c in page1_results]
    
    # Extract next URL
    next_url = data1["next"]
    
    # Parse the next URL to extract query parameters
    parsed_next = urlparse(next_url)
    next_params = parse_qs(parsed_next.query)
    
    # Convert query params to format expected by client
    request_params = {}
    if "limit" in next_params:
        request_params["limit"] = int(next_params["limit"][0])
    if "offset" in next_params:
        request_params["offset"] = int(next_params["offset"][0])
    if "cursor" in next_params:
        request_params["cursor"] = next_params["cursor"][0]
    
    # Follow the next URL
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params=request_params
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    page2_results = data2["results"]
    page2_uuids = [c["uuid"] for c in page2_results]
    
    # Critical assertions
    assert len(page2_results) > 0, "Second page should have results"
    
    # Check for duplicate data (the bug we're trying to catch)
    overlap_uuids = set(page1_uuids) & set(page2_uuids)
    
    assert len(overlap_uuids) == 0, (
        f"BUG DETECTED: Same contact UUIDs returned when following next URL!\n"
        f"Page 1 UUIDs: {page1_uuids}\n"
        f"Page 2 UUIDs: {page2_uuids}\n"
        f"Overlapping UUIDs: {overlap_uuids}\n"
        f"Page 1 Names: {[c['first_name'] for c in page1_results]}\n"
        f"Page 2 Names: {[c['first_name'] for c in page2_results]}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_cursor_pagination(async_client, db_session):
    """Test cursor-based pagination for Apollo contacts."""
    # Create 12 test contacts
    for i in range(12):
        await create_contact(
            db_session,
            first_name=f"Cursor Test {i}",
            email=f"cursor{i}@example.com",
            title="Manager",
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # First page with cursor
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 4, "cursor": encode_offset_cursor(0)}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    assert len(data1["results"]) == 4
    page1_uuids = [c["uuid"] for c in data1["results"]]
    
    # Second page with cursor (offset 4)
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 4, "cursor": encode_offset_cursor(4)}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert len(data2["results"]) == 4
    page2_uuids = [c["uuid"] for c in data2["results"]]
    
    # Verify no overlap
    assert set(page1_uuids).isdisjoint(set(page2_uuids)), (
        f"Cursor pagination bug: Same contacts on different pages\n"
        f"Page 1: {page1_uuids}\n"
        f"Page 2: {page2_uuids}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_pagination_with_filters(async_client, db_session):
    """Test pagination with Apollo filters applied."""
    # Create contacts with different titles
    for i in range(8):
        await create_contact(
            db_session,
            first_name=f"CEO {i}",
            email=f"ceo{i}@example.com",
            title="CEO",
        )
    
    for i in range(5):
        await create_contact(
            db_session,
            first_name=f"Manager {i}",
            email=f"manager{i}@example.com",
            title="Manager",
        )
    
    await db_session.commit()
    
    # Apollo URL with title filter
    apollo_url = "https://app.apollo.io/#/people?personTitles[]=CEO&page=1"
    
    # First page
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Should only get CEOs
    page1_titles = [c["title"] for c in data1["results"]]
    assert all("CEO" in title for title in page1_titles), "Should only get CEOs"
    page1_uuids = [c["uuid"] for c in data1["results"]]
    
    # Second page
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 3}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    page2_titles = [c["title"] for c in data2["results"]]
    assert all("CEO" in title for title in page2_titles), "Should only get CEOs"
    page2_uuids = [c["uuid"] for c in data2["results"]]
    
    # Verify pagination works with filters
    assert set(page1_uuids).isdisjoint(set(page2_uuids)), (
        f"Pagination with filters broken: Same contacts on different pages\n"
        f"Page 1: {page1_uuids}\n"
        f"Page 2: {page2_uuids}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_pagination_consistency(async_client, db_session):
    """Test that multiple requests to the same page return consistent results."""
    # Create 6 test contacts
    for i in range(6):
        await create_contact(
            db_session,
            first_name=f"Consistent {i}",
            email=f"consistent{i}@example.com",
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # Request the same page twice
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Same page should return same results
    uuids1 = [c["uuid"] for c in data1["results"]]
    uuids2 = [c["uuid"] for c in data2["results"]]
    
    assert uuids1 == uuids2, (
        f"Same page request returned different results!\n"
        f"First request: {uuids1}\n"
        f"Second request: {uuids2}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_pagination_last_page(async_client, db_session):
    """Test that the last page doesn't have a 'next' link."""
    # Create exactly 7 contacts
    for i in range(7):
        await create_contact(
            db_session,
            first_name=f"Last Page {i}",
            email=f"lastpage{i}@example.com",
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # Get page with 5 results (2 left for next page)
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 5, "offset": 0}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    assert len(data1["results"]) == 5
    assert data1["next"] is not None, "Should have next link when more results exist"
    
    # Get last page (only 2 results)
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 5, "offset": 5}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert len(data2["results"]) == 2
    assert data2["next"] is None, "Last page should not have next link"
    assert data2["previous"] is not None, "Last page should have previous link"


@pytest.mark.asyncio
async def test_apollo_contacts_empty_results_pagination(async_client, db_session):
    """Test pagination behavior with no results."""
    apollo_url = "https://app.apollo.io/#/people?personTitles[]=NonexistentTitle&page=1"
    
    response = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 10, "offset": 0}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["results"] == []
    assert data["next"] is None
    assert data["previous"] is None


@pytest.mark.asyncio
async def test_apollo_contacts_offset_beyond_results(async_client, db_session):
    """Test pagination with offset beyond available results."""
    # Create 5 contacts
    for i in range(5):
        await create_contact(
            db_session,
            first_name=f"Contact {i}",
            email=f"contact{i}@example.com",
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # Request with offset beyond available results
    response = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 10, "offset": 100}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["results"] == []
    assert data["next"] is None
    assert data["previous"] is not None  # Should still have previous since offset > 0


@pytest.mark.asyncio
async def test_apollo_contacts_view_simple_pagination(async_client, db_session):
    """Test pagination with view=simple parameter."""
    # Create 6 contacts
    company = await create_company(db_session, name="Test Company")
    for i in range(6):
        await create_contact(
            db_session,
            company=company,
            first_name=f"Simple {i}",
            email=f"simple{i}@example.com",
            with_metadata=True,
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    # First page with simple view
    response1 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 0, "view": "simple"}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    assert len(data1["results"]) == 3
    page1_uuids = [c["uuid"] for c in data1["results"]]
    
    # Verify simple view structure
    first_result = data1["results"][0]
    expected_keys = {
        "id", "uuid", "first_name", "last_name", "title",
        "location", "company_name", "person_linkedin_url", "company_domain"
    }
    # Note: The actual response might not have "id" field, only "uuid"
    actual_keys = set(first_result.keys())
    assert "uuid" in actual_keys, "uuid field should be present"
    
    # Second page with simple view
    response2 = await async_client.post(
        "/api/v2/apollo/contacts",
        json={"url": apollo_url},
        params={"limit": 3, "offset": 3, "view": "simple"}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert len(data2["results"]) == 3
    page2_uuids = [c["uuid"] for c in data2["results"]]
    
    # Verify no overlap in simple view pagination
    assert set(page1_uuids).isdisjoint(set(page2_uuids)), (
        f"Simple view pagination broken\n"
        f"Page 1: {page1_uuids}\n"
        f"Page 2: {page2_uuids}"
    )

