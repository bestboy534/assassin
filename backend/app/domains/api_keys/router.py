from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.billing.service import EntitlementExceeded
from app.domains.compliance.router import organization_context
from app.domains.organizations.service import OrganizationContext

from .schemas import (
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyPrincipalResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
)
from .service import (
    ApiKeyAccessForbidden,
    ApiKeyAuthenticationFailed,
    ApiKeyNotFound,
    ApiKeyScopeForbidden,
    ApiKeyService,
)

management_router = APIRouter(
    prefix="/organizations/{organization_id}/api-keys",
    tags=["api-keys"],
)
authentication_router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@management_router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyCreatedResponse:
    try:
        record, secret = await ApiKeyService(session).create(
            context,
            name=body.name,
            scopes=body.scopes,
            expires_at=body.expires_at,
        )
    except ApiKeyAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="API key administration is forbidden") from exc
    return ApiKeyCreatedResponse(**record.model_dump(), secret=secret)


@management_router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyListResponse:
    try:
        return ApiKeyListResponse(items=await ApiKeyService(session).list(context))
    except ApiKeyAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="API key administration is forbidden") from exc


@management_router.post("/{api_key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    api_key_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiKeyResponse:
    try:
        return await ApiKeyService(session).revoke(context, api_key_id)
    except ApiKeyAccessForbidden as exc:
        raise HTTPException(status_code=403, detail="API key administration is forbidden") from exc
    except ApiKeyNotFound as exc:
        raise HTTPException(status_code=404, detail="API key not found") from exc


@authentication_router.get("/current", response_model=ApiKeyPrincipalResponse)
async def current_api_key(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    required_scope: Annotated[str | None, Query(max_length=160)] = None,
) -> ApiKeyPrincipalResponse:
    raw_secret = _bearer_secret(authorization)
    try:
        principal = await ApiKeyService(session).authenticate(
            raw_secret,
            required_scope=required_scope,
        )
    except ApiKeyAuthenticationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        ) from exc
    except ApiKeyScopeForbidden as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is missing scope: {exc}",
        ) from exc
    except EntitlementExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "entitlement_exceeded",
                "entitlement": exc.entitlement,
                "current": exc.current,
                "limit": exc.limit,
                "increment": exc.increment,
                "plan": exc.plan,
            },
        ) from exc
    return ApiKeyPrincipalResponse(
        api_key_id=principal.api_key_id,
        organization_id=principal.organization_id,
        name=principal.name,
        scopes=list(principal.scopes),
    )


def _bearer_secret(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="API key is required")
    scheme, _, value = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not value.strip():
        raise HTTPException(status_code=401, detail="API key is required")
    return value.strip()
