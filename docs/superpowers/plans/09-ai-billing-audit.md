# AI 账单审计与退订 Copilot 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有文本解析 MVP 升级为组织级、异步、可解释的账单审计，支持文件、人工确认、应用匹配、风险识别和退订跟踪。

**Architecture:** 上传或文本输入创建 `analysis_run` 和 Job。流水线依次执行验证、脱敏、规则解析、可选模型解析、归一化、匹配和风险生成。原始输入与派生文本按保留策略管理。

**Tech Stack:** FastAPI、PostgreSQL、Redis Worker、S3、现有启发式解析器、OpenAI-compatible Adapter、React、TanStack Query

---

## 状态模型

```text
analysis_run:
  queued -> validating -> extracting -> matching -> awaiting_review -> completed
  任意处理中状态 -> failed | cancelled

analysis_item:
  need_confirm | active | flagged | cancel_in_progress |
  cancelled | cancellation_failed | verified_saved | ignored
```

## Task 1: 迁移现有解析领域

- [ ] **Step 1: 写回归测试**

将 `backend/tests/test_analyze.py` 的样例迁移到：

```py
def test_csv_regression_detects_api_and_apple(parser):
    result = parser.extract(MOCK_CSV, source_hint="csv")
    assert any(item.risk_type == "api_usage" for item in result)
    assert any(item.risk_type == "apple_unresolved" for item in result)
```

- [ ] **Step 2: 拆分目录**

```text
backend/app/domains/audit_ai/
  models.py
  schemas.py
  parser.py
  normalizer.py
  matcher.py
  risk_engine.py
  service.py
  router.py
  tasks.py
  adapters/llm.py
```

将旧 `heuristic_extractor.py`、`llm_extractor.py`、`normalizer.py`、`route_matcher.py` 的逻辑迁入，不改变已有样例结果。

- [ ] **Step 3: 使用 Decimal**

金额从 `float` 改为 `Decimal`；数据库字段使用 `Numeric(19, 4)`。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/audit_ai/tests/test_parser_regression.py -q
git add backend/app/domains/audit_ai backend/app/heuristic_extractor.py backend/app/llm_extractor.py
git commit -m "refactor: isolate billing audit domain"
```

## Task 2: 分析运行与输入

- [ ] **Step 1: 写创建运行测试**

```py
async def test_create_analysis_belongs_to_organization(client, org_auth, available_file):
    response = await client.post(
        f"/api/v1/organizations/{org_auth.org_id}/analysis-runs",
        json={"file_id": str(available_file.id), "source_hint": "csv"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
```

- [ ] **Step 2: 创建模型**

```text
analysis_runs
analysis_inputs
analysis_items
analysis_feedback
```

`analysis_inputs` 保存 file 引用或加密文本引用、保留到期时间和脱敏状态，不在普通日志保存正文。

- [ ] **Step 3: 创建接口**

```text
POST /organizations/{id}/analysis-runs
GET  /organizations/{id}/analysis-runs
GET  /organizations/{id}/analysis-runs/{run_id}
POST /organizations/{id}/analysis-runs/{run_id}/retry
```

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/audit_ai/tests/test_runs.py -q
git add backend/app/domains/audit_ai backend/migrations
git commit -m "feat: add organization billing analysis runs"
```

## Task 3: 文件解析流水线

- [ ] **Step 1: 写阶段失败测试**

```py
async def test_failed_extraction_records_safe_error_without_raw_text(pipeline, bad_pdf):
    run = await pipeline.execute(bad_pdf.run_id)
    assert run.status == "failed"
    assert run.error_code == "unsupported_pdf_content"
    assert bad_pdf.secret_text not in run.error_message
```

- [ ] **Step 2: 实现阶段**

```py
PIPELINE = [
    validate_input,
    extract_text,
    redact_sensitive_data,
    parse_with_rules,
    parse_with_model_if_enabled,
    normalize_items,
    match_applications,
    generate_risks,
    persist_review_items,
]
```

每个阶段更新 Job progress，并可安全重试。

- [ ] **Step 3: 支持格式**

- CSV
- UTF-8/常见编码文本
- PDF
- PNG/JPEG
- 邮件正文

OCR 通过 Adapter，解析器不依赖具体供应商。

- [ ] **Step 4: 模型 Adapter**

```py
class ExtractionModel(Protocol):
    async def extract(self, redacted_text: str, source_hint: str) -> ExtractedPayload: ...
```

使用严格 JSON Schema，记录 model、prompt_version、latency 和 token usage。

- [ ] **Step 5: 运行并提交**

```powershell
python -m pytest app/domains/audit_ai/tests/test_pipeline.py -q
git add backend/app/domains/audit_ai
git commit -m "feat: add explainable audit extraction pipeline"
```

## Task 4: 风险规则与证据

- [ ] **Step 1: 写规则测试**

```py
@pytest.mark.parametrize("fixture,risk", [
    ("duplicate_vendor_rows", "possible_duplicate"),
    ("price_increase", "price_increase"),
    ("apple_unknown", "apple_unresolved"),
    ("unapproved_tool", "unapproved_software"),
])
async def test_risk_rules(risk_engine, fixture, risk):
    assert risk in [x.code for x in await risk_engine.evaluate(load_fixture(fixture))]
```

- [ ] **Step 2: 风险模型**

每个风险保存：

```text
code
severity
confidence
evidence_json
calculation_json
rule_version
```

- [ ] **Step 3: 规则边界**

未知使用率不能判定闲置；异常涨价需要历史可比基线；重复费用必须排除合法多席位或多实体场景。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/audit_ai/risk_engine.py backend/app/domains/audit_ai/tests
git commit -m "feat: add evidence based billing risk rules"
```

## Task 5: 人工确认与反馈

- [ ] **Step 1: 写乐观锁测试**

```py
async def test_review_rejects_stale_version(client, review_item):
    response = await client.patch(
        f"/api/v1/analysis-items/{review_item.id}",
        json={"version": review_item.version - 1, "software_name": "Notion"},
    )
    assert response.status_code == 409
```

- [ ] **Step 2: 创建操作**

```text
PATCH /analysis-items/{id}
POST  /analysis-items/{id}/confirm-active
POST  /analysis-items/{id}/flag
POST  /analysis-items/{id}/ignore
POST  /analysis-items/{id}/link-application
POST  /analysis-items/{id}/create-application
```

- [ ] **Step 3: 保存反馈**

记录原值、新值、actor、reason、parser_version。组织别名可以更新；全局模型或规则不自动学习单一客户纠正。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/audit_ai/tests/test_review.py -q
git add backend/app/domains/audit_ai
git commit -m "feat: add human review for audit findings"
```

## Task 6: 退订 Copilot

- [ ] **Step 1: 写取消状态测试**

```py
async def test_cancelled_requires_user_evidence(cancellation_service, item):
    with pytest.raises(ValidationError):
        await cancellation_service.mark_cancelled(item.id, evidence=None)
```

- [ ] **Step 2: 路径数据**

`cancellation_routes` 进入数据库并由平台后台管理，包含官方 URL、步骤、支持邮箱、地区和最后验证时间。

- [ ] **Step 3: 创建取消 Case**

```text
POST /analysis-items/{id}/cancellation-case
PATCH /cancellation-cases/{id}
POST /cancellation-cases/{id}/mark-cancelled
POST /cancellation-cases/{id}/mark-failed
```

生成邮件草稿但不自动发送，除非用户明确点击且邮件适配器已启用。

- [ ] **Step 4: 后续验证**

下一账期未出现匹配交易后，系统建议 `verified_saved`，仍需财务确认。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/audit_ai
git commit -m "feat: add auditable cancellation copilot"
```

## Task 7: 前端审计工作台

- [ ] **Step 1: 写上传进度测试**

```tsx
test("shows pipeline progress and review queue", async () => {
  server.use(jobProgressSequence(["validating", "extracting", "awaiting_review"]));
  renderAuditRun();
  expect(await screen.findByText("正在提取账单内容")).toBeVisible();
  expect(await screen.findByText("等待人工确认")).toBeVisible();
});
```

- [ ] **Step 2: 创建页面**

```text
/app/:org/audit
/app/:org/audit/new
/app/:org/audit/:runId
/app/:org/audit/:runId/review
/app/:org/cancellations
```

- [ ] **Step 3: 输入体验**

拖拽上传、文本粘贴、来源选择、隐私提示、支持格式、文件状态和失败重试。

- [ ] **Step 4: 审核体验**

显示证据片段、置信度、风险、金额、匹配应用和批量确认；低置信度优先排序。

- [ ] **Step 5: E2E**

上传样例 CSV -> 等待完成 -> 确认应用 -> 标记优化 -> 创建取消 case -> 上传取消证据。

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/workspace/audit
git commit -m "feat: add billing audit workspace"
```

## 完成验收

- [ ] 旧样例回归不退化。
- [ ] 金额使用 Decimal。
- [ ] 原始输入不进入日志。
- [ ] 每项结果有证据、置信度和版本。
- [ ] 人工修正持久化并审计。
- [ ] 默认不自动登录或点击第三方取消。
- [ ] 节省只在后续验证后成为 verified。

