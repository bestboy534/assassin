import base64
import csv
import hashlib
import io
import secrets
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, SelectLabelStyle, false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import new_uuid
from app.core.transactions import transaction
from app.domains.applications.models import Application
from app.domains.billing.usage import OrganizationUsageScope, UsageService
from app.domains.contracts.models import Renewal
from app.domains.jobs.models import Job
from app.domains.organizations.service import OrganizationContext
from app.domains.procurement.models import PurchaseRequest
from app.domains.savings.models import SavingsOpportunity, SavingsResult
from app.domains.spend.models import Budget, SpendTransaction
from app.domains.vendors.models import RiskFinding

from .metrics import MetricDefinition, metric_registry
from .models import ReportExport, ReportSnapshot, ReportSubscription, SavedReport
from .schemas import (
    CreateReportExportRequest,
    CreateReportSubscriptionRequest,
    CreateSavedReportRequest,
    ReportDimensionListResponse,
    ReportDimensionResponse,
    ReportExportResponse,
    ReportMetricDefinitionResponse,
    ReportMetricListResponse,
    ReportQuery,
    ReportQueryResponse,
    ReportRow,
    ReportSnapshotResponse,
    ReportSubscriptionResponse,
    SavedReportListResponse,
    SavedReportResponse,
)

DIMENSION_LABELS = {
    "department": "部门",
    "category": "类别",
    "merchant_name": "商户",
    "currency": "币种",
    "status": "状态",
    "risk_level": "风险等级",
    "severity": "严重程度",
}

SPEND_DIMENSION_COLUMNS: dict[str, Any] = {
    "department": SpendTransaction.department,
    "category": SpendTransaction.category,
    "merchant_name": SpendTransaction.merchant_name,
    "currency": SpendTransaction.currency,
}
BUDGET_DIMENSION_COLUMNS: dict[str, Any] = {
    "department": Budget.department,
    "currency": Budget.currency,
    "status": Budget.status,
}
APPLICATION_DIMENSION_COLUMNS: dict[str, Any] = {
    "category": Application.category,
    "status": Application.status,
    "risk_level": Application.risk_level,
}
SAVINGS_OPPORTUNITY_DIMENSION_COLUMNS: dict[str, Any] = {
    "department": SavingsOpportunity.department,
    "category": SavingsOpportunity.category,
    "status": SavingsOpportunity.status,
    "currency": SavingsOpportunity.currency,
}
SAVINGS_RESULT_DIMENSION_COLUMNS: dict[str, Any] = {
    "status": SavingsResult.status,
}
RENEWAL_DIMENSION_COLUMNS: dict[str, Any] = {
    "status": Renewal.status,
    "currency": Renewal.currency,
}
RISK_DIMENSION_COLUMNS: dict[str, Any] = {
    "severity": RiskFinding.severity,
    "status": RiskFinding.status,
}
PROCUREMENT_DIMENSION_COLUMNS: dict[str, Any] = {
    "department": PurchaseRequest.department,
    "status": PurchaseRequest.status,
}


class ReportNotFound(LookupError):
    pass


class ReportSnapshotNotFound(LookupError):
    pass


class ReportExportNotFound(LookupError):
    pass


class ReportDownloadExpired(ValueError):
    pass


class InvalidReportQuery(ValueError):
    pass


@dataclass(frozen=True)
class ReportAccessContext:
    organization_id: UUID | str
    user_id: UUID | str
    role: str
    allowed_departments: frozenset[str] | None = None

    @classmethod
    def from_organization_context(cls, context: OrganizationContext) -> "ReportAccessContext":
        return cls(
            organization_id=context.organization_id,
            user_id=context.user_id,
            role=context.role,
            allowed_departments=None,
        )


@dataclass(frozen=True)
class DownloadedReport:
    content: bytes
    content_type: str
    filename: str


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def list_metrics(self) -> ReportMetricListResponse:
        return ReportMetricListResponse(
            items=[
                ReportMetricDefinitionResponse(
                    key=definition.key,
                    label=definition.label,
                    description=definition.description,
                    value_type=definition.value_type,
                    required_permission=definition.required_permission,
                    dimensions=sorted(definition.dimensions),
                )
                for definition in metric_registry.list()
            ]
        )

    def list_dimensions(self) -> ReportDimensionListResponse:
        return ReportDimensionListResponse(
            items=[
                ReportDimensionResponse(key=key, label=label)
                for key, label in sorted(DIMENSION_LABELS.items())
            ]
        )

    async def query(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> ReportQueryResponse:
        definitions = [self._get_metric_definition(metric) for metric in query.metrics]
        self._validate_dimensions(query, definitions)
        merged: dict[tuple[str, ...], dict[str, Decimal]] = {}
        dimensions_by_key: dict[tuple[str, ...], dict[str, str]] = {}

        for definition in definitions:
            values = await self._metric_values(scope, query, definition)
            for key, value in values.items():
                dimensions = {
                    dimension: key[index]
                    for index, dimension in enumerate(query.group_by)
                }
                dimensions_by_key.setdefault(key, dimensions)
                merged.setdefault(key, {})[definition.key] = value

        rows = [
            ReportRow(
                dimensions=dimensions_by_key[key],
                metrics={
                    metric: metrics.get(metric, Decimal("0.0000"))
                    for metric in query.metrics
                },
            )
            for key, metrics in sorted(merged.items())
        ]
        return ReportQueryResponse(
            metrics=query.metrics,
            group_by=query.group_by,
            rows=rows,
            generated_at=datetime.now(UTC),
        )

    async def list_saved_reports(self, scope: ReportAccessContext) -> SavedReportListResponse:
        statement = (
            select(SavedReport)
            .where(SavedReport.organization_id == _uuid(scope.organization_id))
            .order_by(SavedReport.created_at.desc())
        )
        reports = (await self.session.scalars(statement)).all()
        return SavedReportListResponse(
            items=[self._saved_report_response(report) for report in reports]
        )

    async def create_saved_report(
        self,
        scope: ReportAccessContext,
        body: CreateSavedReportRequest,
    ) -> SavedReportResponse:
        self._validate_dimensions(
            body.query,
            [self._get_metric_definition(metric) for metric in body.query.metrics],
        )
        async with transaction(self.session):
            saved_report = SavedReport(
                organization_id=_uuid(scope.organization_id),
                created_by_user_id=_uuid(scope.user_id),
                name=body.name,
                description=body.description,
                query_json=body.query.model_dump(mode="json"),
                chart_type=body.chart_type,
                visibility=body.visibility,
            )
            self.session.add(saved_report)
            await self.session.flush()
        return self._saved_report_response(saved_report)

    async def get_saved_report(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
    ) -> SavedReportResponse:
        return self._saved_report_response(await self._get_saved_report(scope, saved_report_id))

    async def create_snapshot(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
    ) -> ReportSnapshotResponse:
        saved_report = await self._get_saved_report(scope, saved_report_id)
        payload = jsonable_encoder(await self.query(scope, self._saved_query(saved_report)))
        async with transaction(self.session):
            snapshot = ReportSnapshot(
                organization_id=_uuid(scope.organization_id),
                saved_report_id=saved_report.id,
                created_by_user_id=_uuid(scope.user_id),
                payload_json=payload,
            )
            self.session.add(snapshot)
            await self.session.flush()
        return self._snapshot_response(snapshot)

    async def get_snapshot(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
        snapshot_id: UUID,
    ) -> ReportSnapshotResponse:
        statement = select(ReportSnapshot).where(
            ReportSnapshot.organization_id == _uuid(scope.organization_id),
            ReportSnapshot.saved_report_id == saved_report_id,
            ReportSnapshot.id == snapshot_id,
        )
        snapshot = await self.session.scalar(statement)
        if snapshot is None:
            raise ReportSnapshotNotFound(str(snapshot_id))
        return self._snapshot_response(snapshot)

    async def create_export(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
        body: CreateReportExportRequest,
        *,
        api_prefix: str,
    ) -> ReportExportResponse:
        saved_report = await self._get_saved_report(scope, saved_report_id)
        query_result = await self.query(scope, self._saved_query(saved_report))
        content, content_type = self._render_export(saved_report, query_result, body.format)
        token = secrets.token_urlsafe(32)
        filename = f"{self._safe_filename(saved_report.name)}.{body.format}"
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        async with transaction(self.session):
            job = Job(
                organization_id=_uuid(scope.organization_id),
                job_type="report_export",
                status="succeeded",
                progress=100,
                payload_json={
                    "saved_report_id": str(saved_report.id),
                    "format": body.format,
                },
                result_json={
                    "filename": filename,
                    "row_count": len(query_result.rows),
                },
                attempts=1,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
            self.session.add(job)
            await self.session.flush()
            report_export = ReportExport(
                organization_id=_uuid(scope.organization_id),
                saved_report_id=saved_report.id,
                job_id=job.id,
                created_by_user_id=_uuid(scope.user_id),
                format=body.format,
                status="succeeded",
                row_count=len(query_result.rows),
                filename=filename,
                content_type=content_type,
                content_base64=base64.b64encode(content).decode("ascii"),
                download_token_hash=_hash_token(token),
                expires_at=expires_at,
                permissions_snapshot_json={
                    "role": scope.role,
                    "allowed_departments": sorted(scope.allowed_departments)
                    if scope.allowed_departments is not None
                    else None,
                    "metrics": query_result.metrics,
                    "group_by": query_result.group_by,
                },
            )
            self.session.add(report_export)
            await self.session.flush()
            if report_export.row_count > 0:
                await UsageService(self.session).record(
                    OrganizationUsageScope(_uuid(scope.organization_id)),
                    "export_rows",
                    report_export.row_count,
                    source_key=f"report-export:{report_export.id}",
                )
        return self._export_response(report_export, token=token, api_prefix=api_prefix)

    async def download_export(
        self,
        scope: ReportAccessContext,
        export_id: UUID,
        token: str,
    ) -> DownloadedReport:
        statement = select(ReportExport).where(
            ReportExport.id == export_id,
            ReportExport.organization_id == _uuid(scope.organization_id),
        )
        report_export = await self.session.scalar(statement)
        if report_export is None:
            raise ReportExportNotFound(str(export_id))
        if report_export.download_token_hash != _hash_token(token):
            raise ReportExportNotFound(str(export_id))
        expires_at = _aware_utc(report_export.expires_at)
        if expires_at <= datetime.now(UTC):
            raise ReportDownloadExpired(str(export_id))
        return DownloadedReport(
            content=base64.b64decode(report_export.content_base64),
            content_type=report_export.content_type,
            filename=report_export.filename,
        )

    async def create_subscription(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
        body: CreateReportSubscriptionRequest,
    ) -> ReportSubscriptionResponse:
        saved_report = await self._get_saved_report(scope, saved_report_id)
        next_run_at = next_run_from_cron(body.cron, body.timezone)
        async with transaction(self.session):
            subscription = ReportSubscription(
                organization_id=_uuid(scope.organization_id),
                saved_report_id=saved_report.id,
                created_by_user_id=_uuid(scope.user_id),
                frequency=body.frequency,
                cron=body.cron,
                timezone=body.timezone,
                recipients_json=body.recipients,
                next_run_at=next_run_at,
            )
            self.session.add(subscription)
            await self.session.flush()
        return self._subscription_response(subscription)

    async def _metric_values(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
        definition: MetricDefinition,
    ) -> dict[tuple[str, ...], Decimal]:
        if definition.key == "monthly_spend":
            return await self._aggregate_spend(
                scope,
                query,
                "monthly_spend",
                func.sum(SpendTransaction.amount),
            )
        if definition.key == "vendor_concentration":
            return await self._vendor_concentration(scope, query)
        if definition.key == "budget_allocated":
            return await self._aggregate_budget(scope, query)
        if definition.key == "application_count":
            return await self._aggregate_count(
                scope,
                query,
                Application,
                APPLICATION_DIMENSION_COLUMNS,
                Application.created_at,
            )
        if definition.key == "estimated_savings":
            return await self._aggregate_savings_opportunities(scope, query)
        if definition.key in {"realized_savings", "verified_savings"}:
            return await self._aggregate_savings_results(scope, query, definition)
        if definition.key == "renewal_amount":
            return await self._aggregate_renewals(scope, query)
        if definition.key == "high_risk_findings":
            return await self._aggregate_risk_findings(scope, query)
        if definition.key == "procurement_cycle_days":
            return await self._procurement_cycle_days(scope, query)
        if definition.key == "seat_utilization":
            return await self._zero_metric(query)
        raise InvalidReportQuery(f"Unsupported metric: {definition.key}")

    async def _aggregate_spend(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
        metric_key: str,
        aggregate: Any,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            SPEND_DIMENSION_COLUMNS,
            aggregate.label("value"),
        ).select_from(SpendTransaction)
        statement = statement.where(
            SpendTransaction.organization_id == _uuid(scope.organization_id),
            SpendTransaction.transaction_date >= query.date_range.start,
            SpendTransaction.transaction_date <= query.date_range.end,
        )
        statement = self._apply_department_scope(statement, scope, SpendTransaction.department)
        statement = self._apply_filters(statement, query, SPEND_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, metric_key)

    async def _vendor_concentration(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = select(
            SpendTransaction.merchant_name,
            func.sum(SpendTransaction.amount).label("value"),
        ).where(
            SpendTransaction.organization_id == _uuid(scope.organization_id),
            SpendTransaction.transaction_date >= query.date_range.start,
            SpendTransaction.transaction_date <= query.date_range.end,
        )
        statement = self._apply_department_scope(statement, scope, SpendTransaction.department)
        statement = self._apply_filters(statement, query, SPEND_DIMENSION_COLUMNS)
        statement = statement.group_by(SpendTransaction.merchant_name)
        rows = (await self.session.execute(statement)).all()
        total = sum((_as_decimal(row.value) for row in rows), Decimal("0.0000"))
        largest = max((_as_decimal(row.value) for row in rows), default=Decimal("0.0000"))
        concentration = (
            Decimal("0.0000")
            if total == 0
            else (largest / total * Decimal("100")).quantize(Decimal("0.0001"))
        )
        return {tuple("" for _ in query.group_by): concentration}

    async def _aggregate_budget(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            BUDGET_DIMENSION_COLUMNS,
            func.sum(Budget.amount).label("value"),
        ).select_from(Budget)
        statement = statement.where(
            Budget.organization_id == _uuid(scope.organization_id),
            Budget.fiscal_year >= query.date_range.start.year,
            Budget.fiscal_year <= query.date_range.end.year,
        )
        statement = self._apply_department_scope(statement, scope, Budget.department)
        statement = self._apply_filters(statement, query, BUDGET_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, "budget_allocated")

    async def _aggregate_count(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
        model: Any,
        dimensions: dict[str, Any],
        date_column: Any,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            dimensions,
            func.count().label("value"),
        ).select_from(model)
        statement = statement.where(
            model.organization_id == _uuid(scope.organization_id),
            date_column <= datetime.combine(query.date_range.end, datetime.max.time()),
        )
        statement = self._apply_filters(statement, query, dimensions)
        return await self._execute_aggregate(statement, query.group_by, "count")

    async def _aggregate_savings_opportunities(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            SAVINGS_OPPORTUNITY_DIMENSION_COLUMNS,
            func.sum(SavingsOpportunity.estimated_amount).label("value"),
        ).select_from(SavingsOpportunity)
        statement = statement.where(
            SavingsOpportunity.organization_id == _uuid(scope.organization_id),
        )
        statement = self._apply_department_scope(statement, scope, SavingsOpportunity.department)
        statement = self._apply_filters(statement, query, SAVINGS_OPPORTUNITY_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, "estimated_savings")

    async def _aggregate_savings_results(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
        definition: MetricDefinition,
    ) -> dict[tuple[str, ...], Decimal]:
        value_column = (
            SavingsResult.verified_amount
            if definition.key == "verified_savings"
            else SavingsResult.realized_amount
        )
        statement = self._aggregate_statement(
            query.group_by,
            SAVINGS_RESULT_DIMENSION_COLUMNS,
            func.sum(value_column).label("value"),
        ).select_from(SavingsResult)
        statement = statement.where(SavingsResult.organization_id == _uuid(scope.organization_id))
        if definition.allowed_statuses:
            statement = statement.where(SavingsResult.status.in_(definition.allowed_statuses))
        statement = self._apply_filters(statement, query, SAVINGS_RESULT_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, definition.key)

    async def _aggregate_renewals(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            RENEWAL_DIMENSION_COLUMNS,
            func.sum(Renewal.current_amount).label("value"),
        ).select_from(Renewal)
        statement = statement.where(
            Renewal.organization_id == _uuid(scope.organization_id),
            Renewal.renewal_date >= query.date_range.start,
            Renewal.renewal_date <= query.date_range.end,
        )
        statement = self._apply_filters(statement, query, RENEWAL_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, "renewal_amount")

    async def _aggregate_risk_findings(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        statement = self._aggregate_statement(
            query.group_by,
            RISK_DIMENSION_COLUMNS,
            func.count(RiskFinding.id).label("value"),
        ).select_from(RiskFinding)
        statement = statement.where(
            RiskFinding.organization_id == _uuid(scope.organization_id),
            RiskFinding.severity.in_(("high", "critical")),
            RiskFinding.status.in_(("open", "accepted")),
        )
        statement = self._apply_filters(statement, query, RISK_DIMENSION_COLUMNS)
        return await self._execute_aggregate(statement, query.group_by, "high_risk_findings")

    async def _procurement_cycle_days(
        self,
        scope: ReportAccessContext,
        query: ReportQuery,
    ) -> dict[tuple[str, ...], Decimal]:
        rows = (
            await self.session.execute(
                select(PurchaseRequest).where(
                    PurchaseRequest.organization_id == _uuid(scope.organization_id),
                    PurchaseRequest.submitted_at.is_not(None),
                    PurchaseRequest.decided_at.is_not(None),
                )
            )
        ).scalars().all()
        durations = [
            Decimal(str((request.decided_at - request.submitted_at).days))
            for request in rows
            if request.decided_at is not None and request.submitted_at is not None
        ]
        average = (
            Decimal("0.0000")
            if not durations
            else (sum(durations, Decimal("0.0000")) / Decimal(len(durations))).quantize(
                Decimal("0.0001")
            )
        )
        return {tuple("" for _ in query.group_by): average}

    async def _zero_metric(self, query: ReportQuery) -> dict[tuple[str, ...], Decimal]:
        return {tuple("" for _ in query.group_by): Decimal("0.0000")}

    def _aggregate_statement(
        self,
        group_by: list[str],
        dimensions: dict[str, Any],
        aggregate: Any,
    ) -> Select[Any]:
        columns = [dimensions[dimension].label(dimension) for dimension in group_by]
        statement = select(*columns, aggregate).set_label_style(SelectLabelStyle.LABEL_STYLE_NONE)
        if columns:
            statement = statement.group_by(*[dimensions[dimension] for dimension in group_by])
        return statement

    def _apply_department_scope(
        self,
        statement: Select[Any],
        scope: ReportAccessContext,
        department_column: Any,
    ) -> Select[Any]:
        if scope.allowed_departments is None:
            return statement
        if not scope.allowed_departments:
            return statement.where(false())
        return statement.where(department_column.in_(scope.allowed_departments))

    def _apply_filters(
        self,
        statement: Select[Any],
        query: ReportQuery,
        dimensions: dict[str, Any],
    ) -> Select[Any]:
        for report_filter in query.filters:
            column = dimensions.get(report_filter.dimension)
            if column is None:
                raise InvalidReportQuery(f"Unsupported filter dimension: {report_filter.dimension}")
            if report_filter.operator == "equals":
                statement = statement.where(column == report_filter.value)
            else:
                values = (
                    report_filter.value
                    if isinstance(report_filter.value, list)
                    else [report_filter.value]
                )
                statement = statement.where(column.in_(values))
        return statement

    async def _execute_aggregate(
        self,
        statement: Select[Any],
        group_by: list[str],
        metric_key: str,
    ) -> dict[tuple[str, ...], Decimal]:
        rows = (await self.session.execute(statement)).all()
        values: dict[tuple[str, ...], Decimal] = {}
        for row in rows:
            mapping = row._mapping
            key = tuple(str(mapping.get(dimension) or "") for dimension in group_by)
            values[key] = _as_decimal(mapping["value"])
        if not rows and not group_by:
            values[()] = Decimal("0.0000")
        return values

    def _get_metric_definition(self, metric: str) -> MetricDefinition:
        try:
            return metric_registry.get(metric)
        except KeyError as exc:
            raise InvalidReportQuery(str(exc)) from exc

    def _validate_dimensions(
        self,
        query: ReportQuery,
        definitions: Iterable[MetricDefinition],
    ) -> None:
        for definition in definitions:
            unsupported = set(query.group_by) - definition.dimensions
            if unsupported:
                raise InvalidReportQuery(
                    f"Metric {definition.key} does not support dimensions: {sorted(unsupported)}"
                )
        if len(set(query.group_by)) != len(query.group_by):
            raise InvalidReportQuery("Duplicate group_by dimensions are not allowed")

    async def _get_saved_report(
        self,
        scope: ReportAccessContext,
        saved_report_id: UUID,
    ) -> SavedReport:
        statement = select(SavedReport).where(
            SavedReport.id == saved_report_id,
            SavedReport.organization_id == _uuid(scope.organization_id),
        )
        saved_report = await self.session.scalar(statement)
        if saved_report is None:
            raise ReportNotFound(str(saved_report_id))
        return saved_report

    def _saved_query(self, saved_report: SavedReport) -> ReportQuery:
        return ReportQuery.model_validate(saved_report.query_json)

    def _saved_report_response(self, saved_report: SavedReport) -> SavedReportResponse:
        return SavedReportResponse(
            id=saved_report.id,
            organization_id=saved_report.organization_id,
            name=saved_report.name,
            description=saved_report.description,
            query=saved_report.query_json,
            chart_type=saved_report.chart_type,
            visibility=saved_report.visibility,
            created_at=saved_report.created_at,
            updated_at=saved_report.updated_at,
        )

    def _snapshot_response(self, snapshot: ReportSnapshot) -> ReportSnapshotResponse:
        return ReportSnapshotResponse(
            id=snapshot.id,
            saved_report_id=snapshot.saved_report_id,
            payload=snapshot.payload_json,
            created_at=snapshot.created_at,
        )

    def _export_response(
        self,
        report_export: ReportExport,
        *,
        token: str,
        api_prefix: str,
    ) -> ReportExportResponse:
        download_url = (
            f"{api_prefix}/organizations/{report_export.organization_id}/reports/"
            f"exports/{report_export.id}/download?token={token}"
        )
        return ReportExportResponse(
            id=report_export.id,
            job_id=report_export.job_id,
            saved_report_id=report_export.saved_report_id,
            format=report_export.format,
            status=report_export.status,
            row_count=report_export.row_count,
            filename=report_export.filename,
            download_url=download_url,
            expires_at=report_export.expires_at,
            created_at=report_export.created_at,
        )

    def _subscription_response(
        self,
        subscription: ReportSubscription,
    ) -> ReportSubscriptionResponse:
        return ReportSubscriptionResponse(
            id=subscription.id,
            saved_report_id=subscription.saved_report_id,
            frequency=subscription.frequency,
            cron=subscription.cron,
            timezone=subscription.timezone,
            recipients=subscription.recipients_json,
            status=subscription.status,
            next_run_at=_aware_utc(subscription.next_run_at),
            failure_count=subscription.failure_count,
            created_at=subscription.created_at,
        )

    def _render_export(
        self,
        saved_report: SavedReport,
        query_result: ReportQueryResponse,
        export_format: str,
    ) -> tuple[bytes, str]:
        table = self._table_rows(query_result)
        if export_format == "csv":
            return _render_csv(table), "text/csv; charset=utf-8"
        if export_format == "xlsx":
            return (
                _render_xlsx(table),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        if export_format == "pdf":
            return _render_pdf(saved_report.name, table), "application/pdf"
        raise InvalidReportQuery(f"Unsupported export format: {export_format}")

    def _table_rows(self, query_result: ReportQueryResponse) -> list[list[str]]:
        headers = [
            DIMENSION_LABELS.get(dimension, dimension)
            for dimension in query_result.group_by
        ]
        headers.extend(query_result.metrics)
        rows = [headers]
        for row in query_result.rows:
            values = [row.dimensions.get(dimension, "") for dimension in query_result.group_by]
            values.extend(
                str(row.metrics.get(metric, Decimal("0.0000")))
                for metric in query_result.metrics
            )
            rows.append(values)
        return rows

    def _safe_filename(self, name: str) -> str:
        safe = "".join(
            character if character.isascii() and character.isalnum() else "-"
            for character in name
        ).strip("-")
        return safe or f"report-{new_uuid().hex[:8]}"


def next_run_from_cron(cron: str, timezone: str, now: datetime | None = None) -> datetime:
    try:
        minute_raw, hour_raw, day_raw, month_raw, weekday_raw = cron.split()
        minute = int(minute_raw)
        hour = int(hour_raw)
    except ValueError as exc:
        raise InvalidReportQuery("Cron must use five fields") from exc
    zone = _load_timezone(timezone)
    now_utc = now or datetime.now(UTC)
    now_local = now_utc.astimezone(zone)
    for day_offset in range(0, 370):
        candidate_date = now_local.date() + timedelta(days=day_offset)
        if month_raw != "*" and int(month_raw) != candidate_date.month:
            continue
        if day_raw != "*" and int(day_raw) != candidate_date.day:
            continue
        if weekday_raw != "*":
            cron_weekday = int(weekday_raw)
            python_weekday = 6 if cron_weekday == 0 else cron_weekday - 1
            if candidate_date.weekday() != python_weekday:
                continue
        candidate = datetime(
            candidate_date.year,
            candidate_date.month,
            candidate_date.day,
            hour,
            minute,
            tzinfo=zone,
        )
        if candidate > now_local:
            return candidate.astimezone(UTC)
    raise InvalidReportQuery("Unable to calculate next run time")


def _render_csv(rows: list[list[str]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def _render_xlsx(rows: list[list[str]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                "<sheets><sheet name=\"Report\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
                "</workbook>"
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))
    return buffer.getvalue()


def _sheet_xml(rows: list[list[str]]) -> str:
    xml_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_excel_column(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{_xml_escape(value)}</t></is></c>'
            )
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )


def _render_pdf(title: str, rows: list[list[str]]) -> bytes:
    lines = [title, "", *[" | ".join(row) for row in rows]]
    content = "\\n".join(lines).replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 40 780 Td ({content}) Tj ET"
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        + f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n".encode()
        + b"xref\n0 6\n0000000000 65535 f \ntrailer << /Root 1 0 R /Size 6 >>\nstartxref\n0\n%%EOF"
    )


def _excel_column(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _load_timezone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        fixed_offsets = {
            "Asia/Hong_Kong": timezone(timedelta(hours=8), "Asia/Hong_Kong"),
            "UTC": UTC,
        }
        if name in fixed_offsets:
            return fixed_offsets[name]
        raise InvalidReportQuery(f"Unknown timezone: {name}") from exc


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.0000")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.0001"))
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
