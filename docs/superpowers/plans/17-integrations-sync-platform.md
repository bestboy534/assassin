# 集成平台、OAuth 与同步任务实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一集成框架，安全管理 OAuth/密钥、增量游标、同步运行、错误和字段映射，并交付首批身份、协作和会计适配器。

**Architecture:** IntegrationDefinition 描述能力，IntegrationConnection 属于组织。凭证使用 KMS/秘密管理器加密。每次同步形成 SyncRun，Provider Adapter 返回标准化记录，领域服务决定 upsert 规则。

**Tech Stack:** FastAPI、PostgreSQL、Redis Worker、OAuth 2/OIDC、KMS Adapter、React、Pytest

---

## Task 1: 集成定义与连接

- [ ] **Step 1: 写连接隔离测试**

```py
async def test_connection_credentials_never_returned_by_api(client, connection):
    response = await client.get(f"/api/v1/integrations/{connection.id}")
    assert "access_token" not in response.text
    assert response.json()["status"] == "connected"
```

- [ ] **Step 2: 创建模型**

```text
integration_definitions
integration_connections
integration_credentials
integration_field_mappings
sync_runs
sync_errors
sync_cursors
```

- [ ] **Step 3: 定义能力**

```py
IntegrationCapability = Literal[
    "users.read", "groups.read", "applications.read",
    "transactions.read", "invoices.write", "messages.write",
    "contracts.read", "webhooks"
]
```

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/integrations/tests/test_connections.py -q
git add backend/app/domains/integrations backend/migrations
git commit -m "feat: add integration connections"
```

## Task 2: OAuth 与凭证加密

- [ ] **Step 1: 写 state 测试**

```py
async def test_oauth_callback_rejects_expired_state(client, expired_oauth_state):
    response = await client.get("/api/v1/integrations/oauth/callback?state=expired&code=x")
    assert response.status_code == 400
```

- [ ] **Step 2: KMS Adapter**

```py
class SecretCipher(Protocol):
    def encrypt(self, plaintext: bytes, context: dict[str, str]) -> EncryptedSecret: ...
    def decrypt(self, secret: EncryptedSecret, context: dict[str, str]) -> bytes: ...
```

加密 context 包含 organization_id 与 connection_id。

- [ ] **Step 3: OAuth 流程**

```text
POST /integrations/{definition_id}/oauth/start
GET  /integrations/oauth/callback
POST /integrations/{connection_id}/reconnect
DELETE /integrations/{connection_id}
```

验证 state、PKCE、redirect URI；token 不返回浏览器。

- [ ] **Step 4: 密钥连接**

API token/SFTP 等由后端接收并立即加密；响应只显示 last4 或标识。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/integrations/tests/test_oauth.py -q
git add backend/app/domains/integrations backend/app/infrastructure/secrets
git commit -m "feat: secure integration credentials"
```

## Task 3: 同步框架与增量游标

- [ ] **Step 1: 写游标提交测试**

```py
async def test_cursor_advances_only_after_success(sync_service, provider):
    provider.fail_on_page(2)
    run = await sync_service.run(CONNECTION_ID)
    assert run.status == "failed"
    assert await stored_cursor(CONNECTION_ID) == "page-1-original"
```

- [ ] **Step 2: Adapter**

```py
class IntegrationProvider(Protocol):
    async def test_connection(self, credentials: SecretHandle) -> ConnectionHealth: ...
    async def pull(self, resource: str, cursor: str | None) -> PullPage: ...
    async def push(self, resource: str, records: list[dict]) -> PushResult: ...
```

- [ ] **Step 3: SyncRun**

保存开始/结束、resource、cursor before/after、read/created/updated/skipped/failed 数量和错误摘要。

- [ ] **Step 4: 重试**

处理 429、5xx、网络错误和 token 刷新；指数退避，永久授权错误暂停连接。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/integrations/tests/test_sync_engine.py -q
git add backend/app/domains/integrations
git commit -m "feat: add incremental integration sync engine"
```

## Task 4: Google/Microsoft 身份同步

- [ ] **Step 1: 写停用用户测试**

```py
async def test_suspended_directory_user_marks_member_for_review(identity_sync, directory_user):
    directory_user.suspended = True
    await identity_sync.apply(directory_user)
    assert await departure_task_exists(directory_user.email)
```

- [ ] **Step 2: 同步字段**

用户、群组、状态、部门、经理和最后活动。目录不自动覆盖管理员手工锁定字段。

- [ ] **Step 3: 数据所有权**

每字段保存 source 与 locked 标志；冲突进入同步错误而非静默覆盖。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/integrations/tests/test_identity_sync.py -q
git add backend/app/domains/integrations/providers
git commit -m "feat: sync enterprise identity directories"
```

## Task 5: Slack/Teams 通知适配器

- [ ] **Step 1: 写投递测试**

```py
async def test_notification_delivery_records_external_message_id(collaboration_adapter):
    delivery = await collaboration_adapter.send(CHANNEL, approval_message())
    assert delivery.external_message_id
```

- [ ] **Step 2: 能力**

发送审批、续订、风险和同步失败通知；按钮链接回工作台，不在消息中执行高风险动作。

- [ ] **Step 3: 退订和渠道映射**

组织管理员映射默认频道，用户可设置私信偏好。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/integrations/providers backend/app/domains/notifications
git commit -m "feat: deliver collaboration notifications"
```

## Task 6: 集成中心前端

- [ ] **Step 1: 页面**

```text
/app/:org/integrations
/app/:org/integrations/catalog
/app/:org/integrations/:id
/app/:org/integrations/:id/syncs
/app/:org/integrations/:id/mappings
```

- [ ] **Step 2: 连接向导**

展示权限范围、数据流向、首次同步影响、OAuth/密钥步骤和测试连接。

- [ ] **Step 3: 同步诊断**

显示处理数量、游标、错误、重试、最后成功和下次计划时间。

- [ ] **Step 4: E2E**

连接 Fake Identity Provider -> 首次同步 -> 增量同步 -> 处理字段冲突 -> 暂停和删除连接。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/integrations
git commit -m "feat: add integration management center"
```

## Task 7: HRIS、文档、浏览器发现与通用连接器

- [ ] **Step 1: 写 HRIS 生命周期测试**

```py
async def test_hris_hire_and_departure_create_access_workflows(hris_sync, employee):
    await hris_sync.apply(employee.with_status("active"))
    assert await onboarding_tasks_exist(employee.email)
    await hris_sync.apply(employee.with_status("terminated"))
    assert await offboarding_tasks_exist(employee.email)
```

- [ ] **Step 2: 实现 HRIS Adapter**

首个实现使用 BambooHR-compatible 接口，标准化员工、部门、经理、入职日、离职日和状态。字段所有权规则防止覆盖管理员锁定值。

- [ ] **Step 3: 实现文档与签署 Adapter**

Google Drive、OneDrive 和 DocuSign-compatible Adapter 支持：

- 选择或导入合同文件
- 保存外部文档 ID 与版本
- 接收签署完成 Webhook
- 将已签版本关联合同

- [ ] **Step 4: 实现浏览器发现接收端**

浏览器扩展不上传页面正文、密码或 Cookie，只提交组织允许的应用域名、用户哈希、首次/最后访问时间和计数。API：

```text
POST /integrations/browser-discovery/events
```

事件签名、设备注册、批次幂等；管理员可配置域名排除和保留期。

- [ ] **Step 5: 通用连接器**

提供 API Token、入站 Webhook、CSV/SFTP 连接器。每种连接器使用同一 SyncRun、映射、重试和诊断模型。

- [ ] **Step 6: 运行并提交**

```powershell
python -m pytest app/domains/integrations/tests/test_hris.py app/domains/integrations/tests/test_documents.py app/domains/integrations/tests/test_browser_discovery.py -q
git add backend/app/domains/integrations frontend/src/workspace/integrations
git commit -m "feat: add HRIS document and discovery integrations"
```

## 完成验收

- [ ] 凭证不返回前端或进入日志。
- [ ] OAuth 使用 state 与 PKCE。
- [ ] 游标只在成功后推进。
- [ ] 429/5xx 有退避重试。
- [ ] 每次同步有完整数量和错误。
- [ ] HRIS 入离职连接访问生命周期任务。
- [ ] 文档签署事件可关联不可变合同版本。
- [ ] 浏览器发现不采集页面正文、Cookie 或密码。
- [ ] 通用连接器复用同步与诊断框架。
- [ ] 删除连接明确已同步数据保留策略。
