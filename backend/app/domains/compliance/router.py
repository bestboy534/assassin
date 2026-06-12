from typing import Annotated
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

from .schemas import (
    AuditLogExportRequest,
    AuditLogExportResponse,
    AuditLogListResponse,
    AuditLogResponse,
)
from .service import AuditLogForbidden, AuditLogNotFound, ComplianceService

audit_logs_router = APIRouter(
    prefix="/organizations/{organization_id}/audit-logs",
    tags=["compliance"],
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
