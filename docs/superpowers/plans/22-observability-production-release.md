# 可观测性、性能、安全加固、灾备与生产发布实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立生产级日志、指标、追踪、告警、性能门禁、安全测试、备份恢复、环境发布和运行手册，证明完整产品可安全上线。

**Architecture:** OpenTelemetry 贯穿 Web、API、Worker 和外部调用。结构化日志集中采集，Prometheus-compatible 指标驱动 SLO。发布使用迁移兼容、功能开关、灰度和自动冒烟。

**Tech Stack:** OpenTelemetry、结构化日志、Prometheus/Grafana 或托管等价物、错误监控、K6/Locust、Playwright、Docker、CI/CD

---

## Task 1: 结构化日志与请求追踪

- [ ] **Step 1: 写日志字段测试**

```py
def test_request_log_contains_trace_context_without_secrets(client, caplog):
    client.get("/health", headers={"X-Request-ID": "req-123"})
    record = parse_json_log(caplog.records[-1].message)
    assert record["request_id"] == "req-123"
    assert "cookie" not in record
    assert "authorization" not in record
```

- [ ] **Step 2: 日志规范**

字段：

```text
timestamp, level, service, environment, message,
request_id, trace_id, organization_id, actor_id,
route, status_code, duration_ms, error_code
```

- [ ] **Step 3: OpenTelemetry**

追踪 FastAPI、SQLAlchemy、Redis、HTTP client、Worker 和前端 Web Vitals。外部调用附 provider 和 operation，不记录 payload secret。

- [ ] **Step 4: Commit**

```powershell
python -m pytest tests/observability/test_logging.py -q
git add backend/app/core/logging.py backend/app/core/telemetry.py frontend/src/shared/telemetry
git commit -m "ops: add structured tracing and logging"
```

## Task 2: 指标、SLO 与告警

- [ ] **Step 1: 定义 SLO**

```text
API availability: 99.9%
Core API P95: <= 500ms
Job queue age P95: <= 60s
Webhook accepted P95: <= 2s
Critical notification delivery: >= 99%
```

- [ ] **Step 2: 指标**

请求、错误、延迟、DB pool、慢查询、队列长度、任务失败、同步延迟、Webhook、邮件、AI token/cost、文件扫描和业务漏斗。

- [ ] **Step 3: 告警**

每条告警写明严重级别、触发条件、抑制、负责人和 runbook URL。禁止只按单个错误触发噪声告警。

- [ ] **Step 4: 验证**

在 staging 人工触发队列积压、数据库连接失败和 Webhook 死信，确认告警和恢复通知。

- [ ] **Step 5: Commit**

```powershell
git add ops/monitoring ops/runbooks
git commit -m "ops: define service objectives and alerts"
```

## Task 3: 性能与容量

- [ ] **Step 1: 创建负载场景**

```text
dashboard_summary
application_list_10k
transaction_list_1m
report_query
concurrent_file_upload
job_polling
webhook_burst
```

- [ ] **Step 2: 写 K6/Locust 脚本**

场景使用测试租户和合成数据，断言错误率 < 1%，核心 API P95 < 500ms。

- [ ] **Step 3: 数据库分析**

为慢查询保存 `EXPLAIN ANALYZE`，增加组合索引、避免 N+1，并设置列表硬上限和游标分页。

- [ ] **Step 4: 前端预算**

```text
初始 JS gzip <= 250KB（公开站）
工作台初始路由 gzip <= 350KB
LCP <= 2.5s
INP <= 200ms
CLS <= 0.1
```

使用路由级代码拆分和图片尺寸约束。

- [ ] **Step 5: Commit**

```powershell
git add performance frontend/src backend/app
git commit -m "perf: enforce product performance budgets"
```

## Task 4: 安全验证

- [ ] **Step 1: 自动扫描**

CI 执行：

```text
dependency audit
secret scan
SAST
container scan
IaC scan
DAST against staging
```

高危和严重漏洞阻止发布。

- [ ] **Step 2: 授权测试**

自动生成资源 × 操作 × 角色矩阵；每个组织级资源执行跨租户 ID 猜测。

- [ ] **Step 3: 文件与 Webhook 测试**

恶意文件、MIME 欺骗、超大文件、Webhook 重放、旧时间戳、错误签名和 SSRF URL。

- [ ] **Step 4: 人工渗透**

生产发布前由独立人员覆盖认证、会话、租户、支付、文件、集成、业务逻辑和平台后台。

- [ ] **Step 5: Commit**

```powershell
git add security-tests .github/workflows ops/security
git commit -m "security: add production security gates"
```

## Task 5: 备份、恢复与灾备

- [ ] **Step 1: 定义目标**

RPO 15 分钟，RTO 4 小时。列出 PostgreSQL、对象存储、Redis（可重建）、秘密和配置的恢复策略。

- [ ] **Step 2: 自动备份**

数据库连续归档 + 每日快照；对象存储版本和生命周期；备份跨故障域并加密。

- [ ] **Step 3: 恢复演练**

每季度在隔离环境执行：

1. 恢复数据库到指定时间。
2. 恢复对象。
3. 校验租户数量、关键表行数和文件引用。
4. 运行 E2E 冒烟。
5. 记录实际 RPO/RTO。

- [ ] **Step 4: Commit**

```powershell
git add ops/disaster-recovery infrastructure/backup
git commit -m "ops: add tested backup and recovery"
```

## Task 6: 环境与秘密管理

- [ ] **Step 1: 环境**

local、test、staging、production 使用独立数据库、bucket、OAuth app、支付账号和密钥。

- [ ] **Step 2: 配置验证**

应用启动时验证生产禁止：

```text
DEBUG=true
SQLite
FakePaymentProvider
默认密钥
宽泛 CORS
未启用 Secure Cookie
```

- [ ] **Step 3: 秘密轮换**

文档化数据库、KMS、OAuth、Webhook、邮件和支付密钥轮换；支持重叠期。

- [ ] **Step 4: Commit**

```powershell
git add infrastructure backend/app/config.py ops/runbooks/secrets.md
git commit -m "ops: harden environment configuration"
```

## Task 7: 数据迁移与发布流水线

- [ ] **Step 1: 向前兼容迁移测试**

每次迁移在上一生产 schema 副本上执行；应用 N 与 schema N/N+1 兼容。

- [ ] **Step 2: 发布阶段**

```text
build -> unit/integration -> migration check -> deploy staging ->
E2E/security smoke -> production canary -> automated smoke -> full rollout
```

- [ ] **Step 3: 功能开关**

高风险功能按内部、试点组织、百分比、全量阶段发布。

- [ ] **Step 4: 回滚**

优先关闭功能开关或回滚应用；禁止对有数据写入的迁移直接 downgrade，使用 forward fix。

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows infrastructure ops/runbooks/release.md
git commit -m "ops: add safe production release pipeline"
```

## Task 8: 完整生产验收

- [ ] **Step 1: 执行功能 E2E**

```powershell
cd frontend
npm run test:e2e
```

必须覆盖规格第 15.3 节全部 10 条关键流程。

- [ ] **Step 2: 执行后端门禁**

```powershell
cd backend
python -m pytest -q
python -m ruff check app tests
python -m mypy app
```

- [ ] **Step 3: 执行性能与安全**

```powershell
k6 run performance/core-api.js
python -m pytest security-tests -q
```

- [ ] **Step 4: 恢复演练**

从备份恢复 staging 副本并运行冒烟。

- [ ] **Step 5: 发布签字**

产品、工程、安全和运维分别确认：

- 需求覆盖
- 测试证据
- 已知风险
- 回滚方案
- 支持与告警值班

- [ ] **Step 6: Commit**

```powershell
git add docs/release-evidence
git commit -m "docs: record production readiness evidence"
```

## Task 9: 可访问性与浏览器兼容验收

- [ ] **Step 1: 自动可访问性测试**

在 Playwright 中接入 axe，覆盖公开站、登录、总览、应用目录、采购表单、合同审核、交易表格和设置页面；严重和高影响问题阻止发布。

- [ ] **Step 2: 人工键盘测试**

验证：

- 跳过导航
- 焦点顺序与可见焦点
- Mega menu、对话框、抽屉和命令面板
- 表格批量操作
- 动态表单错误
- 图表表格替代

- [ ] **Step 3: 屏幕阅读器与缩放**

使用至少一种桌面屏幕阅读器检查关键流程；200% 缩放和 320 CSS px 宽度无信息丢失或双向滚动。

- [ ] **Step 4: 浏览器矩阵**

支持当前及前一主版本 Chrome、Edge、Firefox、Safari；移动支持 iOS Safari 和 Android Chrome。关键 E2E 在矩阵中执行。

- [ ] **Step 5: Commit**

```powershell
git add frontend/e2e/accessibility ops/accessibility
git commit -m "test: enforce accessible cross browser experience"
```

## 完成验收

- [ ] 日志、指标和追踪可关联同一请求。
- [ ] 告警有 runbook 并完成演练。
- [ ] 核心性能满足 SLO。
- [ ] 安全扫描和人工测试无未接受高危问题。
- [ ] 备份恢复达到 RPO/RTO。
- [ ] 生产配置无开发 Provider 或默认秘密。
- [ ] 发布支持灰度、冒烟和可执行回滚。
- [ ] WCAG 2.2 AA 关键流程和浏览器矩阵通过。
