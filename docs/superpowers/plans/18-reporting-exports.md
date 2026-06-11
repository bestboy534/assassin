# 报表、指标、导出与定时发送实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一指标定义、权限感知分析查询、保存报表、快照、异步导出和定时发送。

**Architecture:** 指标在 MetricRegistry 中集中定义，查询服务将允许的维度与筛选编译为 SQL。大导出创建 Job 和文件。报表订阅通过 Worker 生成快照并发送短期下载链接。

**Tech Stack:** FastAPI、PostgreSQL、SQLAlchemy、Worker、S3、React 图表库、TanStack Query、Pytest

---

## Task 1: 指标注册表

- [ ] **Step 1: 写口径一致测试**

```py
def test_verified_savings_metric_uses_only_verified_results(metric_registry):
    definition = metric_registry.get("verified_savings")
    assert "status = 'verified'" in definition.sql_expression
    assert "realized" not in definition.allowed_statuses
```

- [ ] **Step 2: 定义指标**

```py
@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    description: str
    value_type: Literal["money", "number", "percentage", "duration"]
    required_permission: str
    dimensions: frozenset[str]
```

- [ ] **Step 3: 首批指标**

支出、预算、应用数、供应商集中度、续订金额、席位利用率、采购周期、预计/实现/验证节省和高风险发现。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/reports/tests/test_metric_registry.py -q
git add backend/app/domains/reports
git commit -m "feat: centralize reporting metric definitions"
```

## Task 2: 权限感知查询

- [ ] **Step 1: 写范围测试**

```py
async def test_department_scoped_user_only_sees_department_spend(report_service, scoped_context):
    result = await report_service.query(scoped_context, metric="monthly_spend", group_by=["department"])
    assert {row.dimension_id for row in result.rows} == {scoped_context.department_id}
```

- [ ] **Step 2: 查询请求**

```py
class ReportQuery(BaseModel):
    metrics: list[str]
    date_range: DateRange
    group_by: list[str] = []
    filters: list[ReportFilter] = []
    comparison: Literal["previous_period", "previous_year"] | None = None
```

- [ ] **Step 3: 防任意 SQL**

客户端只传指标、维度和操作符枚举，服务端编译查询，不接受 SQL 或任意表达式。

- [ ] **Step 4: API**

```text
POST /reports/query
GET  /reports/metrics
GET  /reports/dimensions
```

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/reports/tests/test_query_service.py -q
git add backend/app/domains/reports
git commit -m "feat: add permission scoped analytics queries"
```

## Task 3: 保存报表与快照

- [ ] **Step 1: 写快照不可变测试**

```py
async def test_report_snapshot_does_not_change_after_source_updates(snapshot_service, saved_report):
    snapshot = await snapshot_service.create(saved_report.id)
    await mutate_source_data()
    assert (await snapshot_service.get(snapshot.id)).payload == snapshot.payload
```

- [ ] **Step 2: 模型**

```text
saved_reports
report_shares
report_snapshots
report_subscriptions
```

- [ ] **Step 3: 分享权限**

支持私有、组织、指定角色/成员；查看仍受底层资源权限约束。

- [ ] **Step 4: Commit**

```powershell
python -m pytest app/domains/reports/tests/test_saved_reports.py -q
git add backend/app/domains/reports
git commit -m "feat: save and snapshot reports"
```

## Task 4: 异步导出

- [ ] **Step 1: 写字段脱敏测试**

```py
async def test_export_masks_sensitive_fields_for_limited_role(export_service, limited_context):
    file = await export_service.generate(limited_context, report_id=REPORT_ID, format="csv")
    assert "full_card_number" not in await read_file(file)
```

- [ ] **Step 2: 格式**

CSV、XLSX、PDF。导出请求保存查询、字段、权限快照和生成者。

- [ ] **Step 3: 流程**

API 返回 Job；Worker 分块查询并写文件；完成后发送通知和 15 分钟签名下载 URL。

- [ ] **Step 4: 审计**

记录导出资源类型、筛选、行数和下载动作。

- [ ] **Step 5: Commit**

```powershell
python -m pytest app/domains/reports/tests/test_exports.py -q
git add backend/app/domains/reports
git commit -m "feat: generate audited report exports"
```

## Task 5: 定时发送

- [ ] **Step 1: 写时区测试**

```py
def test_monthly_subscription_runs_in_organization_timezone(schedule_service):
    next_run = schedule_service.next_run("0 9 1 * *", timezone="Asia/Hong_Kong")
    assert next_run.hour == 1  # UTC for 09:00 HKT
```

- [ ] **Step 2: 订阅**

频率 daily、weekly、monthly；收件人为有权限成员，发送前重新检查权限。

- [ ] **Step 3: 失败处理**

连续三次失败暂停订阅并通知创建人。

- [ ] **Step 4: Commit**

```powershell
git add backend/app/domains/reports
git commit -m "feat: schedule report delivery"
```

## Task 6: 前端分析工作区

- [ ] **Step 1: 页面**

```text
/app/:org/reports
/app/:org/reports/new
/app/:org/reports/:id
/app/:org/reports/:id/snapshots
```

- [ ] **Step 2: 构建器**

指标、时间、分组、筛选、比较和图表类型。无效组合由后端返回可解释错误。

- [ ] **Step 3: 图表可访问性**

每张图提供表格视图、图例、单位和下载数据；颜色不是唯一编码。

- [ ] **Step 4: E2E**

创建支出报表 -> 按部门分组 -> 保存 -> 分享 -> 导出 XLSX -> 创建月度订阅。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/reports
git commit -m "feat: add self service reporting"
```

## 完成验收

- [ ] 指标口径集中定义。
- [ ] 查询不能绕过部门或资源范围。
- [ ] 快照不可变。
- [ ] 导出权限与字段脱敏正确。
- [ ] 下载链接短期有效。
- [ ] 定时发送前重新检查权限。

