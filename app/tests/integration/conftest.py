import pytest

try:  # pragma: no cover - dependency import guard
    import requests  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - explicit failure message
    raise RuntimeError(
        "The 'requests' package is required to run the API integration tests."
    ) from exc

from .recorder import APITestRecorder


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("api", "API integration test configuration")
    group.addoption(
        "--api-base-url",
        action="store",
        default="http://127.0.0.1:8000",
        dest="api_base_url",
        help="Base URL for hitting the running Contact360 API service.",
    )
    group.addoption(
        "--api-admin-username",
        action="store",
        default=None,
        dest="api_admin_username",
        help="Admin username for endpoints requiring authentication.",
    )
    group.addoption(
        "--api-admin-password",
        action="store",
        default=None,
        dest="api_admin_password",
        help="Admin password for endpoints requiring authentication.",
    )
    group.addoption(
        "--api-timeout",
        action="store",
        type=float,
        default=120.0,
        dest="api_timeout",
        help="Timeout in seconds for HTTP requests performed by the integration suite.",
    )


@pytest.fixture(scope="session")
def api_base_url(pytestconfig: pytest.Config) -> str:
    return str(pytestconfig.getoption("api_base_url")).rstrip("/")


@pytest.fixture(scope="session")
def api_admin_credentials(pytestconfig: pytest.Config):
    username = pytestconfig.getoption("api_admin_username")
    password = pytestconfig.getoption("api_admin_password")
    if username and password:
        return {"username": username, "password": password}
    return None


@pytest.fixture(scope="session")
def api_timeout(pytestconfig: pytest.Config) -> float:
    return float(pytestconfig.getoption("api_timeout"))


@pytest.fixture(scope="session")
def api_session() -> requests.Session:
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def api_test_recorder(pytestconfig: pytest.Config, api_base_url: str) -> APITestRecorder:
    recorder = APITestRecorder(base_url=api_base_url)
    yield recorder
    outputs = recorder.write_outputs(pytestconfig)
    terminal = pytestconfig.pluginmanager.get_plugin("terminalreporter")
    if terminal is not None:
        terminal.write_line(f"API report: {outputs['report']}")
        terminal.write_line(f"API results JSON: {outputs['json']}")
        responses_dir = outputs.get("responses_dir")
        if responses_dir:
            terminal.write_line(f"API responses directory: {responses_dir}")

