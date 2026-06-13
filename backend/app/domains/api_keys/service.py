import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.billing.usage import OrganizationUsageScope, UsageService
from app.domains.compliance.service import AuditLogCreate, ComplianceService, _aware_utc
from app.domains.identity.security import hash_token
from app.domains.organizations.service import OrganizationContext

from .models import ApiKey
from .schemas import ApiKeyResponse

API_KEY_ADMIN_ROLES = {"owner", "admin", "security_admin"}


class ApiKeyAccessForbidden(Exception):
    pass


class ApiKeyNotFound(Exception):
    pass


class ApiKeyAuthenticationFailed(Exception):
    pass


class ApiKeyScopeForbidden(Exception):
    pass


@dataclass(frozen=True)
class ApiKeyPrincipal:
    api_key_id: UUID
    organization_id: UUID
    name: str
    scopes: tuple[str, ...]


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        context: OrganizationContext,
        *,
        name: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> tuple[ApiKeyResponse, str]:
        self._require_admin(context)
        raw_secret, prefix = await self._new_secret()
        record = ApiKey(
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            name=name.strip(),
            prefix=prefix,
            secret_hash=hash_token(raw_secret),
            scopes_json=sorted(set(scopes)),
            expires_at=expires_at,
        )
        async with transaction(self.session):
            self.session.add(record)
        await self.session.commit()
        await self._audit(context, "api_key.created", record.id)
        return self._response(record), raw_secret

    async def list(self, context: OrganizationContext) -> list[ApiKeyResponse]:
        self._require_admin(context)
        records = (
            await self.session.scalars(
                select(ApiKey)
                .where(ApiKey.organization_id == context.organization_id)
                .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
            )
        ).all()
        return [self._response(record) for record in records]

    async def revoke(
        self,
        context: OrganizationContext,
        api_key_id: UUID,
    ) -> ApiKeyResponse:
        self._require_admin(context)
        record = await self._get(context.organization_id, api_key_id)
        if record.revoked_at is None:
            async with transaction(self.session):
                record.revoked_at = datetime.now(UTC)
            await self.session.commit()
            await self._audit(context, "api_key.revoked", record.id)
        return self._response(record)

    async def authenticate(
        self,
        raw_secret: str,
        *,
        required_scope: str | None = None,
    ) -> ApiKeyPrincipal:
        prefix = self._parse_prefix(raw_secret)
        record = await self.session.scalar(select(ApiKey).where(ApiKey.prefix == prefix))
        now = datetime.now(UTC)
        if (
            record is None
            or not hmac.compare_digest(record.secret_hash, hash_token(raw_secret))
            or record.revoked_at is not None
            or (
                record.expires_at is not None
                and _aware_utc(record.expires_at) <= now
            )
        ):
            raise ApiKeyAuthenticationFailed
        scopes = tuple(sorted(set(record.scopes_json)))
        normalized_scope = required_scope.strip().casefold() if required_scope else None
        if normalized_scope and normalized_scope not in scopes:
            raise ApiKeyScopeForbidden(normalized_scope)
        await UsageService(self.session).record(
            OrganizationUsageScope(record.organization_id),
            "api_calls",
            1,
            source_key=f"api-key:{record.id}:{uuid4()}",
        )
        async with transaction(self.session):
            record.last_used_at = now
        await self.session.commit()
        return ApiKeyPrincipal(
            api_key_id=record.id,
            organization_id=record.organization_id,
            name=record.name,
            scopes=scopes,
        )

    async def _new_secret(self) -> tuple[str, str]:
        for _ in range(5):
            prefix = secrets.token_hex(6)
            exists = await self.session.scalar(
                select(ApiKey.id).where(ApiKey.prefix == prefix)
            )
            if exists is None:
                return f"ssa_{prefix}_{secrets.token_urlsafe(32)}", prefix
        raise RuntimeError("Could not allocate API key prefix")

    async def _get(self, organization_id: UUID, api_key_id: UUID) -> ApiKey:
        record = await self.session.scalar(
            select(ApiKey).where(
                ApiKey.id == api_key_id,
                ApiKey.organization_id == organization_id,
            )
        )
        if record is None:
            raise ApiKeyNotFound(str(api_key_id))
        return record

    async def _audit(
        self,
        context: OrganizationContext,
        action: str,
        resource_id: UUID,
    ) -> None:
        await ComplianceService(self.session).record_audit_log(
            AuditLogCreate(
                organization_id=context.organization_id,
                actor_type="user",
                actor_id=context.user_id,
                action=action,
                resource_type="api_key",
                resource_id=str(resource_id),
            )
        )

    @staticmethod
    def _parse_prefix(raw_secret: str) -> str:
        parts = raw_secret.split("_", 2)
        if len(parts) != 3 or parts[0] != "ssa" or not parts[1] or not parts[2]:
            raise ApiKeyAuthenticationFailed
        return parts[1]

    @staticmethod
    def _require_admin(context: OrganizationContext) -> None:
        if context.role not in API_KEY_ADMIN_ROLES:
            raise ApiKeyAccessForbidden

    @staticmethod
    def _response(record: ApiKey) -> ApiKeyResponse:
        return ApiKeyResponse(
            id=record.id,
            organization_id=record.organization_id,
            name=record.name,
            prefix=record.prefix,
            scopes=sorted(set(record.scopes_json)),
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            created_at=record.created_at,
        )
