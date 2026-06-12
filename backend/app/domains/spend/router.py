from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domains.identity.models import User
from app.domains.identity.router import require_user
from app.domains.organizations.service import (
    OrganizationContext,
    OrganizationNotFound,
    OrganizationService,
)

from .schemas import (
    AccountingPeriodListResponse,
    AccountingPeriodResponse,
    BudgetCommitmentResponse,
    BudgetListResponse,
    BudgetResponse,
    BudgetSummaryResponse,
    CreateAccountingPeriodRequest,
    CreateBudgetCommitmentRequest,
    CreateBudgetRequest,
    ImportTransactionsRequest,
    ImportTransactionsResponse,
    SetTransactionSplitsRequest,
    SpendTransactionResponse,
    TransactionAnomalyListResponse,
    TransactionListResponse,
    UpdateTransactionRequest,
)
from .service import (
    AccountingPeriodNotFound,
    BudgetNotFound,
    InvalidTransactionSplits,
    PeriodHasUnclassifiedTransactions,
    PeriodLocked,
    SpendService,
    SpendTransactionNotFound,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["spend"])


async def organization_context(
    organization_id: UUID,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationContext:
    try:
        return await OrganizationService(session).get_context(user.id, organization_id)
    except OrganizationNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
async def create_budget(
    body: CreateBudgetRequest,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BudgetResponse:
    return await SpendService(session).create_budget(context, user, body)


@router.get("/budgets", response_model=BudgetListResponse)
async def list_budgets(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BudgetListResponse:
    return await SpendService(session).list_budgets(context)


@router.post(
    "/budgets/{budget_id}/commitments",
    response_model=BudgetCommitmentResponse,
    status_code=201,
)
async def create_budget_commitment(
    budget_id: UUID,
    body: CreateBudgetCommitmentRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BudgetCommitmentResponse:
    try:
        return await SpendService(session).add_commitment(context, budget_id, body)
    except BudgetNotFound as exc:
        raise HTTPException(status_code=404, detail="Budget not found") from exc


@router.get("/budgets/{budget_id}/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(
    budget_id: UUID,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BudgetSummaryResponse:
    try:
        return await SpendService(session).budget_summary(context, budget_id)
    except BudgetNotFound as exc:
        raise HTTPException(status_code=404, detail="Budget not found") from exc


@router.post(
    "/transactions/import",
    response_model=ImportTransactionsResponse,
    status_code=201,
)
async def import_transactions(
    body: ImportTransactionsRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImportTransactionsResponse:
    try:
        return await SpendService(session).import_transactions(context, body)
    except PeriodLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accounting period is locked",
        ) from exc


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TransactionListResponse:
    return await SpendService(session).list_transactions(context)


@router.patch("/transactions/{transaction_id}", response_model=SpendTransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    body: UpdateTransactionRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SpendTransactionResponse:
    try:
        return await SpendService(session).update_transaction(context, transaction_id, body)
    except SpendTransactionNotFound as exc:
        raise HTTPException(status_code=404, detail="Transaction not found") from exc
    except PeriodLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accounting period is locked",
        ) from exc


@router.post(
    "/transactions/{transaction_id}/splits",
    response_model=SpendTransactionResponse,
)
async def set_transaction_splits(
    transaction_id: UUID,
    body: SetTransactionSplitsRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SpendTransactionResponse:
    try:
        return await SpendService(session).set_splits(context, transaction_id, body)
    except SpendTransactionNotFound as exc:
        raise HTTPException(status_code=404, detail="Transaction not found") from exc
    except InvalidTransactionSplits as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction splits must equal the transaction amount",
        ) from exc
    except PeriodLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accounting period is locked",
        ) from exc


@router.get("/transaction-anomalies", response_model=TransactionAnomalyListResponse)
async def list_transaction_anomalies(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TransactionAnomalyListResponse:
    return await SpendService(session).list_anomalies(context)


@router.post(
    "/accounting-periods",
    response_model=AccountingPeriodResponse,
    status_code=201,
)
async def create_accounting_period(
    body: CreateAccountingPeriodRequest,
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingPeriodResponse:
    return await SpendService(session).create_period(context, body)


@router.get("/accounting-periods", response_model=AccountingPeriodListResponse)
async def list_accounting_periods(
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingPeriodListResponse:
    return await SpendService(session).list_periods(context)


@router.post(
    "/accounting-periods/{period_id}/lock",
    response_model=AccountingPeriodResponse,
)
async def lock_accounting_period(
    period_id: UUID,
    user: Annotated[User, Depends(require_user)],
    context: Annotated[OrganizationContext, Depends(organization_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountingPeriodResponse:
    try:
        return await SpendService(session).lock_period(context, user, period_id)
    except AccountingPeriodNotFound as exc:
        raise HTTPException(status_code=404, detail="Accounting period not found") from exc
    except PeriodHasUnclassifiedTransactions as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Classify all transactions before locking the period",
        ) from exc
