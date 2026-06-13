# 套餐、平台计费、权益与用量实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现试用、套餐、组织订阅、功能权益、用量计量、升级降级、付款失败恢复和客户账单门户。

**Architecture:** PlanDefinition 与 Entitlement 在平台数据库中管理，组织订阅由计费 Provider Webhook 驱动。业务接口通过 EntitlementService 执行限制，前端提示不能替代后端校验。

**Tech Stack:** FastAPI、PostgreSQL、计费 Provider Adapter、Webhook、Worker、React、Pytest

---

## Task 1: 套餐与权益模型

- [x] **Step 1: 写后端限制测试**

```py
async def test_application_limit_is_enforced_by_service(entitlement_service, starter_org):
    await create_applications(starter_org, count=starter_org.plan.application_limit)
    with pytest.raises(EntitlementExceeded):
        await create_application(starter_org, name="One more")
```

- [x] **Step 2: 创建模型**

```text
plans
plan_prices
plan_entitlements
organization_subscriptions
organization_entitlements
usage_counters
usage_events
billing_customers
billing_invoices
```

- [x] **Step 3: 权益类型**

```text
boolean feature
integer limit
metered usage
retention duration
support tier
```

- [x] **Step 4: EntitlementService**

```py
class EntitlementService:
    async def require_feature(self, context, feature: str) -> None: ...
    async def require_capacity(self, context, metric: str, increment: int = 1) -> None: ...
    async def record_usage(self, context, metric: str, amount: int, source_key: str) -> None: ...
```

- [x] **Step 5: Commit**

```powershell
python -m pytest app/domains/billing/tests/test_entitlements.py -q
git add backend/app/domains/billing backend/migrations
git commit -m "feat: add plan entitlements and limits"
```

## Task 2: 试用与组织订阅

- [x] **Step 1: 写试用到期测试**

```py
async def test_expired_trial_becomes_read_only_not_deleted(subscription_service, trial_org):
    await subscription_service.expire_trials(now=trial_org.trial_ends_at + timedelta(seconds=1))
    assert (await subscription_service.get(trial_org.id)).status == "trial_expired"
    assert await organization_data_exists(trial_org.id)
```

- [x] **Step 2: 状态**

```text
trialing
active
past_due
grace_period
suspended
cancel_at_period_end
cancelled
enterprise_contract
```

- [x] **Step 3: 试用规则**

默认试用期限、提醒、可选延长和到期只读。数据按保留策略保留，不立即删除。

- [x] **Step 4: Commit**

```powershell
python -m pytest app/domains/billing/tests/test_subscriptions.py -q
git add backend/app/domains/billing
git commit -m "feat: add organization subscription lifecycle"
```

## Task 3: 计费 Provider 与 Webhook

- [ ] **Step 1: 写事件顺序测试**

```py
async def test_out_of_order_webhook_does_not_revert_newer_subscription(billing_handler, events):
    await billing_handler.handle(events.subscription_updated_new)
    await billing_handler.handle(events.subscription_updated_old)
    assert (await subscription()).provider_version == events.subscription_updated_new.version
```

- [ ] **Step 2: Adapter**

```py
class BillingProvider(Protocol):
    async def create_customer(self, payload: CustomerPayload) -> ExternalRef: ...
    async def create_checkout(self, payload: CheckoutPayload) -> str: ...
    async def create_portal_session(self, customer_id: str, return_url: str) -> str: ...
    def verify_webhook(self, headers, body: bytes) -> BillingEvent: ...
```

- [ ] **Step 3: 事件**

客户、订阅、发票、付款成功/失败、退款和争议。事件 ID 幂等，provider version 防止旧事件覆盖。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/billing/tests/test_webhooks.py -q
git add backend/app/domains/billing
git commit -m "feat: synchronize subscription billing"
```

## Task 4: 升级、降级与取消

- [ ] **Step 1: 写降级影响测试**

```py
async def test_downgrade_preview_lists_over_limit_resources(subscription_service, pro_org):
    preview = await subscription_service.preview_change(pro_org.id, target_plan="starter")
    assert preview.over_limit["members"] == 8
    assert preview.over_limit["applications"] == 43
```

- [ ] **Step 2: 变更预览**

返回价格、生效时间、按比例费用、丢失功能和超限资源。降级不自动删除资源。

- [ ] **Step 3: 执行**

升级可立即生效；降级默认下个周期；取消默认周期末，可撤销。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/billing/tests/test_plan_changes.py -q
git add backend/app/domains/billing
git commit -m "feat: govern plan changes and cancellation"
```

## Task 5: 用量计量

- [ ] **Step 1: 写幂等计量测试**

```py
async def test_usage_source_key_prevents_double_count(usage_service):
    await usage_service.record("ai_pages", 10, source_key="job-1")
    await usage_service.record("ai_pages", 10, source_key="job-1")
    assert await current_usage("ai_pages") == 10
```

- [ ] **Step 2: 指标**

成员、应用、存储、AI 页数、集成连接、导出行数和 API 调用。

- [ ] **Step 3: 阈值**

80%、100% 发送通知；hard limit 拒绝新操作，soft limit 记录超额并告警。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/billing
git commit -m "feat: meter organization product usage"
```

## Task 6: 前端定价与账单设置

- [ ] **Step 1: 页面**

```text
/pricing
/app/:org/settings/billing
/app/:org/settings/billing/usage
/app/:org/settings/billing/invoices
```

- [ ] **Step 2: 账单页面**

套餐、状态、续费日期、用量、发票、付款失败、升级/降级预览和账单门户。

- [ ] **Step 3: 权益 UI**

受限功能展示套餐要求和升级入口；API 返回 entitlement error 时显示同一说明。

- [ ] **Step 4: E2E**

试用 -> 升级 sandbox -> Webhook active -> 达到用量阈值 -> 降级预览 -> 周期末降级 -> 取消撤销。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/billing frontend/src/marketing/pages/PricingPage.tsx
git commit -m "feat: add customer billing experience"
```

## 完成验收

- [ ] 权益由后端执行。
- [ ] 用量事件幂等。
- [ ] 旧 Webhook 不能覆盖新状态。
- [ ] 试用到期不删除数据。
- [ ] 降级前显示影响，不静默删除。
- [ ] 账单入口仅组织 owner/有权限角色可见。
