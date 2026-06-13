from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session
from app.domains.billing.service import EntitlementExceeded
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)
from app.infrastructure.secrets import LocalSecretCipher

from .schemas import (
    ConnectionHealthResponse,
    CreateIntegrationConnectionRequest,
    DeleteConnectionResponse,
    IntegrationConnectionListResponse,
    IntegrationConnectionResponse,
    IntegrationDefinitionListResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
    ReconnectIntegrationConnectionRequest,
    StartOAuthRequest,
    SyncRunListResponse,
    SyncRunResponse,
)
from .service import (
    IntegrationConnectionNotFound,
    IntegrationConnectionNotReady,
    IntegrationDefinitionNotFound,
    IntegrationOAuthStateInvalid,
    IntegrationService,
)

router = APIRouter(prefix="/organizations/{organization_id}/integrations", tags=["integrations"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


def integration_service(session: AsyncSession, settings: Settings) -> IntegrationService:
    return IntegrationService(
        session,
        LocalSecretCipher(settings.integration_secret_key.get_secret_value()),
    )


@router.get("/definitions", response_model=IntegrationDefinitionListResponse)
async def list_integration_definitions(
    session: Annotated[AsyncSession, Depends(get_session)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationDefinitionListResponse:
    _ = context
    return await integration_service(session, settings).list_definitions()


@router.post(
    "/connections",
    response_model=IntegrationConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_integration_connection(
    body: CreateIntegrationConnectionRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionResponse:
    try:
        return await integration_service(session, settings).create_connection(
            context,
            user,
            body,
        )
    except IntegrationDefinitionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration definition not found") from exc
    except EntitlementExceeded as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "entitlement_exceeded",
                "entitlement": exc.entitlement,
                "current": exc.current,
                "limit": exc.limit,
                "increment": exc.increment,
                "plan": exc.plan,
            },
        ) from exc


@router.get("/connections", response_model=IntegrationConnectionListResponse)
async def list_integration_connections(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionListResponse:
    return await integration_service(session, settings).list_connections(context)


@router.get("/connections/{connection_id}", response_model=IntegrationConnectionResponse)
async def get_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionResponse:
    try:
        return await integration_service(session, settings).get_connection_response(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.post(
    "/oauth/{definition_key}/start",
    response_model=OAuthStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_integration_oauth(
    definition_key: str,
    body: StartOAuthRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OAuthStartResponse:
    try:
        return await integration_service(session, settings).start_oauth(
            context,
            definition_key,
            body,
        )
    except IntegrationDefinitionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration definition not found") from exc


@router.get("/oauth/callback", response_model=OAuthCallbackResponse)
async def complete_integration_oauth_callback(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    state: Annotated[str, Query(min_length=1)],
    code: Annotated[str, Query(min_length=1)],
) -> OAuthCallbackResponse:
    try:
        return await integration_service(session, settings).complete_oauth_callback(
            context,
            state,
            code,
        )
    except IntegrationOAuthStateInvalid as exc:
        raise HTTPException(status_code=400, detail="OAuth state is invalid") from exc


@router.post("/connections/{connection_id}/reconnect", response_model=IntegrationConnectionResponse)
async def reconnect_integration_connection(
    connection_id: UUID,
    body: ReconnectIntegrationConnectionRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionResponse:
    try:
        return await integration_service(session, settings).reconnect_connection(
            context,
            connection_id,
            body,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.post(
    "/connections/{connection_id}/test",
    response_model=ConnectionHealthResponse,
)
async def test_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ConnectionHealthResponse:
    try:
        return await integration_service(session, settings).test_connection(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.post("/connections/{connection_id}/sync", response_model=SyncRunResponse)
async def sync_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SyncRunResponse:
    try:
        return await integration_service(session, settings).sync_connection(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc
    except IntegrationConnectionNotReady as exc:
        raise HTTPException(
            status_code=409,
            detail="Integration connection is not connected",
        ) from exc


@router.get("/connections/{connection_id}/sync-runs", response_model=SyncRunListResponse)
async def list_integration_sync_runs(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SyncRunListResponse:
    try:
        return await integration_service(session, settings).list_sync_runs(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.post("/connections/{connection_id}/pause", response_model=IntegrationConnectionResponse)
async def pause_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionResponse:
    try:
        return await integration_service(session, settings).pause_connection(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.post("/connections/{connection_id}/resume", response_model=IntegrationConnectionResponse)
async def resume_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IntegrationConnectionResponse:
    try:
        return await integration_service(session, settings).resume_connection(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc


@router.delete("/connections/{connection_id}", response_model=DeleteConnectionResponse)
async def delete_integration_connection(
    connection_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DeleteConnectionResponse:
    try:
        return await integration_service(session, settings).delete_connection(
            context,
            connection_id,
        )
    except IntegrationConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="Integration connection not found") from exc
