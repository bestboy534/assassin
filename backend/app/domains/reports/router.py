from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .schemas import (
    CreateReportExportRequest,
    CreateReportSubscriptionRequest,
    CreateSavedReportRequest,
    ReportDimensionListResponse,
    ReportExportResponse,
    ReportMetricListResponse,
    ReportQuery,
    ReportQueryResponse,
    ReportSnapshotResponse,
    ReportSubscriptionResponse,
    SavedReportListResponse,
    SavedReportResponse,
)
from .service import (
    InvalidReportQuery,
    ReportAccessContext,
    ReportDownloadExpired,
    ReportExportNotFound,
    ReportNotFound,
    ReportService,
    ReportSnapshotNotFound,
)

router = APIRouter(prefix="/organizations/{organization_id}/reports", tags=["reports"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


def report_context(context: OrganizationContext) -> ReportAccessContext:
    return ReportAccessContext.from_organization_context(context)


@router.get("/metrics", response_model=ReportMetricListResponse)
async def list_metrics() -> ReportMetricListResponse:
    return ReportService(session=None).list_metrics()  # type: ignore[arg-type]


@router.get("/dimensions", response_model=ReportDimensionListResponse)
async def list_dimensions() -> ReportDimensionListResponse:
    return ReportService(session=None).list_dimensions()  # type: ignore[arg-type]


@router.post("/query", response_model=ReportQueryResponse)
async def query_report(
    body: ReportQuery,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportQueryResponse:
    try:
        return await ReportService(session).query(report_context(context), body)
    except InvalidReportQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/saved-reports", response_model=SavedReportListResponse)
async def list_saved_reports(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavedReportListResponse:
    return await ReportService(session).list_saved_reports(report_context(context))


@router.post("/saved-reports", response_model=SavedReportResponse, status_code=201)
async def create_saved_report(
    body: CreateSavedReportRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavedReportResponse:
    try:
        return await ReportService(session).create_saved_report(report_context(context), body)
    except InvalidReportQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/saved-reports/{saved_report_id}", response_model=SavedReportResponse)
async def get_saved_report(
    saved_report_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SavedReportResponse:
    try:
        return await ReportService(session).get_saved_report(
            report_context(context),
            saved_report_id,
        )
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail="Saved report not found") from exc


@router.post(
    "/saved-reports/{saved_report_id}/snapshots",
    response_model=ReportSnapshotResponse,
    status_code=201,
)
async def create_snapshot(
    saved_report_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportSnapshotResponse:
    try:
        return await ReportService(session).create_snapshot(
            report_context(context),
            saved_report_id,
        )
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail="Saved report not found") from exc
    except InvalidReportQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/saved-reports/{saved_report_id}/snapshots/{snapshot_id}",
    response_model=ReportSnapshotResponse,
)
async def get_snapshot(
    saved_report_id: UUID,
    snapshot_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportSnapshotResponse:
    try:
        return await ReportService(session).get_snapshot(
            report_context(context),
            saved_report_id,
            snapshot_id,
        )
    except ReportSnapshotNotFound as exc:
        raise HTTPException(status_code=404, detail="Snapshot not found") from exc


@router.post(
    "/saved-reports/{saved_report_id}/exports",
    response_model=ReportExportResponse,
    status_code=201,
)
async def create_export(
    saved_report_id: UUID,
    body: CreateReportExportRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportExportResponse:
    try:
        return await ReportService(session).create_export(
            report_context(context),
            saved_report_id,
            body,
            api_prefix=get_settings().api_v1_prefix,
        )
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail="Saved report not found") from exc
    except InvalidReportQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    token: Annotated[str, Query(min_length=1)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    try:
        downloaded = await ReportService(session).download_export(
            report_context(context),
            export_id,
            token,
        )
    except ReportDownloadExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download link expired",
        ) from exc
    except ReportExportNotFound as exc:
        raise HTTPException(status_code=404, detail="Export not found") from exc
    return Response(
        content=downloaded.content,
        media_type=downloaded.content_type,
        headers={"Content-Disposition": f'attachment; filename="{downloaded.filename}"'},
    )


@router.post(
    "/saved-reports/{saved_report_id}/subscriptions",
    response_model=ReportSubscriptionResponse,
    status_code=201,
)
async def create_subscription(
    saved_report_id: UUID,
    body: CreateReportSubscriptionRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportSubscriptionResponse:
    try:
        return await ReportService(session).create_subscription(
            report_context(context),
            saved_report_id,
            body,
        )
    except ReportNotFound as exc:
        raise HTTPException(status_code=404, detail="Saved report not found") from exc
    except InvalidReportQuery as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
