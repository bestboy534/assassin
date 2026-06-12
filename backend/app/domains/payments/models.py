from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_payment_requests_org_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    purchase_request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="creating", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    instrument: Mapped["PaymentInstrument | None"] = relationship(
        back_populates="payment_request",
        cascade="all, delete-orphan",
        uselist=False,
    )


class PaymentInstrument(Base):
    __tablename__ = "payment_instruments"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_id",
            name="uq_payment_instruments_provider_external",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    payment_request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payment_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    brand: Mapped[str] = mapped_column(String(40), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sandbox: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    merchant_lock: Mapped[str] = mapped_column(String(180), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    payment_request: Mapped[PaymentRequest] = relationship(back_populates="instrument")
    limits: Mapped["PaymentLimit"] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan",
        uselist=False,
    )
    actions: Mapped[list["PaymentAction"]] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan",
    )


class PaymentLimit(Base):
    __tablename__ = "payment_limits"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payment_instruments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    single_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    daily_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    instrument: Mapped[PaymentInstrument] = relationship(back_populates="limits")


class PaymentAction(Base):
    __tablename__ = "payment_actions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payment_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    instrument: Mapped[PaymentInstrument] = relationship(back_populates="actions")


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_payment_events_provider_event"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    instrument_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payment_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
