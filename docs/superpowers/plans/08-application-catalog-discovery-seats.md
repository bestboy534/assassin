# 应用目录、软件发现与席位管理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立组织的软件事实目录，统一应用、供应商、负责人、来源、席位、用户和使用率，并支持发现、去重、合并与离职访问回收。

**Architecture:** `applications` 是组织级主实体，任何账单、SSO、浏览器或手工来源先形成 `application_sources`，经过匹配后关联主应用。合并使用可撤销事件而不是直接破坏历史数据。

**Tech Stack:** FastAPI、SQLAlchemy、PostgreSQL FTS/Trigram、React、TanStack Query、虚拟化表格、Pytest

---

## 核心模型

```text
applications
application_aliases
application_sources
application_owners
application_events
application_users
licenses
license_assignments
usage_snapshots
access_tasks
application_merge_operations
```

## Task 1: 应用主档 CRUD

- [ ] **Step 1: 写组织唯一性测试**

```py
async def test_application_name_is_unique_per_organization(app_service, org_context):
    await app_service.create(org_context, CreateApplication(name="Notion"))
    with pytest.raises(ConflictError):
        await app_service.create(org_context, CreateApplication(name=" notion "))
```

- [ ] **Step 2: 创建模型与迁移**

关键字段：

```py
name_normalized
category
status: active | trial | pending | deprecated | archived
vendor_id
business_owner_id
technical_owner_id
risk_level
approved
```

唯一约束包含 `organization_id, name_normalized`。

- [ ] **Step 3: 创建 API**

```text
GET    /organizations/{id}/applications
POST   /organizations/{id}/applications
GET    /organizations/{id}/applications/{application_id}
PATCH  /organizations/{id}/applications/{application_id}
POST   /organizations/{id}/applications/{application_id}/archive
```

列表支持 cursor、search、status、category、owner、department 和 approved 筛选。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/applications/tests/test_applications.py -q
git add backend/app/domains/applications backend/migrations
git commit -m "feat: add organization application catalog"
```

## Task 2: 来源记录与匹配

- [ ] **Step 1: 写来源幂等测试**

```py
async def test_same_external_source_upserts_without_duplicate(source_service, context):
    command = SourceCommand(provider="google", external_id="app-123", observed_name="Notion")
    first = await source_service.upsert(context, command)
    second = await source_service.upsert(context, command)
    assert first.id == second.id
```

- [ ] **Step 2: 实现来源**

来源类型：

```text
manual
csv
billing
sso
browser
accounting
card
hris
```

保存 `first_seen_at`、`last_seen_at`、`confidence`、`raw_reference` 和 `external_id`。

- [ ] **Step 3: 实现匹配服务**

匹配顺序：

1. 组织别名精确匹配
2. 外部供应商 ID
3. 规范化域名
4. 名称相似度
5. 人工待确认

低于阈值不自动创建正式关联。

- [ ] **Step 4: 创建确认接口**

```text
GET  /applications/discovery/candidates
POST /applications/discovery/{source_id}/confirm
POST /applications/discovery/{source_id}/create
POST /applications/discovery/{source_id}/ignore
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/applications
git commit -m "feat: add explainable software discovery"
```

## Task 3: 去重、合并与撤销

- [ ] **Step 1: 写合并完整性测试**

```py
async def test_merge_moves_references_and_can_be_undone(merge_service, duplicate_apps):
    operation = await merge_service.merge(
        duplicate_apps.context,
        source_id=duplicate_apps.secondary.id,
        target_id=duplicate_apps.primary.id,
    )
    assert await all_references_point_to(duplicate_apps.primary.id)
    await merge_service.undo(duplicate_apps.context, operation.id)
    assert await original_references_restored(operation.id)
```

- [ ] **Step 2: 创建预览**

`POST /applications/merge-preview` 返回：

```json
{
  "source": "...",
  "target": "...",
  "affected": {
    "transactions": 12,
    "contracts": 2,
    "users": 44,
    "sources": 3
  },
  "field_conflicts": []
}
```

- [ ] **Step 3: 实现事务合并**

保存 operation snapshot；移动外键、别名和来源；source 标为 `merged`。30 天内且无后续冲突时允许撤销。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/applications/tests/test_merge.py -q
git add backend/app/domains/applications
git commit -m "feat: add reversible application merging"
```

## Task 4: 席位、用户与使用率

- [ ] **Step 1: 写席位统计测试**

```py
async def test_license_utilization_counts_active_assignments(license_service, license_fixture):
    summary = await license_service.summary(license_fixture.application_id)
    assert summary.purchased == 100
    assert summary.assigned == 82
    assert summary.active_30d == 61
    assert summary.idle == 21
```

- [ ] **Step 2: 创建模型**

`licenses` 保存数量、单价、周期和来源；`license_assignments` 保存成员或外部用户；`usage_snapshots` 保存窗口、最后活动和来源。

- [ ] **Step 3: 使用率规则**

组织可配置 30/60/90 天无活动阈值。数据过期时只显示未知，不把未知视为闲置。

- [ ] **Step 4: 创建 API**

```text
GET  /applications/{id}/licenses
POST /applications/{id}/licenses
GET  /applications/{id}/users
POST /applications/{id}/assignments
POST /applications/{id}/assignments/{assignment_id}/reclaim
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/applications
git commit -m "feat: add application seats and usage"
```

## Task 5: 入职与离职访问任务

- [ ] **Step 1: 写离职任务测试**

```py
async def test_departure_creates_access_task_for_every_assigned_application(access_service, departing_member):
    tasks = await access_service.create_departure_tasks(departing_member)
    assert {task.application_id for task in tasks} == set(departing_member.application_ids)
    assert all(task.status == "pending" for task in tasks)
```

- [ ] **Step 2: 创建任务状态**

```text
pending -> in_progress -> completed
pending -> skipped
in_progress -> failed
```

保存处理方式 `manual | integration | not_required` 和证据。

- [ ] **Step 3: 实现入职模板**

`onboarding_templates` 按部门、职位、地点和雇佣类型定义建议应用与席位。创建成员或 HRIS 入职事件时生成 assignment tasks；需要付费席位或高风险应用时进入审批，不自动超额购买。

- [ ] **Step 4: 自动化边界**

默认只创建任务；只有组织启用且集成支持时才能异步撤销。外部撤销成功前不得显示 completed。

- [ ] **Step 5: 前端流程**

增加：

```text
/app/:org/access/onboarding
/app/:org/access/offboarding
/app/:org/settings/onboarding-templates
```

展示每个应用的申请、分配、撤销、跳过和失败状态。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/domains/applications
git commit -m "feat: add access lifecycle tasks"
```

## Task 6: 前端应用目录

- [ ] **Step 1: 写列表状态测试**

```tsx
test("application table shows stale source warning", async () => {
  server.use(applicationsWithStaleUsage());
  renderApplications();
  expect(await screen.findByText("使用数据已超过 7 天未同步")).toBeVisible();
});
```

- [ ] **Step 2: 创建页面**

```text
/app/:org/applications
/app/:org/applications/:id/overview
/app/:org/applications/:id/users
/app/:org/applications/:id/contracts
/app/:org/applications/:id/spend
/app/:org/applications/:id/activity
/app/:org/applications/discovery
/app/:org/applications/duplicates
```

- [ ] **Step 3: 表格能力**

服务端分页、列选择、保存视图、批量负责人、标签、归档和导出。超过 100 行使用虚拟化。

- [ ] **Step 4: E2E**

覆盖手工创建、发现确认、重复合并、席位回收和离职任务。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/applications
git commit -m "feat: add application catalog workspace"
```

## 完成验收

- [ ] 应用可从多来源发现并保留证据。
- [ ] 低置信度不自动污染主目录。
- [ ] 合并可预览、审计和撤销。
- [ ] 使用率展示数据新鲜度。
- [ ] 入职模板不会绕过付费席位或安全审批。
- [ ] 离职任务覆盖全部已知应用。
- [ ] 所有列表和详情遵守组织权限。
