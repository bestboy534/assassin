from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.admin.router import require_platform_admin
from app.domains.identity.models import User

from .models import StatusComponent, StatusIncident
from .schemas import (
    AdminStatusIncidentResponse,
    CreateStatusComponentRequest,
    CreateStatusIncidentRequest,
    CreateStatusIncidentUpdateRequest,
    PublicIncidentList,
    PublicStatusComponent,
    PublicStatusOverview,
    StatusSubscriptionRequest,
    StatusSubscriptionResponse,
)
from .service import (
    InvalidIncidentTransition,
    StatusIncidentNotFound,
    StatusPageService,
)

router = APIRouter(prefix="/status", tags=["status"])
admin_router = APIRouter(prefix="/admin/status", tags=["platform-status"])


@router.get("", response_model=PublicStatusOverview)
async def public_status(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicStatusOverview:
    return await StatusPageService(session).overview()


@router.get("/incidents", response_model=PublicIncidentList)
async def public_incidents(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicIncidentList:
    return await StatusPageService(session).incidents()


@router.post(
    "/subscriptions",
    response_model=StatusSubscriptionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def subscribe_to_status(
    body: StatusSubscriptionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StatusSubscriptionResponse:
    response = await StatusPageService(session).subscribe(body.email)
    await session.commit()
    return response


@admin_router.get("/components", response_model=list[PublicStatusComponent])
async def list_admin_status_components(
    user: Annotated[User, Depends(require_platform_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PublicStatusComponent]:
    del user
    components = list(
        (
            await session.scalars(
                select(StatusComponent).order_by(
                    StatusComponent.display_order,
                    StatusComponent.name,
                )
            )
        ).all()
    )
    return [
        PublicStatusComponent(
            id=component.id,
            slug=component.slug,
            name=component.name,
            description=component.description,
            status=component.status,
        )
        for component in components
    ]


@admin_router.post(
    "/components",
    response_model=PublicStatusComponent,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_status_component(
    body: CreateStatusComponentRequest,
    user: Annotated[User, Depends(require_platform_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicStatusComponent:
    del user
    component = StatusComponent(
        slug=body.slug,
        name=body.name.strip(),
        description=body.description.strip(),
        display_order=body.display_order,
    )
    session.add(component)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Status component exists") from exc
    await session.refresh(component)
    return PublicStatusComponent(
        id=component.id,
        slug=component.slug,
        name=component.name,
        description=component.description,
        status=component.status,
    )


@admin_router.post(
    "/incidents",
    response_model=AdminStatusIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_status_incident(
    body: CreateStatusIncidentRequest,
    user: Annotated[User, Depends(require_platform_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminStatusIncidentResponse:
    del user
    incident = StatusIncident(
        status_component_id=body.component_id,
        title=body.title.strip(),
        public_summary=body.public_summary.strip(),
        internal_summary=body.internal_summary.strip(),
        impact=body.impact,
    )
    try:
        incident = await StatusPageService(session).publish_incident(
            incident,
            public_message=body.public_message,
            internal_note=body.internal_note,
        )
    except StatusIncidentNotFound as exc:
        raise HTTPException(status_code=404, detail="Status component not found") from exc
    except InvalidIncidentTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return _admin_incident_response(incident)


@admin_router.post(
    "/incidents/{incident_id}/updates",
    response_model=AdminStatusIncidentResponse,
)
async def create_admin_status_incident_update(
    incident_id: UUID,
    body: CreateStatusIncidentUpdateRequest,
    user: Annotated[User, Depends(require_platform_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminStatusIncidentResponse:
    del user
    try:
        incident = await StatusPageService(session).add_incident_update(
            incident_id,
            status=body.status,
            public_message=body.public_message,
            internal_note=body.internal_note,
        )
    except StatusIncidentNotFound as exc:
        raise HTTPException(status_code=404, detail="Status incident not found") from exc
    except InvalidIncidentTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return _admin_incident_response(incident)


def _admin_incident_response(
    incident: StatusIncident,
) -> AdminStatusIncidentResponse:
    return AdminStatusIncidentResponse(
        id=incident.id,
        component_id=incident.status_component_id,
        title=incident.title,
        public_summary=incident.public_summary,
        internal_summary=incident.internal_summary,
        impact=incident.impact,
        status=incident.status,
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
    )
