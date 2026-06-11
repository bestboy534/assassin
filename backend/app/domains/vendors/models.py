from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_uuid


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "normalized_name",
            name="uq_vendors_organization_normalized_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    country_code: Mapped[str | None] = mapped_column(String(8))
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    business_owner: Mapped[str | None] = mapped_column(String(120))
    risk_owner: Mapped[str | None] = mapped_column(String(120))
    overall_risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="not_assessed",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    aliases: Mapped[list["VendorAlias"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
    )
    assessments: Mapped[list["VendorRiskAssessment"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
    )
    findings: Mapped[list["RiskFinding"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
    )


class VendorAlias(Base):
    __tablename__ = "vendor_aliases"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "normalized_alias",
            name="uq_vendor_aliases_organization_normalized_alias",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    vendor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    vendor: Mapped[Vendor] = relationship(back_populates="aliases")


class VendorRiskAssessment(Base):
    __tablename__ = "vendor_risk_assessments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    vendor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    questionnaire_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions_json: Mapped[str] = mapped_column(Text, nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    vendor: Mapped[Vendor] = relationship(back_populates="assessments")
    findings: Mapped[list["RiskFinding"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
    )


class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    vendor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("vendor_risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mitigation_plan: Mapped[str | None] = mapped_column(Text)
    accepted_reason: Mapped[str | None] = mapped_column(Text)
    accepted_until: Mapped[date | None] = mapped_column(Date)
    accepted_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    vendor: Mapped[Vendor] = relationship(back_populates="findings")
    assessment: Mapped[VendorRiskAssessment] = relationship(back_populates="findings")
