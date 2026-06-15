from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.identity.security import verify_password

from .knowledge_models import PlatformKnowledgeEntry, PlatformKnowledgeVersion
from .knowledge_schemas import (
    KnowledgeBundleResponse,
    KnowledgeEntryResponse,
    KnowledgeListResponse,
    KnowledgeVersionResponse,
    PublicKnowledgeResponse,
)
from .models import PlatformAuditLog

KNOWLEDGE_TYPES = {
    "software-directory": "software",
    "vendor-directory": "vendor",
    "merchant-aliases": "merchant_alias",
    "cancellation-routes": "cancellation_route",
    "risk-rules": "risk_rule",
    "ai-prompts": "ai_prompt",
}


class KnowledgeNotFound(Exception):
    pass


class KnowledgeConflict(Exception):
    pass


class KnowledgeReauthenticationRequired(Exception):
    pass


class PlatformKnowledgeService:
    def __init__(self, session: AsyncSession, actor: User) -> None:
        self.session = session
        self.actor = actor
        if actor.platform_role != "platform_admin":
            raise PermissionError

    async def create(
        self,
        object_type: str,
        *,
        key: str,
        data: dict[str, object],
        change_summary: str,
    ) -> KnowledgeBundleResponse:
        existing = await self.session.scalar(
            select(PlatformKnowledgeEntry.id).where(
                PlatformKnowledgeEntry.object_type == object_type,
                PlatformKnowledgeEntry.key == key,
            )
        )
        if existing is not None:
            raise KnowledgeConflict("Knowledge entry already exists")
        entry = PlatformKnowledgeEntry(
            object_type=object_type,
            key=key,
            created_by_user_id=self.actor.id,
        )
        async with transaction(self.session):
            self.session.add(entry)
            await self.session.flush()
            version = PlatformKnowledgeVersion(
                entry_id=entry.id,
                version_number=1,
                status="draft",
                data_json=data,
                change_summary=change_summary.strip(),
                created_by_user_id=self.actor.id,
            )
            self.session.add(version)
            await self.session.flush()
        return self.bundle(entry, version)

    async def list(self, object_type: str) -> KnowledgeListResponse:
        entries = list(
            (
                await self.session.scalars(
                    select(PlatformKnowledgeEntry)
                    .where(PlatformKnowledgeEntry.object_type == object_type)
                    .order_by(PlatformKnowledgeEntry.key)
                )
            ).all()
        )
        items: list[KnowledgeBundleResponse] = []
        for entry in entries:
            version = await self.session.scalar(
                select(PlatformKnowledgeVersion)
                .where(PlatformKnowledgeVersion.entry_id == entry.id)
                .order_by(PlatformKnowledgeVersion.version_number.desc())
                .limit(1)
            )
            if version is not None:
                items.append(self.bundle(entry, version))
        return KnowledgeListResponse(items=items)

    async def create_draft(
        self,
        entry_id: UUID,
        *,
        data: dict[str, object],
        change_summary: str,
    ) -> KnowledgeVersionResponse:
        entry = await self._entry(entry_id)
        open_version = await self.session.scalar(
            select(PlatformKnowledgeVersion.id).where(
                PlatformKnowledgeVersion.entry_id == entry.id,
                PlatformKnowledgeVersion.status.in_(
                    {"draft", "in_review", "approved"}
                ),
            )
        )
        if open_version is not None:
            raise KnowledgeConflict("An unpublished version already exists")
        next_version = int(
            await self.session.scalar(
                select(func.max(PlatformKnowledgeVersion.version_number)).where(
                    PlatformKnowledgeVersion.entry_id == entry.id
                )
            )
            or 0
        ) + 1
        version = PlatformKnowledgeVersion(
            entry_id=entry.id,
            version_number=next_version,
            status="draft",
            data_json=data,
            change_summary=change_summary.strip(),
            created_by_user_id=self.actor.id,
        )
        async with transaction(self.session):
            self.session.add(version)
            await self.session.flush()
        return self.version_response(version)

    async def submit_review(self, version_id: UUID) -> KnowledgeVersionResponse:
        version = await self._version(version_id)
        if version.status != "draft":
            raise KnowledgeConflict("Only a draft can be submitted for review")
        async with transaction(self.session):
            version.status = "in_review"
        return self.version_response(version)

    async def approve(self, version_id: UUID) -> KnowledgeVersionResponse:
        version = await self._version(version_id)
        if version.status != "in_review":
            raise KnowledgeConflict("Only an in-review version can be approved")
        if version.created_by_user_id == self.actor.id:
            raise KnowledgeConflict("The draft author cannot approve the same version")
        async with transaction(self.session):
            version.status = "approved"
            version.reviewed_by_user_id = self.actor.id
            version.reviewed_at = datetime.now(UTC)
        return self.version_response(version)

    async def publish(
        self,
        version_id: UUID,
        *,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> KnowledgeBundleResponse:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        version = await self._version(version_id)
        if version.status != "approved":
            raise KnowledgeConflict("Only an approved version can be published")
        entry = await self._entry(version.entry_id)
        current = await self._published_version(entry)
        now = datetime.now(UTC)
        async with transaction(self.session):
            if current is not None:
                current.status = "superseded"
            version.status = "published"
            version.published_by_user_id = self.actor.id
            version.published_at = now
            entry.published_version_number = version.version_number
            entry.updated_at = now
            await self._audit(
                action="platform.knowledge_published",
                entry=entry,
                version=version,
                reason=reason,
                before={
                    "published_version_number": (
                        current.version_number if current is not None else None
                    )
                },
                after={"published_version_number": version.version_number},
            )
        return self.bundle(entry, version)

    async def rollback(
        self,
        entry_id: UUID,
        *,
        target_version: int,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> KnowledgeBundleResponse:
        self._require_high_risk(reason, reauth_confirmed, reauth_password)
        entry = await self._entry(entry_id)
        target = await self.session.scalar(
            select(PlatformKnowledgeVersion).where(
                PlatformKnowledgeVersion.entry_id == entry.id,
                PlatformKnowledgeVersion.version_number == target_version,
            )
        )
        if target is None or target.status not in {"published", "superseded"}:
            raise KnowledgeNotFound
        current = await self._published_version(entry)
        next_version = int(
            await self.session.scalar(
                select(func.max(PlatformKnowledgeVersion.version_number)).where(
                    PlatformKnowledgeVersion.entry_id == entry.id
                )
            )
            or 0
        ) + 1
        now = datetime.now(UTC)
        rollback_version = PlatformKnowledgeVersion(
            entry_id=entry.id,
            version_number=next_version,
            status="published",
            data_json=dict(target.data_json),
            change_summary=f"Rollback to version {target_version}: {reason.strip()}",
            created_by_user_id=self.actor.id,
            reviewed_by_user_id=self.actor.id,
            published_by_user_id=self.actor.id,
            reviewed_at=now,
            published_at=now,
        )
        async with transaction(self.session):
            if current is not None:
                current.status = "superseded"
            self.session.add(rollback_version)
            await self.session.flush()
            entry.published_version_number = next_version
            entry.updated_at = now
            await self._audit(
                action="platform.knowledge_rolled_back",
                entry=entry,
                version=rollback_version,
                reason=reason,
                before={
                    "published_version_number": (
                        current.version_number if current is not None else None
                    )
                },
                after={
                    "published_version_number": next_version,
                    "restored_from_version": target_version,
                },
            )
        return self.bundle(entry, rollback_version)

    @staticmethod
    async def public(
        session: AsyncSession,
        object_type: str,
        key: str,
    ) -> PublicKnowledgeResponse:
        entry = await session.scalar(
            select(PlatformKnowledgeEntry).where(
                PlatformKnowledgeEntry.object_type == object_type,
                PlatformKnowledgeEntry.key == key,
                PlatformKnowledgeEntry.status == "active",
                PlatformKnowledgeEntry.published_version_number.is_not(None),
            )
        )
        if entry is None:
            raise KnowledgeNotFound
        version = await session.scalar(
            select(PlatformKnowledgeVersion).where(
                PlatformKnowledgeVersion.entry_id == entry.id,
                PlatformKnowledgeVersion.version_number
                == entry.published_version_number,
                PlatformKnowledgeVersion.status == "published",
            )
        )
        if version is None or version.published_at is None:
            raise KnowledgeNotFound
        return PublicKnowledgeResponse(
            key=entry.key,
            object_type=entry.object_type,
            version_number=version.version_number,
            data=dict(version.data_json),
            published_at=version.published_at,
        )

    async def _entry(self, entry_id: UUID) -> PlatformKnowledgeEntry:
        entry = await self.session.get(PlatformKnowledgeEntry, entry_id)
        if entry is None:
            raise KnowledgeNotFound
        return entry

    async def _version(self, version_id: UUID) -> PlatformKnowledgeVersion:
        version = await self.session.get(PlatformKnowledgeVersion, version_id)
        if version is None:
            raise KnowledgeNotFound
        return version

    async def _published_version(
        self,
        entry: PlatformKnowledgeEntry,
    ) -> PlatformKnowledgeVersion | None:
        if entry.published_version_number is None:
            return None
        return cast(
            PlatformKnowledgeVersion | None,
            await self.session.scalar(
                select(PlatformKnowledgeVersion).where(
                    PlatformKnowledgeVersion.entry_id == entry.id,
                    PlatformKnowledgeVersion.version_number
                    == entry.published_version_number,
                    PlatformKnowledgeVersion.status == "published",
                )
            )
        )

    async def _audit(
        self,
        *,
        action: str,
        entry: PlatformKnowledgeEntry,
        version: PlatformKnowledgeVersion,
        reason: str,
        before: dict[str, object],
        after: dict[str, object],
    ) -> None:
        self.session.add(
            PlatformAuditLog(
                actor_type="user",
                actor_user_id=self.actor.id,
                action=action,
                resource_type=entry.object_type,
                resource_id=str(entry.id),
                reason=reason.strip(),
                before_json=before,
                after_json={
                    **after,
                    "version_id": str(version.id),
                },
                reauth_confirmed_at=datetime.now(UTC),
            )
        )

    def _require_high_risk(
        self,
        reason: str,
        reauth_confirmed: bool,
        reauth_password: str,
    ) -> None:
        if (
            not reauth_confirmed
            or len(reason.strip()) < 5
            or not verify_password(reauth_password, self.actor.password_hash)
        ):
            raise KnowledgeReauthenticationRequired

    @staticmethod
    def entry_response(entry: PlatformKnowledgeEntry) -> KnowledgeEntryResponse:
        return KnowledgeEntryResponse(
            id=entry.id,
            object_type=entry.object_type,
            key=entry.key,
            status=entry.status,
            published_version_number=entry.published_version_number,
            created_at=entry.created_at,
        )

    @staticmethod
    def version_response(
        version: PlatformKnowledgeVersion,
    ) -> KnowledgeVersionResponse:
        return KnowledgeVersionResponse(
            id=version.id,
            entry_id=version.entry_id,
            version_number=version.version_number,
            status=version.status,
            data=dict(version.data_json),
            change_summary=version.change_summary,
            created_by_user_id=version.created_by_user_id,
            reviewed_by_user_id=version.reviewed_by_user_id,
            published_by_user_id=version.published_by_user_id,
            created_at=version.created_at,
            reviewed_at=version.reviewed_at,
            published_at=version.published_at,
        )

    @classmethod
    def bundle(
        cls,
        entry: PlatformKnowledgeEntry,
        version: PlatformKnowledgeVersion,
    ) -> KnowledgeBundleResponse:
        return KnowledgeBundleResponse(
            entry=cls.entry_response(entry),
            version=cls.version_response(version),
        )
