import warnings

import pytest
from pydantic import ValidationError

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import SAWarning

from app.api.v1.endpoints import contacts as contacts_endpoints
from app.core.config import get_settings
from app.repositories.contacts import ContactRepository
from app.schemas.filters import AttributeListParams, CONTACT_FILTER_COLUMN_MAP, ContactFilterParams
from app.tests.factories import create_company, create_contact
from app.utils.cursor import encode_offset_cursor


@pytest.mark.asyncio
async def test_contacts_list_empty(async_client):
    response = await async_client.get("/api/v1/contacts/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["next"] is None
    assert payload["previous"] is None


@pytest.mark.asyncio
async def test_contacts_list_respects_max_page_size(async_client, db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "MAX_PAGE_SIZE", 3)

    for idx in range(5):
        await create_contact(
            db_session,
            first_name=f"Contact {idx}",
            email=f"contact{idx}@example.com",
            text_search=f"City {idx}",
        )

    response = await async_client.get("/api/v1/contacts/", params={"limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 3
    assert payload["next"] is not None
    assert payload["previous"] is None


@pytest.mark.asyncio
async def test_contacts_list_supports_cursor_navigation(async_client, db_session):
    for idx in range(4):
        await create_contact(
            db_session,
            first_name=f"Cursor {idx}",
            email=f"cursor{idx}@example.com",
            text_search=f"Cursor City {idx}",
        )

    cursor = encode_offset_cursor(2)
    response = await async_client.get("/api/v1/contacts/", params={"cursor": cursor, "limit": 2})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 2
    assert payload["previous"] is not None


def test_contact_filter_aliases():
    params = {
        "name": "Acme",
        "industries": "Software",
        "technologies": "Python",
        "keywords": "SaaS",
        "company_location": "Austin",
        "contact_location": "Jane",
        "email_status": "valid",
    }
    filters = ContactFilterParams.model_validate(params)
    assert filters.company == "Acme"
    assert filters.industries == "Software"
    assert filters.technologies == "Python"
    assert filters.keywords == "SaaS"
    assert filters.company_location == "Austin"
    assert filters.contact_location == "Jane"
    assert filters.email_status == "valid"

    alias_params = {
        "text_search": "Taylor",
        "employees": 10,
    }
    alias_filters = ContactFilterParams.model_validate(alias_params)
    assert alias_filters.contact_location == "Taylor"
    assert alias_filters.employees_count == 10


def test_contact_filter_field_metadata_alignment():
    field_names = set(ContactFilterParams.model_fields)
    assert field_names == set(CONTACT_FILTER_COLUMN_MAP)
    for field, column in CONTACT_FILTER_COLUMN_MAP.items():
        assert column, f"Expected column mapping for {field}"


def test_contact_filter_exclude_company_ids_normalization():
    filters = ContactFilterParams.model_validate({"exclude_company_ids": " alpha , beta , , "})
    assert filters.exclude_company_ids == ["alpha", "beta"]

    filters = ContactFilterParams.model_validate(
        {"exclude_company_ids": ['["gamma","delta"]', "gamma", "delta", "epsilon"]}
    )
    assert filters.exclude_company_ids == ["gamma", "delta", "epsilon"]


def test_contact_filter_exclude_titles_normalization():
    filters = ContactFilterParams.model_validate({"exclude_titles": " Director , VP , , "})
    assert filters.exclude_titles == ["Director", "VP"]

    filters = ContactFilterParams.model_validate(
        {"exclude_titles": ['["Engineer","Manager"]', "Engineer", "manager", "VP"]}
    )
    assert filters.exclude_titles == ["Engineer", "Manager", "VP"]


def test_contact_filter_extended_exclusion_normalization():
    filters = ContactFilterParams.model_validate({"exclude_company_locations": " Austin , Dallas , , "})
    assert filters.exclude_company_locations == ["Austin", "Dallas"]

    filters = ContactFilterParams.model_validate(
        {"exclude_departments": ['["Sales","Marketing"]', "sales", "Engineering"]}
    )
    assert filters.exclude_departments == ["Sales", "Marketing", "Engineering"]

    filters = ContactFilterParams.model_validate(
        {"exclude_contact_locations": ['["Houston","Denver"]', "houston", "Seattle"]}
    )
    assert filters.exclude_contact_locations == ["Houston", "Denver", "Seattle"]

    filters = ContactFilterParams.model_validate(
        {"exclude_technologies": ['["Salesforce","AWS"]', "salesforce", "Snowflake"]}
    )
    assert filters.exclude_technologies == ["Salesforce", "AWS", "Snowflake"]

    filters = ContactFilterParams.model_validate(
        {"exclude_industries": ['["Software","Energy"]', "software", "Manufacturing"]}
    )
    assert filters.exclude_industries == ["Software", "Energy", "Manufacturing"]


def test_contact_filter_rejects_negative_ranges():
    with pytest.raises(ValidationError):
        ContactFilterParams.model_validate({"employees_min": -1})
    with pytest.raises(ValidationError):
        ContactFilterParams.model_validate({"annual_revenue_max": -100})


@pytest.mark.asyncio
async def test_contacts_count_empty(async_client):
    response = await async_client.get("/api/v1/contacts/count/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0


@pytest.mark.asyncio
async def test_contacts_filter_by_company_location(async_client, db_session):
    company_a = await create_company(db_session, name="Austin Corp", text_search="Austin, TX")
    company_b = await create_company(db_session, name="NY Corp", text_search="New York, NY")

    contact_a = await create_contact(
        db_session,
        company=company_a,
        first_name="Alice",
        email="alice@example.com",
        text_search="Austin",
    )
    await create_contact(
        db_session,
        company=company_b,
        first_name="Bob",
        email="bob@example.com",
        text_search="New York",
    )

    response = await async_client.get("/api/v1/contacts/", params={"company_location": "Austin"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    assert payload["results"][0]["id"] == contact_a.id


@pytest.mark.asyncio
async def test_contacts_filter_by_numeric_ranges(async_client, db_session):
    await create_contact(
        db_session,
        company=await create_company(db_session, employees_count=500, annual_revenue=2_000_000),
        first_name="Range Match",
        email="range@example.com",
    )
    await create_contact(
        db_session,
        company=await create_company(db_session, employees_count=50, annual_revenue=100_000),
        first_name="Range Miss",
        email="miss@example.com",
    )

    params = {"employees_min": 400, "annual_revenue_min": 1_000_000}
    response = await async_client.get("/api/v1/contacts/", params=params)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    assert payload["results"][0]["first_name"] == "Range Match"


@pytest.mark.asyncio
async def test_contacts_exclude_company_ids(async_client, db_session, monkeypatch):
    excluded_company = await create_company(db_session, name="Blocked Co")
    included_company = await create_company(db_session, name="Allowed Co")

    excluded_contact = await create_contact(
        db_session,
        company=excluded_company,
        first_name="Blocked",
    )
    assert excluded_contact.company_id == excluded_company.uuid
    included_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="Allowed",
    )
    orphan_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="Orphan",
        company_id=None,
    )

    captured_filters = {}

    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get(
        "/api/v1/contacts/", params=[("exclude_company_ids", excluded_company.uuid)]
    )
    assert response.status_code == 200
    payload = response.json()
    returned_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_company_ids == [excluded_company.uuid]
    assert excluded_contact.id not in returned_ids
    assert included_contact.id in returned_ids
    assert orphan_contact.id in returned_ids


@pytest.mark.asyncio
async def test_contacts_exclude_titles(async_client, db_session, monkeypatch):
    company = await create_company(db_session, name="Title Co")

    excluded_contact = await create_contact(
        db_session,
        company=company,
        first_name="Exclude",
        title="Director",
    )
    included_contact = await create_contact(
        db_session,
        company=company,
        first_name="Include",
        title="Engineer",
    )
    untitled_contact = await create_contact(
        db_session,
        company=company,
        first_name="Untitled",
        title=None,
    )

    captured_filters = {}

    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_titles", "Director")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_titles == ["Director"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids
    assert untitled_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_company_locations(async_client, db_session, monkeypatch):
    excluded_company = await create_company(db_session, name="Austin Co", text_search="Austin, TX")
    included_company = await create_company(db_session, name="NY Co", text_search="New York, NY")

    excluded_contact = await create_contact(
        db_session,
        company=excluded_company,
        first_name="Austin Person",
    )
    included_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="NY Person",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_company_locations", "Austin")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_company_locations == ["Austin"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_contact_locations(async_client, db_session, monkeypatch):
    company = await create_company(db_session, name="Location Co")

    excluded_contact = await create_contact(
        db_session,
        company=company,
        first_name="Austin Person",
        text_search="Austin, TX",
    )
    included_contact = await create_contact(
        db_session,
        company=company,
        first_name="Seattle Person",
        text_search="Seattle, WA",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_contact_locations", "Austin")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_contact_locations == ["Austin"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_departments(async_client, db_session, monkeypatch):
    company = await create_company(db_session, name="Dept Co")

    excluded_contact = await create_contact(
        db_session,
        company=company,
        first_name="Sales Person",
        departments=["Sales", "Marketing"],
    )
    included_contact = await create_contact(
        db_session,
        company=company,
        first_name="Engineer Person",
        departments=["Engineering"],
    )
    departmentless_contact = await create_contact(
        db_session,
        company=company,
        first_name="No Dept",
        departments=[],
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_departments", "sales")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_departments == ["sales"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids
    assert departmentless_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_seniorities(async_client, db_session, monkeypatch):
    company = await create_company(db_session, name="Seniority Co")

    excluded_contact = await create_contact(
        db_session,
        company=company,
        first_name="Director Person",
        seniority="Director",
    )
    included_contact = await create_contact(
        db_session,
        company=company,
        first_name="Manager Person",
        seniority="Manager",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_seniorities", "director")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_seniorities == ["director"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_keywords(async_client, db_session, monkeypatch):
    excluded_company = await create_company(db_session, name="Keyword Co", keywords=["Cyber", "Security"])
    included_company = await create_company(db_session, name="Clean Co", keywords=["Finance"])

    excluded_contact = await create_contact(
        db_session,
        company=excluded_company,
        first_name="Cyber Person",
    )
    included_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="Finance Person",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_keywords", "cyber")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_keywords == ["cyber"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_technologies(async_client, db_session, monkeypatch):
    excluded_company = await create_company(db_session, name="Tech Co", technologies=["Salesforce", "AWS"])
    included_company = await create_company(db_session, name="Other Co", technologies=["Mailchimp"])

    excluded_contact = await create_contact(
        db_session,
        company=excluded_company,
        first_name="Tech Person",
    )
    included_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="Other Person",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_technologies", "Salesforce")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_technologies == ["Salesforce"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_exclude_industries(async_client, db_session, monkeypatch):
    excluded_company = await create_company(db_session, name="Industry Co", industries=["Software", "Energy"])
    included_company = await create_company(db_session, name="Manufacturing Co", industries=["Manufacturing"])

    excluded_contact = await create_contact(
        db_session,
        company=excluded_company,
        first_name="Software Person",
    )
    included_contact = await create_contact(
        db_session,
        company=included_company,
        first_name="Manufacturing Person",
    )

    captured_filters = {}
    original_list_contacts = contacts_endpoints.service.list_contacts

    async def wrapped_list_contacts(session, filters, **kwargs):
        captured_filters["value"] = filters
        return await original_list_contacts(session, filters, **kwargs)

    monkeypatch.setattr(contacts_endpoints.service, "list_contacts", wrapped_list_contacts)

    response = await async_client.get("/api/v1/contacts/", params=[("exclude_industries", "software")])
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert captured_filters["value"].exclude_industries == ["software"]
    assert excluded_contact.id not in result_ids
    assert included_contact.id in result_ids


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_companies(async_client, db_session):
    alpha_company = await create_company(db_session, name="Alpha Labs")
    beta_company = await create_company(db_session, name="Beta Holdings")
    gamma_company = await create_company(db_session, name="Gamma Group")

    alpha_contact = await create_contact(
        db_session,
        company=alpha_company,
        first_name="Alex",
        email="alex@alpha.com",
    )
    beta_contact = await create_contact(
        db_session,
        company=beta_company,
        first_name="Bailey",
        email="bailey@beta.com",
    )
    await create_contact(
        db_session,
        company=gamma_company,
        first_name="Gabe",
        email="gabe@gamma.com",
    )

    response = await async_client.get("/api/v1/contacts/", params={"company": "Alpha Labs,Beta Holdings"})
    assert response.status_code == 200
    payload = response.json()
    company_names = {item["company"] for item in payload["results"]}
    assert company_names == {"Alpha Labs", "Beta Holdings"}
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {alpha_contact.id, beta_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/", params={"company": " Beta Holdings , Gamma Group "}
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_names = {item["company"] for item in spaced_payload["results"]}
    assert spaced_names == {"Beta Holdings", "Gamma Group"}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_titles(async_client, db_session):
    company = await create_company(db_session, name="Universal Corp")

    director = await create_contact(
        db_session,
        company=company,
        first_name="Dina",
        title="Director of Sales",
        email="dina@example.com",
    )
    manager = await create_contact(
        db_session,
        company=company,
        first_name="Mark",
        title="Sales Manager",
        email="mark@example.com",
    )
    await create_contact(
        db_session,
        company=company,
        first_name="Owen",
        title="Account Executive",
        email="owen@example.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"title": "Director,Manager"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {director.id, manager.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"title": " Manager , Executive "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_titles = {item["title"] for item in spaced_payload["results"]}
    assert spaced_titles == {"Sales Manager", "Account Executive"}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_seniority(async_client, db_session):
    company = await create_company(db_session, name="Hierarchy Inc.")

    director = await create_contact(
        db_session,
        company=company,
        first_name="Daria",
        seniority="Director",
        email="daria@example.com",
    )
    manager = await create_contact(
        db_session,
        company=company,
        first_name="Morgan",
        seniority="Manager",
        email="morgan@example.com",
    )
    await create_contact(
        db_session,
        company=company,
        first_name="Ian",
        seniority="Individual Contributor",
        email="ian@example.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"seniority": "Director,Manager"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {director.id, manager.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"seniority": " Manager , Contributor "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_seniority = {item["seniority"] for item in spaced_payload["results"]}
    assert spaced_seniority == {"Manager", "Individual Contributor"}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_departments(async_client, db_session):
    company = await create_company(db_session, name="Org Chart LLC")

    sales_contact = await create_contact(
        db_session,
        company=company,
        first_name="Sasha",
        departments=["Sales", "Marketing"],
        email="sasha@example.com",
    )
    support_contact = await create_contact(
        db_session,
        company=company,
        first_name="Sam",
        departments=["Support"],
        email="sam@example.com",
    )
    engineering_contact = await create_contact(
        db_session,
        company=company,
        first_name="Elliot",
        departments=["Engineering"],
        email="elliot@example.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"departments": "Sales,Support"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {sales_contact.id, support_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"departments": " Support , Engineering "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {support_contact.id, engineering_contact.id}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_industries(async_client, db_session):
    tech_company = await create_company(db_session, name="Tech Co", industries=["Technology", "SaaS"])
    manufacturing_company = await create_company(
        db_session, name="Manufacturing Co", industries=["Manufacturing"]
    )
    healthcare_company = await create_company(db_session, name="Healthcare Co", industries=["Healthcare"])

    tech_contact = await create_contact(
        db_session,
        company=tech_company,
        first_name="Tina",
        email="tina@techco.com",
    )
    manufacturing_contact = await create_contact(
        db_session,
        company=manufacturing_company,
        first_name="Mark",
        email="mark@manuco.com",
    )
    healthcare_contact = await create_contact(
        db_session,
        company=healthcare_company,
        first_name="Hannah",
        email="hannah@healthco.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"industries": "Technology,Manufacturing"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {tech_contact.id, manufacturing_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"industries": " Manufacturing , Healthcare "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {manufacturing_contact.id, healthcare_contact.id}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_keywords(async_client, db_session):
    analytics_company = await create_company(db_session, name="Analytics Co", keywords=["Analytics", "BI"])
    cloud_company = await create_company(db_session, name="Cloud Co", keywords=["Cloud", "Infrastructure"])
    security_company = await create_company(db_session, name="Security Co", keywords=["Security"])

    analytics_contact = await create_contact(
        db_session,
        company=analytics_company,
        first_name="Alice",
        email="alice@analyticsco.com",
    )
    cloud_contact = await create_contact(
        db_session,
        company=cloud_company,
        first_name="Charlie",
        email="charlie@cloudco.com",
    )
    security_contact = await create_contact(
        db_session,
        company=security_company,
        first_name="Sophie",
        email="sophie@securityco.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"keywords": "Analytics,Cloud"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {analytics_contact.id, cloud_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"keywords": " Cloud , Security "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {cloud_contact.id, security_contact.id}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_company_locations(async_client, db_session):
    austin_company = await create_company(
        db_session,
        name="Austin Co",
        text_search="Austin, TX",
    )
    nyc_company = await create_company(
        db_session,
        name="NYC Co",
        text_search="New York, NY",
    )
    sf_company = await create_company(
        db_session,
        name="San Francisco Co",
        text_search="San Francisco, CA",
    )

    austin_contact = await create_contact(db_session, company=austin_company, first_name="Amy", email="amy@austin.co")
    nyc_contact = await create_contact(db_session, company=nyc_company, first_name="Nick", email="nick@nyc.co")
    sf_contact = await create_contact(db_session, company=sf_company, first_name="Sam", email="sam@sf.co")

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"company_location": "Austin,New York"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {austin_contact.id, nyc_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"company_location": " New York , San Francisco "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {nyc_contact.id, sf_contact.id}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_contact_locations(async_client, db_session):
    austin_contact = await create_contact(
        db_session,
        text_search="Austin, TX",
        first_name="Lara",
        email="lara@austin.co",
    )
    nyc_contact = await create_contact(
        db_session,
        text_search="New York, NY",
        first_name="Neil",
        email="neil@nyc.co",
    )
    sf_contact = await create_contact(
        db_session,
        text_search="San Francisco, CA",
        first_name="Sid",
        email="sid@sf.co",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"contact_location": "Austin,New York"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {austin_contact.id, nyc_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"contact_location": " New York , San Francisco "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {nyc_contact.id, sf_contact.id}


@pytest.mark.asyncio
async def test_contacts_filter_by_multiple_technologies(async_client, db_session):
    analytics_company = await create_company(db_session, name="Analytics Tech", technologies=["Python", "SQL"])
    cloud_company = await create_company(db_session, name="Cloud Tech", technologies=["AWS", "Kubernetes"])
    security_company = await create_company(db_session, name="Security Tech", technologies=["SIEM"])

    analytics_contact = await create_contact(
        db_session,
        company=analytics_company,
        first_name="Pia",
        email="pia@analytics.tech",
    )
    cloud_contact = await create_contact(
        db_session,
        company=cloud_company,
        first_name="Ken",
        email="ken@cloud.tech",
    )
    security_contact = await create_contact(
        db_session,
        company=security_company,
        first_name="Serena",
        email="serena@security.tech",
    )

    response = await async_client.get(
        "/api/v1/contacts/",
        params={"technologies": "Python,AWS"},
    )
    assert response.status_code == 200
    payload = response.json()
    result_ids = {item["id"] for item in payload["results"]}
    assert result_ids == {analytics_contact.id, cloud_contact.id}

    spaced_response = await async_client.get(
        "/api/v1/contacts/",
        params={"technologies": " AWS , SIEM "},
    )
    assert spaced_response.status_code == 200
    spaced_payload = spaced_response.json()
    spaced_ids = {item["id"] for item in spaced_payload["results"]}
    assert spaced_ids == {cloud_contact.id, security_contact.id}
def test_split_filter_values_normalizes_tokens():
    repo = ContactRepository()
    tokens = repo._split_filter_values(" Cloud ,SaaS,,")
    assert tokens == ["Cloud", "SaaS"]


def test_array_filter_sqlite_fallback_uses_string_match():
    repo = ContactRepository()
    stmt, company_alias, contact_meta_alias, company_meta_alias = repo.base_query()
    filters = ContactFilterParams.model_validate({"technologies": "Cloud"})
    filtered = repo.apply_filters(
        stmt,
        filters,
        company_alias,
        company_meta_alias,
        contact_meta_alias,
        dialect_name="sqlite",
    )
    compiled = filtered.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    sql_text = str(compiled)
    assert "array_to_string" not in sql_text
    assert "company.technologies" in sql_text
    assert "LIKE" in sql_text


def test_array_filter_postgres_uses_string_match():
    repo = ContactRepository()
    stmt, company_alias, contact_meta_alias, company_meta_alias = repo.base_query()
    filters = ContactFilterParams.model_validate({"technologies": "Cloud,AI"})
    filtered = repo.apply_filters(
        stmt,
        filters,
        company_alias,
        company_meta_alias,
        contact_meta_alias,
        dialect_name="postgresql",
    )
    compiled = filtered.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    )
    sql_text = str(compiled)
    assert "array_to_string" in sql_text
    assert "::TEXT[]" not in sql_text


@pytest.mark.asyncio
async def test_contacts_list_accepts_company_filters(async_client):
    params = {
        "name": "Acme Corp",
        "employees_count": 250,
        "annual_revenue": 1000000,
        "total_funding": 5000000,
        "company_location": "Austin",
        "contact_location": "Jane",
        "distinct": True,
    }
    response = await async_client.get("/api/v1/contacts/", params=params)
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["next"] is None
    assert payload["previous"] is None


@pytest.mark.asyncio
async def test_contacts_list_accepts_array_filters(async_client):
    params = {
        "technologies": "Cloud",
        "keywords": "Managed Services",
        "industries": "Information Technology",
        "departments": "Sales",
        "search": "Austin",
    }
    response = await async_client.get("/api/v1/contacts/", params=params)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_contacts_list_rejects_invalid_limit_and_offset(async_client):
    bad_limit_response = await async_client.get("/api/v1/contacts/", params={"limit": 0})
    assert bad_limit_response.status_code == 422

    bad_offset_response = await async_client.get("/api/v1/contacts/", params={"offset": -1})
    assert bad_offset_response.status_code == 422


@pytest.mark.asyncio
async def test_contacts_count_accepts_company_filters(async_client):
    params = {
        "name": "Acme Corp",
        "employees_count": 250,
        "annual_revenue": 1000000,
        "total_funding": 5000000,
        "company_location": "Austin",
        "contact_location": "Jane",
        "page_size": 25,
    }
    response = await async_client.get("/api/v1/contacts/count/", params=params)
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


@pytest.mark.asyncio
async def test_create_contact_sanitizes_blank_values(async_client):
    request_body = {
        "first_name": "  ",
        "last_name": "",
        "email": "  user@example.com ",
        "title": None,
        "departments": ["Sales", "", "  "],
        "mobile_phone": " '+1 555-0100 ",
        "email_status": "_",
        "text_search": "  Austin ",
        "company_id": " ",
        "seniority": "",
    }
    response = await async_client.post("/api/v1/contacts/", json=request_body)
    assert response.status_code == 201
    payload = response.json()
    assert payload["first_name"] is None
    assert payload["last_name"] is None
    assert payload["email"] == "user@example.com"
    assert payload["mobile_phone"] == "+1 555-0100"
    assert payload["email_status"] is None
    assert payload["departments"] == "Sales"
    assert payload["seniority"] == "_"


@pytest.mark.asyncio
async def test_contact_detail_strips_placeholder_metadata(async_client, db_session):
    company = await create_company(
        db_session,
        name=" Example Co ",
        industries=["Software", ""],
        metadata_overrides={
            "phone_number": "'+1 999-0000",
            "website": " https://example.com ",
            "linkedin_url": " https://linkedin.com/company/example ",
            "facebook_url": "_",
            "twitter_url": "_",
            "city": " Austin ",
            "state": "_",
            "country": " USA ",
        },
    )
    contact = await create_contact(
        db_session,
        company=company,
        first_name="  Alice ",
        email="  alice@example.com ",
        departments=["Sales", "", "Marketing"],
        metadata_overrides={
            "linkedin_url": " https://linkedin.com/in/alice ",
            "facebook_url": "_",
            "twitter_url": "_",
            "website": " ",
            "work_direct_phone": "_",
            "home_phone": "_",
            "city": " ",
            "state": "_",
            "country": "_",
            "other_phone": "_",
            "stage": "_",
        },
    )

    response = await async_client.get(f"/api/v1/contacts/{contact.id}")
    assert response.status_code == 200
    payload = response.json()

    assert payload["first_name"] == "Alice"
    assert payload["email"] == "alice@example.com"
    assert payload["departments"] == "Sales, Marketing"
    assert payload["company"] == "Example Co"
    assert payload["company_phone"] == "+1 999-0000"
    assert payload["company_detail"]["industry"] == "Software"
    assert payload["company_detail"]["website"] == "https://example.com"
    assert payload["company_detail"]["linkedin_url"] == "https://linkedin.com/company/example"
    assert payload["metadata"]["linkedin_url"] == "https://linkedin.com/in/alice"
    assert payload["metadata"]["facebook_url"] is None
    assert payload["metadata"]["work_direct_phone"] is None

@pytest.mark.asyncio
async def test_create_contact_rejects_invalid_departments(async_client):
    response = await async_client.post("/api/v1/contacts/", json={"departments": "Sales"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_retrieve_contact_detail_and_not_found(async_client, db_session):
    contact = await create_contact(
        db_session,
        first_name="Detail",
        email="detail@example.com",
        company=await create_company(db_session, name="Detail Corp"),
    )

    response = await async_client.get(f"/api/v1/contacts/{contact.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == contact.id
    assert payload["company_detail"]["name"] == "Detail Corp"

    missing_response = await async_client.get("/api/v1/contacts/999999")
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_list_industries_separated_returns_sorted_unique(async_client, monkeypatch):
    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            assert array_mode is True
            assert params.distinct is True
            return [" Cloud", "SaaS", "Cloud", "", None]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get("/api/v1/contacts/industry/", params={"separated": "true"})
    assert response.status_code == 200
    assert response.json() == ["Cloud", "SaaS"]


@pytest.mark.asyncio
async def test_list_industries_collapsed_filters_empty(async_client, monkeypatch):
    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            assert array_mode is False
            return ["Software,Technology", "", None]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get("/api/v1/contacts/industry/")
    assert response.status_code == 200
    assert response.json() == ["Software,Technology"]


@pytest.mark.asyncio
async def test_list_technologies_separated_returns_sorted_unique(async_client, monkeypatch):
    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            assert array_mode is True
            assert params.distinct is True
            return [" Python", "AWS", "Python", "", None]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get("/api/v1/contacts/technologies/", params={"separated": "true"})
    assert response.status_code == 200
    assert response.json() == ["AWS", "Python"]


@pytest.mark.asyncio
async def test_list_technologies_separated_returns_unique_up_to_limit(async_client, db_session):
    company_alpha = await create_company(
        db_session,
        technologies=["Outlook", "Remote"],
        name="Alpha Tech",
    )
    company_beta = await create_company(
        db_session,
        technologies=["Outlook", "Slack"],
        name="Beta Tech",
    )
    await create_contact(
        db_session,
        company=company_alpha,
        first_name="Alpha",
        email="alpha@example.com",
    )
    await create_contact(
        db_session,
        company=company_beta,
        first_name="Beta",
        email="beta@example.com",
    )

    response = await async_client.get(
        "/api/v1/contacts/technologies/",
        params={"separated": "true", "limit": "2", "ordering": "value"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload == ["Outlook", "Remote"]


@pytest.mark.asyncio
async def test_list_technologies_collapsed_filters_empty(async_client, monkeypatch):
    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            assert array_mode is False
            return ["Python,AWS", "", None]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get("/api/v1/contacts/technologies/")
    assert response.status_code == 200
    assert response.json() == ["Python,AWS"]


@pytest.mark.asyncio
async def test_repository_attribute_values_skip_blank_tokens():
    repo = ContactRepository()
    filters = ContactFilterParams()
    params = AttributeListParams(limit=5, offset=0)
    column_factory = (
        lambda Contact, Company, ContactMetadata, CompanyMetadata: Company.technologies
    )

    class DummyResult:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class DummySession:
        def __init__(self, rows, dialect_name: str):
            class _Dialect:
                def __init__(self, name: str):
                    self.name = name

            class _Bind:
                def __init__(self, name: str):
                    self.dialect = _Dialect(name)

            self.bind = _Bind(dialect_name)
            self._rows = rows
            self.statements = []

        async def execute(self, stmt):
            self.statements.append(stmt)
            return DummyResult(self._rows)

    postgres_session = DummySession(
        rows=[("Python",), ("Remote",)],
        dialect_name="postgresql",
    )
    postgres_values = await repo.list_attribute_values(
        postgres_session,
        filters,
        params,
        column_factory=column_factory,
        array_mode=True,
    )
    assert postgres_values == ["Python", "Remote"]

    compiled = postgres_session.statements[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    sql_text = str(compiled).lower()
    assert "nullif" in sql_text
    assert "trim" in sql_text

    sqlite_session = DummySession(
        rows=[("   ",), ("Remote",)],
        dialect_name="sqlite",
    )
    sqlite_values = await repo.list_attribute_values(
        sqlite_session,
        filters,
        params,
        column_factory=column_factory,
        array_mode=True,
    )
    assert sqlite_values == ["Remote"]


@pytest.mark.asyncio
async def test_list_titles_distinct(async_client, db_session):
    await create_contact(
        db_session,
        first_name="Title One",
        email="title1@example.com",
        title="Director",
    )
    await create_contact(
        db_session,
        first_name="Title Two",
        email="title2@example.com",
        title="Director",
    )
    placeholder_titles = ["_", "....", "//////", "?"]
    for idx, title in enumerate(placeholder_titles):
        await create_contact(
            db_session,
            first_name=f"Placeholder {idx}",
            email=f"placeholder{idx}@example.com",
            title=title,
        )

    response = await async_client.get("/api/v1/contacts/title/", params={"distinct": "true"})
    assert response.status_code == 200
    payload = response.json()
    assert payload == ["Director"]
    for placeholder in placeholder_titles:
        assert placeholder not in payload


@pytest.mark.asyncio
async def test_list_companies_distinct_search_emits_no_cartesian_warnings(async_client, db_session):
    company = await create_company(db_session, name="DCS Systems")
    await create_contact(
        db_session,
        company=company,
        first_name="NoWarning",
        email="nowarning@example.com",
        title="Director",
    )

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", SAWarning)
        response = await async_client.get(
            "/api/v1/contacts/company/",
            params={"distinct": "true", "search": "DCS"},
        )

    assert response.status_code == 200
    assert "DCS Systems" in response.json()
    offending = [
        warning
        for warning in captured
        if issubclass(warning.category, SAWarning)
        and "cartesian product" in str(warning.message).lower()
    ]
    assert offending == []


@pytest.mark.asyncio
async def test_list_keywords_separated_handles_mixed_formats(async_client, monkeypatch):
    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            assert array_mode is True
            assert params.distinct is True
            return [
                " SaaS ",
                ["AI", "ML"],
                '["Cloud","AI"]',
                '{"DevOps","AI"}',
                None,
                "",
            ]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get("/api/v1/contacts/keywords/", params={"separated": "true"})
    assert response.status_code == 200
    assert response.json() == ["AI", "Cloud", "DevOps", "ML", "SaaS"]


@pytest.mark.asyncio
async def test_list_company_address_returns_text_search(async_client, db_session):
    company = await create_company(
        db_session,
        name="Text Search Co",
        text_search="123 Example St, Austin, TX",
    )
    await create_contact(
        db_session,
        company=company,
        first_name="Tessa",
        email="tessa@example.com",
    )
    response = await async_client.get("/api/v1/contacts/company_address/")
    assert response.status_code == 200
    assert response.json() == ["123 Example St, Austin, TX"]


@pytest.mark.asyncio
async def test_list_contact_address_returns_text_search(async_client, db_session):
    await create_contact(
        db_session,
        first_name="Carlos",
        email="carlos@example.com",
        text_search="456 Sample Ave, Denver, CO",
    )
    response = await async_client.get("/api/v1/contacts/contact_address/")
    assert response.status_code == 200
    assert response.json() == ["456 Sample Ave, Denver, CO"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "title",
        "company",
        "company_address",
        "contact_address",
        "industry",
        "keywords",
        "technologies",
    ],
)
async def test_attribute_endpoints_accept_params(async_client, monkeypatch, endpoint):
    captured = {}

    class DummyService:
        async def list_attribute_values(
            self,
            session,
            filters,
            params,
            *,
            column_factory,
            array_mode: bool = False,
        ):
            captured["filters"] = filters
            captured["params"] = params
            captured["array_mode"] = array_mode
            captured["column_factory"] = column_factory
            return ["Value One", "Value Two"]

    monkeypatch.setattr(contacts_endpoints, "service", DummyService())
    response = await async_client.get(
        f"/api/v1/contacts/{endpoint}/",
        params={
            "limit": "5",
            "offset": "10",
            "distinct": "true",
            "search": "Query",
            "ordering": "name",
            "contact_location": "Austin",
        },
    )
    assert response.status_code == 200
    assert response.json() == ["Value One", "Value Two"]

    params = captured["params"]
    assert params.limit == 5
    assert params.offset == 10
    assert params.distinct is True
    assert params.search == "Query"
    assert params.ordering == "name"
    assert captured["array_mode"] is False

    filters = captured["filters"]
    assert isinstance(filters, ContactFilterParams)
    assert filters.contact_location == "Austin"
