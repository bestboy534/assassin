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


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_type",
            "external_id",
            name="uq_invoices_org_source_external",
        ),
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_invoices_org_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(180), nullable=False)
    vendor_name_normalized: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    purchase_order_number: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="review_required",
        index=True,
    )
    exception_codes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    duplicate_of_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        index=True,
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    versions: Mapped[list["InvoiceVersion"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceVersion.version",
    )
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.created_at",
    )
    extraction: Mapped["InvoiceExtraction | None"] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        uselist=False,
    )
    match: Mapped["InvoiceMatch | None"] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        uselist=False,
    )
    export: Mapped["AccountingExport | None"] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        uselist=False,
    )


class InvoiceVersion(Base):
    __tablename__ = "invoice_versions"
    __table_args__ = (
        UniqueConstraint(
            "invoice_id",
            "version",
            name="uq_invoice_versions_invoice_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    invoice: Mapped[Invoice] = relationship(back_populates="versions")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    invoice: Mapped[Invoice] = relationship(back_populates="line_items")


class InvoiceFile(Base):
    __tablename__ = "invoice_files"
    __table_args__ = (
        UniqueConstraint("invoice_id", "file_id", name="uq_invoice_files_invoice_file"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class InvoiceExtraction(Base):
    __tablename__ = "invoice_extractions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    invoice: Mapped[Invoice] = relationship(back_populates="extraction")


class InvoiceMatch(Base):
    __tablename__ = "invoice_matches"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    vendor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    contract_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    transaction_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    application_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    purchase_request_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    invoice: Mapped[Invoice] = relationship(back_populates="match")


class AccountingMapping(Base):
    __tablename__ = "accounting_mappings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "scope_type",
            "scope_value",
            name="uq_accounting_mappings_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope_value: Mapped[str] = mapped_column(String(180), nullable=False)
    account_code: Mapped[str] = mapped_column(String(80), nullable=False)
    tax_code: Mapped[str] = mapped_column(String(80), nullable=False)
    cost_center: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    project: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AccountingExport(Base):
    __tablename__ = "accounting_exports"
    __table_args__ = (
        UniqueConstraint("invoice_id", "provider", name="uq_accounting_exports_invoice_provider"),
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_accounting_exports_org_idempotency",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(180))
    external_version: Mapped[int | None] = mapped_column(Integer)
    exported_invoice_version: Mapped[int | None] = mapped_column(Integer)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    diff_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_detail: Mapped[str | None] = mapped_column(String(500))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    invoice: Mapped[Invoice] = relationship(back_populates="export")
    sync_records: Mapped[list["AccountingSyncRecord"]] = relationship(
        back_populates="export",
        cascade="all, delete-orphan",
    )


class AccountingSyncRecord(Base):
    __tablename__ = "accounting_sync_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    export_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounting_exports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_version: Mapped[int] = mapped_column(Integer, nullable=False)
    external_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    export: Mapped[AccountingExport] = relationship(back_populates="sync_records")
