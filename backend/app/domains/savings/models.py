from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_uuid


class SavingsOpportunity(Base):
    __tablename__ = "savings_opportunities"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_type",
            "source_id",
            "rule_version",
            "period_key",
            name="uq_savings_opportunities_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(180), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new", index=True)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    baseline: Mapped["SavingsBaseline"] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        uselist=False,
    )
    project: Mapped["OptimizationProject | None"] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SavingsBaseline(Base):
    __tablename__ = "savings_baselines"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("savings_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    monthly_cost: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    calculation_months: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(80), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    opportunity: Mapped[SavingsOpportunity] = relationship(back_populates="baseline")


class OptimizationProject(Base):
    __tablename__ = "optimization_projects"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    opportunity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("savings_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    target_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    opportunity: Mapped[SavingsOpportunity] = relationship(back_populates="project")
    tasks: Mapped[list["OptimizationTask"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    result: Mapped["SavingsResult | None"] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )


class OptimizationTask(Base):
    __tablename__ = "optimization_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("optimization_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    project: Mapped[OptimizationProject] = relationship(back_populates="tasks")


class SavingsResult(Base):
    __tablename__ = "savings_results"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("optimization_projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="realized")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    new_monthly_cost: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    realized_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    verified_amount: Mapped[Decimal] = mapped_column(
        Numeric(19, 4),
        nullable=False,
        default=Decimal("0.0000"),
    )
    realization_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    verification_evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    project: Mapped[OptimizationProject] = relationship(back_populates="result")
