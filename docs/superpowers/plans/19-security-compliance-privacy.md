# 安全、合规、审计与隐私实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立不可变审计、数据保留、数据主体请求、合规证据库、API 密钥、Webhook 密钥和安全事件流程。

**Architecture:** AuditLog 采用追加写和数据库权限约束。保留与删除由策略任务执行。敏感操作发出结构化审计事件。API 密钥只存哈希，Webhook secret 加密存储。

**Tech Stack:** FastAPI、PostgreSQL、Worker、KMS、S3、React、Pytest、安全扫描

---

## Task 1: 不可变审计日志

- [x] **Step 1: 写不可变测试**

```py
async def test_audit_log_cannot_be_updated_or_deleted(session, audit_log):
    with pytest.raises(DatabaseError):
        await session.execute(update(AuditLog).where(AuditLog.id == audit_log.id).values(action="changed"))
    with pytest.raises(DatabaseError):
        await session.delete(audit_log)
```

- [x] **Step 2: 模型**

```text
id, organization_id, actor_type, actor_id, action,
resource_type, resource_id, ip_address, user_agent_hash,
request_id, before_json, after_json, metadata_json, created_at
```

敏感值在写入前通过字段策略脱敏。

- [x] **Step 3: 数据库保护**

应用数据库角色仅允许 INSERT/SELECT；禁止 UPDATE/DELETE。必要清理由单独受控保留任务和专用角色执行。

- [x] **Step 4: 查询 API**

```text
GET /audit-logs
GET /audit-logs/{id}
POST /audit-logs/export
```

需要 `audit.read`，导出额外审计。

- [x] **Step 5: Commit**

```powershell
python -m pytest app/domains/compliance/tests/test_audit_logs.py -q
git add backend/app/domains/compliance backend/migrations
git commit -m "feat: add immutable security audit logs"
```

## Task 2: 数据保留与删除

- [x] **Step 1: 写保留例外测试**

```py
async def test_legal_hold_prevents_file_deletion(retention_service, held_file):
    result = await retention_service.delete_expired()
    assert held_file.id in result.skipped_legal_hold
```

- [x] **Step 2: 策略模型**

```text
retention_policies
legal_holds
deletion_jobs
deletion_job_items
```

策略按数据类型设置保留期，原始账单默认短于结构化结果。

- [x] **Step 3: 删除流程**

预览影响 -> 重新认证 -> 排队 -> 删除数据库/对象/派生文件 -> 生成结果与例外清单。

- [x] **Step 4: Commit**

```powershell
python -m pytest app/domains/compliance/tests/test_retention.py -q
git add backend/app/domains/compliance
git commit -m "feat: enforce data retention and deletion"
```

## Task 3: 数据主体请求

- [x] **Step 1: 写身份验证测试**

```py
async def test_dsr_export_requires_verified_identity(client, unverified_user):
    response = await client.post("/api/v1/privacy/requests", json={"type": "access"})
    assert response.status_code == 403
```

- [x] **Step 2: 类型**

access、correction、deletion、portability。请求保存法定截止日、验证、范围、状态和处理记录。

- [x] **Step 3: 导出**

生成机器可读 JSON + 人类可读说明；只包含请求人有权获取的数据。

- [x] **Step 4: 删除**

考虑组织合法业务记录、审计和法律保留，不能直接删除需要保留的财务记录；结果列出匿名化、删除和保留项。

- [x] **Step 5: Commit**

```powershell
python -m pytest app/domains/compliance/tests/test_privacy_requests.py -q
git add backend/app/domains/compliance
git commit -m "feat: process privacy data requests"
```

## Task 4: 合规控制与证据库

- [x] **Step 1: 写过期证据测试**

```py
async def test_control_becomes_attention_required_when_evidence_expires(control_service, evidence):
    evidence.expires_at = utcnow() - timedelta(days=1)
    await control_service.refresh_status(evidence.control_id)
    assert (await control_service.get(evidence.control_id)).status == "attention_required"
```

- [x] **Step 2: 模型**

```text
compliance_frameworks
compliance_controls
control_owners
control_evidence
control_reviews
security_incidents
incident_tasks
```

- [x] **Step 3: 证据访问**

证据文件按权限和短期 URL 访问；下载审计。

- [x] **Step 4: Commit**

```powershell
git add backend/app/domains/compliance
git commit -m "feat: add compliance control evidence"
```

## Task 5: API 密钥与 Webhook

- [x] **Step 1: 写密钥一次展示测试**

```py
async def test_api_key_secret_is_returned_only_on_creation(client):
    created = await client.post("/api/v1/api-keys", json={"name": "BI export", "scopes": ["reports.read"]})
    secret = created.json()["secret"]
    listed = await client.get("/api/v1/api-keys")
    assert secret not in listed.text
```

- [x] **Step 2: API Key**

前缀 + 随机 secret；数据库保存 secret hash、scopes、last_used_at、expires_at 和 revoked_at。

- [x] **Step 3: Webhook**

组织可创建 endpoint、事件订阅和 secret；投递 HMAC 签名、重试和死信；secret 可轮换并有短期重叠。

- [x] **Step 4: Commit**

```powershell
python -m pytest app/domains/compliance/tests/test_api_keys.py app/domains/webhooks/tests -q
git add backend/app/domains/compliance backend/app/domains/webhooks
git commit -m "feat: add scoped API keys and outbound webhooks"
```

## Task 6: 安全基线

- [x] **Step 1: 响应头测试**

```py
def test_security_headers(client):
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src" in response.headers["content-security-policy"]
```

- [x] **Step 2: 中间件**

配置 CSP、HSTS、Referrer-Policy、Permissions-Policy、CSRF 和 request ID。

- [x] **Step 3: 日志脱敏测试**

测试密码、token、Cookie、完整卡号和原始账单不会进入日志或错误追踪。

- [x] **Step 4: 扫描**

CI 增加依赖审计、秘密扫描和容器扫描，发现高危漏洞阻止合并。

- [x] **Step 5: Commit**

```powershell
git add backend/app/core frontend .github/workflows
git commit -m "security: enforce application security baseline"
```

## Task 7: 前端合规与隐私页面

- [x] **Step 1: 页面**

```text
/app/:org/security/audit-log
/app/:org/security/compliance
/app/:org/security/incidents
/app/:org/settings/data-retention
/app/:org/settings/api-keys
/app/:org/settings/webhooks
/account/privacy
```

- [x] **Step 2: 高风险体验**

删除、导出、API key 创建和法律保留要求清晰影响说明、重新认证和最终结果。

- [x] **Step 3: E2E**

创建 API key -> 使用 -> 撤销；发起数据导出 -> 下载；设置保留 -> 法律保留阻止删除；查询审计。

- [x] **Step 4: Commit**

```powershell
git add frontend/src/workspace/security frontend/src/account/privacy
git commit -m "feat: add compliance and privacy administration"
```

## 完成验收

- [x] 审计日志不可修改删除。
- [x] 敏感字段脱敏。
- [x] 保留和法律保留有测试。
- [x] 隐私请求有验证、截止日和结果。
- [x] API secret 只展示一次。
- [x] Webhook 具备签名、重试和轮换。
- [x] CI 阻止高危安全问题。
