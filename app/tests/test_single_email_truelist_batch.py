import pytest

from app.api.v2.endpoints.email import _verify_emails_batch_truelist
from app.schemas.email import EmailVerificationStatus


class DummyTruelistService:
    def __init__(self, status: EmailVerificationStatus = EmailVerificationStatus.VALID):
        self.status = status
        self.calls = []

    async def verify_emails(self, emails):
        self.calls.append(list(emails))
        # Return all emails with the same mapped_status
        return {
            e.lower().strip(): {"mapped_status": self.status.value}
            for e in emails
        }


@pytest.mark.asyncio
async def test_verify_emails_batch_truelist_uses_single_call_for_up_to_51():
    emails = [f"user{i}@example.com" for i in range(51)]
    service = DummyTruelistService(status=EmailVerificationStatus.VALID)

    email, status, checked = await _verify_emails_batch_truelist(emails, service)

    # All emails sent in a single call
    assert len(service.calls) == 1
    assert service.calls[0] == emails
    # First valid email returned
    assert email == emails[0].lower()
    assert status == EmailVerificationStatus.VALID
    assert checked == len(emails)
