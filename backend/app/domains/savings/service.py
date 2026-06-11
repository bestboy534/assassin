import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.money import quantize_money
from app.core.transactions import transaction
from app.domains.organizations.service import OrganizationContext

from .models import (
    OptimizationProject,
    OptimizationTask,
    SavingsBaseline,
    SavingsOpportunity,
    SavingsResult,
)
from .schemas import (
    CreateOptimizationProjectRequest,
    CreateSavingsOpportunityRequest,
    OptimizationProjectBundleResponse,
    OptimizationProjectListResponse,
    OptimizationProjectResponse,
    OptimizationTaskResponse,
    RealizeSavingsRequest,
    SavingsBaselineResponse,
    SavingsOpportunityListResponse,
    SavingsOpportunityResponse,
    SavingsResultResponse,
    SavingsSummaryResponse,
    VerifySavingsRequest,
)


class SavingsOpportunityNotFound(Exception):
    pass


class OptimizationProjectNotFound(Exception):
    pass


class InvalidSavingsTransition(Exception):
    pass


def _month_count(start: date, end: date | None) -> int:
    if end is None:
        return 12
    if end < start:
        return 0
    return min(12, (end.year - start.year) * 12 + end.month - start.month + 1)


def baseline_response(item: SavingsBaseline) -> SavingsBaselineResponse:
    return SavingsBaselineResponse(
        id=item.id,
        version=item.version,
        monthly_cost=quantize_money(item.monthly_cost),
        calculation_months=item.calculation_months,
        amount=quantize_money(item.amount),
        calculation_method=item.calculation_method,
        effective_date=item.effective_date,
        contract_end=item.contract_end,
    )


def opportunity_response(item: SavingsOpportunity) -> SavingsOpportunityResponse:
    return SavingsOpportunityResponse(
        id=item.id,
        organization_id=item.organization_id,
        source_type=item.source_type,
        source_id=item.source_id,
        rule_version=item.rule_version,
        period_key=item.period_key,
        title=item.title,
        department=item.department,
        category=item.category,
        status=item.status,
        estimated_amount=quantize_money(item.estimated_amount),
        currency=item.currency,
        evidence=item.evidence,
        created_at=item.created_at,
        baseline=baseline_response(item.baseline),
    )


def project_response(item: OptimizationProject) -> OptimizationProjectResponse:
    return OptimizationProjectResponse(
        id=item.id,
        opportunity_id=item.opportunity_id,
        owner_name=item.owner_name,
        due_date=item.due_date,
        status=item.status,
        target_amount=quantize_money(item.target_amount),
        currency=item.currency,
    )


def task_response(item: OptimizationTask) -> OptimizationTaskResponse:
    return OptimizationTaskResponse(id=item.id, title=item.title, status=item.status)


def result_response(item: SavingsResult) -> SavingsResultResponse:
    return SavingsResultResponse(
        id=item.id,
        project_id=item.project_id,
        status=item.status,
        action=item.action,
        effective_date=item.effective_date,
        new_monthly_cost=quantize_money(item.new_monthly_cost),
        realized_amount=quantize_money(item.realized_amount),
        verified_amount=quantize_money(item.verified_amount),
        realization_evidence=item.realization_evidence,
        evidence_references=json.loads(item.verification_evidence_json or "[]"),
        verified_at=item.verified_at,
    )


def project_bundle(item: OptimizationProject) -> OptimizationProjectBundleResponse:
    return OptimizationProjectBundleResponse(
        project=project_response(item),
        tasks=[task_response(task) for task in item.tasks],
        result=result_response(item.result) if item.result else None,
    )


class SavingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_opportunity(
        self,
        context: OrganizationContext,
        body: CreateSavingsOpportunityRequest,
    ) -> SavingsOpportunityResponse:
        existing = await self.session.scalar(
            select(SavingsOpportunity)
            .where(
                SavingsOpportunity.organization_id == context.organization_id,
                SavingsOpportunity.source_type == body.source_type,
                SavingsOpportunity.source_id == body.source_id,
                SavingsOpportunity.rule_version == body.rule_version,
                SavingsOpportunity.period_key == body.period_key,
            )
            .options(selectinload(SavingsOpportunity.baseline))
        )
        if existing is not None:
            return opportunity_response(existing)

        months = _month_count(body.effective_date, body.contract_end)
        estimated = quantize_money(body.monthly_baseline * months)
        opportunity = SavingsOpportunity(
            organization_id=context.organization_id,
            source_type=body.source_type.strip(),
            source_id=body.source_id.strip(),
            rule_version=body.rule_version.strip(),
            period_key=body.period_key.strip(),
            title=body.title.strip(),
            department=body.department.strip(),
            category=body.category,
            status="new",
            estimated_amount=estimated,
            currency=body.currency,
            evidence=body.evidence.strip(),
        )
        opportunity.baseline = SavingsBaseline(
            organization_id=context.organization_id,
            version=1,
            monthly_cost=quantize_money(body.monthly_baseline),
            calculation_months=months,
            amount=estimated,
            calculation_method="remaining_term" if body.contract_end else "annualized",
            effective_date=body.effective_date,
            contract_end=body.contract_end,
        )
        async with transaction(self.session):
            self.session.add(opportunity)
            await self.session.flush()
        return opportunity_response(opportunity)

    async def list_opportunities(
        self,
        context: OrganizationContext,
    ) -> SavingsOpportunityListResponse:
        items = (
            await self.session.scalars(
                select(SavingsOpportunity)
                .where(SavingsOpportunity.organization_id == context.organization_id)
                .options(selectinload(SavingsOpportunity.baseline))
                .order_by(SavingsOpportunity.created_at.desc())
            )
        ).all()
        return SavingsOpportunityListResponse(
            items=[opportunity_response(item) for item in items]
        )

    async def get_opportunity(
        self,
        context: OrganizationContext,
        opportunity_id: UUID,
    ) -> SavingsOpportunity:
        item = await self.session.scalar(
            select(SavingsOpportunity)
            .where(
                SavingsOpportunity.id == opportunity_id,
                SavingsOpportunity.organization_id == context.organization_id,
            )
            .options(selectinload(SavingsOpportunity.baseline))
        )
        if item is None:
            raise SavingsOpportunityNotFound
        return item

    async def confirm(
        self,
        context: OrganizationContext,
        opportunity_id: UUID,
    ) -> SavingsOpportunityResponse:
        async with transaction(self.session):
            item = await self.get_opportunity(context, opportunity_id)
            if item.status not in {"new", "confirmed"}:
                raise InvalidSavingsTransition
            item.status = "confirmed"
        return opportunity_response(item)

    async def create_project(
        self,
        context: OrganizationContext,
        opportunity_id: UUID,
        body: CreateOptimizationProjectRequest,
    ) -> OptimizationProjectBundleResponse:
        opportunity = await self.get_opportunity(context, opportunity_id)
        if opportunity.status not in {"confirmed", "in_progress"}:
            raise InvalidSavingsTransition
        existing = await self.session.scalar(
            select(OptimizationProject)
            .where(OptimizationProject.opportunity_id == opportunity.id)
            .options(
                selectinload(OptimizationProject.tasks),
                selectinload(OptimizationProject.result),
            )
        )
        if existing is not None:
            return project_bundle(existing)

        project = OptimizationProject(
            organization_id=context.organization_id,
            opportunity_id=opportunity.id,
            owner_name=body.owner_name.strip(),
            due_date=body.due_date,
            status="in_progress",
            target_amount=opportunity.estimated_amount,
            currency=opportunity.currency,
            result=None,
        )
        project.tasks.append(
            OptimizationTask(
                organization_id=context.organization_id,
                title="确认取消路径与负责人",
                status="open",
            )
        )
        async with transaction(self.session):
            self.session.add(project)
            opportunity.status = "in_progress"
            await self.session.flush()
        return project_bundle(project)

    async def get_project(
        self,
        context: OrganizationContext,
        project_id: UUID,
    ) -> OptimizationProject:
        project = await self.session.scalar(
            select(OptimizationProject)
            .where(
                OptimizationProject.id == project_id,
                OptimizationProject.organization_id == context.organization_id,
            )
            .options(
                selectinload(OptimizationProject.tasks),
                selectinload(OptimizationProject.result),
                selectinload(OptimizationProject.opportunity).selectinload(
                    SavingsOpportunity.baseline
                ),
            )
        )
        if project is None:
            raise OptimizationProjectNotFound
        return project

    async def list_projects(
        self,
        context: OrganizationContext,
    ) -> OptimizationProjectListResponse:
        projects = (
            await self.session.scalars(
                select(OptimizationProject)
                .where(
                    OptimizationProject.organization_id == context.organization_id
                )
                .options(
                    selectinload(OptimizationProject.tasks),
                    selectinload(OptimizationProject.result),
                )
                .order_by(OptimizationProject.created_at.desc())
            )
        ).all()
        return OptimizationProjectListResponse(
            items=[project_bundle(project) for project in projects]
        )

    async def realize(
        self,
        context: OrganizationContext,
        project_id: UUID,
        body: RealizeSavingsRequest,
    ) -> OptimizationProjectBundleResponse:
        async with transaction(self.session):
            project = await self.get_project(context, project_id)
            baseline = project.opportunity.baseline
            future_cost = quantize_money(
                body.new_monthly_cost * baseline.calculation_months
            )
            realized_amount = quantize_money(
                max(Decimal("0"), baseline.amount - future_cost)
            )
            if project.result is None:
                project.result = SavingsResult(
                    organization_id=context.organization_id,
                    action=body.action,
                    effective_date=body.effective_date,
                    new_monthly_cost=quantize_money(body.new_monthly_cost),
                    realized_amount=realized_amount,
                    verified_amount=Decimal("0.0000"),
                    realization_evidence=body.evidence.strip(),
                    verification_evidence_json="[]",
                    status="realized",
                )
            else:
                project.result.action = body.action
                project.result.effective_date = body.effective_date
                project.result.new_monthly_cost = quantize_money(body.new_monthly_cost)
                project.result.realized_amount = realized_amount
                project.result.realization_evidence = body.evidence.strip()
                project.result.status = "realized"
                project.result.verified_amount = Decimal("0.0000")
                project.result.verification_evidence_json = "[]"
                project.result.verified_at = None
            project.status = "realized"
            project.opportunity.status = "realized"
            await self.session.flush()
        return project_bundle(project)

    async def verify(
        self,
        context: OrganizationContext,
        project_id: UUID,
        body: VerifySavingsRequest,
    ) -> OptimizationProjectBundleResponse:
        async with transaction(self.session):
            project = await self.get_project(context, project_id)
            if project.result is None or project.result.status not in {
                "realized",
                "verified",
            }:
                raise InvalidSavingsTransition
            project.result.status = "verified"
            project.result.verified_amount = project.result.realized_amount
            project.result.verification_evidence_json = json.dumps(
                body.evidence_references,
                ensure_ascii=False,
            )
            project.result.verified_at = datetime.now(UTC)
            project.status = "verified"
            project.opportunity.status = "verified"
        return project_bundle(project)

    async def summary(self, context: OrganizationContext) -> SavingsSummaryResponse:
        opportunities = (
            await self.session.scalars(
                select(SavingsOpportunity).where(
                    SavingsOpportunity.organization_id == context.organization_id,
                    SavingsOpportunity.status != "ignored",
                )
            )
        ).all()
        results = (
            await self.session.scalars(
                select(SavingsResult).where(
                    SavingsResult.organization_id == context.organization_id
                )
            )
        ).all()
        estimated = sum(
            (
                item.estimated_amount
                for item in opportunities
                if item.category != "cost_avoidance"
            ),
            Decimal("0"),
        )
        cost_avoidance = sum(
            (
                item.estimated_amount
                for item in opportunities
                if item.category == "cost_avoidance"
            ),
            Decimal("0"),
        )
        realized = sum((item.realized_amount for item in results), Decimal("0"))
        verified = sum(
            (
                item.verified_amount
                for item in results
                if item.status == "verified"
            ),
            Decimal("0"),
        )
        return SavingsSummaryResponse(
            currency="USD",
            estimated=quantize_money(estimated),
            realized=quantize_money(realized),
            verified=quantize_money(verified),
            cost_avoidance=quantize_money(cost_avoidance),
        )
