import pytest

from app.services.icypeas_service import IcyPeasService


@pytest.mark.asyncio
async def test_extract_best_email_prefers_higher_certainty(monkeypatch):
    service = IcyPeasService
    # Use staticmethod directly
    results = {
        "emails": [
            {"email": "a@example.com", "certainty": "probable"},
            {"email": "b@example.com", "certainty": "ultra_sure"},
            {"email": "c@example.com", "certainty": "sure"},
        ]
    }

    best = service._extract_best_email(results)  # type: ignore[attr-defined]
    assert best["email"] == "b@example.com"


@pytest.mark.asyncio
async def test_extract_best_email_returns_none_when_no_certainty():
    service = IcyPeasService
    results = {
        "emails": [
            {"email": "a@example.com", "certainty": ""},
        ]
    }

    best = service._extract_best_email(results)  # type: ignore[attr-defined]
    assert best is None
