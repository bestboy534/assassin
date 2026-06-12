from collections.abc import Awaitable
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session
from app.domains.organizations.service import OrganizationContext
from app.infrastructure.storage.base import ObjectStorage

from .control_schemas import (
    AssignControlOwnerRequest,
    ComplianceControlResponse,
    ControlEvidenceResponse,
    ControlOwnerResponse,
    ControlReviewResponse,
    CreateControlRequest,
    CreateControlReviewRequest,
    CreateEvidenceRequest,
    CreateFrameworkRequest,
    CreateIncidentTaskRequest,
    CreateSecurityIncidentRequest,
    EvidenceDownloadResponse,
    FrameworkListResponse,
    FrameworkResponse,
    IncidentTaskResponse,
    SecurityIncidentListResponse,
    SecurityIncidentResponse,
    UpdateIncidentTaskRequest,
)
from .controls import (
    ComplianceAccessForbidden,
    ComplianceControlService,
    ComplianceResourceConflict,
    ComplianceResourceNotFound,
    CreateControl,
    CreateEvidence,
    CreateFramework,
    CreateIncident,
    CreateIncidentTask,
    SecurityIncidentService,
)
from .router import organization_context, storage_from_request

controls_router = APIRouter(
    prefix="/organizations/{organization_id}/compliance",
    tags=["compliance"],
)
incidents_router = APIRouter(
    prefix="/organizations/{organization_id}/security/incidents",
    tags=["security-incidents"],
)

T = TypeVar("T")


@controls_router.post("/frameworks", response_model=FrameworkResponse, status_code=201)
async def create_framework(
    body: CreateFrameworkRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FrameworkResponse:
    return await _call(
        ComplianceControlService(session).create_framework(
            context,
            CreateFramework(
                code=body.code,
                name=body.name,
                version=body.version,
                description=body.description,
            ),
        )
    )


@controls_router.get("/frameworks", response_model=FrameworkListResponse)
async def list_frameworks(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FrameworkListResponse:
    return FrameworkListResponse(
        items=await _call(ComplianceControlService(session).list_frameworks(context))
    )


@controls_router.post(
    "/frameworks/{framework_id}/controls",
    response_model=ComplianceControlResponse,
    status_code=201,
)
async def create_control(
    framework_id: UUID,
    body: CreateControlRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ComplianceControlResponse:
    return await _call(
        ComplianceControlService(session).create_control(
            context,
            framework_id,
            CreateControl(
                code=body.code,
                title=body.title,
                description=body.description,
                frequency_days=body.frequency_days,
            ),
        )
    )


@controls_router.get(
    "/controls/{control_id}",
    response_model=ComplianceControlResponse,
)
async def get_control(
    control_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ComplianceControlResponse:
    return await _call(ComplianceControlService(session).get_control(context, control_id))


@controls_router.post(
    "/controls/{control_id}/owners",
    response_model=ControlOwnerResponse,
    status_code=201,
)
async def assign_control_owner(
    control_id: UUID,
    body: AssignControlOwnerRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ControlOwnerResponse:
    return await _call(
        ComplianceControlService(session).assign_owner(
            context,
            control_id,
            user_id=body.user_id,
            role=body.role,
        )
    )


@controls_router.post(
    "/controls/{control_id}/evidence",
    response_model=ControlEvidenceResponse,
    status_code=201,
)
async def add_control_evidence(
    control_id: UUID,
    body: CreateEvidenceRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ControlEvidenceResponse:
    return await _call(
        ComplianceControlService(session).add_evidence(
            context,
            control_id,
            CreateEvidence(
                stored_file_id=body.stored_file_id,
                title=body.title,
                description=body.description,
                collected_at=body.collected_at,
                expires_at=body.expires_at,
            ),
        )
    )


@controls_router.post(
    "/controls/{control_id}/reviews",
    response_model=ControlReviewResponse,
    status_code=201,
)
async def create_control_review(
    control_id: UUID,
    body: CreateControlReviewRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ControlReviewResponse:
    return await _call(
        ComplianceControlService(session).create_review(
            context,
            control_id,
            outcome=body.outcome,
            notes=body.notes,
        )
    )


@controls_router.post(
    "/controls/{control_id}/refresh-status",
    response_model=ComplianceControlResponse,
)
async def refresh_control_status(
    control_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ComplianceControlResponse:
    return await _call(
        ComplianceControlService(session).refresh_control_status(context, control_id)
    )


@controls_router.get(
    "/evidence/{evidence_id}/download",
    response_model=EvidenceDownloadResponse,
)
async def download_control_evidence(
    evidence_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(storage_from_request)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvidenceDownloadResponse:
    return await _call(
        ComplianceControlService(session).create_evidence_download(
            context,
            evidence_id,
            storage=storage,
            expires_in=min(settings.storage_presign_expires_seconds, 900),
        )
    )


@incidents_router.post("", response_model=SecurityIncidentResponse, status_code=201)
async def create_security_incident(
    body: CreateSecurityIncidentRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SecurityIncidentResponse:
    return await _call(
        SecurityIncidentService(session).create_incident(
            context,
            CreateIncident(
                title=body.title,
                severity=body.severity,
                summary=body.summary,
                detected_at=body.detected_at,
            ),
        )
    )


@incidents_router.get("", response_model=SecurityIncidentListResponse)
async def list_security_incidents(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SecurityIncidentListResponse:
    return SecurityIncidentListResponse(
        items=await _call(SecurityIncidentService(session).list_incidents(context))
    )


@incidents_router.get("/{incident_id}", response_model=SecurityIncidentResponse)
async def get_security_incident(
    incident_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SecurityIncidentResponse:
    return await _call(
        SecurityIncidentService(session).get_incident(context, incident_id)
    )


@incidents_router.post(
    "/{incident_id}/tasks",
    response_model=IncidentTaskResponse,
    status_code=201,
)
async def create_incident_task(
    incident_id: UUID,
    body: CreateIncidentTaskRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IncidentTaskResponse:
    return await _call(
        SecurityIncidentService(session).add_task(
            context,
            incident_id,
            CreateIncidentTask(
                title=body.title,
                assignee_user_id=body.assignee_user_id,
                due_at=body.due_at,
            ),
        )
    )


@incidents_router.patch(
    "/{incident_id}/tasks/{task_id}",
    response_model=IncidentTaskResponse,
)
async def update_incident_task(
    incident_id: UUID,
    task_id: UUID,
    body: UpdateIncidentTaskRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IncidentTaskResponse:
    return await _call(
        SecurityIncidentService(session).update_task(
            context,
            incident_id,
            task_id,
            status=body.status,
        )
    )


async def _call(awaitable: Awaitable[T]) -> T:
    try:
        return await awaitable
    except ComplianceAccessForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compliance access requires an authorized role",
        ) from exc
    except ComplianceResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Compliance resource not found") from exc
    except ComplianceResourceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
