import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.compliance.controls import (
    ComplianceControlService,
    CreateControl,
    CreateEvidence,
    CreateFramework,
)
from app.domains.compliance.models import (
    ComplianceControl,
    IncidentTask,
    SecurityIncident,
)
from app.domains.compliance.router import (
    storage_from_request as compliance_storage_from_request,
)
from app.domains.files.models import StoredFile
from app.domains.files.router import storage_from_request as file_storage_from_request
from app.domains.organizations.models import OrganizationMember
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.storage.local import LocalObjectStorage
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "合规负责人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def _client(
    database: Database,
    tmp_path: Path,
) -> tuple[TestClient, LocalObjectStorage]:
    storage = LocalObjectStorage(tmp_path / "objects", "compliance-secret")
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'compliance-controls.db'}",
        local_storage_path=tmp_path / "objects",
        storage_signing_secret="compliance-secret",
        storage_presign_expires_seconds=600,
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[compliance_storage_from_request] = lambda: storage
    app.dependency_overrides[file_storage_from_request] = lambda: storage
    return TestClient(app), storage


async def _seed_file(
    database: Database,
    storage: LocalObjectStorage,
    organization_id: UUID,
    *,
    filename: str = "soc2-evidence.pdf",
) -> StoredFile:
    file_id = uuid4()
    key = f"files/{organization_id}/{file_id}/{filename}"
    storage.write_bytes(key, b"%PDF-1.7\ncontrol evidence", "application/pdf")
    async with database.session_factory() as session:
        stored_file = StoredFile(
            id=file_id,
            organization_id=organization_id,
            filename=filename,
            content_type="application/pdf",
            size_bytes=32,
            status="available",
            quarantine_key=f"quarantine/{organization_id}/{file_id}/{filename}",
            storage_key=key,
        )
        session.add(stored_file)
        await session.commit()
        return stored_file


def test_expired_evidence_marks_control_attention_required(
    database: Database,
    tmp_path: Path,
) -> None:
    async def run() -> None:
        organization_id = uuid4()
        user_id = uuid4()
        storage = LocalObjectStorage(tmp_path / "objects", "test-secret")
        stored_file = await _seed_file(database, storage, organization_id)
        context = OrganizationContext(
            organization_id=organization_id,
            user_id=user_id,
            membership_id=uuid4(),
            role="owner",
        )
        async with database.session_factory() as session:
            service = ComplianceControlService(session)
            framework = await service.create_framework(
                context,
                CreateFramework(
                    code="SOC2",
                    name="SOC 2",
                    version="2022",
                    description="安全与可用性控制",
                ),
            )
            control = await service.create_control(
                context,
                framework.id,
                CreateControl(
                    code="CC6.1",
                    title="逻辑访问控制",
                    description="限制系统访问",
                    frequency_days=90,
                ),
            )
            evidence = await service.add_evidence(
                context,
                control.id,
                CreateEvidence(
                    stored_file_id=stored_file.id,
                    title="季度访问复核",
                    description="2026 Q2 访问复核记录",
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                ),
            )

            refreshed = await service.refresh_control_status(context, control.id)

            assert evidence.status == "expired"
            assert refreshed.status == "attention_required"
            current = await session.get(ComplianceControl, control.id)
            assert current is not None
            assert current.status == "attention_required"

    asyncio.run(run())


def test_compliance_api_manages_controls_evidence_reviews_and_audited_downloads(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context, storage = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, user_id = _register(
                client,
                "controls@example.com",
                "控制组织",
            )
            stored_file = asyncio.run(
                _seed_file(database, storage, UUID(organization_id))
            )

            framework = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/frameworks",
                json={
                    "code": "SOC2",
                    "name": "SOC 2",
                    "version": "2022",
                    "description": "安全与可用性控制",
                },
            )
            assert framework.status_code == 201
            framework_id = framework.json()["id"]

            control = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/frameworks/"
                f"{framework_id}/controls",
                json={
                    "code": "CC6.1",
                    "title": "逻辑访问控制",
                    "description": "限制系统访问",
                    "frequency_days": 90,
                },
            )
            assert control.status_code == 201
            control_id = control.json()["id"]

            owner = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/controls/"
                f"{control_id}/owners",
                json={"user_id": user_id, "role": "owner"},
            )
            assert owner.status_code == 201

            evidence = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/controls/"
                f"{control_id}/evidence",
                json={
                    "stored_file_id": str(stored_file.id),
                    "title": "季度访问复核",
                    "description": "2026 Q2 访问复核记录",
                    "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                },
            )
            assert evidence.status_code == 201
            evidence_id = evidence.json()["id"]
            assert evidence.json()["status"] == "active"

            review = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/controls/"
                f"{control_id}/reviews",
                json={
                    "outcome": "effective",
                    "notes": "证据充分，控制有效。",
                },
            )
            assert review.status_code == 201
            assert review.json()["outcome"] == "effective"

            refreshed = client.post(
                f"/api/v1/organizations/{organization_id}/compliance/controls/"
                f"{control_id}/refresh-status"
            )
            assert refreshed.status_code == 200
            assert refreshed.json()["status"] == "effective"
            assert refreshed.json()["owners"][0]["user_id"] == user_id
            assert refreshed.json()["evidence"][0]["id"] == evidence_id

            downloaded = client.get(
                f"/api/v1/organizations/{organization_id}/compliance/evidence/"
                f"{evidence_id}/download"
            )
            assert downloaded.status_code == 200
            assert downloaded.json()["expires_in"] == 600
            assert "local-download" in downloaded.json()["download_url"]
            assert client.get(downloaded.json()["download_url"]).content.startswith(b"%PDF")

            audit_logs = client.get(
                f"/api/v1/organizations/{organization_id}/audit-logs"
            )
            assert audit_logs.status_code == 200
            assert any(
                item["action"] == "compliance.evidence.downloaded"
                and item["resource_id"] == evidence_id
                for item in audit_logs.json()["items"]
            )

            client.post("/api/v1/auth/logout")
            _, member_user_id = _register(
                client,
                "controls-member@example.com",
                "成员自己的组织",
            )

            async def add_member() -> None:
                async with database.session_factory() as session:
                    session.add(
                        OrganizationMember(
                            organization_id=UUID(organization_id),
                            user_id=UUID(member_user_id),
                            role="member",
                            status="active",
                        )
                    )
                    await session.commit()

            asyncio.run(add_member())
            forbidden = client.get(
                f"/api/v1/organizations/{organization_id}/compliance/evidence/"
                f"{evidence_id}/download"
            )
            assert forbidden.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_security_incident_tasks_are_tenant_scoped_and_completable(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context, _ = _client(database, tmp_path)
    try:
        with client_context as client:
            organization_id, user_id = _register(
                client,
                "incident@example.com",
                "事件组织",
            )
            incident = client.post(
                f"/api/v1/organizations/{organization_id}/security/incidents",
                json={
                    "title": "身份提供商异常登录",
                    "severity": "high",
                    "summary": "检测到异常国家登录尝试。",
                    "detected_at": datetime.now(UTC).isoformat(),
                },
            )
            assert incident.status_code == 201
            incident_id = incident.json()["id"]
            assert incident.json()["status"] == "open"

            task = client.post(
                f"/api/v1/organizations/{organization_id}/security/incidents/"
                f"{incident_id}/tasks",
                json={
                    "title": "撤销可疑会话",
                    "assignee_user_id": user_id,
                    "due_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
                },
            )
            assert task.status_code == 201
            task_id = task.json()["id"]

            completed = client.patch(
                f"/api/v1/organizations/{organization_id}/security/incidents/"
                f"{incident_id}/tasks/{task_id}",
                json={"status": "completed"},
            )
            assert completed.status_code == 200
            assert completed.json()["status"] == "completed"
            assert completed.json()["completed_at"] is not None

            detail = client.get(
                f"/api/v1/organizations/{organization_id}/security/incidents/"
                f"{incident_id}"
            )
            assert detail.status_code == 200
            assert detail.json()["tasks"][0]["id"] == task_id

            client.post("/api/v1/auth/logout")
            other_org_id, _ = _register(
                client,
                "incident-other@example.com",
                "其他事件组织",
            )
            hidden = client.get(
                f"/api/v1/organizations/{other_org_id}/security/incidents/"
                f"{incident_id}"
            )
            assert hidden.status_code == 404

            async def verify_records() -> None:
                async with database.session_factory() as session:
                    incident_record = await session.get(
                        SecurityIncident,
                        UUID(incident_id),
                    )
                    assert incident_record is not None
                    task_record = await session.scalar(
                        select(IncidentTask).where(
                            IncidentTask.id == UUID(task_id),
                            IncidentTask.organization_id == UUID(organization_id),
                        )
                    )
                    assert task_record is not None
                    assert task_record.status == "completed"

            asyncio.run(verify_records())
    finally:
        app.dependency_overrides.clear()
