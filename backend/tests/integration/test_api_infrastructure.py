from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.files.router import storage_from_request
from app.domains.jobs.router import queue_from_request
from app.infrastructure.queue.client import InMemoryJobQueue
from app.infrastructure.storage.local import LocalObjectStorage
from app.main import app, optional_session


def test_local_file_flow_over_http(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}",
        local_storage_path=tmp_path / "objects",
        storage_signing_secret="test-secret",
    )
    queue = InMemoryJobQueue()
    storage = LocalObjectStorage(tmp_path / "objects", "test-secret")

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[queue_from_request] = lambda: queue
    app.dependency_overrides[storage_from_request] = lambda: storage
    organization_id = str(uuid4())
    headers = {"X-Organization-ID": organization_id}

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/files/uploads",
                headers=headers,
                json={"filename": "invoice.pdf", "content_type": "application/pdf"},
            )
            assert create_response.status_code == 201
            upload = create_response.json()

            assert (
                client.put(
                    upload["upload_url"],
                    content=b"%PDF-1.7\nlocal integration test",
                    headers={"Content-Type": "application/pdf"},
                ).status_code
                == 204
            )

            complete_response = client.post(
                f"/api/v1/files/{upload['id']}/complete",
                headers=headers,
            )
            assert complete_response.status_code == 200
            assert complete_response.json()["status"] == "available"

            download_response = client.get(
                f"/api/v1/files/{upload['id']}/download",
                headers=headers,
            )
            assert download_response.status_code == 200
            object_response = client.get(download_response.json()["download_url"])
            assert object_response.status_code == 200
            assert object_response.content.startswith(b"%PDF-")

            assert (
                client.get(
                    f"/api/v1/files/{upload['id']}",
                    headers={"X-Organization-ID": str(uuid4())},
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()


def test_existing_bill_audit_history_contract(database: Database) -> None:
    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[optional_session] = session_override
    payload = {
        "source_hint": "csv",
        "raw_text": "2026-05-01,OPENAI *CHATGPT SUBSCRIP,20.00,USD",
    }

    try:
        with TestClient(app) as client:
            assert client.get("/ready").status_code == 200
            analyze_response = client.post("/api/analyze", json=payload)
            assert analyze_response.status_code == 200
            run_id = analyze_response.json()["run_id"]
            assert run_id

            history_response = client.get("/api/history")
            assert history_response.status_code == 200
            assert history_response.json()["items"][0]["id"] == run_id

            detail_response = client.get(f"/api/history/{run_id}")
            assert detail_response.status_code == 200
            assert detail_response.json()["items"][0]["software_name"] == "ChatGPT Plus"
    finally:
        app.dependency_overrides.clear()
