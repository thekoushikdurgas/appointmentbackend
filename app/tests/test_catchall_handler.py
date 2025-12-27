import pytest

import app.utils.catchall_handler as module
from app.schemas.email import EmailVerificationStatus
from app.utils.catchall_handler import handle_catchall_email


class DummyIcyPeasServiceSuccess:
    def __init__(self, email: str, certainty: str):
        self._email = email
        self._certainty = certainty

    async def search_email(self, *args, **kwargs):  # type: ignore[override]
        return {"email": self._email, "certainty": self._certainty}


class DummyIcyPeasServiceFailure:
    async def search_email(self, *args, **kwargs):  # type: ignore[override]
        return None


@pytest.mark.asyncio
async def test_handle_catchall_email_icypeas_success(monkeypatch):
    # Patch IcyPeasService used inside handle_catchall_email
    monkeypatch.setattr(module, "IcyPeasService", lambda: DummyIcyPeasServiceSuccess("icypeas@example.com", "ultra_sure"))

    email, status, certainty = await handle_catchall_email(
        first_name="John",
        last_name="Doe",
        domain="example.com",
        catchall_email="catchall@example.com",
        catchall_status=EmailVerificationStatus.CATCHALL,
    )

    assert email == "icypeas@example.com"
    assert status == EmailVerificationStatus.VALID
    assert certainty == "ultra_sure"


@pytest.mark.asyncio
async def test_handle_catchall_email_icypeas_failure(monkeypatch):
    monkeypatch.setattr(module, "IcyPeasService", lambda: DummyIcyPeasServiceFailure())

    email, status, certainty = await handle_catchall_email(
        first_name="John",
        last_name="Doe",
        domain="example.com",
        catchall_email="catchall@example.com",
        catchall_status=EmailVerificationStatus.CATCHALL,
    )

    assert email == "catchall@example.com"
    assert status == EmailVerificationStatus.CATCHALL
    assert certainty is None
