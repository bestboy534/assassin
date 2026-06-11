from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.organizations.models import Organization, OrganizationMember
from app.domains.organizations.service import make_slug

from .models import User, UserSession
from .schemas import OrganizationSummary, UserResponse
from .security import (
    hash_password,
    hash_token,
    hash_user_agent,
    new_session_token,
    normalize_email,
    verify_password,
)


class AuthenticationError(Exception):
    pass


class ConflictError(Exception):
    pass


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        organization_name: str | None,
        user_agent: str | None,
    ) -> tuple[User, str]:
        email_normalized = normalize_email(email)
        async with transaction(self.session):
            user = User(
                email_normalized=email_normalized,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                status="active",
                email_verified_at=User.verified_now(),
            )
            self.session.add(user)
            await self.session.flush()
            org_name = (organization_name or f"{display_name.strip()} 的工作区").strip()
            organization = Organization(
                name=org_name,
                slug=await self._unique_slug(make_slug(org_name)),
                created_by_user_id=user.id,
            )
            self.session.add(organization)
            await self.session.flush()
            self.session.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=user.id,
                    role="owner",
                    status="active",
                )
            )
            try:
                raw_token = await self._create_session(user.id, user_agent)
            except IntegrityError as exc:
                raise ConflictError("邮箱已存在") from exc
        return user, raw_token

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
    ) -> tuple[User, str]:
        email_normalized = normalize_email(email)
        user = await self._user_by_email(email_normalized)
        if (
            user is None
            or user.status != "active"
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError("邮箱或密码不正确")
        async with transaction(self.session):
            user.last_login_at = datetime.now(UTC)
            raw_token = await self._create_session(user.id, user_agent)
        return user, raw_token

    async def authenticate_token(self, raw_token: str | None) -> User | None:
        if not raw_token:
            return None
        now = datetime.now(UTC)
        token_hash = hash_token(raw_token)
        stmt: Select[tuple[UserSession]] = select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        user_session = await self.session.scalar(stmt)
        if user_session is None:
            return None
        user = await self.session.get(User, user_session.user_id)
        if user is None or user.status != "active":
            return None
        user_session.last_seen_at = now
        await self.session.commit()
        return user

    async def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        user_session = await self.session.scalar(
            select(UserSession).where(UserSession.token_hash == hash_token(raw_token))
        )
        if user_session is None:
            return
        async with transaction(self.session):
            user_session.revoked_at = datetime.now(UTC)

    async def organizations_for_user(self, user_id: UUID) -> list[OrganizationSummary]:
        rows = (
            await self.session.execute(
                select(Organization, OrganizationMember)
                .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
                .where(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "active",
                )
                .order_by(Organization.created_at.asc())
            )
        ).all()
        return [
            OrganizationSummary(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                role=member.role,
            )
            for organization, member in rows
        ]

    async def _user_by_email(self, email_normalized: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.email_normalized == email_normalized)
            ),
        )

    async def _unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        suffix = 2
        while await self.session.scalar(select(Organization.id).where(Organization.slug == slug)):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    async def _create_session(self, user_id: UUID, user_agent: str | None) -> str:
        raw_token = new_session_token()
        self.session.add(
            UserSession(
                user_id=user_id,
                token_hash=hash_token(raw_token),
                user_agent_hash=hash_user_agent(user_agent),
                expires_at=datetime.now(UTC) + timedelta(days=14),
            )
        )
        await self.session.flush()
        return raw_token


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email_normalized,
        display_name=user.display_name,
        status=user.status,
    )
