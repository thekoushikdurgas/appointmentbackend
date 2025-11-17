"""
Test cases to identify count/pagination data mismatch in Apollo contacts.

This module tests for inconsistencies between:
1. The count reported by /apollo/contacts/count
2. The actual data returned by /apollo/contacts pagination
"""

import pytest
from app.tests.factories import create_company, create_contact


@pytest.mark.asyncio
async def test_apollo_contacts_count_matches_pagination(async_client, db_session):
    """Test that count endpoint matches the actual number of contacts in pagination."""
    # Create 15 test contacts
    contacts_created = []
    for i in range(15):
        contact = await create_contact(
            db_session,
            first_name=f"Test {i}",
            email=f"test{i}@example.com",
            title="Engineer",
        )
        contacts_created.append(contact)
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    print("\n" + "="*80)
    print("TESTING COUNT vs PAGINATION MISMATCH")
    print("="*80)
    
    # Step 1: Get count
    print("\n--- Step 1: Get Count ---")
    count_response = await async_client.post(
        "/api/v2/apollo/contacts/count",
        json={"url": apollo_url}
    )
    assert count_response.status_code == 200
    count_data = count_response.json()
    total_count = count_data["count"]
    print(f"Count endpoint reports: {total_count} contacts")
    
    # Step 2: Paginate through ALL contacts
    print("\n--- Step 2: Paginate Through All Contacts ---")
    all_contacts = []
    offset = 0
    page_size = 5
    page_num = 1
    
    while True:
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        print(f"Page {page_num} (offset={offset}): Got {len(results)} contacts")
        
        if not results:
            print("No more results, stopping pagination")
            break
        
        # Collect UUIDs
        for contact in results:
            all_contacts.append(contact["uuid"])
        
        # Check if we should continue
        if data["next"] is None or len(results) < page_size:
            print("Last page reached")
            break
        
        offset += page_size
        page_num += 1
        
        # Safety check to prevent infinite loop
        if page_num > 20:
            print("WARNING: Too many pages, stopping")
            break
    
    # Step 3: Compare
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    print(f"Count endpoint says: {total_count} contacts")
    print(f"Pagination returned: {len(all_contacts)} contacts")
    print(f"Expected (created): {len(contacts_created)} contacts")
    
    # Check for duplicates
    unique_contacts = set(all_contacts)
    if len(unique_contacts) != len(all_contacts):
        print(f"\nWARNING: Found {len(all_contacts) - len(unique_contacts)} duplicate contacts in pagination!")
        duplicates = [uuid for uuid in all_contacts if all_contacts.count(uuid) > 1]
        print(f"Duplicate UUIDs: {set(duplicates)}")
    
    print("="*80)
    
    # Assertions
    assert total_count == len(contacts_created), (
        f"Count mismatch: Count endpoint says {total_count} but we created {len(contacts_created)} contacts"
    )
    
    assert len(all_contacts) == len(contacts_created), (
        f"Pagination mismatch: Pagination returned {len(all_contacts)} contacts but we created {len(contacts_created)}"
    )
    
    assert len(unique_contacts) == len(all_contacts), (
        f"Duplicate contacts in pagination: {len(all_contacts) - len(unique_contacts)} duplicates found"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_with_filters_count_matches(async_client, db_session):
    """Test count matches pagination when filters are applied."""
    # Create contacts with specific titles
    for i in range(10):
        await create_contact(
            db_session,
            first_name=f"CEO {i}",
            email=f"ceo{i}@example.com",
            title="CEO",
        )
    
    for i in range(7):
        await create_contact(
            db_session,
            first_name=f"CTO {i}",
            email=f"cto{i}@example.com",
            title="CTO",
        )
    
    await db_session.commit()
    
    # Apollo URL with title filter
    apollo_url = "https://app.apollo.io/#/people?personTitles[]=CEO&page=1"
    
    print("\n" + "="*80)
    print("TESTING COUNT vs PAGINATION WITH FILTERS")
    print("="*80)
    
    # Get count
    count_response = await async_client.post(
        "/api/v2/apollo/contacts/count",
        json={"url": apollo_url}
    )
    assert count_response.status_code == 200
    ceo_count = count_response.json()["count"]
    print(f"Count says: {ceo_count} CEOs")
    
    # Paginate through all CEOs
    all_ceos = []
    offset = 0
    page_size = 4
    
    while offset < 100:  # Safety limit
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        if not results:
            break
        
        for contact in results:
            all_ceos.append(contact["uuid"])
            # Verify they're actually CEOs
            assert "CEO" in contact["title"], f"Expected CEO but got {contact['title']}"
        
        if data["next"] is None or len(results) < page_size:
            break
        
        offset += page_size
    
    print(f"Pagination returned: {len(all_ceos)} CEOs")
    print("="*80)
    
    assert ceo_count == 10, f"Expected 10 CEOs, count says {ceo_count}"
    assert len(all_ceos) == 10, f"Expected 10 CEOs from pagination, got {len(all_ceos)}"
    assert ceo_count == len(all_ceos), (
        f"Count/pagination mismatch with filters: count={ceo_count}, pagination={len(all_ceos)}"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_uuids_endpoint_matches_list(async_client, db_session):
    """Test that /count/uuids returns the same contacts as /contacts pagination."""
    # Create test contacts
    for i in range(12):
        await create_contact(
            db_session,
            first_name=f"Contact {i}",
            email=f"contact{i}@example.com",
        )
    
    await db_session.commit()
    
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    print("\n" + "="*80)
    print("TESTING /count/uuids vs /contacts CONSISTENCY")
    print("="*80)
    
    # Get UUIDs from /count/uuids endpoint
    uuids_response = await async_client.post(
        "/api/v2/apollo/contacts/count/uuids",
        json={"url": apollo_url}
    )
    assert uuids_response.status_code == 200
    uuids_data = uuids_response.json()
    uuids_from_endpoint = set(uuids_data["uuids"])
    
    print(f"/count/uuids returned: {len(uuids_from_endpoint)} UUIDs")
    
    # Get UUIDs from pagination
    all_uuids_from_pagination = []
    offset = 0
    page_size = 5
    
    while offset < 100:  # Safety limit
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        if not results:
            break
        
        for contact in results:
            all_uuids_from_pagination.append(contact["uuid"])
        
        if data["next"] is None or len(results) < page_size:
            break
        
        offset += page_size
    
    uuids_from_pagination = set(all_uuids_from_pagination)
    print(f"/contacts pagination returned: {len(uuids_from_pagination)} UUIDs")
    
    # Compare
    only_in_uuids_endpoint = uuids_from_endpoint - uuids_from_pagination
    only_in_pagination = uuids_from_pagination - uuids_from_endpoint
    
    if only_in_uuids_endpoint:
        print(f"\nWARNING: {len(only_in_uuids_endpoint)} UUIDs only in /count/uuids:")
        print(f"  {only_in_uuids_endpoint}")
    
    if only_in_pagination:
        print(f"\nWARNING: {len(only_in_pagination)} UUIDs only in pagination:")
        print(f"  {only_in_pagination}")
    
    print("="*80)
    
    assert uuids_from_endpoint == uuids_from_pagination, (
        f"Mismatch between /count/uuids and /contacts:\n"
        f"  Only in /count/uuids: {len(only_in_uuids_endpoint)} UUIDs\n"
        f"  Only in pagination: {len(only_in_pagination)} UUIDs"
    )


@pytest.mark.asyncio
async def test_apollo_contacts_ordering_consistency(async_client, db_session):
    """Test that pagination returns contacts in consistent order."""
    # Create contacts with specific ordering
    for i in range(10):
        await create_contact(
            db_session,
            first_name=f"Person {i:02d}",  # Zero-padded for consistent sorting
            email=f"person{i:02d}@example.com",
        )
    
    await db_session.commit()
    
    # Use default Apollo URL without sorting - our system will use default ordering
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    print("\n" + "="*80)
    print("TESTING ORDERING CONSISTENCY")
    print("="*80)
    
    # Get all contacts through pagination
    all_contacts = []
    offset = 0
    page_size = 3
    
    while offset < 100:
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        assert response.status_code == 200
        data = response.json()
        
        results = data["results"]
        if not results:
            break
        
        for contact in results:
            all_contacts.append({
                "uuid": contact["uuid"],
                "name": contact["first_name"],
                "email": contact["email"]
            })
        
        print(f"Page at offset={offset}: {[c['first_name'] for c in results]}")
        
        if data["next"] is None or len(results) < page_size:
            break
        
        offset += page_size
    
    print(f"\nTotal contacts retrieved: {len(all_contacts)}")
    print(f"All names in order: {[c['name'] for c in all_contacts]}")
    
    # Check for duplicates
    uuids = [c["uuid"] for c in all_contacts]
    unique_uuids = set(uuids)
    
    if len(unique_uuids) != len(uuids):
        duplicates = [uuid for uuid in uuids if uuids.count(uuid) > 1]
        print(f"\nERROR: Found {len(uuids) - len(unique_uuids)} duplicate contacts!")
        for dup_uuid in set(duplicates):
            dup_contacts = [c for c in all_contacts if c["uuid"] == dup_uuid]
            print(f"  Duplicate UUID {dup_uuid}: appears {len(dup_contacts)} times")
    
    print("="*80)
    
    assert len(unique_uuids) == len(uuids), (
        f"Duplicate contacts in ordered pagination: {len(uuids) - len(unique_uuids)} duplicates"
    )
    
    assert len(all_contacts) == 10, (
        f"Expected 10 contacts, got {len(all_contacts)}"
    )

