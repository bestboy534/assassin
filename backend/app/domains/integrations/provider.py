from dataclasses import dataclass
from typing import Any, Protocol


class ProviderPermanentError(Exception):
    pass


class ProviderAuthError(ProviderPermanentError):
    pass


@dataclass(frozen=True)
class ConnectionHealth:
    healthy: bool
    message: str


@dataclass(frozen=True)
class IntegrationRecord:
    external_id: str
    name: str
    category: str
    status: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class PullPage:
    records: list[IntegrationRecord]
    next_cursor: str | None
    has_more: bool


class IntegrationProvider(Protocol):
    async def test_connection(self, credentials: dict[str, str]) -> ConnectionHealth: ...

    async def pull(
        self,
        credentials: dict[str, str],
        resource_type: str,
        cursor: str | None,
        options: dict[str, Any],
    ) -> PullPage: ...


class FakeIdentityProvider:
    async def test_connection(self, credentials: dict[str, str]) -> ConnectionHealth:
        token = credentials.get("api_token", "")
        if not token.startswith("sandbox-"):
            raise ProviderAuthError("Sandbox API token is invalid")
        return ConnectionHealth(healthy=True, message="Sandbox 身份目录连接正常")

    async def pull(
        self,
        credentials: dict[str, str],
        resource_type: str,
        cursor: str | None,
        options: dict[str, Any],
    ) -> PullPage:
        await self.test_connection(credentials)
        if resource_type != "applications":
            raise ProviderPermanentError(f"Unsupported resource: {resource_type}")
        if cursor == "page-1" and int(options.get("fail_on_page", 0) or 0) == 2:
            raise ProviderPermanentError("Sandbox provider failed on page 2")
        if cursor is None:
            return PullPage(
                records=[
                    IntegrationRecord(
                        external_id="app-notion",
                        name="Notion",
                        category="collaboration",
                        status="active",
                        raw={"owner": "运营", "source": "fake_identity"},
                    )
                ],
                next_cursor="page-1",
                has_more=True,
            )
        if cursor == "page-1":
            return PullPage(
                records=[
                    IntegrationRecord(
                        external_id="app-figma",
                        name="Figma",
                        category="design",
                        status="active",
                        raw={"owner": "设计", "source": "fake_identity"},
                    )
                ],
                next_cursor="page-2",
                has_more=True,
            )
        return PullPage(records=[], next_cursor=cursor, has_more=False)


def build_provider(definition_key: str) -> IntegrationProvider:
    if definition_key == "fake_identity":
        return FakeIdentityProvider()
    raise ProviderPermanentError(f"Unsupported integration definition: {definition_key}")
