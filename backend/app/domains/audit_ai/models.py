from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    source_hint: Mapped[str] = mapped_column(String(32), nullable=False)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    total_monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    items: Mapped[list["AnalysisItem"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AnalysisItem.position",
    )


class AnalysisItem(Base):
    __tablename__ = "analysis_items"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    software_name: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_date: Mapped[str | None] = mapped_column(String(32))
    normalized_amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    needs_user_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancel_url: Mapped[str | None] = mapped_column(Text)
    fallback_search_url: Mapped[str | None] = mapped_column(Text)
    support_email: Mapped[str | None] = mapped_column(String(320))
    guide_steps_json: Mapped[str] = mapped_column(Text, nullable=False)
    risk_note: Mapped[str | None] = mapped_column(Text)
    run: Mapped[AnalysisRun] = relationship(back_populates="items")
