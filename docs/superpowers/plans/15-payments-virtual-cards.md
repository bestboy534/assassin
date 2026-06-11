# 支付适配器与虚拟卡实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过合规支付供应商 Adapter 实现供应商支付工具、虚拟卡、限额、冻结、失败处理和 Webhook 对账。

**Architecture:** 平台保存支付供应商资源 ID 和掩码元数据，不保存 PAN/CVV。所有创建和状态操作先记录本地 intent，再调用供应商；最终状态以供应商响应或验签 Webhook 为准。

**Tech Stack:** FastAPI、PostgreSQL、Redis Worker、支付 Provider SDK、Webhook、React、Pytest

---

## Task 1: Provider Adapter 与测试双

- [ ] **Step 1: 写契约测试**

```py
@pytest.mark.parametrize("provider", provider_contract_fixtures())
async def test_payment_provider_contract(provider):
    instrument = await provider.create_instrument(valid_request())
    assert instrument.external_id
    assert instrument.last4
    assert instrument.status == "active"
```

- [ ] **Step 2: 定义接口**

```py
class PaymentProvider(Protocol):
    async def create_instrument(self, request: CreateInstrument) -> ProviderInstrument: ...
    async def update_limits(self, external_id: str, limits: Limits) -> ProviderInstrument: ...
    async def freeze(self, external_id: str) -> ProviderInstrument: ...
    async def unfreeze(self, external_id: str) -> ProviderInstrument: ...
    async def close(self, external_id: str) -> ProviderInstrument: ...
    def verify_webhook(self, headers: Mapping[str, str], body: bytes) -> ProviderEvent: ...
```

- [ ] **Step 3: 创建 FakeProvider**

用于测试和本地演示，明确标识 `sandbox`，不能在生产配置中启用。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/payments/tests/test_provider_contract.py -q
git add backend/app/domains/payments
git commit -m "feat: define payment provider contract"
```

## Task 2: 支付请求与批准边界

- [ ] **Step 1: 写未批准阻止测试**

```py
async def test_unapproved_purchase_cannot_create_payment_instrument(payment_service, pending_request):
    with pytest.raises(PermissionDenied):
        await payment_service.create_for_purchase(pending_request.id)
```

- [ ] **Step 2: 创建模型**

```text
payment_requests
payment_instruments
payment_limits
payment_actions
payment_events
```

- [ ] **Step 3: 创建流程**

只有 approved procurement 或有权限的例外流程可创建 payment request。创建时保存幂等键和业务来源。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/payments/tests/test_payment_requests.py -q
git add backend/app/domains/payments backend/migrations
git commit -m "feat: govern payment instrument creation"
```

## Task 3: 虚拟卡与限额

- [ ] **Step 1: 写供应商确认测试**

```py
async def test_freeze_stays_pending_until_provider_confirms(payment_service, provider):
    provider.freeze_returns(status="pending")
    instrument = await payment_service.freeze(INSTRUMENT_ID)
    assert instrument.status == "freeze_pending"
```

- [ ] **Step 2: 状态**

```text
creating -> active | failed
active -> freeze_pending -> frozen
frozen -> unfreeze_pending -> active
active/frozen -> close_pending -> closed
```

- [ ] **Step 3: 限额**

单笔、日、月、总额、商户锁定、MCC 和地域限制。修改限额需要审计和可选审批。

- [ ] **Step 4: API**

```text
POST /payment-instruments
GET  /payment-instruments
GET  /payment-instruments/{id}
POST /payment-instruments/{id}/freeze
POST /payment-instruments/{id}/unfreeze
POST /payment-instruments/{id}/close
PUT  /payment-instruments/{id}/limits
```

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/payments/tests/test_instruments.py -q
git add backend/app/domains/payments
git commit -m "feat: add virtual card lifecycle"
```

## Task 4: Webhook 验签、防重放与状态同步

- [ ] **Step 1: 写重放测试**

```py
async def test_replayed_webhook_is_acknowledged_once(client, signed_webhook):
    first = await client.post("/api/v1/webhooks/payments/provider", **signed_webhook)
    second = await client.post("/api/v1/webhooks/payments/provider", **signed_webhook)
    assert first.status_code == second.status_code == 200
    assert await payment_event_count(signed_webhook.event_id) == 1
```

- [ ] **Step 2: 验签**

使用原始 body，验证签名、时间戳窗口、event ID 和 provider account。无效签名返回 400，不泄露细节。

- [ ] **Step 3: Inbox**

`provider + event_id` 唯一；业务状态更新和 inbox receipt 同事务。

- [ ] **Step 4: 异步处理**

HTTP 接口只验签并入队，2 秒内返回。永久失败进入 dead-letter 并告警。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/payments/tests/test_webhooks.py -q
git add backend/app/domains/payments
git commit -m "feat: process payment webhooks safely"
```

## Task 5: 支付交易与异常

- [ ] **Step 1: 写失败事件测试**

```py
async def test_declined_payment_notifies_owner_and_finance(event_handler, declined_event):
    await event_handler.handle(declined_event)
    assert await notification_exists("payment_declined", declined_event.owner_id)
    assert await notification_exists("payment_declined", declined_event.finance_admin_id)
```

- [ ] **Step 2: 映射事件**

授权、结算、撤销、退款、拒绝和争议映射到交易领域。事件按 provider transaction ID 幂等。

- [ ] **Step 3: 异常通知**

限额、余额、商户不符、地区限制和疑似欺诈使用不同错误码和可操作说明。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/payments backend/app/domains/spend
git commit -m "feat: reconcile payment events into spend"
```

## Task 6: 前端支付与卡管理

- [ ] **Step 1: 页面**

```text
/app/:org/payments
/app/:org/payments/requests/:id
/app/:org/cards
/app/:org/cards/:id
```

- [ ] **Step 2: 安全显示**

只展示品牌、last4、状态、限额和负责人。前端代码与网络响应都不能出现完整卡号或 CVV。

- [ ] **Step 3: 高风险操作**

冻结、关闭和限额提升需要确认；高额度变更要求 reauth token。

- [ ] **Step 4: E2E**

批准采购 -> 创建 sandbox 卡 -> 修改限额 -> 模拟拒付 Webhook -> 冻结 -> 供应商确认 -> UI 更新。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/payments
git commit -m "feat: add secure payment instrument workspace"
```

## 完成验收

- [ ] 未批准采购不能创建支付工具。
- [ ] 不保存或传输完整卡号/CVV。
- [ ] 最终状态以 provider 确认为准。
- [ ] Webhook 验签且防重放。
- [ ] 支付事件与交易幂等关联。
- [ ] 高风险操作要求权限、确认和审计。

