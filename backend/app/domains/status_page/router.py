from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

from .schemas import (
    PublicIncidentList,
    PublicStatusOverview,
    StatusSubscriptionRequest,
    StatusSubscriptionResponse,
)
from .service import StatusPageService

router = APIRouter(prefix="/status", tags=["status"])


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
