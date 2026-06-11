# 工作台外壳、总览、搜索、通知与待办实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可登录企业工作台的导航、权限路由、组织切换、总览指标、全局搜索、通知中心和我的待办。

**Architecture:** `/app/:organization_slug/*` 使用独立 WorkspaceLayout。后端提供聚合查询 API，前端以 TanStack Query 管理服务端状态。搜索与通知按组织和权限过滤。

**Tech Stack:** React Router、TanStack Query、Zustand、FastAPI、PostgreSQL、Redis、SSE/轮询、Vitest、Playwright

---

## Task 1: 工作台路由与布局

- [ ] **Step 1: 写权限路由测试**

```tsx
test("workspace route requires authentication and membership", async () => {
  authServer.use(anonymousUser());
  renderRoute("/app/acme/dashboard");
  expect(await screen.findByRole("heading", { name: "登录" })).toBeVisible();
});
```

- [ ] **Step 2: 创建路由树**

```tsx
{
  path: "/app/:organizationSlug",
  element: <AuthenticatedOrganizationRoute />,
  children: [{
    element: <WorkspaceLayout />,
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "search", element: <GlobalSearchPage /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "tasks", element: <MyTasksPage /> },
    ],
  }],
}
```

- [ ] **Step 3: 实现布局**

包含：

- 桌面侧栏
- 移动抽屉
- 组织切换器
- 全局搜索按钮
- 快速创建菜单
- 通知按钮
- 用户菜单
- 权限感知一级导航

- [ ] **Step 4: 运行**

```powershell
cd frontend
npm run test -- WorkspaceLayout
npm run typecheck
```

Expected: 匿名、无成员、暂停成员和正常成员场景通过。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/shell frontend/src/app/router.tsx
git commit -m "feat: add authenticated workspace shell"
```

## Task 2: 总览聚合 API

- [ ] **Step 1: 写指标口径测试**

```py
async def test_dashboard_excludes_ignored_and_deleted_records(dashboard_service, seeded_org):
    summary = await dashboard_service.summary(seeded_org.context)
    assert summary.application_count == 12
    assert summary.monthly_spend.amount == Decimal("4280.00")
    assert summary.savings_verified.amount == Decimal("620.00")
```

- [ ] **Step 2: 定义响应**

```py
class DashboardSummary(BaseModel):
    application_count: int
    monthly_spend: Money
    renewals_next_90_days: int
    pending_approvals: int
    savings_opportunity: Money
    savings_verified: Money
    high_risk_findings: int
    data_freshness: list[DataFreshness]
```

- [ ] **Step 3: 创建端点**

```text
GET /api/v1/organizations/{id}/dashboard/summary
GET /api/v1/organizations/{id}/dashboard/spend-trend
GET /api/v1/organizations/{id}/dashboard/action-items
```

所有数字返回 `source_url` 或下钻参数。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/dashboard/tests -q
git add backend/app/domains/dashboard
git commit -m "feat: add traceable dashboard metrics"
```

## Task 3: 总览页面与可配置小组件

- [ ] **Step 1: 写空状态测试**

```tsx
test("new organization sees import actions instead of zero charts", async () => {
  server.use(emptyDashboard());
  renderDashboard();
  expect(await screen.findByText("导入第一份账单")).toBeVisible();
  expect(screen.getByText("连接身份目录")).toBeVisible();
});
```

- [ ] **Step 2: 实现小组件**

```text
MetricCard
SpendTrendChart
RenewalList
ApprovalQueue
SavingsFunnel
RiskSummary
DataFreshnessPanel
```

每个小组件具备 loading、empty、stale、error、permission-denied 状态。

- [ ] **Step 3: 保存布局偏好**

布局偏好可存在用户配置 API；Zustand 只保存未提交拖拽状态。

- [ ] **Step 4: 响应式验证**

Playwright 视口：

```text
1440x1000
1024x768
390x844
```

要求无重叠、无横向滚动、指标可读。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/dashboard
git commit -m "feat: add actionable workspace dashboard"
```

## Task 4: 全局搜索

- [ ] **Step 1: 写权限过滤测试**

```py
async def test_search_does_not_return_contract_without_permission(search_service, limited_context):
    results = await search_service.search(limited_context, "Adobe")
    assert all(result.resource_type != "contract" for result in results)
```

- [ ] **Step 2: 定义搜索结果**

```py
class SearchResult(BaseModel):
    resource_type: Literal["application", "vendor", "contract", "purchase_request", "invoice", "member"]
    resource_id: UUID
    title: str
    subtitle: str | None
    url: str
    matched_fields: list[str]
```

- [ ] **Step 3: 创建端点**

```text
GET /api/v1/organizations/{id}/search?q=&types=&limit=
```

初期使用 PostgreSQL FTS + trigram；查询最少 2 字符，限制返回数量。

- [ ] **Step 4: 实现命令面板**

快捷键 `/` 或 `Ctrl+K`，支持键盘导航、最近访问和按类型分组。

- [ ] **Step 5: 运行并提交**

```powershell
python -m pytest app/domains/search/tests -q
cd ../frontend
npm run test -- GlobalSearch
git add backend/app/domains/search frontend/src/workspace/search
git commit -m "feat: add permission aware global search"
```

## Task 5: 通知中心

- [ ] **Step 1: 写通知幂等测试**

```py
async def test_duplicate_event_creates_one_notification(notification_service):
    await notification_service.handle(event_id="evt-1", recipient=USER_ID, template="approval_assigned")
    await notification_service.handle(event_id="evt-1", recipient=USER_ID, template="approval_assigned")
    assert await notification_count(USER_ID) == 1
```

- [ ] **Step 2: 创建模型与 API**

```text
notifications
notification_preferences
notification_deliveries
```

端点：

```text
GET  /notifications
POST /notifications/{id}/read
POST /notifications/read-all
GET  /notification-preferences
PUT  /notification-preferences
```

- [ ] **Step 3: 实时刷新**

使用 SSE `/notifications/stream`；断线自动退避重连，失败时回退 60 秒轮询。

- [ ] **Step 4: 安全通知规则**

账号安全、支付异常和组织权限变更不能完全关闭，只能选择渠道。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/notifications frontend/src/workspace/notifications
git commit -m "feat: add reliable notification center"
```

## Task 6: 我的待办

- [ ] **Step 1: 写聚合测试**

```py
async def test_my_tasks_merges_sources_and_orders_by_due_date(task_service, context):
    tasks = await task_service.list_for_actor(context)
    assert [task.kind for task in tasks[:3]] == ["approval", "renewal", "risk_review"]
```

- [ ] **Step 2: 定义统一 TaskProjection**

```py
class TaskProjection(BaseModel):
    id: str
    kind: str
    title: str
    due_at: datetime | None
    priority: Literal["low", "normal", "high", "urgent"]
    resource_url: str
    available_actions: list[str]
```

- [ ] **Step 3: 创建页面**

支持按类型、优先级、到期状态筛选；任务操作跳转资源详情，不在聚合页复制复杂业务动作。

- [ ] **Step 4: E2E**

验证审批任务生成后出现在“我的待办”，处理后立即消失并保留通知。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/tasks frontend/src/workspace/tasks
git commit -m "feat: add unified personal task queue"
```

## 完成验收

- [ ] 匿名用户和非成员不能进入工作台。
- [ ] 导航根据权限显示。
- [ ] 总览指标可下钻并显示数据新鲜度。
- [ ] 新组织不展示误导性的零值图表。
- [ ] 搜索严格遵守资源权限。
- [ ] 通知幂等且支持重连。
- [ ] 待办可聚合后续领域任务。

