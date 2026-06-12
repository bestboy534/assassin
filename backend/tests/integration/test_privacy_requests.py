import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.compliance.models import PrivacyRequest, PrivacyRequestAction
from app.domains.identity.models import User, UserSession
from app.domains.organizations.models import OrganizationMember
from app.main import app


def _register(client: TestClient, email: str, organization: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "隐私请求人",
            "organization_name": organization,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return payload["organizations"][0]["id"], payload["user"]["id"]


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'privacy.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_dsr_creation_requires_verified_identity(database: Database, tmp_path: Path) -> None:
    try:
        with _client(database, tmp_path) as client:
            _, user_id = _register(client, "unverified@example.com", "未验证组织")

            async def mark_unverified() -> None:
                async with database.session_factory() as session:
                    user = await session.get(User, UUID(user_id))
                    assert user is not None
                    user.email_verified_at = None
                    await session.commit()

            asyncio.run(mark_unverified())

            response = client.post(
                "/api/v1/privacy/requests",
                json={"type": "access"},
            )

            assert response.status_code == 403
            assert response.json()["detail"] == "Verified identity is required"
    finally:
        app.dependency_overrides.clear()


def test_access_request_exports_only_subject_data_with_processing_history(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            organization_id, user_id = _register(
                client,
                "privacy@example.com",
                "隐私组织",
            )
            client.post("/api/v1/auth/logout")
            _register(client, "other@example.com", "其他组织")
            client.post("/api/v1/auth/logout")
            assert (
                client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "privacy@example.com",
                        "password": "Long passphrase 2026!",
                    },
                ).status_code
                == 200
            )

            created = client.post(
                "/api/v1/privacy/requests",
                json={
                    "type": "access",
                    "scope": ["identity", "organization_memberships"],
                },
            )
            assert created.status_code == 201
            request_id = created.json()["id"]
            assert created.json()["status"] == "verified"
            assert created.json()["identity_verified_at"] is not None
            assert created.json()["due_at"] > created.json()["created_at"]

            processed = client.post(
                f"/api/v1/privacy/requests/{request_id}/process",
                json={"reauth_confirmed": True},
            )
            assert processed.status_code == 200
            payload = processed.json()
            assert payload["status"] == "completed"
            assert payload["result"]["machine_readable"]["identity"]["id"] == user_id
            assert payload["result"]["machine_readable"]["identity"]["email"] == (
                "privacy@example.com"
            )
            assert payload["result"]["machine_readable"]["organization_memberships"][0][
                "organization_id"
            ] == organization_id
            assert "other@example.com" not in processed.text
            assert "数据访问请求" in payload["result"]["human_readable"]
            assert [item["action"] for item in payload["processing_history"]] == [
                "created",
                "completed",
            ]

            listed = client.get("/api/v1/privacy/requests")
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()["items"]] == [request_id]

            async def verify_records() -> None:
                async with database.session_factory() as session:
                    request = await session.get(PrivacyRequest, UUID(request_id))
                    assert request is not None
                    assert request.subject_user_id == UUID(user_id)
                    actions = (
                        await session.scalars(
                            select(PrivacyRequestAction)
                            .where(PrivacyRequestAction.privacy_request_id == request.id)
                            .order_by(PrivacyRequestAction.created_at.asc())
                        )
                    ).all()
                    assert [action.action for action in actions] == ["created", "completed"]

            asyncio.run(verify_records())
    finally:
        app.dependency_overrides.clear()


def test_portability_request_returns_explicit_json_export(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            _, user_id = _register(
                client,
                "portable@example.com",
                "可移植组织",
            )
            created = client.post(
                "/api/v1/privacy/requests",
                json={"type": "portability"},
            )
            assert created.status_code == 201

            processed = client.post(
                f"/api/v1/privacy/requests/{created.json()['id']}/process",
                json={"reauth_confirmed": True},
            )

            assert processed.status_code == 200
            result = processed.json()["result"]
            assert result["export_format"] == "json"
            assert result["machine_readable"]["identity"]["id"] == user_id
            assert "数据可移植请求" in result["human_readable"]
    finally:
        app.dependency_overrides.clear()


def test_access_export_respects_requested_scope(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            _register(client, "scoped@example.com", "范围组织")
            created = client.post(
                "/api/v1/privacy/requests",
                json={"type": "access", "scope": ["identity"]},
            )
            assert created.status_code == 201

            processed = client.post(
                f"/api/v1/privacy/requests/{created.json()['id']}/process",
                json={"reauth_confirmed": True},
            )

            assert processed.status_code == 200
            exported = processed.json()["result"]["machine_readable"]
            assert "identity" in exported
            assert "organization_memberships" not in exported
    finally:
        app.dependency_overrides.clear()


def test_deletion_anonymizes_identity_deletes_sessions_and_retains_business_records(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            organization_id, user_id = _register(
                client,
                "delete-me@example.com",
                "删除请求组织",
            )
            created = client.post(
                "/api/v1/privacy/requests",
                json={"type": "deletion"},
            )
            assert created.status_code == 201

            processed = client.post(
                f"/api/v1/privacy/requests/{created.json()['id']}/process",
                json={"reauth_confirmed": True},
            )

            assert processed.status_code == 200
            result = processed.json()["result"]
            assert result["anonymized"] == [f"user:{user_id}"]
            assert result["deleted"] == [f"sessions:{user_id}"]
            assert f"organization_membership:{organization_id}" in result["retained"]
            assert "audit_logs:immutable" in result["retained"]

            async def verify_deletion() -> None:
                async with database.session_factory() as session:
                    user = await session.get(User, UUID(user_id))
                    assert user is not None
                    assert user.status == "privacy_deleted"
                    assert user.email_normalized.startswith(f"deleted+{user_id}@")
                    assert user.display_name == "已删除用户"
                    assert user.email_verified_at is None
                    assert (
                        await session.scalar(
                            select(UserSession).where(UserSession.user_id == UUID(user_id))
                        )
                    ) is None
                    membership = await session.scalar(
                        select(OrganizationMember).where(
                            OrganizationMember.organization_id == UUID(organization_id),
                            OrganizationMember.user_id == UUID(user_id),
                        )
                    )
                    assert membership is not None

            asyncio.run(verify_deletion())
    finally:
        app.dependency_overrides.clear()


def test_legal_hold_prevents_privacy_deletion(database: Database, tmp_path: Path) -> None:
    try:
        with _client(database, tmp_path) as client:
            organization_id, user_id = _register(
                client,
                "held-user@example.com",
                "法律保留组织",
            )
            hold = client.post(
                f"/api/v1/organizations/{organization_id}/legal-holds",
                json={
                    "resource_type": "user",
                    "resource_id": user_id,
                    "reason": "监管调查期间保留身份记录",
                },
            )
            assert hold.status_code == 201

            created = client.post(
                "/api/v1/privacy/requests",
                json={"type": "deletion"},
            )
            assert created.status_code == 201
            processed = client.post(
                f"/api/v1/privacy/requests/{created.json()['id']}/process",
                json={"reauth_confirmed": True},
            )

            assert processed.status_code == 200
            result = processed.json()["result"]
            assert result["anonymized"] == []
            assert result["deleted"] == []
            assert result["retained"] == [f"user:{user_id}:legal_hold"]

            async def verify_user_preserved() -> None:
                async with database.session_factory() as session:
                    user = await session.get(User, UUID(user_id))
                    assert user is not None
                    assert user.email_normalized == "held-user@example.com"
                    assert user.status == "active"

            asyncio.run(verify_user_preserved())
    finally:
        app.dependency_overrides.clear()


def test_user_legal_hold_requires_membership_in_the_same_organization(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            organization_id, _ = _register(
                client,
                "hold-owner@example.com",
                "保留发起组织",
            )
            client.post("/api/v1/auth/logout")
            _, other_user_id = _register(
                client,
                "outside-user@example.com",
                "外部组织",
            )
            client.post("/api/v1/auth/logout")
            assert (
                client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": "hold-owner@example.com",
                        "password": "Long passphrase 2026!",
                    },
                ).status_code
                == 200
            )

            response = client.post(
                f"/api/v1/organizations/{organization_id}/legal-holds",
                json={
                    "resource_type": "user",
                    "resource_id": other_user_id,
                    "reason": "不应允许跨组织保留",
                },
            )

            assert response.status_code == 404
            assert response.json()["detail"] == "Legal hold resource not found"
    finally:
        app.dependency_overrides.clear()


def test_correction_request_updates_allowed_identity_fields(
    database: Database,
    tmp_path: Path,
) -> None:
    try:
        with _client(database, tmp_path) as client:
            _, user_id = _register(client, "correct@example.com", "更正组织")
            created = client.post(
                "/api/v1/privacy/requests",
                json={
                    "type": "correction",
                    "requested_changes": {"display_name": "更正后的姓名"},
                },
            )
            assert created.status_code == 201

            processed = client.post(
                f"/api/v1/privacy/requests/{created.json()['id']}/process",
                json={"reauth_confirmed": True},
            )
            assert processed.status_code == 200
            assert processed.json()["result"]["corrected"] == ["display_name"]

            async def verify_correction() -> None:
                async with database.session_factory() as session:
                    user = await session.get(User, UUID(user_id))
                    assert user is not None
                    assert user.display_name == "更正后的姓名"
                    assert user.updated_at is not None

            asyncio.run(verify_correction())
    finally:
        app.dependency_overrides.clear()
