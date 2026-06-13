import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.billing.subscriptions import SubscriptionService
from app.domains.identity.models import User

from .models import Organization, OrganizationMember
from .schemas import OrganizationResponse


def make_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().casefold()).strip("-")
    return slug or "org"


@dataclass(frozen=True)
class OrganizationContext:
    organization_id: UUID
    user_id: UUID
    membership_id: UUID
    role: str


class OrganizationNotFound(Exception):
    pass


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[OrganizationResponse]:
        rows = (
            await self.session.execute(
                select(Organization, OrganizationMember)
                .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
                .where(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "active",
                    Organization.status == "active",
                )
                .order_by(Organization.created_at.asc())
            )
        ).all()
        return [
            OrganizationResponse(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                role=member.role,
            )
            for organization, member in rows
        ]

    async def create(self, user: User, name: str) -> OrganizationResponse:
        async with transaction(self.session):
            organization = Organization(
                name=name.strip(),
                slug=await self._unique_slug(make_slug(name)),
                created_by_user_id=user.id,
            )
            self.session.add(organization)
            await self.session.flush()
            member = OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role="owner",
                status="active",
            )
            self.session.add(member)
            await SubscriptionService(self.session).start_trial(organization.id)
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            role="owner",
        )

    async def get_context(self, user_id: UUID, organization_id: UUID) -> OrganizationContext:
        row = (
            await self.session.execute(
                select(Organization, OrganizationMember)
                .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
                .where(
                    Organization.id == organization_id,
                    Organization.status == "active",
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "active",
                )
            )
        ).first()
        if row is None:
            raise OrganizationNotFound
        _, member = row
        return OrganizationContext(
            organization_id=organization_id,
            user_id=user_id,
            membership_id=member.id,
            role=member.role,
        )

    async def _unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while await self.session.scalar(select(Organization.id).where(Organization.slug == slug)):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug
