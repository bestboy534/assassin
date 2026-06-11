# CMS、SEO 与线索表单实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将公开站内容和获客入口变为可发布、可索引、可审计的真实系统，支持内容版本、SEO、预约演示、联系表单和 CRM 同步。

**Architecture:** 内容与表单数据存储在 PostgreSQL。公开 API 只返回已发布内容；管理 API 使用平台角色。表单提交写数据库和 Outbox，Worker 异步发送邮件与 CRM，避免外部服务失败阻塞用户。

**Tech Stack:** FastAPI、SQLAlchemy、PostgreSQL、Alembic、React Router、TanStack Query、React Hook Form、Zod、Redis Worker

---

## 文件结构

**Create**

- `backend/app/domains/cms/models.py`
- `backend/app/domains/cms/schemas.py`
- `backend/app/domains/cms/repository.py`
- `backend/app/domains/cms/service.py`
- `backend/app/domains/cms/router.py`
- `backend/app/domains/cms/permissions.py`
- `backend/app/domains/cms/tests/test_content_api.py`
- `backend/app/domains/leads/models.py`
- `backend/app/domains/leads/schemas.py`
- `backend/app/domains/leads/service.py`
- `backend/app/domains/leads/router.py`
- `backend/app/domains/leads/tasks.py`
- `backend/app/domains/leads/tests/test_lead_submission.py`
- `backend/migrations/versions/*_create_cms_and_leads.py`
- `frontend/src/marketing/api/content.ts`
- `frontend/src/marketing/forms/DemoForm.tsx`
- `frontend/src/marketing/forms/ContactForm.tsx`
- `frontend/src/marketing/forms/PartnerForm.tsx`
- `frontend/src/marketing/seo/PageMeta.tsx`
- `frontend/src/admin/content/ContentEditorPage.tsx`

## 数据模型

```text
content_entries:
  id, content_type, slug, locale, status, current_version_id,
  published_at, created_by, created_at, updated_at

content_versions:
  id, entry_id, version_number, title, excerpt, body_json,
  seo_title, seo_description, canonical_url, og_image_file_id,
  change_note, created_by, created_at

form_submissions:
  id, form_type, email, name, company, role, country,
  message, consent_version, source_url, utm_json, status,
  idempotency_key, created_at

outbox_events:
  id, event_type, aggregate_id, payload_json, status,
  attempts, available_at, created_at, processed_at
```

## Task 1: 内容版本与发布状态

- [ ] **Step 1: 写失败的内容 API 测试**

```py
def test_public_content_returns_only_published_version(client, cms_factory):
    draft = cms_factory(status="draft", slug="draft-post")
    published = cms_factory(status="published", slug="published-post")

    assert client.get(f"/api/v1/content/{draft.slug}").status_code == 404
    response = client.get(f"/api/v1/content/{published.slug}")
    assert response.status_code == 200
    assert response.json()["title"] == published.current_version.title
```

- [ ] **Step 2: 创建迁移**

迁移必须创建 `content_entries`、`content_versions`，并增加唯一约束：

```py
sa.UniqueConstraint("content_type", "slug", "locale", name="uq_content_slug_locale")
```

- [ ] **Step 3: 实现发布服务**

`service.py` 提供：

```py
class CmsService:
    def create_draft(self, actor: Actor, command: CreateContent) -> ContentEntry: ...
    def create_version(self, actor: Actor, entry_id: UUID, command: UpdateContent) -> ContentVersion: ...
    def publish(self, actor: Actor, entry_id: UUID, version_id: UUID, publish_at: datetime | None) -> ContentEntry: ...
    def unpublish(self, actor: Actor, entry_id: UUID) -> ContentEntry: ...
```

发布时验证 slug、SEO 标题、描述和内容主体不为空；版本发布后不可修改。

- [ ] **Step 4: 运行**

```powershell
cd backend
python -m pytest app/domains/cms/tests/test_content_api.py -q
```

Expected: 公开端只返回已发布版本。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/cms backend/migrations
git commit -m "feat: add versioned public content"
```

## Task 2: 管理端内容权限与预览

- [ ] **Step 1: 写权限测试**

```py
@pytest.mark.parametrize("role,expected", [
    ("content_editor", 201),
    ("platform_admin", 201),
    ("organization_admin", 403),
])
def test_create_content_requires_platform_content_role(auth_client, role, expected):
    response = auth_client(role).post("/api/v1/admin/content", json=VALID_CONTENT)
    assert response.status_code == expected
```

- [ ] **Step 2: 实现管理 API**

端点：

```text
POST   /api/v1/admin/content
POST   /api/v1/admin/content/{id}/versions
POST   /api/v1/admin/content/{id}/publish
POST   /api/v1/admin/content/{id}/unpublish
GET    /api/v1/admin/content
GET    /api/v1/admin/content/{id}/preview
```

预览使用一次性、短期签名 token，不把草稿暴露给公开 API。

- [ ] **Step 3: 实现编辑器页面**

编辑器必须包含：

- 内容类型
- slug、locale
- 标题、摘要
- 结构化正文
- SEO 标题与描述
- OG 图片
- 预览
- 立即发布或定时发布
- 变更说明

- [ ] **Step 4: 验证**

Run:

```powershell
cd backend
python -m pytest app/domains/cms/tests -q
cd ../frontend
npm run test -- ContentEditorPage
```

Expected: 权限、版本和预览测试通过。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/cms frontend/src/admin/content
git commit -m "feat: add content publishing workflow"
```

## Task 3: 预约演示与联系表单

- [ ] **Step 1: 写幂等提交测试**

```py
def test_duplicate_idempotency_key_creates_one_submission(client, db):
    headers = {"Idempotency-Key": "demo-123"}
    first = client.post("/api/v1/forms/demo", json=VALID_DEMO, headers=headers)
    second = client.post("/api/v1/forms/demo", json=VALID_DEMO, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["submission_id"] == second.json()["submission_id"]
    assert db.count(FormSubmission) == 1
```

- [ ] **Step 2: 创建表单模型与接口**

接口：

```text
POST /api/v1/forms/demo
POST /api/v1/forms/contact
POST /api/v1/forms/partner
POST /api/v1/forms/press
```

请求共享字段：

```py
class LeadBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    company: str = Field(min_length=2, max_length=180)
    country: str
    consent_version: str
    source_url: HttpUrl
    utm: dict[str, str] = {}
```

所有表单增加隐藏 honeypot、IP/邮箱速率限制和服务端长度校验。

- [ ] **Step 3: 同事务写 Outbox**

创建 `lead.submitted` 事件，payload 只包含 CRM 所需字段，不包含请求头或原始 IP。API 返回：

```json
{
  "submission_id": "01J...",
  "status": "accepted"
}
```

- [ ] **Step 4: 实现前端表单**

使用 React Hook Form + Zod。提交按钮状态：

- 初始
- 校验失败
- 提交中
- 成功
- 可重试错误
- 速率限制

成功后不重复发送，刷新可进入感谢页面。

- [ ] **Step 5: 运行**

```powershell
cd backend
python -m pytest app/domains/leads/tests -q
cd ../frontend
npm run test -- DemoForm ContactForm PartnerForm
```

Expected: 幂等、校验、错误显示和成功状态通过。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/domains/leads backend/migrations frontend/src/marketing/forms
git commit -m "feat: add production lead forms"
```

## Task 4: CRM 与邮件异步投递

- [ ] **Step 1: 写重试测试**

```py
def test_crm_failure_retries_without_duplicate_contact(worker, crm_stub, outbox_event):
    crm_stub.fail_once()
    worker.process(outbox_event.id)
    worker.process(outbox_event.id)
    assert crm_stub.upsert_calls == 2
    assert crm_stub.created_contacts == 1
    assert outbox_event.reload().status == "processed"
```

- [ ] **Step 2: 定义 Adapter**

```py
class CrmAdapter(Protocol):
    def upsert_lead(self, external_key: str, payload: LeadPayload) -> str: ...

class TransactionalEmailAdapter(Protocol):
    def send_template(self, template: str, recipient: str, variables: dict[str, str]) -> str: ...
```

- [ ] **Step 3: 实现 Worker**

处理 `lead.submitted`：

1. 使用 submission ID 作为外部幂等键。
2. Upsert CRM 联系人和线索。
3. 发送内部通知。
4. 发送用户确认邮件。
5. 保存外部 ID 和投递结果。

- [ ] **Step 4: 验证**

Run:

```powershell
python -m pytest app/domains/leads/tests/test_lead_delivery.py -q
```

Expected: 临时失败重试，永久失败进入 dead-letter，不重复创建 CRM 联系人。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/leads backend/app/infrastructure
git commit -m "feat: deliver leads through reliable outbox"
```

## Task 5: SEO、站点地图与结构化数据

- [ ] **Step 1: 写元数据测试**

```tsx
test("report page emits canonical and article metadata", async () => {
  renderRoute("/resources/reports/ai-2025");
  expect(await screen.findByRole("heading", { name: /AI 2025/ })).toBeVisible();
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
    "href",
    "https://example.com/resources/reports/ai-2025",
  );
  expect(document.querySelector('script[type="application/ld+json"]')).toBeTruthy();
});
```

- [ ] **Step 2: 实现 `PageMeta`**

支持：

- title
- description
- canonical
- robots
- Open Graph
- Twitter card
- Article/Organization/FAQPage JSON-LD

- [ ] **Step 3: 增加服务端 SEO 输出**

生产部署必须使用静态预渲染或 SSR，使公开页面初始 HTML 含核心元数据。构建过程生成：

```text
/sitemap.xml
/robots.txt
/rss.xml
```

只包含已发布且允许索引的内容。

- [ ] **Step 4: E2E 验证**

Run:

```powershell
npm run build
npm run test:e2e -- --grep "SEO"
```

Expected: 公开内容具有唯一 canonical，草稿和法律历史版本按策略设置 robots。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/marketing/seo frontend/src/marketing/api frontend/vite.config.ts
git commit -m "feat: add public SEO and content discovery"
```

## 完成验收

- [ ] 内容编辑可创建版本、预览、定时发布和下线。
- [ ] 公开 API 不泄露草稿。
- [ ] 表单提交幂等并经过反垃圾与速率限制。
- [ ] CRM 或邮件失败不影响用户提交结果。
- [ ] 每个公开页面有唯一 SEO 元数据。
- [ ] sitemap、robots 和 RSS 只包含正确内容。

