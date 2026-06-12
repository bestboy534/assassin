import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.compliance.models import DeletionJob, DeletionJobItem, LegalHold
from app.domains.compliance.service import (
    CreateLegalHold,
    CreateRetentionPolicy,
    RetentionService,
)
from app.domains.files.models import StoredFile
from app.infrastructure.storage.local import LocalObjectStorage
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "数据保护负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


async def _seed_available_file(
    database: Database,
    organization_id: str,
    *,
    file_id: UUID,
    filename: str,
    days_old: int,
) -> StoredFile:
    async with database.session_factory() as session:
        stored_file = StoredFile(
            id=file_id,
            organization_id=UUID(organization_id),
            filename=filename,
            content_type="application/pdf",
            size_bytes=128,
            status="available",
            quarantine_key=f"quarantine/{organization_id}/{file_id}/{filename}",
            storage_key=f"files/{organization_id}/{file_id}/{filename}",
            created_at=datetime.now(UTC) - timedelta(days=days_old),
        )
        session.add(stored_file)
        await session.commit()
        return stored_file


def test_legal_hold_prevents_file_deletion(database: Database, tmp_path: Path) -> None:
    async def run() -> None:
        organization_id = UUID("00000000-0000-0000-0000-000000000001")
        user_id = UUID("00000000-0000-0000-0000-000000000002")
        held_file_id = UUID("00000000-0000-0000-0000-000000000003")
        deleted_file_id = UUID("00000000-0000-0000-0000-000000000004")
        storage = LocalObjectStorage(tmp_path / "objects", "test-secret")
        async with database.session_factory() as session:
            held_file = StoredFile(
                id=held_file_id,
                organization_id=organization_id,
                filename="held.pdf",
                content_type="application/pdf",
                size_bytes=128,
                status="available",
                quarantine_key=f"quarantine/{organization_id}/{held_file_id}/held.pdf",
                storage_key=f"files/{organization_id}/{held_file_id}/held.pdf",
                created_at=datetime.now(UTC) - timedelta(days=40),
            )
            expired_file = StoredFile(
                id=deleted_file_id,
                organization_id=organization_id,
                filename="expired.pdf",
                content_type="application/pdf",
                size_bytes=128,
                status="available",
                quarantine_key=f"quarantine/{organization_id}/{deleted_file_id}/expired.pdf",
                storage_key=f"files/{organization_id}/{deleted_file_id}/expired.pdf",
                created_at=datetime.now(UTC) - timedelta(days=40),
            )
            session.add_all([held_file, expired_file])
            await session.commit()
            storage.write_bytes(held_file.storage_key or "", b"held", "application/pdf")
            storage.write_bytes(expired_file.storage_key or "", b"expired", "application/pdf")

            service = RetentionService(session, storage=storage)
            await service.create_policy(
                organization_id=organization_id,
                created_by_user_id=user_id,
                body=CreateRetentionPolicy(
                    data_type="stored_file",
                    retention_days=30,
                    description="原始上传文件 30 天后删除",
                ),
            )
            await service.create_legal_hold(
                organization_id=organization_id,
                created_by_user_id=user_id,
                body=CreateLegalHold(
                    resource_type="stored_file",
                    resource_id=str(held_file_id),
                    reason="合同纠纷证据保留",
                ),
            )

            result = await service.delete_expired(
                organization_id=organization_id,
                actor_user_id=user_id,
                reauth_confirmed=True,
            )

            assert str(held_file_id) in result.skipped_legal_hold
            assert str(deleted_file_id) in result.deleted_resource_ids
            assert storage.read_bytes(held_file.storage_key or "") == b"held"
            assert (await session.get(StoredFile, held_file_id)).status == "available"  # type: ignore[union-attr]
            assert (await session.get(StoredFile, deleted_file_id)).status == "deleted"  # type: ignore[union-attr]
            assert (
                await session.scalar(
                    select(DeletionJobItem).where(
                        DeletionJobItem.resource_id == str(held_file_id),
                        DeletionJobItem.status == "skipped",
                    )
                )
            ) is not None

    asyncio.run(run())


def test_retention_api_previews_and_executes_deletion_with_audit(
    database: Database,
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'retention.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            org_id, _ = _register(client, "retention@example.com", "保留组织")
            held_id = UUID("00000000-0000-0000-0000-000000000103")
            delete_id = UUID("00000000-0000-0000-0000-000000000104")
            asyncio.run(
                _seed_available_file(
                    database,
                    org_id,
                    file_id=held_id,
                    filename="held.pdf",
                    days_old=45,
                )
            )
            asyncio.run(
                _seed_available_file(
                    database,
                    org_id,
                    file_id=delete_id,
                    filename="delete.pdf",
                    days_old=45,
                )
            )

            policy = client.post(
                f"/api/v1/organizations/{org_id}/retention-policies",
                json={
                    "data_type": "stored_file",
                    "retention_days": 30,
                    "description": "文件保留 30 天",
                },
            )
            assert policy.status_code == 201

            hold = client.post(
                f"/api/v1/organizations/{org_id}/legal-holds",
                json={
                    "resource_type": "stored_file",
                    "resource_id": str(held_id),
                    "reason": "监管调查",
                },
            )
            assert hold.status_code == 201
            assert hold.json()["resource_id"] == str(held_id)

            preview = client.get(
                f"/api/v1/organizations/{org_id}/retention/deletion-preview",
                params={"data_type": "stored_file"},
            )
            assert preview.status_code == 200
            assert str(delete_id) in preview.json()["delete_candidates"]
            assert str(held_id) in preview.json()["skipped_legal_hold"]

            blocked = client.post(
                f"/api/v1/organizations/{org_id}/retention/deletion-jobs",
                json={"data_type": "stored_file", "reauth_confirmed": False},
            )
            assert blocked.status_code == 403

            executed = client.post(
                f"/api/v1/organizations/{org_id}/retention/deletion-jobs",
                json={"data_type": "stored_file", "reauth_confirmed": True},
            )
            assert executed.status_code == 201
            assert executed.json()["deleted_resource_ids"] == [str(delete_id)]
            assert executed.json()["skipped_legal_hold"] == [str(held_id)]

            async def verify_records() -> None:
                async with database.session_factory() as session:
                    job = await session.scalar(
                        select(DeletionJob).where(DeletionJob.organization_id == UUID(org_id))
                    )
                    assert job is not None
                    assert job.status == "succeeded"
                    hold_record = await session.scalar(
                        select(LegalHold).where(LegalHold.resource_id == str(held_id))
                    )
                    assert hold_record is not None
                    deleted_file = await session.get(StoredFile, delete_id)
                    assert deleted_file is not None
                    assert deleted_file.status == "deleted"

            asyncio.run(verify_records())

            audit_logs = client.get(f"/api/v1/organizations/{org_id}/audit-logs")
            assert audit_logs.status_code == 200
            assert any(
                item["action"] == "retention.deletion_job.completed"
                for item in audit_logs.json()["items"]
            )
    finally:
        app.dependency_overrides.clear()
