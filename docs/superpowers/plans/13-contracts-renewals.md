# 合同、续订与谈判实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理合同文件与版本、AI 字段抽取、自动续订通知期、续订决策、谈判和新合同结果。

**Architecture:** 合同业务记录与不可变合同版本分离。上传文件触发异步抽取，但只有人工确认后才写入正式字段。Renewal 由合同条款计算，可人工覆盖且必须审计。

**Tech Stack:** FastAPI、PostgreSQL、S3、Redis Worker、AI Extraction Adapter、React、日历组件、Pytest

---

## Task 1: 合同与版本

- [ ] **Step 1: 写版本不可变测试**

```py
async def test_signed_contract_version_cannot_be_modified(contract_service, signed_version):
    with pytest.raises(ImmutableRecordError):
        await contract_service.update_version(signed_version.id, {"amount": "9000"})
```

- [ ] **Step 2: 创建模型**

```text
contracts
contract_versions
contract_parties
contract_applications
contract_files
```

合同状态：draft、active、expired、terminated、cancelled。版本状态：draft、under_review、signed、superseded。

- [ ] **Step 3: API**

```text
GET/POST /contracts
GET/PATCH /contracts/{id}
POST /contracts/{id}/versions
POST /contracts/{id}/versions/{version_id}/mark-signed
```

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/contracts/tests/test_contracts.py -q
git add backend/app/domains/contracts backend/migrations
git commit -m "feat: add immutable contract versions"
```

## Task 2: 合同 AI 抽取与确认

- [ ] **Step 1: 写非正式字段测试**

```py
async def test_extracted_fields_do_not_change_contract_before_confirmation(extraction_service, contract):
    extraction = await extraction_service.complete(contract.id, extracted_fields())
    assert extraction.status == "awaiting_review"
    assert contract.renewal_date is None
```

- [ ] **Step 2: 抽取字段**

```text
start_date
end_date
auto_renew
notice_period_days
billing_frequency
amount
currency
seat_count
price_increase_clause
governing_law
termination_terms
```

每字段保存 value、confidence、evidence page/coordinates。

- [ ] **Step 3: 确认 API**

```text
POST /contracts/{id}/extract
GET  /contracts/{id}/extractions/{extraction_id}
POST /contracts/{id}/extractions/{extraction_id}/confirm
```

确认请求逐字段提交接受值或修正值。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/contracts/tests/test_extraction.py -q
git add backend/app/domains/contracts
git commit -m "feat: add reviewed contract extraction"
```

## Task 3: 续订计算与提醒

- [ ] **Step 1: 写通知期测试**

```py
def test_auto_renew_decision_deadline_uses_notice_period():
    renewal = calculate_renewal(
        end_date=date(2027, 1, 31),
        auto_renew=True,
        notice_period_days=60,
    )
    assert renewal.decision_deadline == date(2026, 12, 2)
```

- [ ] **Step 2: 创建 Renewal**

字段：

```text
renewal_date
decision_deadline
owner_id
status
decision
current_amount
proposed_amount
source_contract_version_id
override_reason
```

- [ ] **Step 3: 提醒调度**

120/90/60/30/7 天提醒按组织设置；自动续订通知期临近时标记 urgent。

- [ ] **Step 4: 覆盖规则**

人工覆盖日期需要 `contracts.manage`、理由和旧/新值审计。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/contracts/tests/test_renewals.py -q
git add backend/app/domains/contracts
git commit -m "feat: add contract renewal scheduling"
```

## Task 4: 续订决策与审批

- [ ] **Step 1: 写决策测试**

```py
@pytest.mark.parametrize("decision", ["renew", "downgrade", "expand", "negotiate", "cancel"])
async def test_renewal_decisions_create_required_tasks(renewal_service, renewal, decision):
    result = await renewal_service.decide(renewal.id, decision, actor=OWNER)
    assert result.tasks
```

- [ ] **Step 2: 决策工作流**

根据金额变化和风险决定是否进入采购审批引擎。取消创建 CancellationCase；续订/变更创建合同草稿。

- [ ] **Step 3: 应用负责人建议**

负责人提交使用情况、业务价值和建议；最终决策人可查看但不能伪装成负责人意见。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/contracts/tests/test_renewal_decisions.py -q
git add backend/app/domains/contracts
git commit -m "feat: add governed renewal decisions"
```

## Task 5: 谈判

- [ ] **Step 1: 写报价版本测试**

```py
async def test_negotiation_quotes_preserve_history(negotiation_service, negotiation):
    await negotiation_service.add_quote(negotiation.id, amount=Decimal("12000"))
    await negotiation_service.add_quote(negotiation.id, amount=Decimal("10500"))
    assert [q.amount for q in await negotiation_service.quotes(negotiation.id)] == [
        Decimal("12000"), Decimal("10500")
    ]
```

- [ ] **Step 2: 创建模型**

```text
negotiations
negotiation_quotes
negotiation_tasks
```

记录目标、报价、联系人、阶段、截止日、结果和关联 SavingsOpportunity。

- [ ] **Step 3: 结果**

成功谈判生成 realized saving，待新合同和后续付款验证。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/contracts
git commit -m "feat: add renewal negotiation tracking"
```

## Task 6: 前端合同与续订

- [ ] **Step 1: 创建页面**

```text
/app/:org/contracts
/app/:org/contracts/:id
/app/:org/contracts/:id/extraction
/app/:org/renewals
/app/:org/renewals/calendar
/app/:org/renewals/:id
/app/:org/negotiations/:id
```

- [ ] **Step 2: 合同查看器**

文件预览与抽取字段并排显示，点击字段定位证据页；用户逐字段确认。

- [ ] **Step 3: 续订日历**

提供月历和列表；颜色只辅助状态，文本标签始终存在。

- [ ] **Step 4: E2E**

上传合同 -> 抽取 -> 修正字段 -> 生成续订 -> 收集负责人建议 -> 谈判 -> 上传新合同 -> 验证节省。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/contracts
git commit -m "feat: add contract and renewal workspace"
```

## 完成验收

- [ ] 已签版本不可修改。
- [ ] AI 抽取不直接改变正式字段。
- [ ] 日期计算覆盖自动续订通知期。
- [ ] 覆盖值有权限、理由和审计。
- [ ] 谈判报价保留历史。
- [ ] 续订决策连接采购、取消和节省领域。

