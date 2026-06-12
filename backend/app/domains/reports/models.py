from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import new_uuid


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    query_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    chart_type: Mapped[str] = mapped_column(String(40), nullable=False, default="table")
    visibility: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="private",
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
    snapshots: Mapped[list["ReportSnapshot"]] = relationship(
        back_populates="saved_report",
        cascade="all, delete-orphan",
    )
    exports: Mapped[list["ReportExport"]] = relationship(
        back_populates="saved_report",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list["ReportSubscription"]] = relationship(
        back_populates="saved_report",
        cascade="all, delete-orphan",
    )


class ReportShare(Base):
    __tablename__ = "report_shares"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(80), index=True)
    member_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    saved_report: Mapped[SavedReport] = relationship(back_populates="snapshots")


class ReportExport(Base):
    __tablename__ = "report_exports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    content_base64: Mapped[str] = mapped_column(Text, nullable=False)
    download_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    permissions_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    saved_report: Mapped[SavedReport] = relationship(back_populates="exports")


class ReportSubscription(Base):
    __tablename__ = "report_subscriptions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    saved_report_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("saved_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    cron: Mapped[str] = mapped_column(String(80), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    recipients_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    saved_report: Mapped[SavedReport] = relationship(back_populates="subscriptions")
