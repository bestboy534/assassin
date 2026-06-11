# 发票、OCR、匹配与会计自动化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现发票和收据导入、OCR/AI 字段抽取、重复检测、交易/合同/应用匹配、科目映射和会计系统导出。

**Architecture:** 文件通过隔离存储进入 Invoice Job。抽取结果与正式发票分离，字段确认后才能进入匹配和会计同步。同步采用 Adapter 和外部版本，修改已同步数据产生差异记录。

**Tech Stack:** FastAPI、PostgreSQL、S3、Worker、OCR Adapter、Accounting Adapter、React、Pytest

---

## Task 1: 发票模型与导入

- [ ] **Step 1: 写重复检测测试**

```py
async def test_same_vendor_invoice_number_is_flagged_duplicate(invoice_service, existing_invoice):
    candidate = await invoice_service.create(
        vendor_id=existing_invoice.vendor_id,
        invoice_number=existing_invoice.invoice_number,
        amount=existing_invoice.amount,
    )
    assert candidate.duplicate_of_id == existing_invoice.id
```

- [ ] **Step 2: 创建模型**

```text
invoices
invoice_versions
invoice_line_items
invoice_files
invoice_extractions
invoice_matches
accounting_mappings
accounting_exports
accounting_sync_records
```

- [ ] **Step 3: 输入渠道**

- 文件上传
- 邮件转发
- API
- 集成同步

每个来源有外部 ID 和幂等键。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/accounting/tests/test_invoice_import.py -q
git add backend/app/domains/accounting backend/migrations
git commit -m "feat: add invoice ingestion"
```

## Task 2: OCR 与字段级置信度

- [ ] **Step 1: 写字段证据测试**

```py
async def test_extraction_preserves_field_confidence_and_location(extractor, invoice_file):
    result = await extractor.extract(invoice_file)
    assert result.fields["total"].confidence >= Decimal("0")
    assert result.fields["total"].evidence.page == 1
```

- [ ] **Step 2: 定义 Adapter**

```py
class InvoiceExtractor(Protocol):
    async def extract(self, file: StoredFile) -> InvoiceExtractionResult: ...
```

- [ ] **Step 3: 字段**

供应商、发票号、日期、到期日、币种、小计、税额、总额、税号、采购单号、行项目。

- [ ] **Step 4: 确认**

低置信度或总额不平衡进入人工队列；确认前不产生正式会计记录。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/accounting/tests/test_extraction.py -q
git add backend/app/domains/accounting
git commit -m "feat: add reviewed invoice extraction"
```

## Task 3: 三方与四方匹配

- [ ] **Step 1: 写匹配测试**

```py
async def test_invoice_matches_contract_transaction_and_application(match_service, fixture):
    result = await match_service.match(fixture.invoice_id)
    assert result.contract_id == fixture.contract_id
    assert result.transaction_id == fixture.transaction_id
    assert result.application_id == fixture.application_id
```

- [ ] **Step 2: 匹配维度**

- 供应商
- 金额与币种
- 日期窗口
- 合同/采购单
- 支付交易
- 应用

- [ ] **Step 3: 差异规则**

金额、税额、币种、数量和供应商不一致生成 exception，不自动通过。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/accounting/tests/test_matching.py -q
git add backend/app/domains/accounting
git commit -m "feat: match invoices to business records"
```

## Task 4: 科目、税码与维度映射

- [ ] **Step 1: 写映射优先级测试**

```py
def test_mapping_priority_prefers_application_over_category(mapping_service):
    result = mapping_service.resolve(application=APP, category="software")
    assert result.account_code == APP.account_code
```

- [ ] **Step 2: 映射顺序**

应用 -> 供应商 -> 类别 -> 组织默认。每项可映射科目、税码、成本中心、部门和项目。

- [ ] **Step 3: 异常队列**

缺少必填映射时阻止同步，并显示缺少字段。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/accounting
git commit -m "feat: map invoices to accounting dimensions"
```

## Task 5: 会计 Adapter 与同步

- [ ] **Step 1: 写外部幂等测试**

```py
async def test_export_retry_updates_existing_external_bill(accounting_adapter, export_service, invoice):
    first = await export_service.export(invoice.id)
    second = await export_service.retry(first.id)
    assert first.external_id == second.external_id
```

- [ ] **Step 2: 定义 Adapter**

```py
class AccountingProvider(Protocol):
    async def upsert_vendor(self, vendor: VendorPayload) -> ExternalRef: ...
    async def upsert_bill(self, bill: BillPayload, idempotency_key: str) -> ExternalRef: ...
    async def attach_file(self, bill_id: str, file: StoredFile) -> None: ...
```

- [ ] **Step 3: 同步状态**

```text
queued -> syncing -> synced
queued/syncing -> failed
synced -> out_of_sync
```

已同步发票修改后标记 out_of_sync，并展示差异。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/accounting/tests/test_exports.py -q
git add backend/app/domains/accounting
git commit -m "feat: export invoices to accounting systems"
```

## Task 6: 前端发票与会计

- [ ] **Step 1: 页面**

```text
/app/:org/invoices
/app/:org/invoices/:id
/app/:org/invoices/review
/app/:org/accounting/mappings
/app/:org/accounting/exports
```

- [ ] **Step 2: 审核工作区**

文件预览、字段、置信度、匹配、异常和会计映射同屏；键盘支持下一条。

- [ ] **Step 3: 同步差异**

已同步数据修改时显示本地/外部差异和“更新外部”操作。

- [ ] **Step 4: E2E**

上传发票 -> OCR -> 修正税额 -> 匹配合同与交易 -> 补齐科目 -> 导出 -> 修改 -> 处理 out_of_sync。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/accounting
git commit -m "feat: add invoice and accounting workspace"
```

## 完成验收

- [ ] 文件扫描通过后才解析。
- [ ] 字段有置信度和证据位置。
- [ ] 重复发票和不平衡总额进入异常。
- [ ] 匹配结果可解释。
- [ ] 外部同步幂等。
- [ ] 已同步修改产生差异而非静默覆盖。

