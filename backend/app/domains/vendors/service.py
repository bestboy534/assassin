import json
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transactions import transaction
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext

from .models import RiskFinding, Vendor, VendorAlias, VendorRiskAssessment
from .schemas import (
    AcceptRiskFindingRequest,
    CreateVendorAssessmentRequest,
    CreateVendorRequest,
    LatestVendorAssessmentResponse,
    RiskDimensionResponse,
    RiskFindingListResponse,
    RiskFindingResponse,
    VendorAliasResponse,
    VendorAssessmentBundleResponse,
    VendorAssessmentResponse,
    VendorListResponse,
    VendorResponse,
)

RISK_RULE_VERSION = "vendor-risk-v1"
RISK_ACCEPTANCE_ROLES = {"owner", "admin", "security", "security_admin"}


class VendorNotFound(Exception):
    pass


class VendorConflict(Exception):
    pass


class RiskFindingNotFound(Exception):
    pass


class RiskAcceptanceForbidden(Exception):
    pass


def normalize_vendor_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


@dataclass(frozen=True)
class RiskScore:
    total: int
    dimensions: dict[str, RiskDimensionResponse]


def score_vendor_risk(body: CreateVendorAssessmentRequest) -> RiskScore:
    security_reasons: list[str] = []
    security = 0
    if not body.has_soc2:
        security += 30
        security_reasons.append("未提供 SOC 2 报告")
    if not body.has_iso27001:
        security += 20
        security_reasons.append("未提供 ISO 27001 认证")
    if not body.supports_sso:
        security += 20
        security_reasons.append("不支持企业单点登录")
    if not body.has_incident_response:
        security += 10
        security_reasons.append("未确认事件响应机制")

    privacy_reasons: list[str] = []
    privacy = 30 if body.stores_sensitive_data else 0
    if body.stores_sensitive_data:
        privacy_reasons.append("处理敏感数据")
    if not body.has_dpa:
        privacy += 60 if body.stores_sensitive_data else 20
        privacy_reasons.append("未提供数据处理协议")

    financial_map = {"strong": 15, "medium": 45, "weak": 85}
    financial = financial_map[body.financial_stability]
    financial_reasons = [f"财务稳定性评估为 {body.financial_stability}"]

    criticality_map = {"low": 15, "medium": 35, "high": 55}
    operational = criticality_map[body.service_criticality]
    operational_reasons = [f"服务关键性为 {body.service_criticality}"]
    if not body.has_incident_response:
        operational += 20
        operational_reasons.append("缺少事件响应证明")

    compliance_reasons: list[str] = []
    compliance = 0
    if not body.has_soc2:
        compliance += 30
        compliance_reasons.append("SOC 2 证据缺失")
    if not body.has_iso27001:
        compliance += 25
        compliance_reasons.append("ISO 27001 证据缺失")
    if body.stores_sensitive_data and not body.has_dpa:
        compliance += 25
        compliance_reasons.append("敏感数据场景缺少 DPA")

    dimensions = {
        "security": RiskDimensionResponse(score=min(security, 100), reasons=security_reasons),
        "privacy": RiskDimensionResponse(score=min(privacy, 100), reasons=privacy_reasons),
        "financial": RiskDimensionResponse(score=financial, reasons=financial_reasons),
        "operational": RiskDimensionResponse(
            score=min(operational, 100),
            reasons=operational_reasons,
        ),
        "compliance": RiskDimensionResponse(
            score=min(compliance, 100),
            reasons=compliance_reasons,
        ),
    }
    total = round(sum(item.score for item in dimensions.values()) / len(dimensions))
    return RiskScore(total=total, dimensions=dimensions)


def vendor_response(vendor: Vendor) -> VendorResponse:
    return VendorResponse(
        id=vendor.id,
        organization_id=vendor.organization_id,
        name=vendor.name,
        domain=vendor.domain,
        country_code=vendor.country_code,
        category=vendor.category,
        status=vendor.status,
        business_owner=vendor.business_owner,
        risk_owner=vendor.risk_owner,
        overall_risk_score=vendor.overall_risk_score,
        risk_level=vendor.risk_level,
        created_at=vendor.created_at,
    )


def assessment_response(assessment: VendorRiskAssessment) -> VendorAssessmentResponse:
    raw_dimensions = json.loads(assessment.dimensions_json)
    dimensions = {
        key: RiskDimensionResponse.model_validate(value)
        for key, value in raw_dimensions.items()
    }
    return VendorAssessmentResponse(
        id=assessment.id,
        vendor_id=assessment.vendor_id,
        questionnaire_version=assessment.questionnaire_version,
        rule_version=assessment.rule_version,
        status=assessment.status,
        total_score=assessment.total_score,
        dimensions=dimensions,
        submitted_at=assessment.submitted_at,
    )


def finding_response(finding: RiskFinding) -> RiskFindingResponse:
    return RiskFindingResponse(
        id=finding.id,
        vendor_id=finding.vendor_id,
        assessment_id=finding.assessment_id,
        dimension=finding.dimension,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        status=finding.status,
        owner_name=finding.owner_name,
        due_date=finding.due_date,
        mitigation_plan=finding.mitigation_plan,
        accepted_reason=finding.accepted_reason,
        accepted_until=finding.accepted_until,
    )


class VendorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        context: OrganizationContext,
        user: User,
        body: CreateVendorRequest,
    ) -> VendorResponse:
        normalized_name = normalize_vendor_name(body.name)
        existing = await self.session.scalar(
            select(Vendor).where(
                Vendor.organization_id == context.organization_id,
                Vendor.normalized_name == normalized_name,
            )
        )
        if existing is not None:
            raise VendorConflict
        vendor = Vendor(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            name=body.name.strip(),
            normalized_name=normalized_name,
            domain=body.domain.strip().casefold() if body.domain else None,
            country_code=body.country_code.strip().upper() if body.country_code else None,
            category=body.category.strip(),
            business_owner=body.business_owner.strip() if body.business_owner else None,
            risk_owner=body.risk_owner.strip() if body.risk_owner else None,
            status="active",
        )
        async with transaction(self.session):
            self.session.add(vendor)
            await self.session.flush()
        return vendor_response(vendor)

    async def list(self, context: OrganizationContext) -> VendorListResponse:
        vendors = (
            await self.session.scalars(
                select(Vendor)
                .where(Vendor.organization_id == context.organization_id)
                .order_by(Vendor.created_at.desc())
            )
        ).all()
        return VendorListResponse(items=[vendor_response(vendor) for vendor in vendors])

    async def get(self, context: OrganizationContext, vendor_id: UUID) -> Vendor:
        vendor = await self.session.get(Vendor, vendor_id)
        if vendor is None or vendor.organization_id != context.organization_id:
            raise VendorNotFound
        return vendor

    async def get_response(
        self,
        context: OrganizationContext,
        vendor_id: UUID,
    ) -> VendorResponse:
        return vendor_response(await self.get(context, vendor_id))

    async def archive(
        self,
        context: OrganizationContext,
        vendor_id: UUID,
    ) -> VendorResponse:
        async with transaction(self.session):
            vendor = await self.get(context, vendor_id)
            vendor.status = "archived"
        return vendor_response(vendor)

    async def add_alias(
        self,
        context: OrganizationContext,
        vendor_id: UUID,
        alias_value: str,
    ) -> VendorAliasResponse:
        vendor = await self.get(context, vendor_id)
        normalized_alias = normalize_vendor_name(alias_value)
        existing = await self.session.scalar(
            select(VendorAlias).where(
                VendorAlias.organization_id == context.organization_id,
                VendorAlias.normalized_alias == normalized_alias,
            )
        )
        if existing is not None:
            if existing.vendor_id != vendor.id:
                raise VendorConflict
            return VendorAliasResponse(id=existing.id, vendor_id=vendor.id, alias=existing.alias)
        alias = VendorAlias(
            organization_id=context.organization_id,
            vendor_id=vendor.id,
            alias=alias_value.strip(),
            normalized_alias=normalized_alias,
        )
        async with transaction(self.session):
            self.session.add(alias)
            await self.session.flush()
        return VendorAliasResponse(id=alias.id, vendor_id=vendor.id, alias=alias.alias)

    async def match(
        self,
        context: OrganizationContext,
        candidate: str,
    ) -> VendorResponse:
        normalized = normalize_vendor_name(candidate)
        vendor = await self.session.scalar(
            select(Vendor).where(
                Vendor.organization_id == context.organization_id,
                Vendor.normalized_name == normalized,
            )
        )
        if vendor is None:
            vendor = await self.session.scalar(
                select(Vendor)
                .join(VendorAlias, VendorAlias.vendor_id == Vendor.id)
                .where(
                    Vendor.organization_id == context.organization_id,
                    VendorAlias.normalized_alias == normalized,
                )
            )
        if vendor is None:
            raise VendorNotFound
        return vendor_response(vendor)

    async def assess(
        self,
        context: OrganizationContext,
        user: User,
        vendor_id: UUID,
        body: CreateVendorAssessmentRequest,
    ) -> VendorAssessmentBundleResponse:
        score = score_vendor_risk(body)
        async with transaction(self.session):
            vendor = await self.get(context, vendor_id)
            assessment = VendorRiskAssessment(
                organization_id=context.organization_id,
                vendor_id=vendor.id,
                questionnaire_version=body.questionnaire_version,
                rule_version=RISK_RULE_VERSION,
                status="completed",
                total_score=score.total,
                dimensions_json=json.dumps(
                    {
                        key: value.model_dump()
                        for key, value in score.dimensions.items()
                    },
                    ensure_ascii=False,
                ),
                answers_json=body.model_dump_json(),
                submitted_by_user_id=user.id,
            )
            self.session.add(assessment)
            await self.session.flush()
            findings: list[RiskFinding] = []
            owner_name = vendor.risk_owner or "未分配"
            for dimension, dimension_score in score.dimensions.items():
                if dimension_score.score < 75:
                    continue
                finding = RiskFinding(
                    organization_id=context.organization_id,
                    vendor_id=vendor.id,
                    assessment_id=assessment.id,
                    dimension=dimension,
                    title=f"{dimension_label(dimension)}风险需要处理",
                    description="；".join(dimension_score.reasons),
                    severity="high" if dimension_score.score >= 80 else "medium",
                    status="open",
                    owner_name=owner_name,
                    due_date=date.today() + timedelta(days=30),
                )
                self.session.add(finding)
                findings.append(finding)
            await self.session.flush()
            vendor.overall_risk_score = score.total
            vendor.risk_level = risk_level(score.total)
        return VendorAssessmentBundleResponse(
            assessment=assessment_response(assessment),
            findings=[finding_response(item) for item in findings],
        )

    async def latest_assessment(
        self,
        context: OrganizationContext,
        vendor_id: UUID,
    ) -> LatestVendorAssessmentResponse:
        vendor = await self.get(context, vendor_id)
        assessment = await self.session.scalar(
            select(VendorRiskAssessment)
            .where(
                VendorRiskAssessment.organization_id == context.organization_id,
                VendorRiskAssessment.vendor_id == vendor.id,
            )
            .order_by(VendorRiskAssessment.submitted_at.desc())
            .limit(1)
        )
        if assessment is None:
            return LatestVendorAssessmentResponse(item=None)
        findings = (
            await self.session.scalars(
                select(RiskFinding)
                .where(
                    RiskFinding.organization_id == context.organization_id,
                    RiskFinding.assessment_id == assessment.id,
                )
                .order_by(RiskFinding.created_at.asc())
            )
        ).all()
        return LatestVendorAssessmentResponse(
            item=VendorAssessmentBundleResponse(
                assessment=assessment_response(assessment),
                findings=[finding_response(item) for item in findings],
            )
        )

    async def list_findings(
        self,
        context: OrganizationContext,
    ) -> RiskFindingListResponse:
        findings = (
            await self.session.scalars(
                select(RiskFinding)
                .where(RiskFinding.organization_id == context.organization_id)
                .order_by(RiskFinding.created_at.desc())
            )
        ).all()
        return RiskFindingListResponse(items=[finding_response(item) for item in findings])

    async def accept_finding(
        self,
        context: OrganizationContext,
        user: User,
        finding_id: UUID,
        body: AcceptRiskFindingRequest,
    ) -> RiskFindingResponse:
        if context.role not in RISK_ACCEPTANCE_ROLES:
            raise RiskAcceptanceForbidden
        async with transaction(self.session):
            finding = await self.session.get(RiskFinding, finding_id)
            if finding is None or finding.organization_id != context.organization_id:
                raise RiskFindingNotFound
            finding.status = "accepted"
            finding.accepted_reason = body.reason.strip()
            finding.accepted_until = body.expires_at
            finding.owner_name = body.risk_owner.strip()
            finding.accepted_by_user_id = user.id
            finding.accepted_at = datetime.now(UTC)
        return finding_response(finding)


def dimension_label(dimension: str) -> str:
    labels = {
        "security": "安全",
        "privacy": "隐私",
        "financial": "财务",
        "operational": "运营",
        "compliance": "合规",
    }
    return labels.get(dimension, dimension)


def risk_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"
