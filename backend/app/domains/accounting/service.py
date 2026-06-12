import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import quantize_money
from app.domains.applications.models import Application
from app.domains.applications.service import normalize_application_name
from app.domains.contracts.models import Contract
from app.domains.identity.models import User
from app.domains.organizations.service import OrganizationContext
from app.domains.procurement.models import PurchaseRequest
from app.domains.spend.models import SpendTransaction
from app.domains.vendors.models import Vendor
from app.domains.vendors.service import normalize_vendor_name

from .adapters import (
    AccountingProvider,
    BillPayload,
    InvoiceExtractionResult,
    InvoiceExtractor,
)
from .models import (
    AccountingExport,
    AccountingMapping,
    AccountingSyncRecord,
    Invoice,
    InvoiceExtraction,
    InvoiceLineItem,
    InvoiceMatch,
    InvoiceVersion,
)
from .schemas import (
    AccountingExportResponse,
    AccountingMappingListResponse,
    AccountingMappingRequest,
    AccountingMappingResponse,
    ConfirmInvoiceRequest,
    ExtractInvoiceRequest,
    ExtractionResponse,
    InvoiceBundleResponse,
    InvoiceLineItemInput,
    InvoiceLineItemResponse,
    InvoiceListResponse,
    InvoiceMatchResponse,
    InvoiceResponse,
    ResolvedAccountingMappingResponse,
    UpdateInvoiceRequest,
)


class InvoiceNotFound(Exception):
    pass


class InvoiceConflict(Exception):
    pass


class InvoiceNotReady(Exception):
    pass


class AccountingMappingMissing(Exception):
    pass


class AccountingExportNotFound(Exception):
    pass


def extraction_fields(result: InvoiceExtractionResult) -> dict[str, Any]:
    return {
        key: {
            "value": field.value,
            "confidence": str(field.confidence),
            "evidence": {
                "page": field.evidence.page,
                "line": field.evidence.line,
                "text": field.evidence.text,
            },
        }
        for key, field in result.fields.items()
    }


def invoice_snapshot(invoice: Invoice) -> dict[str, str]:
    return {
        "vendor_name": invoice.vendor_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "currency": invoice.currency,
        "subtotal": str(quantize_money(invoice.subtotal)),
        "tax": str(quantize_money(invoice.tax)),
        "total": str(quantize_money(invoice.total)),
        "purchase_order_number": invoice.purchase_order_number,
    }


def invoice_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        organization_id=invoice.organization_id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        subtotal=quantize_money(invoice.subtotal),
        tax=quantize_money(invoice.tax),
        total=quantize_money(invoice.total),
        purchase_order_number=invoice.purchase_order_number,
        status=invoice.status,
        exception_codes=json.loads(invoice.exception_codes_json),
        duplicate_of_id=invoice.duplicate_of_id,
        current_version=invoice.current_version,
        filename=invoice.filename,
        created_at=invoice.created_at,
    )


def line_response(item: InvoiceLineItem) -> InvoiceLineItemResponse:
    return InvoiceLineItemResponse(
        id=item.id,
        description=item.description,
        quantity=quantize_money(item.quantity),
        unit_price=quantize_money(item.unit_price),
        amount=quantize_money(item.amount),
        category=item.category,
    )


def extraction_response(item: InvoiceExtraction) -> ExtractionResponse:
    return ExtractionResponse(
        provider=item.provider,
        status=item.status,
        fields=json.loads(item.fields_json),
    )


def match_response(item: InvoiceMatch) -> InvoiceMatchResponse:
    return InvoiceMatchResponse(
        id=item.id,
        vendor_id=item.vendor_id,
        contract_id=item.contract_id,
        transaction_id=item.transaction_id,
        application_id=item.application_id,
        purchase_request_id=item.purchase_request_id,
        confidence=quantize_money(item.confidence),
        status=item.status,
        explanation=json.loads(item.explanation_json),
    )


def mapping_response(item: AccountingMapping) -> AccountingMappingResponse:
    return AccountingMappingResponse(
        id=item.id,
        scope_type=item.scope_type,
        scope_value=item.scope_value,
        account_code=item.account_code,
        tax_code=item.tax_code,
        cost_center=item.cost_center,
        department=item.department,
        project=item.project,
    )


def export_response(item: AccountingExport) -> AccountingExportResponse:
    return AccountingExportResponse(
        id=item.id,
        invoice_id=item.invoice_id,
        provider=item.provider,
        status=item.status,
        external_id=item.external_id,
        external_version=item.external_version,
        exported_invoice_version=item.exported_invoice_version,
        diff=json.loads(item.diff_json),
        attempts=item.attempts,
    )


class AccountingService:
    def __init__(
        self,
        session: AsyncSession,
        extractor: InvoiceExtractor,
        provider: AccountingProvider,
        provider_name: str = "fake",
    ) -> None:
        self.session = session
        self.extractor = extractor
        self.provider = provider
        self.provider_name = provider_name

    async def extract_invoice(
        self,
        context: OrganizationContext,
        user: User,
        body: ExtractInvoiceRequest,
        idempotency_key: str,
    ) -> InvoiceBundleResponse:
        existing = await self.session.scalar(
            select(Invoice).where(
                Invoice.organization_id == context.organization_id,
                Invoice.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return await self.bundle(context, existing.id)

        result = await self.extractor.extract(body.text)
        required = (
            "vendor",
            "invoice_number",
            "invoice_date",
            "due_date",
            "currency",
            "subtotal",
            "tax",
            "total",
        )
        missing = [key for key in required if key not in result.fields]
        if missing:
            raise InvoiceConflict(f"Missing extracted fields: {', '.join(missing)}")

        def value(key: str) -> str:
            return result.fields[key].value

        vendor_name = value("vendor").strip()
        vendor_normalized = normalize_vendor_name(vendor_name)
        invoice_number = value("invoice_number").strip()
        subtotal = quantize_money(Decimal(value("subtotal")))
        tax = quantize_money(Decimal(value("tax")))
        total = quantize_money(Decimal(value("total")))
        duplicate = await self._find_duplicate(
            context,
            vendor_normalized,
            invoice_number,
        )
        exceptions = self._exceptions(subtotal, tax, total)
        status = "duplicate" if duplicate is not None else "review_required"
        purchase_order_field = result.fields.get(
            "purchase_order_number"
        ) or result.fields.get("po_number")
        invoice = Invoice(
            organization_id=context.organization_id,
            created_by_user_id=user.id,
            source_type=body.source_type,
            external_id=body.external_id.strip(),
            idempotency_key=idempotency_key,
            filename=body.filename.strip(),
            vendor_name=vendor_name,
            vendor_name_normalized=vendor_normalized,
            invoice_number=invoice_number,
            invoice_date=date.fromisoformat(value("invoice_date")),
            due_date=date.fromisoformat(value("due_date")),
            currency=value("currency").upper(),
            subtotal=subtotal,
            tax=tax,
            total=total,
            purchase_order_number=(
                purchase_order_field.value if purchase_order_field else ""
            ),
            status=status,
            exception_codes_json=json.dumps(exceptions),
            duplicate_of_id=duplicate.id if duplicate is not None else None,
            current_version=1,
        )
        self.session.add(invoice)
        await self.session.flush()
        fields = extraction_fields(result)
        self.session.add(
            InvoiceVersion(
                organization_id=context.organization_id,
                invoice_id=invoice.id,
                version=1,
                fields_json=json.dumps(invoice_snapshot(invoice)),
            )
        )
        self.session.add(
            InvoiceExtraction(
                organization_id=context.organization_id,
                invoice_id=invoice.id,
                provider="fake_ocr",
                status="completed",
                fields_json=json.dumps(fields),
            )
        )
        for line in result.line_items:
            self.session.add(
                InvoiceLineItem(
                    organization_id=context.organization_id,
                    invoice_id=invoice.id,
                    version=1,
                    description=line.description,
                    quantity=quantize_money(line.quantity),
                    unit_price=quantize_money(line.unit_price),
                    amount=quantize_money(line.amount),
                    category="software",
                )
            )
        await self.session.commit()
        return await self.bundle(context, invoice.id)

    async def confirm_invoice(
        self,
        context: OrganizationContext,
        user: User,
        invoice_id: UUID,
        body: ConfirmInvoiceRequest,
    ) -> InvoiceBundleResponse:
        invoice = await self.get_invoice(context, invoice_id)
        duplicate = await self._find_duplicate(
            context,
            normalize_vendor_name(body.vendor_name),
            body.invoice_number,
            exclude_id=invoice.id,
        )
        invoice.vendor_name = body.vendor_name.strip()
        invoice.vendor_name_normalized = normalize_vendor_name(body.vendor_name)
        invoice.invoice_number = body.invoice_number.strip()
        invoice.invoice_date = body.invoice_date
        invoice.due_date = body.due_date
        invoice.currency = body.currency
        invoice.subtotal = quantize_money(body.subtotal)
        invoice.tax = quantize_money(body.tax)
        invoice.total = quantize_money(body.total)
        invoice.purchase_order_number = body.purchase_order_number.strip()
        invoice.current_version += 1
        exceptions = self._exceptions(invoice.subtotal, invoice.tax, invoice.total)
        invoice.exception_codes_json = json.dumps(exceptions)
        invoice.duplicate_of_id = duplicate.id if duplicate is not None else None
        if duplicate is not None:
            invoice.status = "duplicate"
        elif exceptions:
            invoice.status = "review_required"
        else:
            invoice.status = "ready"
        await self._add_version(
            context,
            user,
            invoice,
            body.line_items,
        )
        await self.session.commit()
        return await self.bundle(context, invoice.id)

    async def update_invoice(
        self,
        context: OrganizationContext,
        user: User,
        invoice_id: UUID,
        body: UpdateInvoiceRequest,
    ) -> InvoiceBundleResponse:
        invoice = await self.get_invoice(context, invoice_id)
        before = invoice_snapshot(invoice)
        if body.subtotal is not None:
            invoice.subtotal = quantize_money(body.subtotal)
        if body.tax is not None:
            invoice.tax = quantize_money(body.tax)
        if body.total is not None:
            invoice.total = quantize_money(body.total)
        exceptions = self._exceptions(invoice.subtotal, invoice.tax, invoice.total)
        if exceptions:
            raise InvoiceConflict("Invoice total is not balanced")
        invoice.current_version += 1
        current_lines = await self._current_lines(invoice)
        await self._add_version(
            context,
            user,
            invoice,
            [
                InvoiceLineItemInput(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    amount=item.amount,
                    category=item.category,
                )
                for item in current_lines
            ],
        )
        export = await self.session.scalar(
            select(AccountingExport).where(AccountingExport.invoice_id == invoice.id)
        )
        if export is not None and export.status == "synced":
            after = invoice_snapshot(invoice)
            diff = {
                key: {"external": before[key], "local": after[key]}
                for key in after
                if before.get(key) != after[key]
            }
            invoice.status = "out_of_sync"
            export.status = "out_of_sync"
            export.diff_json = json.dumps(diff)
        await self.session.commit()
        return await self.bundle(context, invoice.id)

    async def match_invoice(
        self,
        context: OrganizationContext,
        invoice_id: UUID,
    ) -> InvoiceBundleResponse:
        invoice = await self.get_invoice(context, invoice_id)
        vendor = await self.session.scalar(
            select(Vendor).where(
                Vendor.organization_id == context.organization_id,
                Vendor.normalized_name == invoice.vendor_name_normalized,
            )
        )
        contracts = (
            await self.session.scalars(
                select(Contract).where(
                    Contract.organization_id == context.organization_id
                )
            )
        ).all()
        contract = next(
            (
                item
                for item in contracts
                if normalize_vendor_name(item.vendor_name)
                == invoice.vendor_name_normalized
            ),
            None,
        )
        transactions = (
            await self.session.scalars(
                select(SpendTransaction).where(
                    SpendTransaction.organization_id == context.organization_id,
                    SpendTransaction.currency == invoice.currency,
                    SpendTransaction.amount == invoice.total,
                )
            )
        ).all()
        spend_transaction = next(
            (
                item
                for item in transactions
                if normalize_vendor_name(item.merchant_name)
                == invoice.vendor_name_normalized
                and abs((item.transaction_date - invoice.invoice_date).days) <= 30
            ),
            None,
        )
        application = None
        if contract is not None and contract.application_name:
            application = await self.session.scalar(
                select(Application).where(
                    Application.organization_id == context.organization_id,
                    Application.name_normalized
                    == normalize_application_name(contract.application_name),
                )
            )
        if application is None and spend_transaction is not None:
            application = await self.session.get(
                Application,
                spend_transaction.application_id,
            )
            if (
                application is not None
                and application.organization_id != context.organization_id
            ):
                application = None
        purchase = None
        if application is not None:
            purchase = await self.session.scalar(
                select(PurchaseRequest)
                .where(
                    PurchaseRequest.organization_id == context.organization_id,
                    PurchaseRequest.software_name.ilike(f"%{application.name}%"),
                )
                .order_by(PurchaseRequest.created_at.desc())
            )
        evidence = {
            "vendor": vendor is not None,
            "contract": contract is not None,
            "transaction": spend_transaction is not None,
            "application": application is not None,
            "purchase_request": purchase is not None,
        }
        required_matches = (
            vendor is not None,
            contract is not None,
            spend_transaction is not None,
            application is not None,
        )
        confidence = Decimal("1.0000") if all(required_matches) else Decimal("0.5000")
        invoice_match = await self.session.scalar(
            select(InvoiceMatch).where(InvoiceMatch.invoice_id == invoice.id)
        )
        if invoice_match is None:
            invoice_match = InvoiceMatch(
                organization_id=context.organization_id,
                invoice_id=invoice.id,
                confidence=confidence,
                status="matched" if all(required_matches) else "review_required",
                explanation_json=json.dumps(evidence),
            )
            self.session.add(invoice_match)
        invoice_match.vendor_id = vendor.id if vendor is not None else None
        invoice_match.contract_id = contract.id if contract is not None else None
        invoice_match.transaction_id = (
            spend_transaction.id if spend_transaction is not None else None
        )
        invoice_match.application_id = (
            application.id if application is not None else None
        )
        invoice_match.purchase_request_id = purchase.id if purchase is not None else None
        invoice_match.confidence = confidence
        invoice_match.status = (
            "matched" if all(required_matches) else "review_required"
        )
        invoice_match.explanation_json = json.dumps(evidence)
        await self.session.commit()
        return await self.bundle(context, invoice.id)

    async def upsert_mapping(
        self,
        context: OrganizationContext,
        body: AccountingMappingRequest,
    ) -> AccountingMappingResponse:
        item = await self.session.scalar(
            select(AccountingMapping).where(
                AccountingMapping.organization_id == context.organization_id,
                AccountingMapping.scope_type == body.scope_type,
                AccountingMapping.scope_value == body.scope_value,
            )
        )
        if item is None:
            item = AccountingMapping(
                organization_id=context.organization_id,
                scope_type=body.scope_type,
                scope_value=body.scope_value,
                account_code=body.account_code,
                tax_code=body.tax_code,
                cost_center=body.cost_center,
                department=body.department,
                project=body.project,
            )
            self.session.add(item)
        else:
            item.account_code = body.account_code
            item.tax_code = body.tax_code
            item.cost_center = body.cost_center
            item.department = body.department
            item.project = body.project
        await self.session.commit()
        return mapping_response(item)

    async def list_mappings(
        self,
        context: OrganizationContext,
    ) -> AccountingMappingListResponse:
        items = (
            await self.session.scalars(
                select(AccountingMapping)
                .where(AccountingMapping.organization_id == context.organization_id)
                .order_by(
                    AccountingMapping.scope_type.asc(),
                    AccountingMapping.created_at.asc(),
                )
            )
        ).all()
        return AccountingMappingListResponse(
            items=[mapping_response(item) for item in items]
        )

    async def resolve_mapping(
        self,
        context: OrganizationContext,
        invoice_id: UUID,
    ) -> ResolvedAccountingMappingResponse:
        invoice = await self.get_invoice(context, invoice_id)
        invoice_match = await self.session.scalar(
            select(InvoiceMatch).where(InvoiceMatch.invoice_id == invoice.id)
        )
        lines = await self._current_lines(invoice)
        category = lines[0].category if lines else "software"
        candidates = [
            (
                "application",
                str(invoice_match.application_id)
                if invoice_match is not None and invoice_match.application_id
                else "",
            ),
            (
                "vendor",
                str(invoice_match.vendor_id)
                if invoice_match is not None and invoice_match.vendor_id
                else "",
            ),
            ("category", category),
            ("default", "*"),
        ]
        for scope_type, scope_value in candidates:
            if not scope_value:
                continue
            mapping = await self.session.scalar(
                select(AccountingMapping).where(
                    AccountingMapping.organization_id == context.organization_id,
                    AccountingMapping.scope_type == scope_type,
                    AccountingMapping.scope_value == scope_value,
                )
            )
            if mapping is not None:
                return ResolvedAccountingMappingResponse(
                    mapping_id=mapping.id,
                    resolved_scope_type=mapping.scope_type,
                    account_code=mapping.account_code,
                    tax_code=mapping.tax_code,
                    cost_center=mapping.cost_center,
                    department=mapping.department,
                    project=mapping.project,
                )
        raise AccountingMappingMissing

    async def export_invoice(
        self,
        context: OrganizationContext,
        invoice_id: UUID,
        idempotency_key: str,
    ) -> InvoiceBundleResponse:
        invoice = await self.get_invoice(context, invoice_id)
        if invoice.status not in {"ready", "out_of_sync"}:
            raise InvoiceNotReady
        mapping = await self.resolve_mapping(context, invoice.id)
        export = await self.session.scalar(
            select(AccountingExport).where(
                AccountingExport.invoice_id == invoice.id,
                AccountingExport.provider == self.provider_name,
            )
        )
        if (
            export is not None
            and export.status == "synced"
            and export.exported_invoice_version == invoice.current_version
        ):
            return await self.bundle(context, invoice.id)
        if export is None:
            export = AccountingExport(
                organization_id=context.organization_id,
                invoice_id=invoice.id,
                provider=self.provider_name,
                idempotency_key=idempotency_key,
                status="syncing",
                attempts=1,
            )
            self.session.add(export)
        else:
            export.status = "syncing"
            export.attempts += 1
            export.error_detail = None
        await self.session.commit()
        payload = self._bill_payload(invoice, mapping)
        try:
            external = await self.provider.upsert_bill(
                payload,
                export.idempotency_key,
            )
        except Exception as exc:
            export.status = "failed"
            export.error_detail = str(exc)
            await self.session.commit()
            raise
        snapshot = invoice_snapshot(invoice)
        export.status = "synced"
        export.external_id = external.external_id
        export.external_version = external.external_version
        export.exported_invoice_version = invoice.current_version
        export.snapshot_json = json.dumps(snapshot)
        export.diff_json = "{}"
        invoice.status = "synced"
        payload_json = json.dumps(payload.__dict__, sort_keys=True)
        self.session.add(
            AccountingSyncRecord(
                organization_id=context.organization_id,
                export_id=export.id,
                invoice_version=invoice.current_version,
                external_version=external.external_version,
                payload_hash=hashlib.sha256(payload_json.encode()).hexdigest(),
                status="synced",
            )
        )
        await self.session.commit()
        return await self.bundle(context, invoice.id)

    async def retry_export(
        self,
        context: OrganizationContext,
        export_id: UUID,
    ) -> AccountingExportResponse:
        export = await self.session.get(AccountingExport, export_id)
        if export is None or export.organization_id != context.organization_id:
            raise AccountingExportNotFound
        await self.export_invoice(
            context,
            export.invoice_id,
            export.idempotency_key,
        )
        refreshed = await self.session.get(AccountingExport, export.id)
        if refreshed is None:
            raise AccountingExportNotFound
        return export_response(refreshed)

    async def list_invoices(
        self,
        context: OrganizationContext,
    ) -> InvoiceListResponse:
        invoices = (
            await self.session.scalars(
                select(Invoice)
                .where(Invoice.organization_id == context.organization_id)
                .order_by(Invoice.created_at.desc())
            )
        ).all()
        return InvoiceListResponse(
            items=[await self.bundle(context, item.id) for item in invoices]
        )

    async def get_invoice(
        self,
        context: OrganizationContext,
        invoice_id: UUID,
    ) -> Invoice:
        invoice = await self.session.get(Invoice, invoice_id)
        if invoice is None or invoice.organization_id != context.organization_id:
            raise InvoiceNotFound
        return invoice

    async def bundle(
        self,
        context: OrganizationContext,
        invoice_id: UUID,
    ) -> InvoiceBundleResponse:
        invoice = await self.get_invoice(context, invoice_id)
        lines = await self._current_lines(invoice)
        extraction = await self.session.scalar(
            select(InvoiceExtraction).where(
                InvoiceExtraction.invoice_id == invoice.id
            )
        )
        invoice_match = await self.session.scalar(
            select(InvoiceMatch).where(InvoiceMatch.invoice_id == invoice.id)
        )
        export = await self.session.scalar(
            select(AccountingExport).where(AccountingExport.invoice_id == invoice.id)
        )
        return InvoiceBundleResponse(
            invoice=invoice_response(invoice),
            line_items=[line_response(item) for item in lines],
            extraction=extraction_response(extraction) if extraction else None,
            match=match_response(invoice_match) if invoice_match else None,
            export=export_response(export) if export else None,
        )

    async def _add_version(
        self,
        context: OrganizationContext,
        user: User,
        invoice: Invoice,
        line_items: list[InvoiceLineItemInput],
    ) -> None:
        self.session.add(
            InvoiceVersion(
                organization_id=context.organization_id,
                invoice_id=invoice.id,
                version=invoice.current_version,
                fields_json=json.dumps(invoice_snapshot(invoice)),
                confirmed_by_user_id=user.id,
                confirmed_at=datetime.now(UTC),
            )
        )
        for item in line_items:
            self.session.add(
                InvoiceLineItem(
                    organization_id=context.organization_id,
                    invoice_id=invoice.id,
                    version=invoice.current_version,
                    description=item.description.strip(),
                    quantity=quantize_money(item.quantity),
                    unit_price=quantize_money(item.unit_price),
                    amount=quantize_money(item.amount),
                    category=item.category.strip(),
                )
            )
        await self.session.flush()

    async def _current_lines(self, invoice: Invoice) -> list[InvoiceLineItem]:
        return list(
            (
                await self.session.scalars(
                    select(InvoiceLineItem)
                    .where(
                        InvoiceLineItem.invoice_id == invoice.id,
                        InvoiceLineItem.version == invoice.current_version,
                    )
                    .order_by(InvoiceLineItem.created_at.asc())
                )
            ).all()
        )

    async def _find_duplicate(
        self,
        context: OrganizationContext,
        vendor_normalized: str,
        invoice_number: str,
        *,
        exclude_id: UUID | None = None,
    ) -> Invoice | None:
        statement = select(Invoice).where(
            Invoice.organization_id == context.organization_id,
            Invoice.vendor_name_normalized == vendor_normalized,
            Invoice.invoice_number == invoice_number,
        )
        if exclude_id is not None:
            statement = statement.where(Invoice.id != exclude_id)
        return cast(
            Invoice | None,
            await self.session.scalar(statement.order_by(Invoice.created_at.asc())),
        )

    @staticmethod
    def _exceptions(
        subtotal: Decimal,
        tax: Decimal,
        total: Decimal,
    ) -> list[str]:
        return (
            []
            if quantize_money(subtotal + tax) == quantize_money(total)
            else ["amount_imbalance"]
        )

    @staticmethod
    def _bill_payload(
        invoice: Invoice,
        mapping: ResolvedAccountingMappingResponse,
    ) -> BillPayload:
        return BillPayload(
            vendor_name=invoice.vendor_name,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date.isoformat(),
            due_date=invoice.due_date.isoformat(),
            currency=invoice.currency,
            total=str(quantize_money(invoice.total)),
            account_code=mapping.account_code,
            tax_code=mapping.tax_code,
            department=mapping.department,
            external_version=invoice.current_version,
        )
