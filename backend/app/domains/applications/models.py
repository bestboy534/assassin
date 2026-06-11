from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import new_uuid


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "name_normalized",
            name="uq_applications_org_name_normalized",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="uncategorized")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    business_owner: Mapped[str | None] = mapped_column(String(120))
    technical_owner: Mapped[str | None] = mapped_column(String(120))
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
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


class ApplicationSource(Base):
    __tablename__ = "application_sources"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "provider",
            "external_id",
            name="uq_application_sources_external",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    application_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    observed_name: Mapped[str] = mapped_column(String(180), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed")
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
