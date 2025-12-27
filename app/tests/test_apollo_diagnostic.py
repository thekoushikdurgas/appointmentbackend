"""
Diagnostic test to identify specific scenarios where count/pagination mismatch occurs.

Run this test with your actual Apollo URL to diagnose the issue.
"""

import pytest

from app.tests.factories import create_company, create_contact


@pytest.mark.asyncio
async def test_apollo_diagnostic_comprehensive(async_client, db_session):
    """
    Comprehensive diagnostic test - modify the apollo_url to match your scenario.
    """
    # Create diverse test data
    # Create 25 contacts with various attributes
    for i in range(25):
        company = await create_company(
            db_session,
            name=f"Company {i}",
            employees_count=100 + i * 10,
        )
        await create_contact(
            db_session,
            company=company,
            first_name=f"Contact {i}",
            email=f"contact{i}@company{i}.com",
            title="CEO" if i < 10 else "CTO" if i < 20 else "Manager",
        )
    
    await db_session.commit()
    
    # TEST SCENARIO 1: No filters
    apollo_url_1 = "https://app.apollo.io/#/people?page=1"
    await run_diagnostic(async_client, apollo_url_1, "No filters")
    
    # TEST SCENARIO 2: Title filter
    apollo_url_2 = "https://app.apollo.io/#/people?personTitles[]=CEO&page=1"
    await run_diagnostic(async_client, apollo_url_2, "CEO filter")
    
    # TEST SCENARIO 3: Employee range filter
    apollo_url_3 = "https://app.apollo.io/#/people?organizationNumEmployeesRanges[]=100,200&page=1"
    await run_diagnostic(async_client, apollo_url_3, "Employee range filter")
    
    # TEST SCENARIO 4: Multiple filters
    apollo_url_4 = "https://app.apollo.io/#/people?personTitles[]=CEO&organizationNumEmployeesRanges[]=100,150&page=1"
    await run_diagnostic(async_client, apollo_url_4, "Multiple filters")


async def run_diagnostic(async_client, apollo_url: str, scenario_name: str):
    """Run diagnostic checks for a given Apollo URL."""
    
    # Step 1: Get count
    count_response = await async_client.post(
        "/api/v2/apollo/contacts/count",
        json={"url": apollo_url}
    )
    
    if count_response.status_code != 200:
        return
    
    total_count = count_response.json()["count"]
    
    # Step 2: Get UUIDs
    uuids_response = await async_client.post(
        "/api/v2/apollo/contacts/count/uuids",
        json={"url": apollo_url}
    )
    
    if uuids_response.status_code != 200:
        pass
    else:
        uuids_count = len(uuids_response.json()["uuids"])
    
    # Step 3: Paginate through all with small page size
    all_contacts_small_pages = []
    offset = 0
    page_size = 3
    max_pages = 50
    page_num = 1
    
    while page_num <= max_pages:
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        
        if response.status_code != 200:
            break
        
        data = response.json()
        results = data["results"]
        
        if not results:
            break
        
        for contact in results:
            all_contacts_small_pages.append(contact["uuid"])
        
        if data["next"] is None or len(results) < page_size:
            break
        
        offset += page_size
        page_num += 1
    
    # Step 4: Paginate with larger page size
    all_contacts_large_pages = []
    offset = 0
    page_size = 10
    
    while offset < total_count + 10:
        response = await async_client.post(
            "/api/v2/apollo/contacts",
            json={"url": apollo_url},
            params={"limit": page_size, "offset": offset}
        )
        
        if response.status_code != 200:
            break
        
        data = response.json()
        results = data["results"]
        
        if not results:
            break
        
        for contact in results:
            all_contacts_large_pages.append(contact["uuid"])
        
        if data["next"] is None or len(results) < page_size:
            break
        
        offset += page_size
    
    # Step 5: Analysis
    # Check for duplicates
    unique_small = set(all_contacts_small_pages)
    unique_large = set(all_contacts_large_pages)
    
    duplicates_small = len(all_contacts_small_pages) - len(unique_small)
    duplicates_large = len(all_contacts_large_pages) - len(unique_large)
    
    # Check consistency
    if len(unique_small) != len(unique_large):
        only_small = unique_small - unique_large
        only_large = unique_large - unique_small
    
    # Compare with count
    actual_unique = len(unique_small)


@pytest.mark.asyncio
async def test_apollo_specific_url_diagnosis(async_client, db_session):
    """
    Test with a specific Apollo URL that's causing issues.
    
    INSTRUCTIONS:
    Replace the apollo_url below with your actual Apollo URL that's showing the mismatch.
    """
    # Create comprehensive test data
    for i in range(50):
        company = await create_company(
            db_session,
            name=f"Test Company {i}",
            employees_count=50 + i * 5,
        )
        await create_contact(
            db_session,
            company=company,
            first_name=f"Test Person {i}",
            email=f"person{i}@test.com",
            title="Director" if i % 2 == 0 else "Manager",
        )
    
    await db_session.commit()
    
    # REPLACE THIS WITH YOUR ACTUAL APOLLO URL:
    apollo_url = "https://app.apollo.io/#/people?page=1"
    
    await run_diagnostic(async_client, apollo_url, "Specific URL")

