from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .models import SupportGrant
from .schemas import (
    CreateSupportGrantRequest,
    CreateSupportMessageRequest,
    CreateSupportSatisfactionRequest,
    CreateSupportTicketRequest,
    DiagnosticAccessRequest,
    ResolveSupportTicketRequest,
    SupportAgentListResponse,
    SupportAgentResponse,
    SupportDiagnosticResponse,
    SupportGrantListResponse,
    SupportGrantResponse,
    SupportMessageListResponse,
    SupportMessageResponse,
    SupportSatisfactionResponse,
    SupportTicketListResponse,
    SupportTicketResponse,
    UpdateSupportTicketRequest,
)
from .service import (
    InvalidSupportOperation,
    SupportAccessService,
    SupportGrantService,
    SupportPermissionDenied,
    SupportTicketNotFound,
    SupportTicketService,
)

ticket_router = APIRouter(prefix="/support/tickets", tags=["support"])
grant_management_router = APIRouter(
    prefix="/organizations/{organization_id}/support-grants",
    tags=["support"],
)
grant_access_router = APIRouter(prefix="/support/grants", tags=["support"])
operations_router = APIRouter(prefix="/support/operations", tags=["support-operations"])
agents_router = APIRouter(prefix="/support/agents", tags=["support"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


async def require_support_operator(
    user: Annotated[User, Depends(require_user)],
) -> User:
    if user.platform_role not in {"support_agent", "platform_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Support operations forbidden",
        )
    return user


@ticket_router.post(
    "",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_ticket(
    body: CreateSupportTicketRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketResponse:
    context = await organization_context(body.organization_id, user, session)
    response = await SupportTicketService(session).create(context, user, body)
    await session.commit()
    return response


@ticket_router.get("", response_model=SupportTicketListResponse)
async def list_support_tickets(
    organization_id: Annotated[UUID, Query()],
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketListResponse:
    context = await organization_context(organization_id, user, session)
    return await SupportTicketService(session).list(context)


@ticket_router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(
    ticket_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketResponse:
    try:
        ticket = await SupportTicketService(session).get_for_user(ticket_id, user.id)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    return SupportTicketService.ticket_response(ticket)


@ticket_router.get(
    "/{ticket_id}/messages",
    response_model=SupportMessageListResponse,
)
async def list_customer_support_messages(
    ticket_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportMessageListResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_user(ticket_id, user.id)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    return await service.messages(ticket, include_internal=False)


@ticket_router.patch("/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: UUID,
    body: UpdateSupportTicketRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_user(ticket_id, user.id)
        response = await service.update_status(ticket, body.status)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@ticket_router.post(
    "/{ticket_id}/messages",
    response_model=SupportMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_message(
    ticket_id: UUID,
    body: CreateSupportMessageRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportMessageResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_user(ticket_id, user.id)
        response = await service.add_customer_message(ticket, user, body.body)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@ticket_router.post(
    "/{ticket_id}/resolve",
    response_model=SupportTicketResponse,
)
async def resolve_support_ticket(
    ticket_id: UUID,
    body: ResolveSupportTicketRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_user(ticket_id, user.id)
        response = await service.resolve(ticket, body.resolution, user)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    await session.commit()
    return response


@ticket_router.post(
    "/{ticket_id}/satisfaction",
    response_model=SupportSatisfactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_support_satisfaction(
    ticket_id: UUID,
    body: CreateSupportSatisfactionRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportSatisfactionResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_user(ticket_id, user.id)
        response = await service.submit_satisfaction(ticket, user, body)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@grant_management_router.post(
    "",
    response_model=SupportGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_grant(
    body: CreateSupportGrantRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportGrantResponse:
    try:
        response = await SupportGrantService(session).create(context, body)
    except SupportPermissionDenied as exc:
        raise HTTPException(status_code=403, detail="Support grant management forbidden") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return response


@grant_management_router.get("", response_model=SupportGrantListResponse)
async def list_support_grants(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportGrantListResponse:
    try:
        return await SupportGrantService(session).list(context)
    except SupportPermissionDenied as exc:
        raise HTTPException(status_code=403, detail="Support grant management forbidden") from exc


@grant_management_router.post(
    "/{grant_id}/revoke",
    response_model=SupportGrantResponse,
)
async def revoke_support_grant(
    grant_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportGrantResponse:
    try:
        response = await SupportGrantService(session).revoke(context, grant_id)
    except SupportPermissionDenied as exc:
        raise HTTPException(status_code=403, detail="Support grant management forbidden") from exc
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support grant not found") from exc
    await session.commit()
    return response


@grant_access_router.post(
    "/{grant_id}/diagnostics",
    response_model=SupportDiagnosticResponse,
)
async def read_support_diagnostics(
    grant_id: UUID,
    body: DiagnosticAccessRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportDiagnosticResponse:
    try:
        response = await SupportAccessService(session).read_sync_diagnostics(
            grant_id,
            support_user_id=user.id,
            purpose=body.purpose,
        )
    except SupportPermissionDenied as exc:
        raise HTTPException(status_code=403, detail="Support grant is not active") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return response


@agents_router.get("", response_model=SupportAgentListResponse)
async def list_support_agents(
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportAgentListResponse:
    del user
    agents = list(
        (
            await session.scalars(
                select(User)
                .where(User.platform_role.in_({"support_agent", "platform_admin"}))
                .order_by(User.display_name, User.email_normalized)
            )
        ).all()
    )
    return SupportAgentListResponse(
        items=[
            SupportAgentResponse(
                id=agent.id,
                display_name=agent.display_name,
                platform_role=agent.platform_role or "support_agent",
            )
            for agent in agents
        ]
    )


@operations_router.get("/tickets", response_model=SupportTicketListResponse)
async def list_operational_tickets(
    operator: Annotated[User, Depends(require_support_operator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportTicketListResponse:
    del operator
    return await SupportTicketService(session).list_for_operator()


@operations_router.get(
    "/tickets/{ticket_id}/messages",
    response_model=SupportMessageListResponse,
)
async def list_operational_ticket_messages(
    ticket_id: UUID,
    operator: Annotated[User, Depends(require_support_operator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportMessageListResponse:
    del operator
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_operator(ticket_id)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    return await service.messages(ticket, include_internal=True)


@operations_router.post(
    "/tickets/{ticket_id}/messages",
    response_model=SupportMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_operational_ticket_message(
    ticket_id: UUID,
    body: CreateSupportMessageRequest,
    operator: Annotated[User, Depends(require_support_operator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportMessageResponse:
    service = SupportTicketService(session)
    try:
        ticket = await service.get_for_operator(ticket_id)
        response = await service.add_support_message(ticket, operator, body.body)
    except SupportTicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Support ticket not found") from exc
    except InvalidSupportOperation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@operations_router.get("/grants", response_model=SupportGrantListResponse)
async def list_operational_grants(
    operator: Annotated[User, Depends(require_support_operator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportGrantListResponse:
    grants = list(
        (
            await session.scalars(
                select(SupportGrant)
                .where(SupportGrant.support_user_id == operator.id)
                .order_by(SupportGrant.created_at.desc())
            )
        ).all()
    )
    return SupportGrantListResponse(
        items=[SupportGrantService.response(grant) for grant in grants]
    )
