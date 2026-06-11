from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext

from .models import Contract, ContractVersion, Renewal
from .schemas import (
    ContractBundleResponse,
    ContractListResponse,
    ContractResponse,
    ContractVersionResponse,
    CreateContractRequest,
    RenewalListResponse,
    RenewalResponse,
    UpdateContractVersionRequest,
)


class ContractNotFound(Exception):
    pass


class ContractVersionNotFound(Exception):
    pass


class ImmutableContractVersion(Exception):
    pass


class InvalidContractDates(Exception):
    pass


def contract_response(contract: Contract) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        organization_id=contract.organization_id,
        name=contract.name,
        vendor_name=contract.vendor_name,
        application_name=contract.application_name,
        owner_name=contract.owner_name,
        status=contract.status,
        current_version_id=contract.current_version_id,
        created_at=contract.created_at,
    )


def version_response(version: ContractVersion) -> ContractVersionResponse:
    return ContractVersionResponse(
        id=version.id,
        organization_id=version.organization_id,
        contract_id=version.contract_id,
        version_number=version.version_number,
        status=version.status,
        start_date=version.start_date,
        end_date=version.end_date,
        amount=version.amount,
        currency=version.currency,
        billing_frequency=version.billing_frequency,
        auto_renew=version.auto_renew,
        notice_period_days=version.notice_period_days,
        signed_at=version.signed_at,
    )


def renewal_response(renewal: Renewal) -> RenewalResponse:
    return RenewalResponse(
        id=renewal.id,
        organization_id=renewal.organization_id,
        contract_id=renewal.contract_id,
        source_version_id=renewal.source_version_id,
        renewal_date=renewal.renewal_date,
        decision_deadline=renewal.decision_deadline,
        owner_name=renewal.owner_name,
        status=renewal.status,
        decision=renewal.decision,
        current_amount=renewal.current_amount,
        currency=renewal.currency,
    )


class ContractService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateContractRequest,
    ) -> ContractBundleResponse:
        contract = Contract(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            name=body.name.strip(),
            vendor_name=body.vendor_name.strip(),
            application_name=body.application_name.strip() if body.application_name else None,
            owner_name=body.owner_name.strip(),
            status="draft",
        )
        async with transaction(self.session):
            self.session.add(contract)
            await self.session.flush()
            version = ContractVersion(
                organization_id=context.organization_id,
                contract_id=contract.id,
                version_number=1,
                status="draft",
                start_date=body.start_date,
                end_date=body.end_date,
                amount=body.amount,
                currency=body.currency.upper(),
                billing_frequency=body.billing_frequency,
                auto_renew=body.auto_renew,
                notice_period_days=body.notice_period_days,
            )
            self.session.add(version)
            await self.session.flush()
            contract.current_version_id = version.id
        return ContractBundleResponse(
            contract=contract_response(contract),
            version=version_response(version),
        )

    async def list(self, context: OrganizationContext) -> ContractListResponse:
        contracts = (
            await self.session.scalars(
                select(Contract)
                .where(Contract.organization_id == context.organization_id)
                .order_by(Contract.created_at.desc())
            )
        ).all()
        return ContractListResponse(items=[contract_response(contract) for contract in contracts])

    async def get(self, context: OrganizationContext, contract_id: UUID) -> Contract:
        contract = await self.session.get(Contract, contract_id)
        if contract is None or contract.organization_id != context.organization_id:
            raise ContractNotFound
        return contract

    async def get_response(
        self,
        context: OrganizationContext,
        contract_id: UUID,
    ) -> ContractResponse:
        return contract_response(await self.get(context, contract_id))

    async def get_version(
        self,
        context: OrganizationContext,
        contract_id: UUID,
        version_id: UUID,
    ) -> ContractVersion:
        version = await self.session.get(ContractVersion, version_id)
        if (
            version is None
            or version.organization_id != context.organization_id
            or version.contract_id != contract_id
        ):
            raise ContractVersionNotFound
        return version

    async def update_version(
        self,
        context: OrganizationContext,
        contract_id: UUID,
        version_id: UUID,
        body: UpdateContractVersionRequest,
    ) -> ContractVersionResponse:
        async with transaction(self.session):
            version = await self.get_version(context, contract_id, version_id)
            if version.status == "signed":
                raise ImmutableContractVersion
            if body.start_date is not None:
                version.start_date = body.start_date
            if body.end_date is not None:
                version.end_date = body.end_date
            if version.end_date <= version.start_date:
                raise InvalidContractDates
            if body.amount is not None:
                version.amount = body.amount
            if body.currency is not None:
                version.currency = body.currency.upper()
            if body.billing_frequency is not None:
                version.billing_frequency = body.billing_frequency
            if body.auto_renew is not None:
                version.auto_renew = body.auto_renew
            if body.notice_period_days is not None:
                version.notice_period_days = body.notice_period_days
        return version_response(version)

    async def mark_signed(
        self,
        context: OrganizationContext,
        contract_id: UUID,
        version_id: UUID,
    ) -> ContractBundleResponse:
        async with transaction(self.session):
            contract = await self.get(context, contract_id)
            version = await self.get_version(context, contract_id, version_id)
            renewal = await self.session.scalar(
                select(Renewal).where(
                    Renewal.contract_id == contract.id,
                    Renewal.source_version_id == version.id,
                )
            )
            if version.status != "signed":
                version.status = "signed"
                version.signed_at = datetime.now(UTC)
                contract.status = "active"
                contract.current_version_id = version.id
            if renewal is None:
                renewal = Renewal(
                    organization_id=context.organization_id,
                    contract_id=contract.id,
                    source_version_id=version.id,
                    renewal_date=version.end_date,
                    decision_deadline=version.end_date
                    - timedelta(days=version.notice_period_days),
                    owner_name=contract.owner_name,
                    status="upcoming",
                    current_amount=version.amount,
                    currency=version.currency,
                )
                self.session.add(renewal)
                await self.session.flush()
        return ContractBundleResponse(
            contract=contract_response(contract),
            version=version_response(version),
            renewal=renewal_response(renewal),
        )

    async def list_renewals(self, context: OrganizationContext) -> RenewalListResponse:
        renewals = (
            await self.session.scalars(
                select(Renewal)
                .where(Renewal.organization_id == context.organization_id)
                .order_by(Renewal.decision_deadline.asc())
            )
        ).all()
        return RenewalListResponse(items=[renewal_response(item) for item in renewals])
