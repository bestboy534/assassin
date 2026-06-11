from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext

from .models import Application, ApplicationSource
from .schemas import ApplicationResponse, CreateApplicationRequest, UpdateApplicationRequest


class ApplicationConflict(Exception):
    pass


class ApplicationNotFound(Exception):
    pass


def normalize_application_name(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def application_response(application: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=application.id,
        organization_id=application.organization_id,
        name=application.name,
        category=application.category,
        status=application.status,
        business_owner=application.business_owner,
        technical_owner=application.technical_owner,
        risk_level=application.risk_level,
        approved=application.approved,
    )


class ApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        context: OrganizationContext,
        *,
        search: str | None = None,
        status: str | None = None,
    ) -> list[ApplicationResponse]:
        stmt = select(Application).where(Application.organization_id == context.organization_id)
        if search:
            stmt = stmt.where(
                func.lower(Application.name).contains(normalize_application_name(search))
            )
        if status:
            stmt = stmt.where(Application.status == status)
        rows = (
            await self.session.scalars(stmt.order_by(Application.name_normalized.asc()))
        ).all()
        return [application_response(application) for application in rows]

    async def create(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateApplicationRequest,
    ) -> ApplicationResponse:
        name_normalized = normalize_application_name(body.name)
        existing_application_id = await self.session.scalar(
            select(Application.id).where(
                Application.organization_id == context.organization_id,
                Application.name_normalized == name_normalized,
            )
        )
        if existing_application_id is not None:
            raise ApplicationConflict("应用名称已存在")

        application = Application(
            organization_id=context.organization_id,
            name=body.name.strip(),
            name_normalized=name_normalized,
            category=body.category.strip() or "uncategorized",
            business_owner=body.business_owner,
            technical_owner=body.technical_owner,
            approved=body.approved,
            risk_level="unknown",
            status="active",
            created_by_user_id=user.id,
        )
        async with transaction(self.session):
            self.session.add(application)
            try:
                await self.session.flush()
            except IntegrityError as exc:
                raise ApplicationConflict("应用名称已存在") from exc
            self.session.add(
                ApplicationSource(
                    organization_id=context.organization_id,
                    application_id=application.id,
                    source_type="manual",
                    provider="manual",
                    external_id=str(application.id),
                    observed_name=application.name,
                    confidence="manual",
                    status="confirmed",
                )
            )
            await self.session.flush()
        return application_response(application)

    async def get(self, context: OrganizationContext, application_id: UUID) -> Application:
        application = await self.session.get(Application, application_id)
        if application is None or application.organization_id != context.organization_id:
            raise ApplicationNotFound
        return application

    async def update(
        self,
        context: OrganizationContext,
        application_id: UUID,
        body: UpdateApplicationRequest,
    ) -> ApplicationResponse:
        async with transaction(self.session):
            application = await self.get(context, application_id)
            if body.category is not None:
                application.category = body.category
            if body.business_owner is not None:
                application.business_owner = body.business_owner
            if body.technical_owner is not None:
                application.technical_owner = body.technical_owner
            if body.approved is not None:
                application.approved = body.approved
            if body.risk_level is not None:
                application.risk_level = body.risk_level
        return application_response(application)

    async def archive(
        self,
        context: OrganizationContext,
        application_id: UUID,
    ) -> ApplicationResponse:
        async with transaction(self.session):
            application = await self.get(context, application_id)
            application.status = "archived"
        return application_response(application)
