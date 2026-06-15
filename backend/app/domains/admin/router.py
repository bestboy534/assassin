from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.billing.service import EntitlementConfigurationError
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.jobs.router import queue_from_request
from app.infrastructure.queue.client import JobQueue

from .schemas import (
    AdminEmailDeliveryList,
    AdminIntegrationList,
    AdminJobList,
    AdminOrganizationList,
    AdminResourceStatus,
    AdminSubscriptionChangeResponse,
    AdminSubscriptionList,
    AdminUserList,
    AdminWebhookList,
    ChangeSubscriptionPlanRequest,
    EnableFeatureFlagRequest,
    FeatureFlagItem,
    FeatureFlagList,
    HighRiskActionRequest,
)
from .service import (
    AdminReauthenticationRequired,
    AdminResourceNotFound,
    PlatformAdminService,
)

router = APIRouter(prefix="/admin", tags=["platform-admin"])


async def require_platform_admin(
    user: Annotated[User, Depends(require_user)],
) -> User:
    if user.platform_role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administration forbidden",
        )
    return user


def service_for(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_platform_admin)],
) -> PlatformAdminService:
    return PlatformAdminService(session, user)


@router.get("/organizations", response_model=AdminOrganizationList)
async def list_organizations(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminOrganizationList:
    return await service.organizations()


@router.get("/users", response_model=AdminUserList)
async def list_users(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminUserList:
    return await service.users()


@router.get("/subscriptions", response_model=AdminSubscriptionList)
async def list_subscriptions(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminSubscriptionList:
    return await service.subscriptions()


@router.get("/feature-flags", response_model=FeatureFlagList)
async def list_feature_flags(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> FeatureFlagList:
    return await service.feature_flags()


@router.get("/jobs", response_model=AdminJobList)
async def list_jobs(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminJobList:
    return await service.jobs()


@router.get("/integrations", response_model=AdminIntegrationList)
async def list_integrations(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminIntegrationList:
    return await service.integrations()


@router.get("/webhooks", response_model=AdminWebhookList)
async def list_webhooks(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminWebhookList:
    return await service.webhooks()


@router.get("/email-deliveries", response_model=AdminEmailDeliveryList)
async def list_email_deliveries(
    service: Annotated[PlatformAdminService, Depends(service_for)],
) -> AdminEmailDeliveryList:
    return await service.email_deliveries()


@router.post(
    "/organizations/{organization_id}/suspend",
    response_model=AdminResourceStatus,
)
async def suspend_organization(
    organization_id: UUID,
    body: HighRiskActionRequest,
    service: Annotated[PlatformAdminService, Depends(service_for)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminResourceStatus:
    try:
        response = await service.suspend_organization(
            organization_id,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except AdminReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except AdminResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc
    await session.commit()
    return response


@router.post("/users/{user_id}/ban", response_model=AdminResourceStatus)
async def ban_user(
    user_id: UUID,
    body: HighRiskActionRequest,
    service: Annotated[PlatformAdminService, Depends(service_for)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminResourceStatus:
    try:
        response = await service.ban_user(
            user_id,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except AdminReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except AdminResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    await session.commit()
    return response


@router.post(
    "/jobs/{job_id}/replay",
    response_model=AdminResourceStatus,
    status_code=status.HTTP_201_CREATED,
)
async def replay_job(
    job_id: UUID,
    body: HighRiskActionRequest,
    service: Annotated[PlatformAdminService, Depends(service_for)],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[JobQueue, Depends(queue_from_request)],
) -> AdminResourceStatus:
    try:
        replay = await service.replay_job(
            job_id,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except AdminReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except AdminResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    await session.commit()
    await queue.enqueue(replay.id, replay.job_type, replay.payload_json)
    return AdminResourceStatus(id=replay.id, status=replay.status)


@router.post(
    "/subscriptions/{subscription_id}/change-plan",
    response_model=AdminSubscriptionChangeResponse,
)
async def change_subscription_plan(
    subscription_id: UUID,
    body: ChangeSubscriptionPlanRequest,
    service: Annotated[PlatformAdminService, Depends(service_for)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminSubscriptionChangeResponse:
    try:
        response = await service.change_subscription_plan(
            subscription_id,
            target_plan=body.target_plan,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except AdminReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except AdminResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Subscription not found") from exc
    except EntitlementConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    return response


@router.post(
    "/feature-flags/{flag_id}/enable",
    response_model=FeatureFlagItem,
)
async def enable_feature_flag(
    flag_id: UUID,
    body: EnableFeatureFlagRequest,
    service: Annotated[PlatformAdminService, Depends(service_for)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FeatureFlagItem:
    try:
        response = await service.enable_feature_flag(
            flag_id,
            rollout_percentage=body.rollout_percentage,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except AdminReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except AdminResourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Feature flag not found") from exc
    await session.commit()
    return response
