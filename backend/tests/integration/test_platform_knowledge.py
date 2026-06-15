import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import assign_platform_role
from app.config import Settings, get_settings
from app.core.database import Database, get_session
from app.domains.admin.knowledge_models import PlatformKnowledgeVersion
from app.main import app


def _client(database: Database, tmp_path: Path) -> TestClient:
    settings = Settings(
        app_environment="test",
        enable_database=True,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'knowledge.db'}",
    )

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _register(client: TestClient, email: str, organization_name: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long passphrase 2026!",
            "display_name": "知识管理员",
            "organization_name": organization_name,
        },
    )
    assert response.status_code == 201


def _login(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Long passphrase 2026!"},
    )
    assert response.status_code == 200


def _promote(database: Database, email: str) -> None:
    asyncio.run(
        assign_platform_role(
            email,
            "platform_admin",
            database,
            reason="Platform knowledge workflow test",
        )
    )


def test_cancel_route_change_requires_review_publish_and_supports_rollback(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(client, "knowledge-author@example.com", "Knowledge Author")
            _promote(database, "knowledge-author@example.com")
            client.post("/api/v1/auth/logout")
            _register(client, "knowledge-reviewer@example.com", "Knowledge Reviewer")
            _promote(database, "knowledge-reviewer@example.com")
            client.post("/api/v1/auth/logout")
            _login(client, "knowledge-author@example.com")

            created = client.post(
                "/api/v1/admin/cancellation-routes",
                json={
                    "key": "vendor-example",
                    "data": {
                        "vendor_key": "vendor-example",
                        "url": "https://vendor.example/cancel-v1",
                        "instructions": ["打开账户设置", "选择取消订阅"],
                    },
                    "change_summary": "Initial verified cancellation route",
                },
            )
            assert created.status_code == 201
            first_version = created.json()["version"]
            assert first_version["status"] == "draft"

            hidden = client.get(
                "/api/v1/catalog/cancellation-routes/vendor-example"
            )
            assert hidden.status_code == 404

            submitted = client.post(
                f"/api/v1/admin/knowledge/versions/{first_version['id']}/submit-review"
            )
            assert submitted.status_code == 200
            assert submitted.json()["status"] == "in_review"

            client.post("/api/v1/auth/logout")
            _login(client, "knowledge-reviewer@example.com")
            approved = client.post(
                f"/api/v1/admin/knowledge/versions/{first_version['id']}/approve"
            )
            assert approved.status_code == 200
            assert approved.json()["status"] == "approved"
            published = client.post(
                f"/api/v1/admin/knowledge/versions/{first_version['id']}/publish",
                json={
                    "reason": "Reviewed route ready for customers",
                    "reauth_confirmed": True,
                    "reauth_password": "Long passphrase 2026!",
                },
            )
            assert published.status_code == 200
            assert published.json()["version"]["status"] == "published"

            public_v1 = client.get(
                "/api/v1/catalog/cancellation-routes/vendor-example"
            )
            assert public_v1.status_code == 200
            assert public_v1.json()["data"]["url"].endswith("cancel-v1")

            client.post("/api/v1/auth/logout")
            _login(client, "knowledge-author@example.com")
            second = client.post(
                f"/api/v1/admin/knowledge/{created.json()['entry']['id']}/drafts",
                json={
                    "data": {
                        "vendor_key": "vendor-example",
                        "url": "https://vendor.example/cancel-v2",
                        "instructions": ["打开新版账户中心", "确认取消"],
                    },
                    "change_summary": "Vendor launched a new cancellation flow",
                },
            )
            assert second.status_code == 201
            second_version = second.json()
            assert second_version["version_number"] == 2
            assert client.get(
                "/api/v1/catalog/cancellation-routes/vendor-example"
            ).json()["data"]["url"].endswith("cancel-v1")

            client.post(
                f"/api/v1/admin/knowledge/versions/{second_version['id']}/submit-review"
            )
            client.post("/api/v1/auth/logout")
            _login(client, "knowledge-reviewer@example.com")
            client.post(
                f"/api/v1/admin/knowledge/versions/{second_version['id']}/approve"
            )
            client.post(
                f"/api/v1/admin/knowledge/versions/{second_version['id']}/publish",
                json={
                    "reason": "Reviewed replacement route",
                    "reauth_confirmed": True,
                    "reauth_password": "Long passphrase 2026!",
                },
            )
            assert client.get(
                "/api/v1/catalog/cancellation-routes/vendor-example"
            ).json()["data"]["url"].endswith("cancel-v2")

            rolled_back = client.post(
                f"/api/v1/admin/knowledge/{created.json()['entry']['id']}/rollback",
                json={
                    "target_version": 1,
                    "reason": "Vendor reverted the cancellation flow",
                    "reauth_confirmed": True,
                    "reauth_password": "Long passphrase 2026!",
                },
            )
            assert rolled_back.status_code == 200
            assert rolled_back.json()["version"]["version_number"] == 3
            assert client.get(
                "/api/v1/catalog/cancellation-routes/vendor-example"
            ).json()["data"]["url"].endswith("cancel-v1")

            async def version_states() -> list[str]:
                async with database.session_factory() as session:
                    versions = list(
                        (
                            await session.scalars(
                                select(PlatformKnowledgeVersion).order_by(
                                    PlatformKnowledgeVersion.version_number
                                )
                            )
                        ).all()
                    )
                    return [version.status for version in versions]

            assert asyncio.run(version_states()) == [
                "superseded",
                "superseded",
                "published",
            ]
    finally:
        app.dependency_overrides.clear()


def test_all_global_knowledge_types_share_the_versioned_workflow(
    database: Database,
    tmp_path: Path,
) -> None:
    client_context = _client(database, tmp_path)
    try:
        with client_context as client:
            _register(client, "catalog-admin@example.com", "Catalog Admin")
            _promote(database, "catalog-admin@example.com")
            client.post("/api/v1/auth/logout")
            _login(client, "catalog-admin@example.com")

            endpoints = {
                "software-directory": "software",
                "vendor-directory": "vendor",
                "merchant-aliases": "merchant_alias",
                "cancellation-routes": "cancellation_route",
                "risk-rules": "risk_rule",
                "ai-prompts": "ai_prompt",
            }
            for path, object_type in endpoints.items():
                response = client.post(
                    f"/api/v1/admin/{path}",
                    json={
                        "key": f"{object_type}-example",
                        "data": {"name": f"{object_type} example"},
                        "change_summary": "Initial draft",
                    },
                )
                assert response.status_code == 201, path
                assert response.json()["entry"]["object_type"] == object_type

                listed = client.get(f"/api/v1/admin/{path}")
                assert listed.status_code == 200
                assert listed.json()["items"][0]["entry"]["object_type"] == object_type
    finally:
        app.dependency_overrides.clear()
