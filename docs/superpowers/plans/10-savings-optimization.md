# 节省机会与优化项目实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把审计、席位、合同和交易产生的信号转为可执行的节省机会，并区分预计、已实现和已验证节省。

**Architecture:** 各领域发布候选事件，SavingsService 以来源业务键去重并生成 opportunity。优化项目负责协作执行；SavingsResult 记录基线与验证证据。

**Tech Stack:** FastAPI、PostgreSQL、Outbox、React、TanStack Query、Pytest

---

## 金额定义

```text
estimated_savings：规则估算的未来 12 个月潜在节省
realized_savings：取消、降级、谈判或回收已执行后的预期节省
verified_savings：后续账单或合同证明实际生效的节省
cost_avoidance：避免新增支出，不与现金节省混算
```

## Task 1: 机会模型与去重

- [ ] **Step 1: 写去重测试**

```py
async def test_same_source_creates_one_open_opportunity(savings_service):
    event = IdleSeatDetected(application_id=APP_ID, license_id=LICENSE_ID, month="2026-06")
    first = await savings_service.ingest(event)
    second = await savings_service.ingest(event)
    assert first.id == second.id
```

- [ ] **Step 2: 创建模型**

```text
savings_opportunities
optimization_projects
optimization_tasks
savings_baselines
savings_results
```

机会唯一键：`organization_id + source_type + source_id + rule_version + period_key`。

- [ ] **Step 3: 状态机**

```text
new -> confirmed -> in_progress -> realized -> verified
new/confirmed -> ignored
confirmed/in_progress -> deferred
```

忽略和延期必须记录理由。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/savings/tests/test_opportunities.py -q
git add backend/app/domains/savings backend/migrations
git commit -m "feat: add deduplicated savings opportunities"
```

## Task 2: 基线计算

- [ ] **Step 1: 写计算测试**

```py
def test_annual_baseline_uses_remaining_term_for_fixed_contract():
    baseline = calculate_baseline(
        monthly_cost=Decimal("100"),
        effective_date=date(2026, 7, 1),
        contract_end=date(2026, 12, 31),
    )
    assert baseline.amount == Decimal("600.00")
```

- [ ] **Step 2: 实现分类计算**

- 取消：剩余合同期或 12 个月较小值。
- 降级：原方案与新方案差额。
- 谈判：旧报价与已签新报价差额。
- 席位回收：可实际减少购买数量时才计金额。
- 成本避免：被拒采购请求的预计金额，单独分类。

- [ ] **Step 3: 基线修改审批**

修改基线需要 `savings.manage_baseline`，记录旧值、新值、理由和审批人。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/savings/tests/test_calculations.py -q
git add backend/app/domains/savings
git commit -m "feat: add auditable savings baselines"
```

## Task 3: 优化项目

- [ ] **Step 1: 写项目创建测试**

```py
async def test_confirmed_opportunity_can_create_project(project_service, opportunity):
    project = await project_service.create_from_opportunity(opportunity.id, owner_id=OWNER_ID)
    assert project.target_amount == opportunity.estimated_amount
    assert project.tasks
```

- [ ] **Step 2: 实现项目 API**

```text
GET  /savings-opportunities
POST /savings-opportunities/{id}/confirm
POST /savings-opportunities/{id}/ignore
POST /savings-opportunities/{id}/defer
POST /savings-opportunities/{id}/projects
GET  /optimization-projects/{id}
PATCH /optimization-projects/{id}
POST /optimization-projects/{id}/tasks
```

- [ ] **Step 3: 协作**

项目支持负责人、截止日、任务、评论、附件、关注者和通知。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/savings/tests/test_projects.py -q
git add backend/app/domains/savings
git commit -m "feat: add savings optimization projects"
```

## Task 4: 实现与验证

- [ ] **Step 1: 写验证测试**

```py
async def test_verified_savings_requires_post_action_evidence(result_service, project):
    with pytest.raises(ValidationError):
        await result_service.verify(project.id, evidence_ids=[])
```

- [ ] **Step 2: 实现结果**

`realize` 保存 action、effective_date、新成本和证据。`verify` 需要后续交易、合同或财务确认之一。

- [ ] **Step 3: 防重复计算**

同一 transaction、contract_version 或 license reduction 只能属于一个 active SavingsResult。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/savings/tests/test_results.py -q
git add backend/app/domains/savings
git commit -m "feat: verify realized software savings"
```

## Task 5: 前端节省工作台

- [ ] **Step 1: 写漏斗测试**

```tsx
test("formal savings total uses verified results only", async () => {
  server.use(savingsFixture({ estimated: 1000, realized: 700, verified: 420 }));
  renderSavings();
  expect(await screen.findByText("¥420")).toBeVisible();
  expect(screen.getByText("已验证节省")).toBeVisible();
});
```

- [ ] **Step 2: 创建页面**

```text
/app/:org/savings
/app/:org/savings/opportunities/:id
/app/:org/savings/projects/:id
/app/:org/savings/results
```

- [ ] **Step 3: 页面内容**

机会表格、节省漏斗、按来源/部门分类、项目看板、证据时间线和验证队列。

- [ ] **Step 4: E2E**

从审计 finding 创建机会 -> 确认 -> 创建项目 -> 标记已执行 -> 关联后续交易 -> 验证。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/savings
git commit -m "feat: add savings execution workspace"
```

## 完成验收

- [ ] 同一来源不会重复生成开放机会。
- [ ] 每笔节省有明确基线和计算公式。
- [ ] 预计、实现、验证和成本避免分开。
- [ ] 修改基线需要权限和审计。
- [ ] 正式报表只计 verified。

