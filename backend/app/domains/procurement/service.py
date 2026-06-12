import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext

from .models import ApprovalDecision, ApprovalTask, PurchaseRequest
from .schemas import (
    ApprovalTaskListResponse,
    ApprovalTaskResponse,
    ApproveTaskRequest,
    CreatePurchaseRequest,
    PurchaseRequestListResponse,
    PurchaseRequestResponse,
)


class PurchaseRequestNotFound(Exception):
    pass


class ApprovalTaskNotFound(Exception):
    pass


def _categories_from_request(request: PurchaseRequest) -> list[str]:
    try:
        raw = json.loads(request.data_categories_json or "[]")
    except json.JSONDecodeError:
        raw = []
    return [str(category) for category in raw if str(category).strip()]


def purchase_request_response(request: PurchaseRequest) -> PurchaseRequestResponse:
    return PurchaseRequestResponse(
        id=request.id,
        organization_id=request.organization_id,
        software_name=request.software_name,
        business_reason=request.business_reason,
        estimated_monthly_cost_usd=request.estimated_monthly_cost_usd,
        department=request.department,
        handles_sensitive_data=request.handles_sensitive_data,
        data_categories=_categories_from_request(request),
        status=request.status,
        current_approval_task_id=request.current_approval_task_id,
        submitted_at=request.submitted_at,
        decided_at=request.decided_at,
        created_at=request.created_at,
    )


def approval_task_response(task: ApprovalTask) -> ApprovalTaskResponse:
    return ApprovalTaskResponse(
        id=task.id,
        organization_id=task.organization_id,
        purchase_request_id=task.purchase_request_id,
        assignee_role=task.assignee_role,
        status=task.status,
        created_at=task.created_at,
    )


class ProcurementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        context: OrganizationContext,
        user: User,
        body: CreatePurchaseRequest,
    ) -> PurchaseRequestResponse:
        request = PurchaseRequest(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            software_name=body.software_name.strip(),
            business_reason=body.business_reason.strip(),
            estimated_monthly_cost_usd=body.estimated_monthly_cost_usd,
            department=body.department.strip(),
            handles_sensitive_data=body.handles_sensitive_data,
            data_categories_json=json.dumps(body.data_categories, ensure_ascii=False),
            status="draft",
        )
        async with transaction(self.session):
            self.session.add(request)
            await self.session.flush()
        return purchase_request_response(request)

    async def list_requests(self, context: OrganizationContext) -> PurchaseRequestListResponse:
        requests = (
            await self.session.scalars(
                select(PurchaseRequest)
                .where(PurchaseRequest.organization_id == context.organization_id)
                .order_by(PurchaseRequest.created_at.desc())
            )
        ).all()
        return PurchaseRequestListResponse(
            items=[purchase_request_response(item) for item in requests]
        )

    async def get_request(self, context: OrganizationContext, request_id: UUID) -> PurchaseRequest:
        request = await self.session.get(PurchaseRequest, request_id)
        if request is None or request.organization_id != context.organization_id:
            raise PurchaseRequestNotFound
        return request

    async def get_request_response(
        self,
        context: OrganizationContext,
        request_id: UUID,
    ) -> PurchaseRequestResponse:
        return purchase_request_response(await self.get_request(context, request_id))

    async def submit_request(
        self,
        context: OrganizationContext,
        request_id: UUID,
    ) -> PurchaseRequestResponse:
        async with transaction(self.session):
            request = await self.get_request(context, request_id)
            if request.status == "draft":
                request.status = "in_review"
                request.submitted_at = datetime.now(UTC)
                if request.current_approval_task_id is None:
                    task = ApprovalTask(
                        organization_id=context.organization_id,
                        purchase_request_id=request.id,
                        assignee_role="finance",
                        status="pending",
                    )
                    self.session.add(task)
                    await self.session.flush()
                    request.current_approval_task_id = task.id
        return purchase_request_response(request)

    async def list_tasks(self, context: OrganizationContext) -> ApprovalTaskListResponse:
        tasks = (
            await self.session.scalars(
                select(ApprovalTask)
                .where(ApprovalTask.organization_id == context.organization_id)
                .order_by(ApprovalTask.created_at.desc())
            )
        ).all()
        return ApprovalTaskListResponse(items=[approval_task_response(task) for task in tasks])

    async def get_task(self, context: OrganizationContext, task_id: UUID) -> ApprovalTask:
        task = await self.session.get(ApprovalTask, task_id)
        if task is None or task.organization_id != context.organization_id:
            raise ApprovalTaskNotFound
        return task

    async def approve_task(
        self,
        context: OrganizationContext,
        task_id: UUID,
        user: User,
        body: ApproveTaskRequest,
        idempotency_key: str,
    ) -> ApprovalTaskResponse:
        async with transaction(self.session):
            task = await self.get_task(context, task_id)
            existing = await self.session.scalar(
                select(ApprovalDecision).where(
                    ApprovalDecision.approval_task_id == task.id,
                    ApprovalDecision.idempotency_key == idempotency_key,
                )
            )
            if existing is None:
                self.session.add(
                    ApprovalDecision(
                        organization_id=context.organization_id,
                        approval_task_id=task.id,
                        decided_by_user_id=user.id,
                        decision="approved",
                        comment=body.comment.strip(),
                        idempotency_key=idempotency_key,
                    )
                )
                try:
                    await self.session.flush()
                except IntegrityError as exc:
                    raise ApprovalTaskNotFound from exc
                task.status = "approved"
                request = await self.get_request(context, task.purchase_request_id)
                request.status = "approved"
                request.decided_at = datetime.now(UTC)
        return approval_task_response(task)
