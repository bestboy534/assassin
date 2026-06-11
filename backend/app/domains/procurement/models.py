from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_uuid


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    software_name: Mapped[str] = mapped_column(String(180), nullable=False)
    business_reason: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    handles_sensitive_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_categories_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    current_approval_task_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    approval_tasks: Mapped[list["ApprovalTask"]] = relationship(
        back_populates="purchase_request",
        cascade="all, delete-orphan",
        order_by="ApprovalTask.created_at",
    )


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    purchase_request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("purchase_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assignee_role: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
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
    purchase_request: Mapped[PurchaseRequest] = relationship(back_populates="approval_tasks")
    decisions: Mapped[list["ApprovalDecision"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ApprovalDecision.created_at",
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint(
            "approval_task_id",
            "idempotency_key",
            name="uq_approval_decisions_task_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    approval_task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("approval_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    decided_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    task: Mapped[ApprovalTask] = relationship(back_populates="decisions")
