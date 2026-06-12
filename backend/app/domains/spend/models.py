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


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "fiscal_year",
            "department",
            "currency",
            name="uq_budgets_org_year_department_currency",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    commitments: Mapped[list["BudgetCommitment"]] = relationship(
        back_populates="budget",
        cascade="all, delete-orphan",
    )


class BudgetCommitment(Base):
    __tablename__ = "budget_commitments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    budget_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commitment_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    budget: Mapped[Budget] = relationship(back_populates="commitments")


class SpendTransaction(Base):
    __tablename__ = "spend_transactions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_provider",
            "source_account_id",
            "external_id",
            name="uq_spend_transactions_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    source_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    source_account_id: Mapped[str] = mapped_column(String(120), nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    merchant_name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    application_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    match_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0.0000"),
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
    splits: Mapped[list["TransactionSplit"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spend_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    transaction: Mapped[SpendTransaction] = relationship(back_populates="splits")


class TransactionAnomaly(Base):
    __tablename__ = "transaction_anomalies"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "code",
            "rule_version",
            name="uq_transaction_anomalies_rule",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spend_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    budget_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("budgets.id", ondelete="SET NULL"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False)
    baseline_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    observed_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "start_date",
            "end_date",
            name="uq_accounting_periods_org_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    locked_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
