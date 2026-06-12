from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_uuid


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(180), nullable=False)
    application_name: Mapped[str | None] = mapped_column(String(180))
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    current_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
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
    versions: Mapped[list["ContractVersion"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractVersion.version_number",
    )
    renewals: Mapped[list["Renewal"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="Renewal.renewal_date",
    )


class ContractVersion(Base):
    __tablename__ = "contract_versions"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "version_number",
            name="uq_contract_versions_contract_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    billing_frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notice_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    contract: Mapped[Contract] = relationship(back_populates="versions")


class Renewal(Base):
    __tablename__ = "renewals"
    __table_args__ = (
        UniqueConstraint(
            "contract_id",
            "source_version_id",
            name="uq_renewals_contract_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    contract_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contract_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    renewal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    decision_deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="upcoming", index=True)
    decision: Mapped[str | None] = mapped_column(String(32))
    current_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    contract: Mapped[Contract] = relationship(back_populates="renewals")
