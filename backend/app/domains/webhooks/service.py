import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.compliance.service import AuditLogCreate, ComplianceService
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.secrets import EncryptedSecret, SecretCipher

from .models import WebhookDelivery, WebhookEndpoint
from .schemas import WebhookEndpointResponse

WEBHOOK_ADMIN_ROLES = {"owner", "admin", "security_admin"}


class WebhookAccessForbidden(Exception):
    pass


class WebhookEndpointNotFound(Exception):
    pass


class WebhookDeliveryNotFound(Exception):
    pass


class WebhookSecretUnavailable(Exception):
    pass


class WebhookService:
    def __init__(self, session: AsyncSession, cipher: SecretCipher) -> None:
        self.session = session
        self.cipher = cipher

    async def create_endpoint(
        self,
        *,
        organization_id: UUID,
        created_by_user_id: UUID,
        name: str,
        url: str,
        events: list[str],
    ) -> tuple[WebhookEndpoint, str]:
        secret = self._new_secret()
        endpoint = WebhookEndpoint(
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            name=name.strip(),
            url=url.strip(),
            events_json=sorted(set(events)),
            status="active",
            secret_version=1,
            secret_cipher_suite="pending",
            secret_ciphertext="pending",
        )
        async with transaction(self.session):
            self.session.add(endpoint)
            await self.session.flush()
            encrypted = self.cipher.encrypt(
                secret.encode(),
                self._secret_context(organization_id, endpoint.id, 1),
            )
            endpoint.secret_cipher_suite = encrypted.cipher_suite
            endpoint.secret_ciphertext = encrypted.ciphertext
        await self.session.commit()
        await self._audit(
            organization_id=organization_id,
            actor_user_id=created_by_user_id,
            action="webhook.endpoint.created",
            resource_id=endpoint.id,
        )
        await self.session.refresh(endpoint)
        return endpoint, secret

    async def create_for_context(
        self,
        context: OrganizationContext,
        *,
        name: str,
        url: str,
        events: list[str],
    ) -> tuple[WebhookEndpointResponse, str]:
        self.require_admin(context)
        endpoint, secret = await self.create_endpoint(
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            name=name,
            url=url,
            events=events,
        )
        return self.endpoint_response(endpoint), secret

    async def list_endpoints(
        self,
        context: OrganizationContext,
    ) -> list[WebhookEndpointResponse]:
        self.require_admin(context)
        endpoints = (
            await self.session.scalars(
                select(WebhookEndpoint)
                .where(WebhookEndpoint.organization_id == context.organization_id)
                .order_by(WebhookEndpoint.created_at.desc(), WebhookEndpoint.id.desc())
            )
        ).all()
        return [self.endpoint_response(endpoint) for endpoint in endpoints]

    async def rotate_secret(
        self,
        context: OrganizationContext,
        endpoint_id: UUID,
        *,
        overlap_seconds: int,
    ) -> tuple[WebhookEndpoint, str]:
        self.require_admin(context)
        endpoint = await self.get_endpoint(context.organization_id, endpoint_id)
        now = datetime.now(UTC)
        new_version = endpoint.secret_version + 1
        secret = self._new_secret()
        encrypted = self.cipher.encrypt(
            secret.encode(),
            self._secret_context(context.organization_id, endpoint.id, new_version),
        )
        async with transaction(self.session):
            endpoint.previous_secret_version = endpoint.secret_version
            endpoint.previous_secret_cipher_suite = endpoint.secret_cipher_suite
            endpoint.previous_secret_ciphertext = endpoint.secret_ciphertext
            endpoint.previous_secret_expires_at = now + timedelta(
                seconds=overlap_seconds
            )
            endpoint.secret_version = new_version
            endpoint.secret_cipher_suite = encrypted.cipher_suite
            endpoint.secret_ciphertext = encrypted.ciphertext
        await self.session.commit()
        await self._audit(
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="webhook.secret.rotated",
            resource_id=endpoint.id,
        )
        await self.session.refresh(endpoint)
        return endpoint, secret

    async def publish_event(
        self,
        *,
        organization_id: UUID,
        event_id: UUID,
        event_type: str,
        payload: dict[str, object],
        endpoint_id: UUID | None = None,
    ) -> list[WebhookDelivery]:
        statement = select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.status == "active",
        )
        if endpoint_id is not None:
            statement = statement.where(WebhookEndpoint.id == endpoint_id)
        endpoints = (await self.session.scalars(statement)).all()
        normalized_event = event_type.strip().casefold()
        deliveries: list[WebhookDelivery] = []
        async with transaction(self.session):
            for endpoint in endpoints:
                if normalized_event not in endpoint.events_json:
                    continue
                existing = await self.session.scalar(
                    select(WebhookDelivery.id).where(
                        WebhookDelivery.endpoint_id == endpoint.id,
                        WebhookDelivery.event_id == event_id,
                    )
                )
                if existing is not None:
                    continue
                delivery = WebhookDelivery(
                    organization_id=organization_id,
                    endpoint_id=endpoint.id,
                    event_id=event_id,
                    event_type=normalized_event,
                    payload_json=payload,
                    secret_version=endpoint.secret_version,
                    status="pending",
                    attempts=0,
                    next_attempt_at=datetime.now(UTC),
                )
                self.session.add(delivery)
                deliveries.append(delivery)
        await self.session.commit()
        return deliveries

    async def list_deliveries(
        self,
        context: OrganizationContext,
        endpoint_id: UUID,
    ) -> list[WebhookDelivery]:
        self.require_admin(context)
        await self.get_endpoint(context.organization_id, endpoint_id)
        return list(
            (
                await self.session.scalars(
                    select(WebhookDelivery)
                    .where(
                        WebhookDelivery.organization_id == context.organization_id,
                        WebhookDelivery.endpoint_id == endpoint_id,
                    )
                    .order_by(WebhookDelivery.created_at.desc())
                )
            ).all()
        )

    async def get_endpoint(
        self,
        organization_id: UUID,
        endpoint_id: UUID,
    ) -> WebhookEndpoint:
        endpoint = await self.session.scalar(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.organization_id == organization_id,
            )
        )
        if endpoint is None:
            raise WebhookEndpointNotFound(str(endpoint_id))
        return endpoint

    def decrypt_secret(
        self,
        endpoint: WebhookEndpoint,
        secret_version: int,
        *,
        now: datetime,
    ) -> str:
        if secret_version == endpoint.secret_version:
            encrypted = EncryptedSecret(
                cipher_suite=endpoint.secret_cipher_suite,
                ciphertext=endpoint.secret_ciphertext,
            )
        elif (
            secret_version == endpoint.previous_secret_version
            and endpoint.previous_secret_cipher_suite is not None
            and endpoint.previous_secret_ciphertext is not None
            and endpoint.previous_secret_expires_at is not None
            and self._aware_utc(endpoint.previous_secret_expires_at) > now
        ):
            encrypted = EncryptedSecret(
                cipher_suite=endpoint.previous_secret_cipher_suite,
                ciphertext=endpoint.previous_secret_ciphertext,
            )
        else:
            raise WebhookSecretUnavailable
        return self.cipher.decrypt(
            encrypted,
            self._secret_context(endpoint.organization_id, endpoint.id, secret_version),
        ).decode()

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: str,
        resource_id: UUID,
    ) -> None:
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=organization_id,
                actor_type="user",
                actor_id=actor_user_id,
                action=action,
                resource_type="webhook_endpoint",
                resource_id=str(resource_id),
            )
        )

    @staticmethod
    def endpoint_response(endpoint: WebhookEndpoint) -> WebhookEndpointResponse:
        return WebhookEndpointResponse(
            id=endpoint.id,
            organization_id=endpoint.organization_id,
            name=endpoint.name,
            url=endpoint.url,
            events=sorted(set(endpoint.events_json)),
            status=endpoint.status,
            secret_version=endpoint.secret_version,
            previous_secret_expires_at=endpoint.previous_secret_expires_at,
            created_at=endpoint.created_at,
            updated_at=endpoint.updated_at,
        )

    @staticmethod
    def _new_secret() -> str:
        return f"whsec_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _secret_context(
        organization_id: UUID,
        endpoint_id: UUID,
        version: int,
    ) -> dict[str, str]:
        return {
            "organization_id": str(organization_id),
            "endpoint_id": str(endpoint_id),
            "secret_version": str(version),
        }

    @staticmethod
    def require_admin(context: OrganizationContext) -> None:
        if context.role not in WEBHOOK_ADMIN_ROLES:
            raise WebhookAccessForbidden

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
