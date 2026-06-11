# 供应商与风险管理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立供应商主档、安全/隐私/财务风险评估、问卷、证据、发现项和有时限的风险接受流程。

**Architecture:** 供应商是组织级业务实体，可关联应用、采购、合同、发票和交易。风险评估由版本化问卷和可解释评分组成，证据过期会触发复审。

**Tech Stack:** FastAPI、PostgreSQL、S3、Worker、React、TanStack Query、Pytest

---

## Task 1: 供应商主档

- [ ] **Step 1: 写别名匹配测试**

```py
async def test_vendor_alias_resolves_transaction_merchant(vendor_service, vendor):
    await vendor_service.add_alias(vendor.id, "ADOBE *CREATIVE CLOUD")
    assert await vendor_service.match("Adobe Creative Cloud") == vendor.id
```

- [ ] **Step 2: 创建模型**

```text
vendors
vendor_aliases
vendor_contacts
vendor_events
```

字段包括名称、域名、注册地、状态、类别、业务负责人、风险负责人。

- [ ] **Step 3: API**

```text
GET/POST /vendors
GET/PATCH /vendors/{id}
POST /vendors/{id}/aliases
POST /vendors/{id}/archive
```

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/vendors/tests/test_vendors.py -q
git add backend/app/domains/vendors backend/migrations
git commit -m "feat: add vendor master records"
```

## Task 2: 问卷模板与评估

- [ ] **Step 1: 写版本测试**

```py
async def test_assessment_uses_frozen_questionnaire_version(assessment_service, template):
    assessment = await assessment_service.start(template.id, VENDOR_ID)
    await publish_new_template_version(template.id)
    assert assessment.template_version_id != (await latest_version(template.id)).id
```

- [ ] **Step 2: 模型**

```text
questionnaire_templates
questionnaire_versions
questionnaire_questions
vendor_assessments
assessment_answers
```

问题支持 yes/no、text、single/multi select、file、date 和 number。

- [ ] **Step 3: 评估 API**

```text
POST /vendors/{id}/assessments
GET  /vendors/{id}/assessments/{assessment_id}
PATCH /vendors/{id}/assessments/{assessment_id}/answers
POST /vendors/{id}/assessments/{assessment_id}/submit
```

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/vendors/tests/test_assessments.py -q
git add backend/app/domains/vendors
git commit -m "feat: add versioned vendor assessments"
```

## Task 3: 可解释风险评分

- [ ] **Step 1: 写评分测试**

```py
def test_risk_score_returns_dimension_breakdown(scoring_engine):
    result = scoring_engine.score(assessment_answers())
    assert result.total == 68
    assert result.dimensions["security"].score == 80
    assert result.dimensions["privacy"].reasons
```

- [ ] **Step 2: 评分模型**

维度：

```text
security
privacy
financial
operational
compliance
```

保存规则版本、维度分、原因和缺失信息，不只保存总分。

- [ ] **Step 3: 风险发现**

高风险答案创建 `risk_findings`，包含严重性、负责人、截止日、缓解措施和证据。

- [ ] **Step 4: 外部风险检查 Adapter**

```py
class VendorRiskProvider(Protocol):
    async def screen(self, vendor: VendorScreeningInput) -> list[ExternalRiskSignal]: ...
```

支持制裁、注册状态和公开安全信号。外部命中只创建待复核 finding，不自动拒绝供应商；保存 provider、查询时间、匹配字段和原始引用。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/vendors/tests/test_scoring.py -q
git add backend/app/domains/vendors
git commit -m "feat: add explainable vendor risk scoring"
```

## Task 4: 证据、认证和到期复审

- [ ] **Step 1: 写过期测试**

```py
async def test_expired_evidence_reopens_assessment(review_scheduler, evidence):
    evidence.expires_at = utcnow() - timedelta(days=1)
    await review_scheduler.run()
    assert (await get_assessment(evidence.assessment_id)).status == "review_required"
```

- [ ] **Step 2: 证据类型**

- SOC 2
- ISO 27001
- GDPR/DPA
- 渗透测试摘要
- 保险证明
- 财务证明
- 自定义证据

- [ ] **Step 3: 调度任务**

每天扫描 90/30/7 天内过期证据，生成任务和通知；过期后降低相关维度可信度。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/vendors
git commit -m "feat: track expiring vendor evidence"
```

## Task 5: 风险接受与缓解

- [ ] **Step 1: 写权限测试**

```py
async def test_high_risk_acceptance_requires_security_role(client, high_risk_finding, finance_user):
    response = await client.post(
        f"/api/v1/risk-findings/{high_risk_finding.id}/accept",
        json={"reason": "Business exception", "expires_at": "2026-12-31"},
        user=finance_user,
    )
    assert response.status_code == 403
```

- [ ] **Step 2: 接受规则**

风险接受需要：

- 特定权限
- 理由
- 到期日
- 风险所有者
- 高风险时二次审批

- [ ] **Step 3: 缓解任务**

缓解计划包含任务、负责人、截止日和完成证据；到期未完成自动升级。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/vendors/tests/test_risk_acceptance.py -q
git add backend/app/domains/vendors
git commit -m "feat: govern vendor risk acceptance"
```

## Task 6: 前端供应商与风险页面

- [ ] **Step 1: 创建路由**

```text
/app/:org/vendors
/app/:org/vendors/:id
/app/:org/vendors/:id/assessments
/app/:org/risk
/app/:org/risk/:findingId
```

- [ ] **Step 2: 详情页**

展示关联应用、合同、支出、风险维度、证据、问卷、事件和负责人。

- [ ] **Step 3: E2E**

创建供应商 -> 发起问卷 -> 上传证据 -> 生成风险 -> 创建缓解 -> 有权限用户接受风险。

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/workspace/vendors frontend/src/workspace/risk
git commit -m "feat: add vendor risk workspace"
```

## 完成验收

- [ ] 供应商别名支持匹配。
- [ ] 问卷与评分规则均有版本。
- [ ] 风险分可解释。
- [ ] 外部风险信号经过人工复核，不直接作最终决定。
- [ ] 证据过期触发复审。
- [ ] 风险接受有权限、理由和期限。
- [ ] 供应商详情可追溯应用、合同和支出。
