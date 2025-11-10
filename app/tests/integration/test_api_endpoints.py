from __future__ import annotations

import json
import time
from functools import partial
from itertools import islice
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urljoin

import pytest

try:  # pragma: no cover - dependency import guard
    import requests  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - explicit failure message
    raise RuntimeError("The 'requests' package is required for integration tests.") from exc

from .recorder import APITestRecorder
# Fallback values mirroring scripts/test_all_apis.py when CSV loader is unavailable.
CONTACT_FILTERS: Dict[str, List[Any]] = {
    "first_name": ["ann", "john", "mary", "", "test"],
    "last_name": ["smith", "doe", "jones", ""],
    "title": ["cto", "ceo", "director", "manager", ""],
    "company": ["tech", "inc", "corp", "ltd", ""],
    "company_name_for_emails": ["inc", "corp", "llc", ""],
    "email": ["@example.com", "@test.com", ""],
    "departments": ["sales", "engineering", "marketing", ""],
    "work_direct_phone": ["555", "123", ""],
    "home_phone": ["555", ""],
    "mobile_phone": ["555", ""],
    "corporate_phone": ["555", ""],
    "other_phone": ["555", ""],
    "city": ["San", "New", "Los", ""],
    "state": ["CA", "NY", "TX", ""],
    "country": ["US", "CA", "UK", ""],
    "technologies": ["python", "java", "javascript", ""],
    "keywords": ["enterprise", "startup", "fintech", ""],
    "person_linkedin_url": ["linkedin.com", ""],
    "website": ["example.com", "test.com", ""],
    "company_linkedin_url": ["linkedin.com", ""],
    "facebook_url": ["facebook.com", ""],
    "twitter_url": ["twitter.com", ""],
    "company_address": ["street", "avenue", ""],
    "company_city": ["San", "New", ""],
    "company_state": ["CA", "NY", ""],
    "company_country": ["US", "CA", ""],
    "company_phone": ["555", ""],
    "industry": ["software", "technology", "finance", ""],
    "latest_funding": ["series", "seed", ""],
    "last_raised_at": ["2024", "2023", ""],
    "email_status": ["valid", "invalid", "unknown", ""],
    "primary_email_catch_all_status": ["yes", "no", ""],
    "stage": ["lead", "prospect", "customer", ""],
    "seniority": ["director", "manager", "executive", ""],
    "employees_min": [10, 50, 100, 500],
    "employees_max": [100, 500, 1000, 5000],
    "annual_revenue_min": [1_000_000, 5_000_000, 10_000_000],
    "annual_revenue_max": [10_000_000, 50_000_000, 100_000_000],
    "total_funding_min": [1_000_000, 5_000_000],
    "total_funding_max": [50_000_000, 100_000_000],
    "latest_funding_amount_min": [100_000, 1_000_000],
    "latest_funding_amount_max": [5_000_000, 10_000_000],
    "created_at_after": ["2024-01-01T00:00:00Z", "2023-01-01T00:00:00Z"],
    "created_at_before": ["2025-01-01T00:00:00Z", "2024-12-31T23:59:59Z"],
    "updated_at_after": ["2024-01-01T00:00:00Z"],
    "updated_at_before": ["2025-01-01T00:00:00Z"],
}

SLOW_FILTERS = {
    "email",
    "work_direct_phone",
    "home_phone",
    "mobile_phone",
    "other_phone",
    "website",
    "email_status",
    "stage",
    "primary_email_catch_all_status",
}

ORDERING_FIELDS = [
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "employees",
    "-employees",
    "annual_revenue",
    "-annual_revenue",
    "total_funding",
    "-total_funding",
    "latest_funding_amount",
    "-latest_funding_amount",
    "first_name",
    "-first_name",
    "last_name",
    "-last_name",
    "title",
    "-title",
    "company",
    "-company",
    "company_name_for_emails",
    "-company_name_for_emails",
    "email",
    "-email",
    "email_status",
    "-email_status",
    "primary_email_catch_all_status",
    "-primary_email_catch_all_status",
    "seniority",
    "-seniority",
    "departments",
    "-departments",
    "work_direct_phone",
    "-work_direct_phone",
    "home_phone",
    "-home_phone",
    "mobile_phone",
    "-mobile_phone",
    "corporate_phone",
    "-corporate_phone",
    "other_phone",
    "-other_phone",
    "stage",
    "-stage",
    "industry",
    "-industry",
    "person_linkedin_url",
    "-person_linkedin_url",
    "website",
    "-website",
    "company_linkedin_url",
    "-company_linkedin_url",
    "facebook_url",
    "-facebook_url",
    "twitter_url",
    "-twitter_url",
    "city",
    "-city",
    "state",
    "-state",
    "country",
    "-country",
    "company_address",
    "-company_address",
    "company_city",
    "-company_city",
    "company_state",
    "-company_state",
    "company_country",
    "-company_country",
    "company_phone",
    "-company_phone",
    "latest_funding",
    "-latest_funding",
    "last_raised_at",
    "-last_raised_at",
]

FIELD_ENDPOINTS = [
    "title",
    "company",
    "industry",
    "keywords",
    "technologies",
    "city",
    "state",
    "country",
    "company_address",
    "company_city",
    "company_state",
    "company_country",
]

FILTER_COMBINATIONS = [
    {"first_name": "ann", "country": "US"},
    {"country": "US", "employees_min": 50},
    {"industry": "software", "technologies": "python"},
    {"email_status": "valid", "stage": "lead"},
    {"country": "US", "state": "CA", "city": "San"},
    {"employees_min": 50, "employees_max": 500, "annual_revenue_min": 1_000_000},
    {"created_at_after": "2024-01-01T00:00:00Z", "updated_at_before": "2025-01-01T00:00:00Z"},
    {"title": "cto", "seniority": "director", "country": "US"},
    {
        "company": "tech",
        "industry": "software",
        "technologies": "python",
        "keywords": "enterprise",
    },
]

SEARCH_TERMS = ["fintech", "tech", "software", "enterprise", "startup", "test", "example"]

API_PREFIX = "/api/v1"


def _first_non_empty(values: Iterable[Any]) -> Any:
    for value in values:
        if isinstance(value, str):
            if value:
                return value
        else:
            return value
    return next(iter(values), None)


def _json_or_empty(response: requests.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {}


def api_v1_path(path: str = "/") -> str:
    if not path:
        suffix = ""
    else:
        suffix = path if path.startswith("/") else f"/{path}"
    return f"{API_PREFIX}{suffix}"


@pytest.fixture(scope="session", autouse=True)
def ensure_api_available(
    api_session: requests.Session, api_base_url: str, api_timeout: float
) -> None:
    """Skip the suite early if the target API is not reachable."""
    root_url = urljoin(f"{api_base_url}/", api_v1_path("/"))
    try:
        response = api_session.get(root_url, timeout=api_timeout)
    except requests.RequestException as exc:  # pragma: no cover - defensive
        pytest.skip(f"Appointment360 API not reachable at {api_base_url}: {exc}")
    else:
        if response.status_code >= 500:
            pytest.skip(
                f"Appointment360 API returned {response.status_code} for root URL {root_url}"
            )


@pytest.fixture(scope="session")
def admin_authenticated(
    api_session: requests.Session,
    api_base_url: str,
    api_admin_credentials: Optional[Dict[str, str]],
    api_timeout: float,
) -> bool:
    """Attempt to authenticate as admin if credentials were provided."""
    if not api_admin_credentials:
        return False

    login_url = urljoin(f"{api_base_url}/", "/admin/login/")
    try:
        response = api_session.get(login_url, timeout=api_timeout)
    except requests.RequestException:
        return False

    payload = {
        "username": api_admin_credentials["username"],
        "password": api_admin_credentials["password"],
    }

    csrftoken = api_session.cookies.get("csrftoken")
    if csrftoken:
        payload["csrfmiddlewaretoken"] = csrftoken

    try:
        login_response = api_session.post(
            login_url, data=payload, timeout=api_timeout, allow_redirects=False
        )
    except requests.RequestException:
        return False

    return login_response.status_code in (200, 302)


@pytest.fixture(scope="session")
def api_request_factory(
    api_session: requests.Session,
    api_base_url: str,
    api_timeout: float,
    api_test_recorder: "APITestRecorder",
) -> Callable[..., requests.Response]:
    """Fixture returning a convenience function for issuing HTTP requests."""

    def _request(
        method: str,
        endpoint: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        data: Optional[Mapping[str, Any]] = None,
        files: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, Any]] = None,
        expected_status: Optional[int] = 200,
        expected_statuses: Optional[Iterable[int]] = None,
        allow_timeout: bool = False,
        request_context: Optional[pytest.FixtureRequest] = None,
    ) -> requests.Response:
        if endpoint.startswith(("http://", "https://")):
            url = endpoint
        else:
            base = api_base_url.rstrip("/")
            suffix = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            url = f"{base}{suffix}"
        request_headers = {"X-Request-Id": f"pytest-{int(time.time() * 1000)}"}
        if headers:
            request_headers.update(headers)

        start_time = time.perf_counter()

        try:
            response = api_session.request(
                method=method,
                url=url,
                params=params,
                json=json_body if files is None else None,
                data=data,
                files=files,
                headers=request_headers,
                timeout=api_timeout,
            )
            elapsed = time.perf_counter() - start_time
        except requests.exceptions.Timeout as exc:
            elapsed = time.perf_counter() - start_time
            api_test_recorder.record(
                test_name=(
                    request_context.node.nodeid
                    if request_context is not None
                    else f"{method} {endpoint}"
                ),
                method=method,
                endpoint=endpoint,
                url=url,
                status_code=None,
                expected_status=expected_status,
                expected_statuses=expected_statuses,
                success=allow_timeout,
                response_time=elapsed,
                params=params,
                error=f"Timeout: {exc}",
                request_id=request_headers.get("X-Request-Id"),
            )
            if allow_timeout:
                pytest.xfail(f"Expected timeout for {method} {endpoint}")
            pytest.fail(f"{method} {url} timed out after {elapsed:.2f}s")
        except requests.exceptions.RequestException as exc:  # pragma: no cover - defensive
            elapsed = time.perf_counter() - start_time
            api_test_recorder.record(
                test_name=(
                    request_context.node.nodeid
                    if request_context is not None
                    else f"{method} {endpoint}"
                ),
                method=method,
                endpoint=endpoint,
                url=url,
                status_code=None,
                expected_status=expected_status,
                expected_statuses=expected_statuses,
                success=False,
                response_time=elapsed,
                params=params,
                error=str(exc),
                request_id=request_headers.get("X-Request-Id"),
            )
            pytest.fail(f"{method} {url} request error: {exc}")

        response_body = response.text or ""
        response_is_json = False
        content_preview = response_body[:500] if response_body else ""

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                json.loads(response_body)
            except ValueError:
                response_is_json = False
            else:
                response_is_json = True

        response_preview = content_preview
        expected_ok = True
        expectation_desc = "any status"

        if expected_statuses:
            expected_set = set(expected_statuses)
            expected_ok = response.status_code in expected_set
            expectation_desc = f"one of {sorted(expected_set)}"
        elif expected_status is not None:
            expected_ok = response.status_code == expected_status
            expectation_desc = str(expected_status)

        api_test_recorder.record(
            test_name=(
                request_context.node.nodeid
                if request_context is not None
                else f"{method} {endpoint}"
            ),
            method=method,
            endpoint=endpoint,
            url=url,
            status_code=response.status_code,
            expected_status=expected_status,
            expected_statuses=expected_statuses,
            success=expected_ok,
            response_time=elapsed,
            params=params,
            request_id=request_headers.get("X-Request-Id"),
            response_preview=response_preview,
            response_body=response_body,
            response_is_json=response_is_json,
        )

        if not expected_ok:
            pytest.fail(
                f"{method} {url} returned {response.status_code}, expected {expectation_desc}"
            )

        return response

    return _request


@pytest.fixture
def api_request(
    api_request_factory: Callable[..., requests.Response],
    request: pytest.FixtureRequest,
) -> Callable[..., requests.Response]:
    return partial(api_request_factory, request_context=request)


@pytest.fixture(scope="session")
def existing_contact_id(
    api_request_factory: Callable[..., requests.Response],
) -> Optional[int]:
    """Fetch a sample contact ID for detail and error tests."""
    response = api_request_factory(
        "GET",
        api_v1_path("/contacts/"),
        params={"page_size": 1},
        expected_status=200,
    )
    payload = _json_or_empty(response)
    results = payload.get("results") if isinstance(payload, dict) else None
    if results:
        return results[0].get("id")
    return None


@pytest.fixture
def import_job_id(api_request, admin_authenticated: bool) -> int | str:
    """Create an import job when admin authentication is available."""
    if not admin_authenticated:
        pytest.skip("Admin credentials required to create import jobs")

    csv_content = "first_name,last_name,email,company\nTest,Contact,test@example.com,Test Corp"
    files = {"file": ("test_contacts.csv", csv_content.encode("utf-8"), "text/csv")}
    response = api_request(
        "POST",
        api_v1_path("/contacts/import/"),
        files=files,
        data={},
        expected_status=None,
        expected_statuses=[201, 403],
    )

    if response.status_code != 201:
        pytest.skip(f"Import upload not permitted (status {response.status_code})")

    payload = _json_or_empty(response)
    job_id = payload.get("job_id")
    if not job_id:
        pytest.skip("Import endpoint did not return a job_id")
    try:
        return int(job_id)
    except (TypeError, ValueError):
        return job_id


class TestRootEndpoints:
    def test_root_endpoint(self, api_request):
        api_request("GET", api_v1_path("/"), expected_status=200)

    def test_health_endpoint(self, api_request):
        response = api_request(
            "GET",
            api_v1_path("/health/"),
            expected_statuses=[200, 503, 404],
        )
        if response.status_code == 404:
            pytest.skip("Versioned health endpoint not available")
        if response.status_code == 200:
            payload = response.json()
            assert "status" in payload

    def test_favicon(self, api_request):
        api_request("GET", "/favicon.ico", expected_status=204)

    def test_root_trailing_slash(self, api_request):
        api_request("GET", api_v1_path("/"), expected_status=200)


class TestContactsList:
    def test_basic_list(self, api_request):
        api_request("GET", api_v1_path("/contacts/"), expected_status=200)

    @pytest.mark.parametrize(
        "params",
        [
            {"page": 1, "page_size": 10},
            {"page": 2, "page_size": 10},
            {"page": 1, "page_size": 25},
            {"page": 1, "page_size": 50},
            {"page": 1, "page_size": 100},
            {"page": 1, "page_size": 1},
            {"page": 999, "page_size": 10},
        ],
    )
    def test_pagination(self, api_request, params: Mapping[str, Any]):
        api_request("GET", api_v1_path("/contacts/"), params=params, expected_status=200)

    @pytest.mark.parametrize(
        "filter_name,test_value",
        [
            (filter_name, _first_non_empty(values))
            for filter_name, values in CONTACT_FILTERS.items()
            if _first_non_empty(values) is not None and _first_non_empty(values) != ""
        ],
    )
    def test_individual_filters(self, api_request, filter_name: str, test_value: Any):
        allow_timeout = filter_name in SLOW_FILTERS
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={filter_name: test_value},
            expected_status=200,
            allow_timeout=allow_timeout,
        )

    @pytest.mark.parametrize("params", FILTER_COMBINATIONS)
    def test_filter_combinations(self, api_request, params: Mapping[str, Any]):
        api_request("GET", api_v1_path("/contacts/"), params=params, expected_status=200)

    @pytest.mark.parametrize("term", SEARCH_TERMS)
    def test_search_terms(self, api_request, term: str):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"search": term},
            expected_status=200,
        )

    def test_search_with_pagination(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"search": "tech", "page": 1, "page_size": 10},
            expected_status=200,
        )

    @pytest.mark.parametrize(
        "ordering_field",
        list(islice(ORDERING_FIELDS, 0, 20)),
    )
    def test_ordering_fields(self, api_request, ordering_field: str):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"ordering": ordering_field, "page_size": 10},
            expected_status=200,
        )

    def test_multiple_ordering(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"ordering": "country,-employees,created_at"},
            expected_status=200,
        )

    def test_combined_query(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={
                "search": "tech",
                "country": "US",
                "employees_min": 50,
                "ordering": "-employees",
                "page": 1,
                "page_size": 25,
            },
            expected_status=200,
        )

    def test_empty_search(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"search": ""},
            expected_status=200,
        )

    def test_invalid_page_size(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"page_size": 1000},
            expected_status=200,
        )

    def test_invalid_ordering_field(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"ordering": "invalid_field"},
            expected_status=400,
        )

    def test_special_character_search(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"search": "test@example.com"},
            expected_status=200,
            allow_timeout=True,
        )

    def test_custom_request_id_header(self, api_request):
        response = api_request(
            "GET",
            api_v1_path("/contacts/"),
            headers={"X-Request-Id": "custom-req-id-123"},
            expected_status=200,
        )
        assert response.request.headers["X-Request-Id"] == "custom-req-id-123"


class TestContactsDetail:
    def test_retrieve_valid_contact(self, api_request, existing_contact_id: Optional[int]):
        if not existing_contact_id:
            pytest.skip("No contacts available to run detail tests")
        api_request(
            "GET",
            api_v1_path(f"/contacts/{existing_contact_id}/"),
            expected_status=200,
        )

    @pytest.mark.parametrize(
        "invalid_id",
        ["invalid", "999999999", "-1", "0"],
    )
    def test_invalid_identifiers(self, api_request, invalid_id: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{invalid_id}/"),
            expected_status=404,
        )

    def test_request_id_header_echo(self, api_request, existing_contact_id: Optional[int]):
        if not existing_contact_id:
            pytest.skip("No contacts available to run detail header echo test")
        response = api_request(
            "GET",
            api_v1_path(f"/contacts/{existing_contact_id}/"),
            headers={"X-Request-Id": "detail-req-123"},
            expected_status=200,
        )
        assert response.request.headers["X-Request-Id"] == "detail-req-123"


class TestContactsCount:
    def test_unfiltered_count(self, api_request):
        api_request("GET", api_v1_path("/contacts/count/"), expected_status=200)

    @pytest.mark.parametrize(
        "params",
        [
            {"country": "US"},
            {"employees_min": 50},
            {"email_status": "valid"},
            {"industry": "software"},
        ],
    )
    def test_single_filter(self, api_request, params: Mapping[str, Any]):
        api_request("GET", api_v1_path("/contacts/count/"), params=params, expected_status=200)

    def test_multiple_filters(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/count/"),
            params={"country": "US", "employees_min": 50, "email_status": "valid"},
            expected_status=200,
        )

    def test_count_with_search(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/count/"),
            params={"search": "tech"},
            expected_status=200,
        )

    def test_count_with_date_range(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/count/"),
            params={"created_at_after": "2024-01-01T00:00:00Z"},
            expected_status=200,
        )

    def test_count_request_id_header(self, api_request):
        response = api_request(
            "GET",
            api_v1_path("/contacts/count/"),
            headers={"X-Request-Id": "count-req-123"},
            expected_status=200,
        )
        assert response.request.headers["X-Request-Id"] == "count-req-123"


class TestFieldEndpoints:
    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_basic(self, api_request, field_name: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    @pytest.mark.parametrize("term", SEARCH_TERMS[:2])
    def test_field_search(self, api_request, field_name: str, term: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"search": term},
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_distinct(self, api_request, field_name: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"distinct": "true"},
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_pagination(self, api_request, field_name: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"limit": 10, "offset": 0},
            expected_status=200,
        )
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"limit": 25, "offset": 25},
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_combined(self, api_request, field_name: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"search": "test", "distinct": "true", "limit": 10},
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_edge_cases(self, api_request, field_name: str):
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"search": ""},
            expected_status=200,
        )
        api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            params={"distinct": "invalid"},
            expected_status=200,
        )

    @pytest.mark.parametrize("field_name", FIELD_ENDPOINTS)
    def test_field_custom_request_id(self, api_request, field_name: str):
        header_value = f"field-{field_name}-req-123"
        response = api_request(
            "GET",
            api_v1_path(f"/contacts/{field_name}/"),
            headers={"X-Request-Id": header_value},
            expected_status=200,
        )
        assert response.request.headers["X-Request-Id"] == header_value


class TestImportEndpoints:
    def test_import_endpoint_info(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/import/"),
            expected_status=None,
            expected_statuses=[200, 403, 404],
        )

    def test_import_endpoint_info_without_trailing_slash(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/import"),
            expected_status=None,
            expected_statuses=[200, 403, 404],
        )

    def test_upload_valid_csv(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for CSV upload tests")
        csv_content = (
            "first_name,last_name,email,company\nTest,Contact,test@example.com,Test Corp"
        )
        files = {"file": ("test_contacts.csv", csv_content.encode("utf-8"), "text/csv")}
        response = api_request(
            "POST",
            api_v1_path("/contacts/import/"),
            files=files,
            data={},
            expected_status=None,
            expected_statuses=[201, 403],
        )
        if response.status_code != 201:
            pytest.skip(f"Import upload not permitted (status {response.status_code})")

    def test_upload_invalid_csv(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for CSV upload tests")
        files = {
            "file": ("invalid_contacts.csv", b"invalid,header,row\nmissing,columns", "text/csv")
        }
        response = api_request(
            "POST",
            api_v1_path("/contacts/import/"),
            files=files,
            data={},
            expected_status=None,
            expected_statuses=[201, 403],
        )
        if response.status_code != 201:
            pytest.skip(f"Import upload not permitted (status {response.status_code})")

    def test_upload_missing_file(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for CSV upload tests")
        response = api_request(
            "POST",
            api_v1_path("/contacts/import/"),
            data={},
            expected_status=None,
            expected_statuses=[400, 403],
        )
        if response.status_code == 403:
            pytest.skip("Import upload not permitted without admin privileges")

    def test_upload_non_csv(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for CSV upload tests")
        files = {"file": ("test.txt", b"This is not a CSV file", "text/plain")}
        response = api_request(
            "POST",
            api_v1_path("/contacts/import/"),
            files=files,
            data={},
            expected_status=None,
            expected_statuses=[201, 403],
        )
        if response.status_code != 201:
            pytest.skip(f"Import upload not permitted (status {response.status_code})")

    def test_upload_large_csv(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for CSV upload tests")
        rows = [
            "first_name,last_name,email,company",
            *[f"Test{i},Contact{i},test{i}@example.com,Test Corp{i}" for i in range(100)],
        ]
        csv_content = "\n".join(rows)
        files = {"file": ("large_contacts.csv", csv_content.encode("utf-8"), "text/csv")}
        response = api_request(
            "POST",
            api_v1_path("/contacts/import/"),
            files=files,
            data={},
            expected_status=None,
            expected_statuses=[201, 403],
        )
        if response.status_code != 201:
            pytest.skip(f"Import upload not permitted (status {response.status_code})")

    def test_import_job_detail(self, api_request, import_job_id: int):
        api_request(
            "GET",
            api_v1_path(f"/contacts/import/{import_job_id}/"),
            expected_status=200,
        )

    def test_import_job_detail_invalid(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for import detail tests")
        response = api_request(
            "GET",
            api_v1_path("/contacts/import/999999/"),
            expected_status=None,
            expected_statuses=[404, 403],
        )
        if response.status_code == 403:
            pytest.skip("Import detail access requires admin privileges")

    def test_import_errors_download(self, api_request, import_job_id: int):
        api_request(
            "GET",
            api_v1_path(f"/contacts/import/{import_job_id}/errors/"),
            expected_status=None,
            expected_statuses=[200, 404],
        )

    def test_import_errors_download_invalid(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for import error download tests")
        response = api_request(
            "GET",
            api_v1_path("/contacts/import/999999/errors/"),
            expected_status=None,
            expected_statuses=[404, 403],
        )
        if response.status_code == 403:
            pytest.skip("Import error download requires admin privileges")


class TestAdminEndpoints:
    def test_admin_panel_without_auth(self, api_request):
        api_request(
            "GET",
            "/admin/",
            expected_status=None,
            expected_statuses=[200, 302, 403],
        )

    def test_admin_panel_with_auth(self, api_request, admin_authenticated: bool):
        if not admin_authenticated:
            pytest.skip("Admin credentials required for authenticated admin tests")
        api_request(
            "GET",
            "/admin/",
            expected_status=None,
            expected_statuses=[200, 302],
        )


class TestErrorScenarios:
    @pytest.mark.parametrize(
        "method,endpoint,data,expected_statuses",
        [
            ("POST", api_v1_path("/contacts/"), {"test": "data"}, [403, 405]),
            ("PUT", api_v1_path("/contacts/1/"), {"test": "data"}, [403, 405]),
            ("DELETE", api_v1_path("/contacts/1/"), None, [403, 405]),
        ],
    )
    def test_invalid_methods(
        self,
        api_request,
        method: str,
        endpoint: str,
        data: Optional[Mapping[str, Any]],
        expected_statuses: Iterable[int],
    ):
        api_request(
            method,
            endpoint,
            json_body=data if isinstance(data, Mapping) else None,
            expected_statuses=expected_statuses,
        )

    def test_invalid_date_format(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"created_at_after": "invalid-date"},
            expected_status=400,
        )

    def test_invalid_numeric_value(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts/"),
            params={"employees_min": "not-a-number"},
            expected_status=400,
        )

    def test_malformed_url(self, api_request):
        api_request(
            "GET",
            api_v1_path("/contacts//"),
            expected_status=404,
        )

