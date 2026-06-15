from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User

from .knowledge_schemas import (
    CreateKnowledgeDraftRequest,
    CreateKnowledgeEntryRequest,
    KnowledgeBundleResponse,
    KnowledgeListResponse,
    KnowledgeVersionResponse,
    PublicKnowledgeResponse,
    RollbackKnowledgeRequest,
)
from .knowledge_service import (
    KNOWLEDGE_TYPES,
    KnowledgeConflict,
    KnowledgeNotFound,
    KnowledgeReauthenticationRequired,
    PlatformKnowledgeService,
)
from .router import require_platform_admin
from .schemas import HighRiskActionRequest

admin_router = APIRouter(prefix="/admin", tags=["platform-knowledge"])
public_router = APIRouter(prefix="/catalog", tags=["public-catalog"])


def knowledge_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_platform_admin)],
) -> PlatformKnowledgeService:
    return PlatformKnowledgeService(session, user)


async def _list(
    collection: str,
    service: PlatformKnowledgeService,
) -> KnowledgeListResponse:
    return await service.list(KNOWLEDGE_TYPES[collection])


async def _create(
    collection: str,
    body: CreateKnowledgeEntryRequest,
    service: PlatformKnowledgeService,
    session: AsyncSession,
) -> KnowledgeBundleResponse:
    try:
        response = await service.create(
            KNOWLEDGE_TYPES[collection],
            key=body.key,
            data=body.data,
            change_summary=body.change_summary,
        )
    except KnowledgeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@admin_router.get("/software-directory", response_model=KnowledgeListResponse)
async def list_software(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("software-directory", service)


@admin_router.post(
    "/software-directory",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_software(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("software-directory", body, service, session)


@admin_router.get("/vendor-directory", response_model=KnowledgeListResponse)
async def list_vendors(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("vendor-directory", service)


@admin_router.post(
    "/vendor-directory",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vendor(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("vendor-directory", body, service, session)


@admin_router.get("/merchant-aliases", response_model=KnowledgeListResponse)
async def list_merchant_aliases(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("merchant-aliases", service)


@admin_router.post(
    "/merchant-aliases",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_merchant_alias(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("merchant-aliases", body, service, session)


@admin_router.get("/cancellation-routes", response_model=KnowledgeListResponse)
async def list_cancellation_routes(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("cancellation-routes", service)


@admin_router.post(
    "/cancellation-routes",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cancellation_route(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("cancellation-routes", body, service, session)


@admin_router.get("/risk-rules", response_model=KnowledgeListResponse)
async def list_risk_rules(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("risk-rules", service)


@admin_router.post(
    "/risk-rules",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_rule(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("risk-rules", body, service, session)


@admin_router.get("/ai-prompts", response_model=KnowledgeListResponse)
async def list_ai_prompts(
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
) -> KnowledgeListResponse:
    return await _list("ai-prompts", service)


@admin_router.post(
    "/ai-prompts",
    response_model=KnowledgeBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_prompt(
    body: CreateKnowledgeEntryRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    return await _create("ai-prompts", body, service, session)


@admin_router.post(
    "/knowledge/{entry_id}/drafts",
    response_model=KnowledgeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft(
    entry_id: UUID,
    body: CreateKnowledgeDraftRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeVersionResponse:
    try:
        response = await service.create_draft(
            entry_id,
            data=body.data,
            change_summary=body.change_summary,
        )
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Knowledge entry not found") from exc
    except KnowledgeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@admin_router.post(
    "/knowledge/versions/{version_id}/submit-review",
    response_model=KnowledgeVersionResponse,
)
async def submit_review(
    version_id: UUID,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeVersionResponse:
    try:
        response = await service.submit_review(version_id)
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Knowledge version not found") from exc
    except KnowledgeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@admin_router.post(
    "/knowledge/versions/{version_id}/approve",
    response_model=KnowledgeVersionResponse,
)
async def approve_version(
    version_id: UUID,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeVersionResponse:
    try:
        response = await service.approve(version_id)
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Knowledge version not found") from exc
    except KnowledgeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@admin_router.post(
    "/knowledge/versions/{version_id}/publish",
    response_model=KnowledgeBundleResponse,
)
async def publish_version(
    version_id: UUID,
    body: HighRiskActionRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    try:
        response = await service.publish(
            version_id,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except KnowledgeReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Knowledge version not found") from exc
    except KnowledgeConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return response


@admin_router.post(
    "/knowledge/{entry_id}/rollback",
    response_model=KnowledgeBundleResponse,
)
async def rollback_entry(
    entry_id: UUID,
    body: RollbackKnowledgeRequest,
    service: Annotated[PlatformKnowledgeService, Depends(knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> KnowledgeBundleResponse:
    try:
        response = await service.rollback(
            entry_id,
            target_version=body.target_version,
            reason=body.reason,
            reauth_confirmed=body.reauth_confirmed,
            reauth_password=body.reauth_password,
        )
    except KnowledgeReauthenticationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Reauthentication is required",
        ) from exc
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Knowledge version not found") from exc
    await session.commit()
    return response


@public_router.get(
    "/{collection}/{key}",
    response_model=PublicKnowledgeResponse,
)
async def public_knowledge(
    collection: str,
    key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicKnowledgeResponse:
    object_type = KNOWLEDGE_TYPES.get(collection)
    if object_type is None:
        raise HTTPException(status_code=404, detail="Catalog not found")
    try:
        return await PlatformKnowledgeService.public(session, object_type, key)
    except KnowledgeNotFound as exc:
        raise HTTPException(status_code=404, detail="Published entry not found") from exc
