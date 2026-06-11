# 身份认证与账号安全实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现安全的注册、登录、邮箱验证、密码重置、会话管理、TOTP MFA 和 OIDC 登录，为所有工作台接口提供可靠身份。

**Architecture:** 服务端使用 HttpOnly Secure Cookie 保存短期会话标识，数据库存储哈希后的 refresh/session secret。认证服务与组织授权分离；本计划只证明“用户是谁”，计划 06 决定“用户在组织内能做什么”。

**Tech Stack:** FastAPI、SQLAlchemy、Argon2、PyJWT/JOSE、TOTP、React Router、TanStack Query、React Hook Form、Zod

---

## 数据模型

```text
users:
  id, email_normalized, display_name, password_hash, email_verified_at,
  status, last_login_at, created_at, updated_at

user_identities:
  id, user_id, provider, provider_subject, email, created_at

sessions:
  id, user_id, secret_hash, user_agent_hash, ip_prefix,
  expires_at, last_seen_at, revoked_at, created_at

email_tokens:
  id, user_id, purpose, token_hash, expires_at, consumed_at

mfa_methods:
  id, user_id, method_type, secret_ciphertext, verified_at, created_at

mfa_recovery_codes:
  id, user_id, code_hash, used_at
```

## Task 1: 用户注册与邮箱验证

- [ ] **Step 1: 写失败测试**

```py
async def test_registration_normalizes_email_and_sends_verification(client, mail_outbox):
    response = await client.post("/api/v1/auth/register", json={
        "email": " Owner@Example.COM ",
        "password": "Long passphrase 2026!",
        "display_name": "负责人",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "verification_required"
    assert mail_outbox.last.template == "verify_email"
```

- [ ] **Step 2: 创建模型与迁移**

`email_normalized` 唯一，使用 `casefold().strip()`；密码哈希使用 Argon2id。原始验证 token 只发送一次，数据库仅存 SHA-256 哈希。

- [ ] **Step 3: 实现注册接口**

```text
POST /api/v1/auth/register
POST /api/v1/auth/verify-email
POST /api/v1/auth/resend-verification
```

对已存在邮箱统一返回 202，防止账号枚举。

- [ ] **Step 4: 运行**

```powershell
python -m pytest app/domains/identity/tests/test_registration.py -q
```

Expected: 正常注册、重复邮箱、过期 token、重复使用 token 测试通过。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/identity backend/migrations
git commit -m "feat: add verified user registration"
```

## Task 2: 密码登录与安全会话

- [ ] **Step 1: 写 Cookie 测试**

```py
async def test_login_sets_secure_http_only_session_cookie(client, verified_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": verified_user.email,
        "password": "Long passphrase 2026!",
    })
    cookie = response.cookies.get("session")
    assert response.status_code == 204
    assert cookie is not None
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Lax" in response.headers["set-cookie"]
```

- [ ] **Step 2: 实现 SessionService**

```py
class SessionService:
    async def create(self, user: User, context: LoginContext) -> RawSessionToken: ...
    async def authenticate(self, raw_token: str) -> AuthenticatedUser: ...
    async def rotate(self, session_id: UUID) -> RawSessionToken: ...
    async def revoke(self, user_id: UUID, session_id: UUID) -> None: ...
    async def revoke_all(self, user_id: UUID, except_session_id: UUID | None = None) -> None: ...
```

每次敏感操作更新 `last_seen_at`，会话 token 轮换并检测旧 token 重用。

- [ ] **Step 3: 创建接口**

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
GET    /api/v1/auth/sessions
DELETE /api/v1/auth/sessions/{id}
DELETE /api/v1/auth/sessions
```

- [ ] **Step 4: 加入速率限制**

按 email + IP 限制失败登录；达到阈值后要求验证码或短期冷却，不能永久锁死账号。

- [ ] **Step 5: 运行**

```powershell
python -m pytest app/domains/identity/tests/test_sessions.py -q
```

Expected: 登录、轮换、撤销、过期、重用检测和速率限制通过。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/domains/identity
git commit -m "feat: add revocable secure sessions"
```

## Task 3: 密码重置与重新认证

- [ ] **Step 1: 写重置后撤销测试**

```py
async def test_password_reset_revokes_existing_sessions(client, user_with_sessions):
    token = await request_reset(user_with_sessions.email)
    await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "Another long passphrase 2026!",
    })
    assert await active_session_count(user_with_sessions.id) == 0
```

- [ ] **Step 2: 实现端点**

```text
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/reauthenticate
```

重新认证返回 10 分钟有效的 `reauth_token`，仅用于删除组织、导出敏感数据、MFA 变更等操作。

- [ ] **Step 3: 验证密码策略**

至少 12 字符，允许长口令，不强制周期更换；使用泄露密码 denylist Adapter。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/identity/tests/test_password_reset.py -q
git add backend/app/domains/identity
git commit -m "feat: add password recovery and reauthentication"
```

## Task 4: TOTP MFA 与恢复码

- [ ] **Step 1: 写 MFA 挑战测试**

```py
async def test_mfa_user_receives_challenge_before_session(client, mfa_user):
    response = await client.post("/api/v1/auth/login", json=credentials(mfa_user))
    assert response.status_code == 202
    assert response.json()["status"] == "mfa_required"
    assert "session=" not in response.headers.get("set-cookie", "")
```

- [ ] **Step 2: 实现设置流程**

```text
POST /api/v1/auth/mfa/totp/setup
POST /api/v1/auth/mfa/totp/verify
POST /api/v1/auth/mfa/challenge
POST /api/v1/auth/mfa/recovery
DELETE /api/v1/auth/mfa/{id}
```

TOTP secret 加密存储；验证成功后生成 10 个一次性恢复码，只展示一次。

- [ ] **Step 3: 防重放**

记录最后接受的 TOTP 时间步，拒绝同一验证码重复使用。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/identity/tests/test_mfa.py -q
git add backend/app/domains/identity
git commit -m "feat: add TOTP multi factor authentication"
```

## Task 5: Google 与 Microsoft OIDC

- [ ] **Step 1: 写 state/nonce 测试**

```py
async def test_oidc_callback_rejects_wrong_state(client, oidc_stub):
    response = await client.get("/api/v1/auth/oidc/google/callback?state=wrong&code=abc")
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_oidc_state"
```

- [ ] **Step 2: 定义 Provider Adapter**

```py
class OidcProvider(Protocol):
    def authorization_url(self, state: str, nonce: str, redirect_uri: str) -> str: ...
    async def exchange(self, code: str, redirect_uri: str) -> OidcClaims: ...
```

- [ ] **Step 3: 实现账号链接规则**

- 已验证同邮箱账号：要求登录后明确链接。
- 新邮箱：创建已验证用户。
- Provider subject 已绑定：直接登录。
- 禁止仅凭未验证 provider email 自动合并。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/identity/tests/test_oidc.py -q
git add backend/app/domains/identity
git commit -m "feat: add OIDC sign in"
```

## Task 6: 前端认证页面与保护路由

- [ ] **Step 1: 写路由保护测试**

```tsx
test("redirects anonymous user to login and restores destination", async () => {
  renderApp("/app/applications");
  expect(await screen.findByRole("heading", { name: "登录" })).toBeVisible();
  expect(window.location.search).toContain("return_to=%2Fapp%2Fapplications");
});
```

- [ ] **Step 2: 创建页面**

```text
/login
/signup
/verify-email
/forgot-password
/reset-password
/mfa
/account/sessions
/account/security
```

- [ ] **Step 3: 创建 AuthProvider**

TanStack Query 请求 `/auth/me`；401 清空缓存并跳转登录；会话使用 Cookie，前端不存 access token。

- [ ] **Step 4: E2E**

```ts
test("registers, verifies, logs in and logs out", async ({ page }) => {
  // 使用测试邮件捕获器获取验证链接。
});
```

- [ ] **Step 5: 运行并提交**

```powershell
cd frontend
npm run test -- auth
npm run test:e2e -- --grep "registers"
git add src/app src/auth
git commit -m "feat: add secure authentication experience"
```

## Task 7: 企业 SAML/OIDC SSO 与 SCIM

- [ ] **Step 1: 写强制 SSO 测试**

```py
async def test_enforced_sso_blocks_password_login_for_member(client, sso_org, member):
    response = await client.post("/api/v1/auth/login", json={
        "email": member.email,
        "password": "Long passphrase 2026!",
    })
    assert response.status_code == 409
    assert response.json()["code"] == "organization_sso_required"
```

- [ ] **Step 2: 创建企业身份配置**

```text
sso_connections
sso_domains
scim_tokens
scim_sync_events
```

SAML 保存 entity ID、SSO URL、证书指纹和加密元数据；OIDC 保存 issuer、client ID 和加密 secret。域名验证完成后才能强制 SSO。

- [ ] **Step 3: 实现 SSO**

```text
POST /organizations/{id}/sso/saml
POST /organizations/{id}/sso/oidc
POST /organizations/{id}/sso/test
POST /organizations/{id}/sso/enforce
GET  /auth/sso/discover?email=
GET  /auth/sso/{connection_id}/callback
```

验证 SAML 签名、audience、recipient、InResponseTo 和时钟偏差；OIDC 验证 issuer、audience、nonce 和 PKCE。

- [ ] **Step 4: 实现 SCIM 2.0**

```text
GET/POST/PATCH/DELETE /scim/v2/Users
GET/POST/PATCH/DELETE /scim/v2/Groups
GET /scim/v2/ServiceProviderConfig
GET /scim/v2/Schemas
```

Bearer token 仅保存哈希；用户停用触发成员暂停与离职访问任务；群组映射到组织角色或部门。

- [ ] **Step 5: 紧急访问**

组织必须保留至少一个标记为 break-glass 的 owner；使用密码 + MFA，不能被普通 SSO 策略禁用；每次使用发送高优先级安全通知。

- [ ] **Step 6: 运行并提交**

```powershell
python -m pytest app/domains/identity/tests/test_enterprise_sso.py app/domains/identity/tests/test_scim.py -q
git add backend/app/domains/identity frontend/src/workspace/settings/sso
git commit -m "feat: add enterprise SSO and SCIM provisioning"
```

## 完成验收

- [ ] 邮箱枚举受到保护。
- [ ] Cookie 为 HttpOnly、Secure、SameSite。
- [ ] 会话可查看、单独撤销和全部撤销。
- [ ] 密码重置使旧会话失效。
- [ ] MFA secret 加密，恢复码一次性。
- [ ] OIDC 验证 state、nonce、issuer 和 audience。
- [ ] 强制 SSO 无法被普通密码登录绕过。
- [ ] SCIM 停用触发组织成员停用和访问回收。
- [ ] Break-glass owner 可用且每次使用均告警。
- [ ] 前端不保存长期令牌。
