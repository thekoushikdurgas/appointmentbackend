import asyncio
from typing import Dict

import pytest

import app.services.truelist_service as truelist_module
from app.services.truelist_service import TruelistService


@pytest.mark.asyncio
async def test_truelist_verify_emails_chunks_by_51(monkeypatch):
    """TruelistService.verify_emails should chunk requests by 51 emails."""

    calls: list[Dict] = []

    class DummyResponse:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            # Return a minimal valid Truelist-like payload
            return {"emails": []}

    class DummyClient:
        def __init__(self):
            self.timeout = 30.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, params=None, headers=None):
            calls.append({"url": url, "params": params, "headers": headers})
            return DummyResponse()

    # Patch httpx.AsyncClient used inside TruelistService
    monkeypatch.setattr(truelist_module.httpx, "AsyncClient", lambda timeout=30.0: DummyClient())

    service = TruelistService()

    # 102 emails should result in 2 calls when chunk size is 51
    emails = [f"user{i}@example.com" for i in range(102)]

    await service.verify_emails(emails)

    # Expect 2 chunks: 51 + 51
    assert len(calls) == 2
    assert calls[0]["params"]["email"].count("@example.com") == 51
    assert calls[1]["params"]["email"].count("@example.com") == 51
