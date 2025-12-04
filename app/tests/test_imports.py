from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.imports import ContactImportJob, ImportJobStatus
from app.tests.factories import create_import_job


@pytest.mark.asyncio
async def test_import_info_endpoint(async_client):
    response = await async_client.get("/api/v1/contacts/import/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"].startswith("Upload a CSV file")


@pytest.mark.asyncio
async def test_upload_contacts_import_success(async_client, db_session, monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    captured: dict[str, str] = {}

    def fake_delay(job_id: str, file_path: str):
        captured["job_id"] = job_id
        captured["file_path"] = file_path

    monkeypatch.setattr(
        "app.api.v1.endpoints.imports.process_contacts_import.delay",
        fake_delay,
    )

    async def fake_create_job(self, session, *, job_id: str, file_name: str, file_path: str, total_rows: int = 0):
        job = await create_import_job(
            session,
            job_id=job_id,
            file_name=file_name,
            file_path=file_path,
            total_rows=total_rows,
        )
        await session.commit()
        return job

    monkeypatch.setattr(
        "app.services.import_service.ImportService.create_job",
        fake_create_job,
    )

    files = {"file": ("sample.csv", b"email\nfoo@example.com\n", "text/csv")}
    response = await async_client.post("/api/v1/contacts/import/", files=files)
    assert response.status_code == 202

    payload = response.json()
    assert payload["job_id"] == captured["job_id"]
    assert Path(captured["file_path"]).exists()

    result = await db_session.execute(
        select(ContactImportJob).where(ContactImportJob.job_id == payload["job_id"])
    )
    job = result.scalar_one()
    assert job.file_name == "sample.csv"


@pytest.mark.asyncio
async def test_upload_contacts_import_missing_filename(async_client, monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    files = {"file": ("", b"email\nfoo@example.com\n", "text/csv")}
    response = await async_client.post("/api/v1/contacts/import/", files=files)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_contacts_import_empty_file(async_client, monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    files = {"file": ("empty.csv", b"", "text/csv")}
    response = await async_client.post("/api/v1/contacts/import/", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


@pytest.mark.asyncio
async def test_import_job_detail_with_and_without_errors(async_client, db_session):
    job_with_errors = await create_import_job(
        db_session,
        status=ImportJobStatus.completed,
        errors=[
            {"row_number": 1, "error_message": "Invalid email", "payload": '{"email": "bad"}'},
            {"row_number": 2, "error_message": "Missing name", "payload": '{"name": ""}'},
        ],
    )
    job_without_errors = await create_import_job(
        db_session,
        status=ImportJobStatus.processing,
        job_id="job-no-errors",
    )

    response_with = await async_client.get(
        f"/api/v1/contacts/import/{job_with_errors.job_id}/",
        params={"include_errors": "true"},
    )
    assert response_with.status_code == 200
    payload_with = response_with.json()
    assert payload_with["status"] == ImportJobStatus.completed
    assert len(payload_with["errors"]) == 2

    response_without = await async_client.get(
        f"/api/v1/contacts/import/{job_without_errors.job_id}/",
    )
    assert response_without.status_code == 200
    payload_without = response_without.json()
    assert "errors" not in payload_without
    assert payload_without["status"] == ImportJobStatus.processing


@pytest.mark.asyncio
async def test_import_job_detail_not_found(async_client):
    response = await async_client.get("/api/v1/contacts/import/unknown-job/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Import job not found"


@pytest.mark.asyncio
async def test_download_import_errors(async_client, db_session):
    job = await create_import_job(
        db_session,
        job_id="errors-job",
        errors=[
            {"row_number": 1, "error_message": "First error"},
            {"row_number": 3, "error_message": "Second error"},
        ],
    )

    response = await async_client.get(f"/api/v1/contacts/import/{job.job_id}/errors/")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["row_number"] == 1


@pytest.mark.asyncio
async def test_download_import_errors_not_found(async_client):
    response = await async_client.get("/api/v1/contacts/import/missing/errors/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Import job not found"

