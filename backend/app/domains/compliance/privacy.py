from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.transactions import transaction
from app.domains.identity.models import User, UserSession
from app.domains.organizations.models import Organization, OrganizationMember

from .models import LegalHold, PrivacyRequest, PrivacyRequestAction
from .schemas import PrivacyRequestActionResponse, PrivacyRequestResponse
from .service import AuditLogCreate, ComplianceService, _aware_utc

PRIVACY_REQUEST_TYPES = {"access", "correction", "deletion", "portability"}
PRIVACY_SCOPE = {"identity", "organization_memberships"}
CORRECTABLE_FIELDS = {"display_name"}


class PrivacyIdentityVerificationRequired(Exception):
    pass


class PrivacyRequestNotFound(Exception):
    pass


class PrivacyReauthenticationRequired(Exception):
    pass


class PrivacyRequestAlreadyProcessed(Exception):
    pass


class InvalidPrivacyRequest(Exception):
    pass


@dataclass(frozen=True)
class CreatePrivacyRequest:
    request_type: str
    scope: list[str] = field(
        default_factory=lambda: ["identity", "organization_memberships"]
    )
    requested_changes: dict[str, str] = field(default_factory=dict)


class PrivacyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        *,
        user: User,
        body: CreatePrivacyRequest,
    ) -> PrivacyRequestResponse:
        if user.email_verified_at is None:
            raise PrivacyIdentityVerificationRequired
        self._validate_create(body)
        now = datetime.now(UTC)
        request = PrivacyRequest(
            subject_user_id=user.id,
            request_type=body.request_type,
            status="verified",
            identity_verified_at=now,
            due_at=now + timedelta(days=30),
            scope_json=list(dict.fromkeys(body.scope)),
            requested_changes_json=dict(body.requested_changes),
            result_json={},
        )
        action = PrivacyRequestAction(
            privacy_request=request,
            actor_user_id=user.id,
            action="created",
            metadata_json={"identity_method": "verified_email"},
            created_at=now,
        )
        async with transaction(self.session):
            self.session.add_all([request, action])
        await self._record_audit(
            user.id,
            action="privacy.request.created",
            request=request,
            metadata={"type": request.request_type},
        )
        return self._response(await self._owned_request(user.id, request.id))

    async def list_requests(self, user_id: UUID) -> list[PrivacyRequestResponse]:
        requests = (
            await self.session.scalars(
                select(PrivacyRequest)
                .options(selectinload(PrivacyRequest.actions))
                .where(PrivacyRequest.subject_user_id == user_id)
                .order_by(PrivacyRequest.created_at.desc(), PrivacyRequest.id.desc())
            )
        ).all()
        return [self._response(request) for request in requests]

    async def get_request(
        self,
        *,
        user_id: UUID,
        request_id: UUID,
    ) -> PrivacyRequestResponse:
        return self._response(await self._owned_request(user_id, request_id))

    async def process_request(
        self,
        *,
        user: User,
        request_id: UUID,
        reauth_confirmed: bool,
    ) -> PrivacyRequestResponse:
        if not reauth_confirmed:
            raise PrivacyReauthenticationRequired
        request = await self._owned_request(user.id, request_id)
        if request.status == "completed":
            raise PrivacyRequestAlreadyProcessed

        result = await self._build_result(user, request)
        completed_at = datetime.now(UTC)
        async with transaction(self.session):
            request.status = "completed"
            request.result_json = result
            request.completed_at = completed_at
            request.actions.append(
                PrivacyRequestAction(
                    actor_user_id=user.id,
                    action="completed",
                    metadata_json={
                        "type": request.request_type,
                        "retained_count": len(result.get("retained", [])),
                    },
                    created_at=completed_at,
                )
            )
        await self.session.refresh(request, attribute_names=["actions"])
        await self._record_audit(
            user.id,
            action="privacy.request.completed",
            request=request,
            metadata={
                "type": request.request_type,
                "anonymized": result.get("anonymized", []),
                "deleted": result.get("deleted", []),
                "retained": result.get("retained", []),
            },
        )
        return self._response(await self._owned_request(user.id, request.id))

    async def _build_result(
        self,
        user: User,
        request: PrivacyRequest,
    ) -> dict[str, Any]:
        if request.request_type in {"access", "portability"}:
            return await self._export_result(
                user,
                request.request_type,
                request.scope_json,
            )
        if request.request_type == "correction":
            return await self._correction_result(user, request.requested_changes_json)
        if request.request_type == "deletion":
            return await self._deletion_result(user)
        raise InvalidPrivacyRequest("Unsupported privacy request type")

    async def _export_result(
        self,
        user: User,
        request_type: str,
        scope: list[str],
    ) -> dict[str, Any]:
        machine_readable: dict[str, Any] = {}
        if "identity" in scope:
            machine_readable["identity"] = {
                "id": str(user.id),
                "email": user.email_normalized,
                "display_name": user.display_name,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
        memberships: list[dict[str, Any]] = []
        if "organization_memberships" in scope:
            memberships = await self._memberships(user.id)
            machine_readable["organization_memberships"] = memberships
        label = "数据访问请求" if request_type == "access" else "数据可移植请求"
        return {
            "export_format": "json",
            "machine_readable": machine_readable,
            "human_readable": (
                f"{label}已完成。数据包仅包含请求范围内的"
                f"{len(machine_readable)} 类数据。"
            ),
            "anonymized": [],
            "deleted": [],
            "retained": ["audit_logs:immutable"],
            "corrected": [],
        }

    async def _correction_result(
        self,
        user: User,
        requested_changes: dict[str, Any],
    ) -> dict[str, Any]:
        corrected: list[str] = []
        display_name = requested_changes.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            async with transaction(self.session):
                user.display_name = display_name.strip()
            corrected.append("display_name")
        return {
            "machine_readable": {},
            "human_readable": f"数据更正请求已完成，共更正 {len(corrected)} 个字段。",
            "anonymized": [],
            "deleted": [],
            "retained": ["audit_logs:immutable"],
            "corrected": corrected,
        }

    async def _deletion_result(self, user: User) -> dict[str, Any]:
        if await self._has_active_user_hold(user.id):
            return {
                "machine_readable": {},
                "human_readable": "删除请求已处理，但用户记录受有效法律保留约束。",
                "anonymized": [],
                "deleted": [],
                "retained": [f"user:{user.id}:legal_hold"],
                "corrected": [],
            }

        memberships = await self._memberships(user.id)
        retained = [
            f"organization_membership:{membership['organization_id']}"
            for membership in memberships
        ]
        retained.append("audit_logs:immutable")
        async with transaction(self.session):
            await self.session.execute(
                delete(UserSession).where(UserSession.user_id == user.id)
            )
            user.email_normalized = f"deleted+{user.id}@privacy.invalid"
            user.display_name = "已删除用户"
            user.password_hash = "privacy-deleted"
            user.status = "privacy_deleted"
            user.email_verified_at = None
            user.last_login_at = None
        return {
            "machine_readable": {},
            "human_readable": (
                "删除请求已完成。登录会话已删除，身份已匿名化；"
                "组织业务关系和不可变审计记录依法保留。"
            ),
            "anonymized": [f"user:{user.id}"],
            "deleted": [f"sessions:{user.id}"],
            "retained": retained,
            "corrected": [],
        }

    async def _owned_request(
        self,
        user_id: UUID,
        request_id: UUID,
    ) -> PrivacyRequest:
        request = await self.session.scalar(
            select(PrivacyRequest)
            .options(selectinload(PrivacyRequest.actions))
            .where(
                PrivacyRequest.id == request_id,
                PrivacyRequest.subject_user_id == user_id,
            )
        )
        if request is None:
            raise PrivacyRequestNotFound(str(request_id))
        return request

    async def _memberships(self, user_id: UUID) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(OrganizationMember, Organization)
                .join(
                    Organization,
                    Organization.id == OrganizationMember.organization_id,
                )
                .where(OrganizationMember.user_id == user_id)
                .order_by(OrganizationMember.created_at.asc())
            )
        ).all()
        return [
            {
                "organization_id": str(membership.organization_id),
                "organization_name": organization.name,
                "role": membership.role,
                "status": membership.status,
            }
            for membership, organization in rows
        ]

    async def _has_active_user_hold(self, user_id: UUID) -> bool:
        now = datetime.now(UTC)
        holds = (
            await self.session.scalars(
                select(LegalHold).where(
                    LegalHold.resource_type == "user",
                    LegalHold.resource_id == str(user_id),
                    LegalHold.status == "active",
                )
            )
        ).all()
        return any(
            hold.expires_at is None or _aware_utc(hold.expires_at) > now
            for hold in holds
        )

    async def _record_audit(
        self,
        user_id: UUID,
        *,
        action: str,
        request: PrivacyRequest,
        metadata: dict[str, Any],
    ) -> None:
        organization_ids = [
            membership.organization_id
            for membership in (
                await self.session.scalars(
                    select(OrganizationMember).where(
                        OrganizationMember.user_id == user_id,
                        OrganizationMember.status == "active",
                    )
                )
            ).all()
        ]
        for organization_id in organization_ids:
            await ComplianceService(self.session).record_audit_log(
                AuditLogCreate(
                    organization_id=organization_id,
                    actor_type="user",
                    actor_id=user_id,
                    action=action,
                    resource_type="privacy_request",
                    resource_id=str(request.id),
                    metadata=metadata,
                )
            )

    def _validate_create(self, body: CreatePrivacyRequest) -> None:
        if body.request_type not in PRIVACY_REQUEST_TYPES:
            raise InvalidPrivacyRequest("Unsupported privacy request type")
        unsupported_scope = set(body.scope) - PRIVACY_SCOPE
        if unsupported_scope:
            raise InvalidPrivacyRequest(
                f"Unsupported privacy scope: {', '.join(sorted(unsupported_scope))}"
            )
        if body.request_type == "correction":
            unsupported_fields = set(body.requested_changes) - CORRECTABLE_FIELDS
            if unsupported_fields:
                raise InvalidPrivacyRequest(
                    f"Unsupported correction fields: {', '.join(sorted(unsupported_fields))}"
                )
            if not body.requested_changes.get("display_name", "").strip():
                raise InvalidPrivacyRequest("Correction requires a display_name")
        elif body.requested_changes:
            raise InvalidPrivacyRequest(
                "requested_changes is only allowed for correction requests"
            )

    def _response(self, request: PrivacyRequest) -> PrivacyRequestResponse:
        return PrivacyRequestResponse(
            id=request.id,
            subject_user_id=request.subject_user_id,
            type=request.request_type,
            status=request.status,
            identity_verified_at=request.identity_verified_at,
            due_at=request.due_at,
            scope=request.scope_json,
            requested_changes=request.requested_changes_json,
            result=request.result_json,
            processing_history=[
                PrivacyRequestActionResponse(
                    id=action.id,
                    action=action.action,
                    metadata=action.metadata_json,
                    created_at=action.created_at,
                )
                for action in request.actions
            ],
            created_at=request.created_at,
            updated_at=request.updated_at,
            completed_at=request.completed_at,
        )
