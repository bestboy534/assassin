# 客户支持、状态页与平台管理后台实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现客户支持工单、诊断授权、公开状态事件和受控平台管理后台，使运营团队可以支持客户而不默认访问敏感数据。

**Architecture:** SupportTicket 属于组织；平台支持角色只能访问元数据。需要业务数据时创建有范围、有时限、客户批准的 SupportGrant。平台后台高风险操作必须二次确认和审计。

**Tech Stack:** FastAPI、PostgreSQL、S3、Worker、React、TanStack Query、Pytest

---

## Task 1: 支持工单

- [x] **Step 1: 写组织可见性测试**

```py
async def test_support_ticket_is_visible_only_to_organization_and_support_role(client, ticket, other_org_user):
    response = await client.get(f"/api/v1/support/tickets/{ticket.id}", user=other_org_user)
    assert response.status_code == 404
```

- [x] **Step 2: 创建模型**

```text
support_tickets
support_messages
support_attachments
support_sla_events
support_satisfaction
```

状态 new、open、waiting_customer、waiting_support、resolved、closed。

- [x] **Step 3: API**

```text
GET/POST /support/tickets
GET/PATCH /support/tickets/{id}
POST /support/tickets/{id}/messages
POST /support/tickets/{id}/resolve
POST /support/tickets/{id}/satisfaction
```

- [x] **Step 4: SLA**

按套餐计算首次响应和解决目标，暂停等待客户时间；违约前通知支持负责人。

- [x] **Step 5: Commit**

```powershell
python -m pytest app/domains/support/tests/test_tickets.py -q
git add backend/app/domains/support backend/migrations
git commit -m "feat: add customer support tickets"
```

## Task 2: 客户授权诊断

- [x] **Step 1: 写过期访问测试**

```py
async def test_expired_support_grant_blocks_diagnostic_access(support_access, expired_grant):
    with pytest.raises(PermissionDenied):
        await support_access.read_sync_diagnostics(expired_grant.id)
```

- [x] **Step 2: Grant 模型**

包含 organization、support_user、scope、reason、approved_by、expires_at、revoked_at。

- [x] **Step 3: 范围**

```text
configuration.read
sync_diagnostics.read
job_logs.read
business_records.read
```

默认只允许前三类；业务记录必须单独授权。

- [x] **Step 4: 审计**

每次使用 grant 记录访问资源和用途；客户可随时撤销。

- [x] **Step 5: Commit**

```powershell
python -m pytest app/domains/support/tests/test_support_grants.py -q
git add backend/app/domains/support
git commit -m "feat: add time bounded support access"
```

## Task 3: 系统状态页

- [ ] **Step 1: 写组件状态测试**

```py
async def test_active_incident_degrades_component_status(status_service, incident):
    await status_service.publish(incident)
    assert (await status_service.component(incident.component_id)).status == "degraded"
```

- [ ] **Step 2: 模型**

```text
status_components
status_incidents
status_incident_updates
status_subscribers
```

- [ ] **Step 3: 公开端点**

```text
GET /status
GET /status/incidents
POST /status/subscriptions
```

公开数据不泄露内部供应商或安全细节。

- [ ] **Step 4: 事件流程**

investigating -> identified -> monitoring -> resolved；每次更新带时间和公开说明。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/status frontend/src/marketing/pages/StatusPage.tsx
git commit -m "feat: publish product service status"
```

## Task 4: 平台组织与用户后台

- [ ] **Step 1: 写平台角色测试**

```py
async def test_organization_admin_cannot_access_platform_admin(client, organization_admin):
    response = await client.get("/api/v1/admin/organizations", user=organization_admin)
    assert response.status_code == 403
```

- [ ] **Step 2: 页面与 API**

```text
/admin/organizations
/admin/users
/admin/subscriptions
/admin/feature-flags
/admin/jobs
/admin/integrations
/admin/webhooks
/admin/email-deliveries
/admin/software-directory
/admin/cancellation-routes
```

- [ ] **Step 3: 高风险操作**

暂停组织、封禁用户、重放任务、修改套餐、启用功能开关需要理由、重新认证和审计。

- [ ] **Step 4: 禁止任意 SQL**

后台不提供 SQL 控制台。数据修复通过版本化 CLI 命令或显式 repair action。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/admin/tests -q
git add backend/app/domains/admin frontend/src/admin
git commit -m "feat: add controlled platform administration"
```

## Task 5: 全局目录与规则管理

- [ ] **Step 1: 写发布版本测试**

```py
async def test_cancel_route_change_requires_publish(rule_service, route):
    draft = await rule_service.update_draft(route.id, {"url": "https://vendor.example/cancel"})
    assert (await public_route(route.id)).url != draft.url
    await rule_service.publish(draft.id)
    assert (await public_route(route.id)).url == draft.url
```

- [ ] **Step 2: 管理对象**

- 软件目录
- 供应商目录
- 商户别名
- 取消路径
- 风险规则
- AI 提示版本

均使用草稿、审核、发布和回滚版本。

- [ ] **Step 3: Commit**

```powershell
git add backend/app/domains/admin frontend/src/admin/catalog
git commit -m "feat: manage versioned platform knowledge"
```

## Task 6: 支持与后台前端

- [ ] **Step 1: 客户页面**

```text
/app/:org/support
/app/:org/support/new
/app/:org/support/:ticketId
/app/:org/settings/support-access
```

- [ ] **Step 2: 平台后台**

使用独立 AdminLayout 和平台权限；显著显示当前环境，生产高风险按钮采用危险样式与二次确认。

- [ ] **Step 3: E2E**

客户开工单 -> 支持回复 -> 客户授权诊断 -> 支持查看同步错误 -> 授权过期；平台发布状态事件 -> 订阅者收到更新。

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/workspace/support frontend/src/admin
git commit -m "feat: add customer support and admin operations"
```

## 完成验收

- [ ] 客户工单组织隔离。
- [ ] 支持默认不能访问业务数据。
- [ ] 诊断授权有范围、原因、期限和审计。
- [ ] 状态页不泄露内部细节。
- [ ] 后台高风险操作需要重新认证。
- [ ] 无任意 SQL 或无审计修复入口。
