from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .adapters import build_accounting_provider, build_invoice_extractor
from .schemas import (
    AccountingExportResponse,
    AccountingMappingListResponse,
    AccountingMappingRequest,
    AccountingMappingResponse,
    ConfirmInvoiceRequest,
    ExtractInvoiceRequest,
    InvoiceBundleResponse,
    InvoiceListResponse,
    ResolvedAccountingMappingResponse,
    UpdateInvoiceRequest,
)
from .service import (
    AccountingExportNotFound,
    AccountingMappingMissing,
    AccountingService,
    InvoiceConflict,
    InvoiceNotFound,
    InvoiceNotReady,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["accounting"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


def accounting_service(session: AsyncSession) -> AccountingService:
    return AccountingService(
        session,
        build_invoice_extractor(),
        build_accounting_provider(),
    )


@router.post(
    "/invoices/extract",
    response_model=InvoiceBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def extract_invoice(
    body: ExtractInvoiceRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).extract_invoice(
            context,
            user,
            body,
            idempotency_key,
        )
    except InvoiceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceListResponse:
    return await accounting_service(session).list_invoices(context)


@router.get("/invoices/{invoice_id}", response_model=InvoiceBundleResponse)
async def get_invoice(
    invoice_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).bundle(context, invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc


@router.post(
    "/invoices/{invoice_id}/confirm",
    response_model=InvoiceBundleResponse,
)
async def confirm_invoice(
    invoice_id: UUID,
    body: ConfirmInvoiceRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).confirm_invoice(
            context,
            user,
            invoice_id,
            body,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc


@router.patch("/invoices/{invoice_id}", response_model=InvoiceBundleResponse)
async def update_invoice(
    invoice_id: UUID,
    body: UpdateInvoiceRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).update_invoice(
            context,
            user,
            invoice_id,
            body,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc
    except InvoiceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/invoices/{invoice_id}/match",
    response_model=InvoiceBundleResponse,
)
async def match_invoice(
    invoice_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).match_invoice(context, invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc


@router.post(
    "/accounting-mappings",
    response_model=AccountingMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_accounting_mapping(
    body: AccountingMappingRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingMappingResponse:
    return await accounting_service(session).upsert_mapping(context, body)


@router.get(
    "/accounting-mappings",
    response_model=AccountingMappingListResponse,
)
async def list_accounting_mappings(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingMappingListResponse:
    return await accounting_service(session).list_mappings(context)


@router.get(
    "/invoices/{invoice_id}/mapping",
    response_model=ResolvedAccountingMappingResponse,
)
async def resolve_invoice_mapping(
    invoice_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResolvedAccountingMappingResponse:
    try:
        return await accounting_service(session).resolve_mapping(context, invoice_id)
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc
    except AccountingMappingMissing as exc:
        raise HTTPException(status_code=409, detail="Accounting mapping is required") from exc


@router.post(
    "/invoices/{invoice_id}/export",
    response_model=InvoiceBundleResponse,
)
async def export_invoice(
    invoice_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
) -> InvoiceBundleResponse:
    try:
        return await accounting_service(session).export_invoice(
            context,
            invoice_id,
            idempotency_key,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(status_code=404, detail="Invoice not found") from exc
    except InvoiceNotReady as exc:
        raise HTTPException(status_code=409, detail="Invoice is not ready to export") from exc
    except AccountingMappingMissing as exc:
        raise HTTPException(status_code=409, detail="Accounting mapping is required") from exc


@router.post(
    "/accounting-exports/{export_id}/retry",
    response_model=AccountingExportResponse,
)
async def retry_accounting_export(
    export_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingExportResponse:
    try:
        return await accounting_service(session).retry_export(context, export_id)
    except AccountingExportNotFound as exc:
        raise HTTPException(status_code=404, detail="Accounting export not found") from exc
    except InvoiceNotReady as exc:
        raise HTTPException(status_code=409, detail="Invoice is not ready to export") from exc
    except AccountingMappingMissing as exc:
        raise HTTPException(status_code=409, detail="Accounting mapping is required") from exc
