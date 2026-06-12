from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)
from app.infrastructure.storage.base import ObjectStorage
from app.infrastructure.storage.factory import build_storage

from .privacy import (
    CreatePrivacyRequest,
    InvalidPrivacyRequest,
    PrivacyIdentityVerificationRequired,
    PrivacyReauthenticationRequired,
    PrivacyRequestAlreadyProcessed,
    PrivacyRequestNotFound,
    PrivacyService,
)
from .schemas import (
    AuditLogExportRequest,
    AuditLogExportResponse,
    AuditLogListResponse,
    AuditLogResponse,
    CreateDeletionJobRequest,
    CreateLegalHoldRequest,
    CreatePrivacyRequestRequest,
    CreateRetentionPolicyRequest,
    DeletionJobResponse,
    DeletionPreviewResponse,
    LegalHoldResponse,
    PrivacyRequestListResponse,
    PrivacyRequestResponse,
    ProcessPrivacyRequestRequest,
    RetentionPolicyResponse,
)
from .service import (
    AuditLogForbidden,
    AuditLogNotFound,
    ComplianceService,
    CreateLegalHold,
    CreateRetentionPolicy,
    LegalHoldResourceNotFound,
    ReauthenticationRequired,
    RetentionPolicyNotFound,
    RetentionService,
    deletion_result_response,
)

audit_logs_router = APIRouter(
    prefix="/organizations/{organization_id}/audit-logs",
    tags=["compliance"],
)
retention_router = APIRouter(
    prefix="/organizations/{organization_id}",
    tags=["compliance"],
)
privacy_router = APIRouter(
    prefix="/privacy/requests",
    tags=["privacy"],
)


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc


def storage_from_request(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "storage", None)
    return cast(ObjectStorage, storage) if storage is not None else build_storage()


@audit_logs_router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AuditLogListResponse:
    try:
        items = await ComplianceService(session).list_audit_logs(context, limit=limit)
    except AuditLogForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires audit.read",
        ) from exc
    return AuditLogListResponse(items=items)


@retention_router.post(
    "/retention-policies",
    response_model=RetentionPolicyResponse,
    status_code=201,
)
async def create_retention_policy(
    body: CreateRetentionPolicyRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RetentionPolicyResponse:
    _require_retention_manager(context)
    return await RetentionService(session).create_policy(
        organization_id=context.organization_id,
        created_by_user_id=context.user_id,
        body=CreateRetentionPolicy(
            data_type=body.data_type,
            retention_days=body.retention_days,
            description=body.description,
        ),
    )


@retention_router.post(
    "/legal-holds",
    response_model=LegalHoldResponse,
    status_code=201,
)
async def create_legal_hold(
    body: CreateLegalHoldRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LegalHoldResponse:
    _require_retention_manager(context)
    try:
        return await RetentionService(session).create_legal_hold(
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            body=CreateLegalHold(
                resource_type=body.resource_type,
                resource_id=body.resource_id,
                reason=body.reason,
                expires_at=body.expires_at,
            ),
        )
    except LegalHoldResourceNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="Legal hold resource not found",
        ) from exc


@retention_router.get(
    "/retention/deletion-preview",
    response_model=DeletionPreviewResponse,
)
async def preview_deletion(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    data_type: Annotated[str, Query(pattern="^stored_file$")] = "stored_file",
) -> DeletionPreviewResponse:
    _require_retention_manager(context)
    try:
        return await RetentionService(session).preview_expired(
            organization_id=context.organization_id,
            data_type=data_type,
        )
    except RetentionPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="Retention policy not found") from exc


@retention_router.post(
    "/retention/deletion-jobs",
    response_model=DeletionJobResponse,
    status_code=201,
)
async def create_deletion_job(
    body: CreateDeletionJobRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
) -> DeletionJobResponse:
    _require_retention_manager(context)
    try:
        result = await RetentionService(session, storage=storage).delete_expired(
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            data_type=body.data_type,
            reauth_confirmed=body.reauth_confirmed,
        )
    except ReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reauthentication confirmation is required",
        ) from exc
    except RetentionPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="Retention policy not found") from exc
    return deletion_result_response(result)


def _require_retention_manager(context: OrganizationContext) -> None:
    if context.role not in {"owner", "admin", "security", "security_admin", "auditor"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retention management requires compliance permissions",
        )


@privacy_router.post("", response_model=PrivacyRequestResponse, status_code=201)
async def create_privacy_request(
    body: CreatePrivacyRequestRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrivacyRequestResponse:
    try:
        return await PrivacyService(session).create_request(
            user=user,
            body=CreatePrivacyRequest(
                request_type=body.type,
                scope=body.scope,
                requested_changes=body.requested_changes,
            ),
        )
    except PrivacyIdentityVerificationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified identity is required",
        ) from exc
    except InvalidPrivacyRequest as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@privacy_router.get("", response_model=PrivacyRequestListResponse)
async def list_privacy_requests(
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrivacyRequestListResponse:
    return PrivacyRequestListResponse(
        items=await PrivacyService(session).list_requests(user.id)
    )


@privacy_router.get("/{request_id}", response_model=PrivacyRequestResponse)
async def get_privacy_request(
    request_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrivacyRequestResponse:
    try:
        return await PrivacyService(session).get_request(
            user_id=user.id,
            request_id=request_id,
        )
    except PrivacyRequestNotFound as exc:
        raise HTTPException(status_code=404, detail="Privacy request not found") from exc


@privacy_router.post(
    "/{request_id}/process",
    response_model=PrivacyRequestResponse,
)
async def process_privacy_request(
    request_id: UUID,
    body: ProcessPrivacyRequestRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PrivacyRequestResponse:
    try:
        return await PrivacyService(session).process_request(
            user=user,
            request_id=request_id,
            reauth_confirmed=body.reauth_confirmed,
        )
    except PrivacyReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reauthentication confirmation is required",
        ) from exc
    except PrivacyRequestNotFound as exc:
        raise HTTPException(status_code=404, detail="Privacy request not found") from exc
    except PrivacyRequestAlreadyProcessed as exc:
        raise HTTPException(status_code=409, detail="Privacy request already processed") from exc


@audit_logs_router.get("/{audit_log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_log_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuditLogResponse:
    try:
        return await ComplianceService(session).get_audit_log(context, audit_log_id)
    except AuditLogForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires audit.read",
        ) from exc
    except AuditLogNotFound as exc:
        raise HTTPException(status_code=404, detail="Audit log not found") from exc


@audit_logs_router.post("/export", response_model=AuditLogExportResponse, status_code=201)
async def export_audit_logs(
    body: AuditLogExportRequest,
    request: Request,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuditLogExportResponse:
    try:
        return await ComplianceService(session).export_audit_logs(
            context,
            export_format=body.format,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request.headers.get("x-request-id"),
        )
    except AuditLogForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires audit.read",
        ) from exc
