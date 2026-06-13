import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.transactions import transaction
from app.domains.applications.models import Application, ApplicationSource
from app.domains.applications.service import normalize_application_name
from app.domains.billing.service import EntitlementService
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.secrets import EncryptedSecret, SecretCipher

from .models import (
    IntegrationConnection,
    IntegrationCredential,
    IntegrationDefinition,
    IntegrationOAuthState,
    SyncCursor,
    SyncError,
    SyncRun,
)
from .provider import (
    IntegrationRecord,
    ProviderAuthError,
    ProviderPermanentError,
    build_provider,
)
from .schemas import (
    ConnectionHealthResponse,
    CreateIntegrationConnectionRequest,
    DeleteConnectionResponse,
    IntegrationConnectionListResponse,
    IntegrationConnectionResponse,
    IntegrationDefinitionListResponse,
    IntegrationDefinitionResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
    ReconnectIntegrationConnectionRequest,
    StartOAuthRequest,
    SyncErrorResponse,
    SyncRunListResponse,
    SyncRunResponse,
)


class IntegrationConnectionNotFound(Exception):
    pass


class IntegrationDefinitionNotFound(Exception):
    pass


class IntegrationConnectionNotReady(Exception):
    pass


class IntegrationOAuthStateInvalid(Exception):
    pass


BUILT_IN_DEFINITIONS = [
    {
        "key": "fake_identity",
        "name": "Sandbox 身份目录",
        "provider": "fake_identity",
        "category": "identity",
        "auth_type": "api_token",
        "capabilities": ["applications.read", "users.read", "groups.read"],
        "resource_types": ["applications"],
        "status": "available",
    }
]


def definition_response(item: IntegrationDefinition) -> IntegrationDefinitionResponse:
    return IntegrationDefinitionResponse(
        id=item.id,
        key=item.key,
        name=item.name,
        provider=item.provider,
        category=item.category,
        auth_type=item.auth_type.replace("_", " "),
        capabilities=json.loads(item.capabilities_json),
        resource_types=json.loads(item.resource_types_json),
        status=item.status,
    )


def connection_response(item: IntegrationConnection) -> IntegrationConnectionResponse:
    definition = item.definition
    return IntegrationConnectionResponse(
        id=item.id,
        organization_id=item.organization_id,
        definition_key=definition.key,
        definition_name=definition.name,
        display_name=item.display_name,
        status=item.status,
        auth_type=item.auth_type.replace("_", " "),
        credential_label=item.credential_label,
        credential_last4=item.credential_last4,
        capabilities=json.loads(definition.capabilities_json),
        resource_types=json.loads(definition.resource_types_json),
        last_health_status=item.last_health_status,
        last_sync_at=item.last_sync_at.isoformat() if item.last_sync_at else None,
        created_at=item.created_at.isoformat(),
    )


def sync_error_response(item: SyncError) -> SyncErrorResponse:
    return SyncErrorResponse(
        code=item.code,
        message=item.message,
        external_id=item.external_id,
        retryable=item.retryable,
    )


def sync_run_response(item: SyncRun, errors: list[SyncError]) -> SyncRunResponse:
    return SyncRunResponse(
        id=item.id,
        connection_id=item.connection_id,
        resource_type=item.resource_type,
        status=item.status,
        cursor_before=item.cursor_before,
        cursor_after=item.cursor_after,
        read_count=item.read_count,
        created_count=item.created_count,
        updated_count=item.updated_count,
        skipped_count=item.skipped_count,
        failed_count=item.failed_count,
        error_summary=item.error_summary,
        started_at=item.started_at.isoformat(),
        finished_at=item.finished_at.isoformat() if item.finished_at else None,
        errors=[sync_error_response(error) for error in errors],
    )


class IntegrationService:
    def __init__(self, session: AsyncSession, cipher: SecretCipher) -> None:
        self.session = session
        self.cipher = cipher

    async def list_definitions(self) -> IntegrationDefinitionListResponse:
        await self._ensure_definitions()
        items = (
            await self.session.scalars(
                select(IntegrationDefinition).order_by(IntegrationDefinition.name.asc())
            )
        ).all()
        return IntegrationDefinitionListResponse(
            items=[definition_response(item) for item in items]
        )

    async def create_connection(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateIntegrationConnectionRequest,
    ) -> IntegrationConnectionResponse:
        await EntitlementService(self.session).require_capacity(
            context,
            "integration_connections",
        )
        definition = await self._definition_by_key(body.definition_key)
        token = body.api_token.strip()
        connection = IntegrationConnection(
            organization_id=context.organization_id,
            definition_id=definition.id,
            created_by_user_id=user.id,
            display_name=body.display_name.strip(),
            status="connected",
            auth_type=definition.auth_type,
            credential_label="API token",
            credential_last4=token[-4:],
            sandbox_options_json=json.dumps(body.sandbox_options),
        )
        async with transaction(self.session):
            self.session.add(connection)
            await self.session.flush()
            secret = self.cipher.encrypt(
                json.dumps({"api_token": token}).encode("utf-8"),
                self._secret_context(context.organization_id, connection.id),
            )
            connection.credential = IntegrationCredential(
                organization_id=context.organization_id,
                cipher_suite=secret.cipher_suite,
                ciphertext=secret.ciphertext,
            )
        return connection_response(connection)

    async def list_connections(
        self,
        context: OrganizationContext,
    ) -> IntegrationConnectionListResponse:
        items = (
            await self.session.scalars(
                select(IntegrationConnection)
                .where(IntegrationConnection.organization_id == context.organization_id)
                .options(selectinload(IntegrationConnection.definition))
                .order_by(IntegrationConnection.created_at.desc())
            )
        ).all()
        return IntegrationConnectionListResponse(
            items=[connection_response(item) for item in items]
        )

    async def get_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> IntegrationConnection:
        item = await self.session.scalar(
            select(IntegrationConnection)
            .where(
                IntegrationConnection.id == connection_id,
                IntegrationConnection.organization_id == context.organization_id,
            )
            .options(
                selectinload(IntegrationConnection.definition),
                selectinload(IntegrationConnection.credential),
            )
        )
        if item is None:
            raise IntegrationConnectionNotFound
        return item

    async def get_connection_response(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> IntegrationConnectionResponse:
        return connection_response(await self.get_connection(context, connection_id))

    async def start_oauth(
        self,
        context: OrganizationContext,
        definition_key: str,
        body: StartOAuthRequest,
    ) -> OAuthStartResponse:
        definition = await self._definition_by_key(definition_key)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = self._pkce_challenge(verifier)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        oauth_state = IntegrationOAuthState(
            organization_id=context.organization_id,
            definition_key=definition.key,
            state_hash=self._hash_token(state),
            pkce_verifier_hash=self._hash_token(verifier),
            redirect_uri=body.redirect_uri,
            expires_at=expires_at,
        )
        self.session.add(oauth_state)
        await self.session.commit()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": definition.key,
                "redirect_uri": body.redirect_uri,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return OAuthStartResponse(
            authorization_url=f"https://sandbox.identity.local/oauth/authorize?{query}",
            state=state,
            expires_at=expires_at.isoformat(),
        )

    async def complete_oauth_callback(
        self,
        context: OrganizationContext,
        state: str,
        code: str,
    ) -> OAuthCallbackResponse:
        if not state.strip() or not code.strip():
            raise IntegrationOAuthStateInvalid
        now = datetime.now(UTC)
        oauth_state = await self.session.scalar(
            select(IntegrationOAuthState).where(
                IntegrationOAuthState.organization_id == context.organization_id,
                IntegrationOAuthState.state_hash == self._hash_token(state),
            )
        )
        if oauth_state is None or oauth_state.consumed_at is not None:
            raise IntegrationOAuthStateInvalid
        expires_at = self._aware_utc(oauth_state.expires_at)
        if expires_at <= now:
            raise IntegrationOAuthStateInvalid
        oauth_state.consumed_at = now
        await self.session.commit()
        return OAuthCallbackResponse(
            status="authorized",
            organization_id=context.organization_id,
            definition_key=oauth_state.definition_key,
        )

    async def reconnect_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
        body: ReconnectIntegrationConnectionRequest,
    ) -> IntegrationConnectionResponse:
        connection = await self.get_connection(context, connection_id)
        token = body.api_token.strip()
        secret = self.cipher.encrypt(
            json.dumps({"api_token": token}).encode("utf-8"),
            self._secret_context(context.organization_id, connection.id),
        )
        connection.credential.cipher_suite = secret.cipher_suite
        connection.credential.ciphertext = secret.ciphertext
        connection.credential.rotated_at = datetime.now(UTC)
        connection.credential_label = "API token"
        connection.credential_last4 = token[-4:]
        connection.status = "connected"
        connection.deleted_at = None
        await self.session.commit()
        return connection_response(connection)

    async def test_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> ConnectionHealthResponse:
        connection = await self.get_connection(context, connection_id)
        credentials = self._decrypt_credentials(context, connection)
        provider = build_provider(connection.definition.key)
        health = await provider.test_connection(credentials)
        connection.last_health_status = "healthy" if health.healthy else "unhealthy"
        connection.last_health_checked_at = datetime.now(UTC)
        await self.session.commit()
        return ConnectionHealthResponse(healthy=health.healthy, message=health.message)

    async def sync_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
        resource_type: str = "applications",
    ) -> SyncRunResponse:
        connection = await self.get_connection(context, connection_id)
        if connection.status != "connected":
            raise IntegrationConnectionNotReady
        cursor = await self._cursor(context, connection_id, resource_type)
        run = SyncRun(
            organization_id=context.organization_id,
            connection_id=connection.id,
            resource_type=resource_type,
            status="running",
            cursor_before=cursor.cursor if cursor else None,
        )
        self.session.add(run)
        await self.session.commit()

        provider = build_provider(connection.definition.key)
        credentials = self._decrypt_credentials(context, connection)
        options = json.loads(connection.sandbox_options_json)
        cursor_value = run.cursor_before
        next_cursor = cursor_value
        records: list[IntegrationRecord] = []
        errors: list[SyncError] = []
        try:
            while True:
                page = await provider.pull(
                    credentials,
                    resource_type,
                    cursor_value,
                    options,
                )
                records.extend(page.records)
                next_cursor = page.next_cursor
                if not page.has_more:
                    break
                cursor_value = page.next_cursor
        except (ProviderAuthError, ProviderPermanentError) as exc:
            run.status = "failed"
            run.read_count = len(records)
            run.failed_count = 1
            run.error_summary = str(exc)
            run.finished_at = datetime.now(UTC)
            error = SyncError(
                organization_id=context.organization_id,
                sync_run_id=run.id,
                connection_id=connection.id,
                code="provider_error",
                message=str(exc),
                retryable=False,
            )
            self.session.add(error)
            await self.session.commit()
            errors.append(error)
            return sync_run_response(run, errors)

        created, updated, skipped = await self._apply_records(
            context,
            connection,
            records,
        )
        if cursor is None:
            cursor = SyncCursor(
                organization_id=context.organization_id,
                connection_id=connection.id,
                resource_type=resource_type,
                cursor=next_cursor or "",
            )
            self.session.add(cursor)
        else:
            cursor.cursor = next_cursor or cursor.cursor
        run.status = "succeeded"
        run.cursor_after = cursor.cursor
        run.read_count = len(records)
        run.created_count = created
        run.updated_count = updated
        run.skipped_count = skipped
        run.finished_at = datetime.now(UTC)
        connection.last_sync_at = run.finished_at
        await self.session.commit()
        return sync_run_response(run, [])

    async def list_sync_runs(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> SyncRunListResponse:
        await self.get_connection(context, connection_id)
        runs = (
            await self.session.scalars(
                select(SyncRun)
                .where(
                    SyncRun.organization_id == context.organization_id,
                    SyncRun.connection_id == connection_id,
                )
                .order_by(SyncRun.started_at.desc())
            )
        ).all()
        items = []
        for run in runs:
            errors = (
                await self.session.scalars(
                    select(SyncError)
                    .where(SyncError.sync_run_id == run.id)
                    .order_by(SyncError.created_at.asc())
                )
            ).all()
            items.append(sync_run_response(run, list(errors)))
        return SyncRunListResponse(items=items)

    async def pause_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> IntegrationConnectionResponse:
        connection = await self.get_connection(context, connection_id)
        connection.status = "paused"
        await self.session.commit()
        return connection_response(connection)

    async def resume_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> IntegrationConnectionResponse:
        connection = await self.get_connection(context, connection_id)
        connection.status = "connected"
        await self.session.commit()
        return connection_response(connection)

    async def delete_connection(
        self,
        context: OrganizationContext,
        connection_id: UUID,
    ) -> DeleteConnectionResponse:
        connection = await self.get_connection(context, connection_id)
        connection.status = "deleted"
        connection.deleted_at = datetime.now(UTC)
        await self.session.commit()
        return DeleteConnectionResponse(
            status="deleted",
            data_retention="retain_synced_data",
        )

    async def _apply_records(
        self,
        context: OrganizationContext,
        connection: IntegrationConnection,
        records: list[IntegrationRecord],
    ) -> tuple[int, int, int]:
        created = 0
        updated = 0
        skipped = 0
        async with transaction(self.session):
            for record in records:
                source = await self.session.scalar(
                    select(ApplicationSource).where(
                        ApplicationSource.organization_id == context.organization_id,
                        ApplicationSource.provider == connection.definition.key,
                        ApplicationSource.external_id == record.external_id,
                    )
                )
                if source is not None and source.application_id is not None:
                    application = await self.session.get(Application, source.application_id)
                    if (
                        application is not None
                        and application.organization_id == context.organization_id
                    ):
                        application.name = record.name
                        application.name_normalized = normalize_application_name(record.name)
                        application.category = record.category
                        application.status = record.status
                        updated += 1
                    else:
                        skipped += 1
                    continue

                existing_application = await self.session.scalar(
                    select(Application).where(
                        Application.organization_id == context.organization_id,
                        Application.name_normalized
                        == normalize_application_name(record.name),
                    )
                )
                application = existing_application
                if application is None:
                    application = Application(
                        organization_id=context.organization_id,
                        name=record.name,
                        name_normalized=normalize_application_name(record.name),
                        category=record.category,
                        status=record.status,
                        business_owner=str(record.raw.get("owner", "")) or None,
                        technical_owner=None,
                        risk_level="unknown",
                        approved=False,
                        created_by_user_id=connection.created_by_user_id,
                    )
                    self.session.add(application)
                    await self.session.flush()
                    created += 1
                else:
                    skipped += 1
                self.session.add(
                    ApplicationSource(
                        organization_id=context.organization_id,
                        application_id=application.id,
                        source_type="integration",
                        provider=connection.definition.key,
                        external_id=record.external_id,
                        observed_name=record.name,
                        confidence="synced",
                        status="confirmed",
                    )
                )
        return created, updated, skipped

    async def _cursor(
        self,
        context: OrganizationContext,
        connection_id: UUID,
        resource_type: str,
    ) -> SyncCursor | None:
        return cast(
            SyncCursor | None,
            await self.session.scalar(
                select(SyncCursor).where(
                    SyncCursor.organization_id == context.organization_id,
                    SyncCursor.connection_id == connection_id,
                    SyncCursor.resource_type == resource_type,
                )
            ),
        )

    async def _definition_by_key(self, key: str) -> IntegrationDefinition:
        await self._ensure_definitions()
        definition = await self.session.scalar(
            select(IntegrationDefinition).where(IntegrationDefinition.key == key)
        )
        if definition is None:
            raise IntegrationDefinitionNotFound
        return definition

    async def _ensure_definitions(self) -> None:
        for item in BUILT_IN_DEFINITIONS:
            existing = await self.session.scalar(
                select(IntegrationDefinition).where(
                    IntegrationDefinition.key == item["key"]
                )
            )
            if existing is None:
                self.session.add(
                    IntegrationDefinition(
                        key=str(item["key"]),
                        name=str(item["name"]),
                        provider=str(item["provider"]),
                        category=str(item["category"]),
                        auth_type=str(item["auth_type"]),
                        capabilities_json=json.dumps(item["capabilities"]),
                        resource_types_json=json.dumps(item["resource_types"]),
                        status=str(item["status"]),
                    )
                )
        await self.session.commit()

    def _decrypt_credentials(
        self,
        context: OrganizationContext,
        connection: IntegrationConnection,
    ) -> dict[str, str]:
        secret = EncryptedSecret(
            cipher_suite=connection.credential.cipher_suite,
            ciphertext=connection.credential.ciphertext,
        )
        plaintext = self.cipher.decrypt(
            secret,
            self._secret_context(context.organization_id, connection.id),
        )
        loaded = json.loads(plaintext.decode("utf-8"))
        return {key: str(value) for key, value in loaded.items()}

    @staticmethod
    def _secret_context(organization_id: UUID, connection_id: UUID) -> dict[str, str]:
        return {
            "organization_id": str(organization_id),
            "connection_id": str(connection_id),
        }

    @staticmethod
    def _hash_token(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _pkce_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
