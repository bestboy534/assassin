# 采购申请与审批引擎实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现动态采购申请、自动查重、预算预检、版本化审批流程、多角色审批、补充资料和履约。

**Architecture:** WorkflowDefinition 可编辑，提交申请时冻结为 WorkflowVersion。ApprovalTask 由状态机驱动；每个决定带幂等键和审计记录。审批完成发布事件给合同、支付和应用领域。

**Tech Stack:** FastAPI、PostgreSQL、Outbox、React Hook Form、Zod、TanStack Query、Pytest

---

## 状态机

```text
purchase_request:
draft -> submitted -> triage -> in_review -> approved | rejected | withdrawn
approved -> fulfilled -> closed
in_review -> changes_requested -> submitted

approval_task:
pending -> approved | rejected | changes_requested | skipped | cancelled
```

## Task 1: 动态申请表单

- [ ] **Step 1: 写 Schema 验证测试**

```py
def test_security_fields_required_for_sensitive_data(form_schema):
    payload = valid_request() | {"handles_sensitive_data": True, "data_categories": []}
    errors = form_schema.validate(payload)
    assert "data_categories" in errors
```

- [ ] **Step 2: 创建模型**

```text
request_form_definitions
request_form_versions
purchase_requests
purchase_request_answers
purchase_request_items
```

表单字段支持 text、textarea、number、money、select、multi_select、boolean、date、file、member、application。

- [ ] **Step 3: 创建 API**

```text
GET  /purchase-request-forms/active
POST /purchase-requests
PATCH /purchase-requests/{id}
POST /purchase-requests/{id}/submit
POST /purchase-requests/{id}/withdraw
```

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/procurement/tests/test_forms.py -q
git add backend/app/domains/procurement backend/migrations
git commit -m "feat: add versioned procurement request forms"
```

## Task 2: 查重与预检

- [ ] **Step 1: 写推荐测试**

```py
async def test_submit_returns_existing_application_suggestion(procurement_service, notion_app):
    result = await procurement_service.preflight(request_for("Notion"))
    assert result.duplicate_candidates[0].application_id == notion_app.id
```

- [ ] **Step 2: 实现 Preflight**

返回：

```json
{
  "duplicate_candidates": [],
  "budget_check": {"status": "within_budget", "remaining": "12000.00"},
  "vendor_status": "existing",
  "required_reviews": ["finance", "security"]
}
```

- [ ] **Step 3: 提交确认**

若有高置信度重复应用，申请人必须选择“使用现有应用”或填写继续采购理由。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/procurement/tests/test_preflight.py -q
git add backend/app/domains/procurement
git commit -m "feat: add procurement preflight checks"
```

## Task 3: 版本化工作流定义

- [ ] **Step 1: 写版本冻结测试**

```py
async def test_submitted_request_keeps_original_workflow_version(workflow_service, request):
    await workflow_service.submit(request.id)
    original = request.workflow_version_id
    await workflow_service.publish_new_version(request.organization_id, changed_definition())
    assert (await reload(request)).workflow_version_id == original
```

- [ ] **Step 2: 工作流模型**

```text
workflow_definitions
workflow_versions
workflow_nodes
workflow_edges
```

节点支持 approval、condition、parallel_group、notification、automatic_check。

- [ ] **Step 3: 条件表达式**

使用结构化 DSL，不执行任意代码：

```json
{"all": [
  {"field": "amount", "op": "gte", "value": 10000},
  {"field": "handles_sensitive_data", "op": "eq", "value": true}
]}
```

- [ ] **Step 4: 验证图**

发布前检测无入口、环路、不可达节点和缺少结束节点。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/procurement/tests/test_workflows.py -q
git add backend/app/domains/procurement
git commit -m "feat: add versioned procurement workflows"
```

## Task 4: 审批任务与决定

- [ ] **Step 1: 写幂等决定测试**

```py
async def test_duplicate_approval_decision_is_idempotent(client, approval_task):
    headers = {"Idempotency-Key": "approve-task-1"}
    first = await client.post(f"/api/v1/approval-tasks/{approval_task.id}/approve", headers=headers)
    second = await client.post(f"/api/v1/approval-tasks/{approval_task.id}/approve", headers=headers)
    assert first.status_code == second.status_code == 200
    assert await decision_count(approval_task.id) == 1
```

- [ ] **Step 2: 实现审批**

创建 `approval_tasks`、`approval_decisions` 和 `approval_delegations`；决定记录不可变，任务保存当前状态和版本。

```text
GET  /approval-tasks
POST /approval-tasks/{id}/approve
POST /approval-tasks/{id}/reject
POST /approval-tasks/{id}/request-changes
POST /approval-tasks/{id}/delegate
```

批准/拒绝必须带备注；委托需要权限和截止日期。

- [ ] **Step 3: 并行语义**

支持：

- all：全部批准
- any：任一批准
- threshold：达到 N 个

拒绝策略由流程节点明确配置。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/procurement/tests/test_approvals.py -q
git add backend/app/domains/procurement
git commit -m "feat: add auditable approval decisions"
```

## Task 5: 评论、附件与通知

- [ ] **Step 1: 写可见性测试**

内部安全审查评论可限制为安全组；普通评论对申请参与者可见。

- [ ] **Step 2: 实现评论**

```text
GET  /purchase-requests/{id}/comments
POST /purchase-requests/{id}/comments
```

支持提及与附件，编辑保留修订记录，不允许删除审批决定。

- [ ] **Step 3: 通知事件**

发布：

```text
procurement.submitted
approval.assigned
approval.overdue
procurement.changes_requested
procurement.approved
procurement.rejected
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/procurement
git commit -m "feat: add procurement collaboration events"
```

## Task 6: 履约与下游实体

- [ ] **Step 1: 写履约幂等测试**

```py
async def test_fulfillment_creates_one_application_and_contract_draft(fulfillment_service, approved_request):
    await fulfillment_service.fulfill(approved_request.id)
    await fulfillment_service.fulfill(approved_request.id)
    assert await linked_application_count(approved_request.id) == 1
```

- [ ] **Step 2: 实现履约**

批准后根据配置：

- 创建或关联供应商
- 创建应用草稿
- 创建合同草稿
- 创建支付请求
- 创建席位分配任务

- [ ] **Step 3: Commit**

```powershell
python -m pytest app/domains/procurement/tests/test_fulfillment.py -q
git add backend/app/domains/procurement
git commit -m "feat: fulfill approved software purchases"
```

## Task 7: 前端采购体验

- [ ] **Step 1: 创建页面**

```text
/app/:org/procurement
/app/:org/procurement/new
/app/:org/procurement/:id
/app/:org/approvals
/app/:org/settings/procurement/forms
/app/:org/settings/procurement/workflows
```

- [ ] **Step 2: 动态表单渲染**

根据后端 schema 渲染，前后端共享字段语义；服务端错误映射回字段。

- [ ] **Step 3: 流程编辑器**

第一版使用有序节点与条件配置表，不实现任意拖拽画布；发布前显示模拟路径。

- [ ] **Step 4: E2E**

提交敏感数据采购 -> 财务与安全并行审批 -> 请求补充 -> 重新提交 -> 全部批准 -> 创建应用。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/procurement
git commit -m "feat: add end to end procurement workspace"
```

## 完成验收

- [ ] 表单和工作流均有版本。
- [ ] 提交后历史不受新版本影响。
- [ ] 重复应用需要明确处理。
- [ ] 审批动作幂等并有理由。
- [ ] 并行节点语义有测试。
- [ ] 履约不会重复创建下游实体。
