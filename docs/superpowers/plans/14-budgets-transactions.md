# 预算、交易、多币种与月结实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立预算版本、交易导入与归类、多币种换算、匹配、异常规则和会计期间锁定。

**Architecture:** 交易保留原始金额和不可变来源标识，分类与拆分另表记录。预算以财年、期间和组织维度分配。换算使用带来源和日期的 ExchangeRate，不覆盖原始币种。

**Tech Stack:** FastAPI、PostgreSQL Numeric、Worker、React、TanStack Query、Pytest

---

## Task 1: Money 与汇率基础

- [ ] **Step 1: 写精度测试**

```py
def test_money_never_uses_binary_float():
    money = Money(amount=Decimal("0.10") + Decimal("0.20"), currency="USD")
    assert money.amount == Decimal("0.30")
```

- [ ] **Step 2: 创建共享类型**

```py
class Money(BaseModel):
    amount: Decimal
    currency: str = Field(pattern=r"^[A-Z]{3}$")
```

数据库使用 `Numeric(19, 4)`，汇率使用 `Numeric(20, 10)`。

- [ ] **Step 3: 汇率模型**

`exchange_rates(base_currency, quote_currency, rate_date, rate, source)` 唯一。换算记录使用的 rate ID。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/core/tests/test_money.py -q
git add backend/app/core backend/migrations
git commit -m "feat: add precise money and exchange rates"
```

## Task 2: 预算与版本

- [ ] **Step 1: 写预算计算测试**

```py
async def test_budget_summary_separates_actual_committed_and_forecast(budget_service, budget):
    summary = await budget_service.summary(budget.id)
    assert summary.actual == Decimal("4200")
    assert summary.committed == Decimal("1800")
    assert summary.forecast == Decimal("900")
    assert summary.remaining == Decimal("3100")
```

- [ ] **Step 2: 创建模型**

```text
budgets
budget_versions
budget_periods
budget_allocations
budget_commitments
```

维度支持部门、成本中心、法人、项目和类别。

- [ ] **Step 3: 状态**

```text
draft -> active -> superseded
active -> closed
```

同一预算期间只能有一个 active version。

- [ ] **Step 4: API**

```text
GET/POST /budgets
GET/PATCH /budgets/{id}
POST /budgets/{id}/versions
POST /budgets/{id}/versions/{version_id}/activate
GET /budgets/{id}/summary
```

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/spend/tests/test_budgets.py -q
git add backend/app/domains/spend
git commit -m "feat: add versioned software budgets"
```

## Task 3: 交易导入与幂等

- [ ] **Step 1: 写重复导入测试**

```py
async def test_reimport_same_external_transaction_does_not_duplicate(import_service):
    await import_service.import_rows("stripe", [ROW])
    await import_service.import_rows("stripe", [ROW])
    assert await transaction_count(external_id=ROW.external_id) == 1
```

- [ ] **Step 2: 创建模型**

```text
transaction_imports
transactions
transaction_splits
transaction_classifications
```

交易唯一键：`organization_id + source_provider + source_account_id + external_id`。

- [ ] **Step 3: 导入预览**

CSV 流程：

1. 上传
2. 字段映射
3. 解析预览
4. 错误下载
5. 确认导入

确认前不写正式交易。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/spend/tests/test_transaction_import.py -q
git add backend/app/domains/spend
git commit -m "feat: add idempotent transaction imports"
```

## Task 4: 匹配、分类与拆分

- [ ] **Step 1: 写低置信度测试**

```py
async def test_low_confidence_match_remains_unassigned(matching_service, transaction):
    result = await matching_service.match(transaction)
    assert result.confidence < Decimal("0.70")
    assert transaction.application_id is None
```

- [ ] **Step 2: 匹配顺序**

1. 支付工具绑定供应商
2. 外部供应商 ID
3. 组织商户别名
4. 交易描述规则
5. 模糊匹配
6. 人工队列

- [ ] **Step 3: 拆分规则**

拆分总额必须严格等于交易原始金额；每个 split 具有部门、成本中心、项目、应用和税务信息。

- [ ] **Step 4: API**

```text
GET   /transactions
PATCH /transactions/{id}
POST  /transactions/{id}/splits
POST  /transactions/bulk-classify
```

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/spend/tests/test_matching.py app/domains/spend/tests/test_splits.py -q
git add backend/app/domains/spend
git commit -m "feat: classify and split software transactions"
```

## Task 5: 异常规则

- [ ] **Step 1: 写异常测试**

```py
@pytest.mark.parametrize("fixture,code", [
    ("duplicate_charge", "duplicate_charge"),
    ("price_spike", "price_increase"),
    ("unapproved_vendor", "unapproved_vendor"),
    ("over_budget", "budget_exceeded"),
])
async def test_transaction_anomalies(anomaly_engine, fixture, code):
    assert code in await anomaly_engine.evaluate(load_transaction_fixture(fixture))
```

- [ ] **Step 2: 证据**

每个异常保存基线、比较窗口、阈值、规则版本和相关交易 ID。

- [ ] **Step 3: 事件**

异常发布到通知与 savings，但使用来源业务键避免重复机会。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/spend
git commit -m "feat: detect transaction and budget anomalies"
```

## Task 6: 月结锁定

- [ ] **Step 1: 写锁定测试**

```py
async def test_locked_period_rejects_transaction_edit(spend_service, locked_period, transaction):
    with pytest.raises(PeriodLocked):
        await spend_service.update_transaction(transaction.id, category="software")
```

- [ ] **Step 2: 创建期间**

`accounting_periods` 状态 open、closing、locked。锁定前检查未分类、未匹配和同步失败。

- [ ] **Step 3: 重开**

需要 `spend.reopen_period`、重新认证、理由和审计。重开不删除原锁定记录。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/spend/tests/test_period_close.py -q
git add backend/app/domains/spend
git commit -m "feat: add controlled accounting period close"
```

## Task 7: 前端预算与交易页面

- [ ] **Step 1: 页面**

```text
/app/:org/spend/overview
/app/:org/spend/transactions
/app/:org/spend/imports/:id
/app/:org/budgets
/app/:org/budgets/:id
/app/:org/spend/close
```

- [ ] **Step 2: 交易表格**

服务端分页、批量分类、拆分编辑、匹配置信度、异常标签和导入来源。

- [ ] **Step 3: 预算视图**

实际、承诺、预测、剩余分开；支持下钻，不把未换算金额混入总计。

- [ ] **Step 4: E2E**

导入 CSV -> 修正低置信度匹配 -> 拆分交易 -> 触发预算异常 -> 锁定期间 -> 验证编辑被阻止。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/spend
git commit -m "feat: add budget and transaction workspace"
```

## 完成验收

- [ ] 金额与汇率无 float。
- [ ] 重复导入幂等。
- [ ] 低置信度不自动归类。
- [ ] 拆分总额严格平衡。
- [ ] 异常有基线和规则版本。
- [ ] 锁定期间不可静默修改。

