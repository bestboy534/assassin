from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import quantize_money
from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext

from .models import (
    AccountingPeriod,
    Budget,
    BudgetCommitment,
    SpendTransaction,
    TransactionAnomaly,
    TransactionSplit,
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
    TransactionAnomalyResponse,
    TransactionListResponse,
    TransactionSplitResponse,
    UpdateTransactionRequest,
)

ANOMALY_RULE_VERSION = "spend-anomaly-v1"


class BudgetNotFound(Exception):
    pass


class SpendTransactionNotFound(Exception):
    pass


class AccountingPeriodNotFound(Exception):
    pass


class InvalidTransactionSplits(Exception):
    pass


class PeriodLocked(Exception):
    pass


class PeriodHasUnclassifiedTransactions(Exception):
    pass


def budget_response(budget: Budget) -> BudgetResponse:
    return BudgetResponse(
        id=budget.id,
        organization_id=budget.organization_id,
        name=budget.name,
        fiscal_year=budget.fiscal_year,
        department=budget.department,
        amount=quantize_money(budget.amount),
        currency=budget.currency,
        status=budget.status,
        created_at=budget.created_at,
    )


def split_response(split: TransactionSplit) -> TransactionSplitResponse:
    return TransactionSplitResponse(
        id=split.id,
        amount=quantize_money(split.amount),
        department=split.department,
        category=split.category,
    )


async def spend_transaction_response(
    session: AsyncSession,
    item: SpendTransaction,
) -> SpendTransactionResponse:
    splits = (
        await session.scalars(
            select(TransactionSplit)
            .where(TransactionSplit.transaction_id == item.id)
            .order_by(TransactionSplit.created_at.asc())
        )
    ).all()
    return SpendTransactionResponse(
        id=item.id,
        organization_id=item.organization_id,
        source_provider=item.source_provider,
        source_account_id=item.source_account_id,
        external_id=item.external_id,
        transaction_date=item.transaction_date,
        merchant_name=item.merchant_name,
        description=item.description,
        amount=quantize_money(item.amount),
        currency=item.currency,
        department=item.department,
        category=item.category,
        application_id=item.application_id,
        match_confidence=quantize_money(item.match_confidence),
        splits=[split_response(split) for split in splits],
    )


def anomaly_response(anomaly: TransactionAnomaly) -> TransactionAnomalyResponse:
    return TransactionAnomalyResponse(
        id=anomaly.id,
        transaction_id=anomaly.transaction_id,
        budget_id=anomaly.budget_id,
        code=anomaly.code,
        rule_version=anomaly.rule_version,
        baseline_amount=quantize_money(anomaly.baseline_amount),
        observed_amount=quantize_money(anomaly.observed_amount),
        status=anomaly.status,
        evidence=anomaly.evidence,
    )


def period_response(period: AccountingPeriod) -> AccountingPeriodResponse:
    return AccountingPeriodResponse(
        id=period.id,
        organization_id=period.organization_id,
        name=period.name,
        start_date=period.start_date,
        end_date=period.end_date,
        status=period.status,
        locked_at=period.locked_at,
    )


class SpendService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_budget(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateBudgetRequest,
    ) -> BudgetResponse:
        budget = Budget(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            name=body.name.strip(),
            fiscal_year=body.fiscal_year,
            department=body.department.strip(),
            amount=quantize_money(body.amount),
            currency=body.currency,
            status="active",
        )
        async with transaction(self.session):
            self.session.add(budget)
            await self.session.flush()
        return budget_response(budget)

    async def list_budgets(self, context: OrganizationContext) -> BudgetListResponse:
        budgets = (
            await self.session.scalars(
                select(Budget)
                .where(Budget.organization_id == context.organization_id)
                .order_by(Budget.fiscal_year.desc(), Budget.created_at.desc())
            )
        ).all()
        return BudgetListResponse(items=[budget_response(item) for item in budgets])

    async def get_budget(self, context: OrganizationContext, budget_id: UUID) -> Budget:
        budget = await self.session.get(Budget, budget_id)
        if budget is None or budget.organization_id != context.organization_id:
            raise BudgetNotFound
        return budget

    async def add_commitment(
        self,
        context: OrganizationContext,
        budget_id: UUID,
        body: CreateBudgetCommitmentRequest,
    ) -> BudgetCommitmentResponse:
        budget = await self.get_budget(context, budget_id)
        commitment = BudgetCommitment(
            organization_id=context.organization_id,
            budget_id=budget.id,
            commitment_type=body.commitment_type,
            amount=quantize_money(body.amount),
            description=body.description.strip(),
        )
        async with transaction(self.session):
            self.session.add(commitment)
            await self.session.flush()
        return BudgetCommitmentResponse(
            id=commitment.id,
            budget_id=commitment.budget_id,
            commitment_type=commitment.commitment_type,
            amount=quantize_money(commitment.amount),
            description=commitment.description,
        )

    async def budget_summary(
        self,
        context: OrganizationContext,
        budget_id: UUID,
    ) -> BudgetSummaryResponse:
        budget = await self.get_budget(context, budget_id)
        actual = await self._actual_for_budget(context, budget)
        commitments = (
            await self.session.scalars(
                select(BudgetCommitment).where(BudgetCommitment.budget_id == budget.id)
            )
        ).all()
        committed = sum(
            (item.amount for item in commitments if item.commitment_type == "committed"),
            Decimal("0"),
        )
        forecast = sum(
            (item.amount for item in commitments if item.commitment_type == "forecast"),
            Decimal("0"),
        )
        remaining = budget.amount - actual - committed - forecast
        return BudgetSummaryResponse(
            budget_id=budget.id,
            currency=budget.currency,
            allocated=quantize_money(budget.amount),
            actual=quantize_money(actual),
            committed=quantize_money(committed),
            forecast=quantize_money(forecast),
            remaining=quantize_money(remaining),
        )

    async def import_transactions(
        self,
        context: OrganizationContext,
        body: ImportTransactionsRequest,
    ) -> ImportTransactionsResponse:
        created: list[SpendTransaction] = []
        items: list[SpendTransaction] = []
        existing_count = 0
        async with transaction(self.session):
            for row in body.rows:
                await self._ensure_period_open(context, row.transaction_date)
                existing = await self.session.scalar(
                    select(SpendTransaction).where(
                        SpendTransaction.organization_id == context.organization_id,
                        SpendTransaction.source_provider == body.source_provider,
                        SpendTransaction.source_account_id == body.source_account_id,
                        SpendTransaction.external_id == row.external_id,
                    )
                )
                if existing is not None:
                    items.append(existing)
                    existing_count += 1
                    continue
                spend_item = SpendTransaction(
                    organization_id=context.organization_id,
                    source_provider=body.source_provider.strip(),
                    source_account_id=body.source_account_id.strip(),
                    external_id=row.external_id.strip(),
                    transaction_date=row.transaction_date,
                    merchant_name=row.merchant_name.strip(),
                    description=row.description.strip(),
                    amount=quantize_money(row.amount),
                    currency=row.currency,
                    department=row.department.strip(),
                    match_confidence=Decimal("0.0000"),
                )
                self.session.add(spend_item)
                await self.session.flush()
                created.append(spend_item)
                items.append(spend_item)
                await self._reconcile_budget_anomalies(context, spend_item)
        return ImportTransactionsResponse(
            created_count=len(created),
            existing_count=existing_count,
            items=[await spend_transaction_response(self.session, item) for item in items],
        )

    async def _reconcile_budget_anomalies(
        self,
        context: OrganizationContext,
        spend_item: SpendTransaction,
    ) -> None:
        budgets = (
            await self.session.scalars(
                select(Budget).where(
                    Budget.organization_id == context.organization_id,
                    Budget.fiscal_year == spend_item.transaction_date.year,
                    Budget.currency == spend_item.currency,
                    Budget.status == "active",
                )
            )
        ).all()
        for budget in budgets:
            observed = await self._actual_for_budget(context, budget)
            anomalies = (
                await self.session.scalars(
                    select(TransactionAnomaly)
                    .where(
                        TransactionAnomaly.organization_id
                        == context.organization_id,
                        TransactionAnomaly.budget_id == budget.id,
                        TransactionAnomaly.code == "budget_exceeded",
                        TransactionAnomaly.rule_version == ANOMALY_RULE_VERSION,
                    )
                    .order_by(TransactionAnomaly.created_at.desc())
                )
            ).all()
            if observed <= budget.amount:
                for anomaly in anomalies:
                    if anomaly.status == "open":
                        anomaly.status = "resolved"
                continue

            evidence = (
                f"{budget.department} {budget.fiscal_year} actual "
                f"{quantize_money(observed)} exceeds {quantize_money(budget.amount)}"
            )
            current = anomalies[0] if anomalies else None
            if current is not None:
                current.status = "open"
                current.baseline_amount = budget.amount
                current.observed_amount = observed
                current.evidence = evidence
                for duplicate in anomalies[1:]:
                    duplicate.status = "resolved"
                continue
            self.session.add(
                TransactionAnomaly(
                    organization_id=context.organization_id,
                    transaction_id=spend_item.id,
                    budget_id=budget.id,
                    code="budget_exceeded",
                    rule_version=ANOMALY_RULE_VERSION,
                    baseline_amount=budget.amount,
                    observed_amount=observed,
                    status="open",
                    evidence=evidence,
                )
            )
        await self.session.flush()

    async def _actual_for_budget(
        self,
        context: OrganizationContext,
        budget: Budget,
    ) -> Decimal:
        transactions = (
            await self.session.scalars(
                select(SpendTransaction).where(
                    SpendTransaction.organization_id == context.organization_id,
                    SpendTransaction.currency == budget.currency,
                    SpendTransaction.transaction_date
                    >= date(budget.fiscal_year, 1, 1),
                    SpendTransaction.transaction_date
                    <= date(budget.fiscal_year, 12, 31),
                )
            )
        ).all()
        if not transactions:
            return Decimal("0")

        transaction_ids = [item.id for item in transactions]
        splits = (
            await self.session.scalars(
                select(TransactionSplit).where(
                    TransactionSplit.transaction_id.in_(transaction_ids)
                )
            )
        ).all()
        split_transaction_ids: set[UUID] = set()
        split_amounts: dict[UUID, Decimal] = {}
        for split in splits:
            split_transaction_ids.add(split.transaction_id)
            if split.department == budget.department:
                split_amounts[split.transaction_id] = (
                    split_amounts.get(split.transaction_id, Decimal("0"))
                    + split.amount
                )

        actual = Decimal("0")
        for item in transactions:
            if item.id in split_transaction_ids:
                actual += split_amounts.get(item.id, Decimal("0"))
            elif item.department == budget.department:
                actual += item.amount
        return actual

    async def list_transactions(
        self,
        context: OrganizationContext,
    ) -> TransactionListResponse:
        items = (
            await self.session.scalars(
                select(SpendTransaction)
                .where(SpendTransaction.organization_id == context.organization_id)
                .order_by(
                    SpendTransaction.transaction_date.desc(),
                    SpendTransaction.created_at.desc(),
                )
            )
        ).all()
        return TransactionListResponse(
            items=[await spend_transaction_response(self.session, item) for item in items]
        )

    async def get_transaction(
        self,
        context: OrganizationContext,
        transaction_id: UUID,
    ) -> SpendTransaction:
        spend_item = await self.session.get(SpendTransaction, transaction_id)
        if spend_item is None or spend_item.organization_id != context.organization_id:
            raise SpendTransactionNotFound
        return spend_item

    async def update_transaction(
        self,
        context: OrganizationContext,
        transaction_id: UUID,
        body: UpdateTransactionRequest,
    ) -> SpendTransactionResponse:
        async with transaction(self.session):
            spend_item = await self.get_transaction(context, transaction_id)
            await self._ensure_period_open(context, spend_item.transaction_date)
            if body.category is not None:
                spend_item.category = body.category.strip()
            if body.department is not None:
                spend_item.department = body.department.strip()
            await self.session.flush()
            await self._reconcile_budget_anomalies(context, spend_item)
        return await spend_transaction_response(self.session, spend_item)

    async def set_splits(
        self,
        context: OrganizationContext,
        transaction_id: UUID,
        body: SetTransactionSplitsRequest,
    ) -> SpendTransactionResponse:
        spend_item = await self.get_transaction(context, transaction_id)
        total = quantize_money(sum((item.amount for item in body.splits), Decimal("0")))
        if total != quantize_money(spend_item.amount):
            raise InvalidTransactionSplits
        async with transaction(self.session):
            await self._ensure_period_open(context, spend_item.transaction_date)
            await self.session.execute(
                delete(TransactionSplit).where(
                    TransactionSplit.transaction_id == spend_item.id
                )
            )
            for item in body.splits:
                self.session.add(
                    TransactionSplit(
                        organization_id=context.organization_id,
                        transaction_id=spend_item.id,
                        amount=quantize_money(item.amount),
                        department=item.department.strip(),
                        category=item.category.strip(),
                    )
                )
            await self.session.flush()
            await self._reconcile_budget_anomalies(context, spend_item)
        return await spend_transaction_response(self.session, spend_item)

    async def list_anomalies(
        self,
        context: OrganizationContext,
    ) -> TransactionAnomalyListResponse:
        anomalies = (
            await self.session.scalars(
                select(TransactionAnomaly)
                .where(TransactionAnomaly.organization_id == context.organization_id)
                .order_by(TransactionAnomaly.created_at.desc())
            )
        ).all()
        return TransactionAnomalyListResponse(
            items=[anomaly_response(item) for item in anomalies]
        )

    async def create_period(
        self,
        context: OrganizationContext,
        body: CreateAccountingPeriodRequest,
    ) -> AccountingPeriodResponse:
        period = AccountingPeriod(
            organization_id=context.organization_id,
            name=body.name.strip(),
            start_date=body.start_date,
            end_date=body.end_date,
            status="open",
        )
        async with transaction(self.session):
            self.session.add(period)
            await self.session.flush()
        return period_response(period)

    async def list_periods(
        self,
        context: OrganizationContext,
    ) -> AccountingPeriodListResponse:
        periods = (
            await self.session.scalars(
                select(AccountingPeriod)
                .where(AccountingPeriod.organization_id == context.organization_id)
                .order_by(
                    AccountingPeriod.end_date.desc(),
                    AccountingPeriod.created_at.desc(),
                )
            )
        ).all()
        return AccountingPeriodListResponse(
            items=[period_response(period) for period in periods]
        )

    async def lock_period(
        self,
        context: OrganizationContext,
        user: User,
        period_id: UUID,
    ) -> AccountingPeriodResponse:
        async with transaction(self.session):
            period = await self.session.get(AccountingPeriod, period_id)
            if period is None or period.organization_id != context.organization_id:
                raise AccountingPeriodNotFound
            unclassified = await self.session.scalar(
                select(SpendTransaction).where(
                    SpendTransaction.organization_id == context.organization_id,
                    SpendTransaction.transaction_date >= period.start_date,
                    SpendTransaction.transaction_date <= period.end_date,
                    SpendTransaction.category.is_(None),
                )
            )
            if unclassified is not None:
                raise PeriodHasUnclassifiedTransactions
            period.status = "locked"
            period.locked_by_user_id = user.id
            period.locked_at = datetime.now(UTC)
        return period_response(period)

    async def _ensure_period_open(
        self,
        context: OrganizationContext,
        transaction_date: date,
    ) -> None:
        locked = await self.session.scalar(
            select(AccountingPeriod).where(
                AccountingPeriod.organization_id == context.organization_id,
                AccountingPeriod.status == "locked",
                AccountingPeriod.start_date <= transaction_date,
                AccountingPeriod.end_date >= transaction_date,
            )
        )
        if locked is not None:
            raise PeriodLocked
