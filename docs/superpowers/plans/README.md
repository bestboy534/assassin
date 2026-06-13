# 企业软件管理平台实施计划索引

本目录将 [总体设计规格](../specs/2026-06-11-enterprise-saas-platform-design.md) 拆为 22 份可独立执行、可测试、可提交的实施计划。

## 执行原则

1. 必须按依赖顺序执行，不允许绕过身份、多租户、权限和审计基础。
2. 每项任务使用测试驱动开发：先写失败测试，再写最小实现，再执行完整测试。
3. 每个计划完成后必须通过该计划的验收清单，不能只以“构建成功”代替业务验收。
4. PostgreSQL 是业务事实来源；Zustand 只保存界面偏好。
5. 所有业务查询必须带组织边界，所有关键写操作必须写审计日志。
6. 所有异步消费者必须幂等，所有外部 Webhook 必须验签并防重放。
7. AI 输出必须展示证据和置信度，不自动成为正式财务、合同或安全结论。
8. 支付能力通过合规供应商适配器实现，系统不保存完整卡号或 CVV。

## 计划清单

> 2026-06-13 复核：各计划文档内的 checkbox 仍作为执行清单模板保留，目前 01-22 均未逐项勾选。严格按每份计划的完整验收标准，当前没有计划可标记为“全部完成”；下表只描述已经存在的实现范围。

| 编号 | 计划 | 主要交付 | 依赖 | 实现状态 |
|---|---|---|---|---|
| 01 | [工程基线](./01-engineering-foundation.md) | 仓库清理、测试、CI、统一命令 | 无 | 部分实现 |
| 02 | [前端架构与公开站](./02-frontend-routing-design-system.md) | 路由拆分、设计系统、45 个公开页迁移 | 01 | 核心已验证 |
| 03 | [CMS、SEO 与线索表单](./03-cms-seo-lead-forms.md) | 内容发布、SEO、预约演示与 CRM Outbox | 01、02、04 | 部分实现 |
| 04 | [数据与异步基础设施](./04-data-async-infrastructure.md) | PostgreSQL、Alembic、Redis、Worker、对象存储 | 01 | 核心已验证 |
| 05 | [身份认证与账号安全](./05-authentication-account-security.md) | 登录、会话、验证、重置、MFA、OIDC | 04 | 部分实现 |
| 06 | [组织、多租户与 RBAC](./06-organizations-rbac.md) | 组织、成员、邀请、角色、权限、租户隔离 | 05 | 部分实现 |
| 07 | [工作台外壳与全局能力](./07-workspace-shell-dashboard.md) | 工作台导航、总览、搜索、通知、待办 | 02、06 | 部分实现 |
| 08 | [应用目录、发现与席位](./08-application-catalog-discovery-seats.md) | 应用主档、来源、去重、席位、使用率、离职 | 06、07 | 部分实现 |
| 09 | [AI 账单审计](./09-ai-billing-audit.md) | 文件导入、解析、确认、匹配、退订 Copilot | 04、06、08 | 部分实现 |
| 10 | [节省机会与优化项目](./10-savings-optimization.md) | 机会、项目、基线、实现与验证节省 | 08、09 | 核心已验证 |
| 11 | [采购申请与审批](./11-procurement-approvals.md) | 动态申请、流程版本、审批任务、履约 | 06、07、08 | 部分实现 |
| 12 | [供应商与风险](./12-vendor-risk-management.md) | 供应商主档、问卷、证据、风险与接受 | 06、11 | 部分实现 |
| 13 | [合同、续订与谈判](./13-contracts-renewals.md) | 合同版本、AI 抽取、续订日历、谈判 | 08、11、12 | 部分实现 |
| 14 | [预算与交易](./14-budgets-transactions.md) | 预算、交易导入、匹配、多币种、月结 | 06、08 | 核心已验证 |
| 15 | [支付与虚拟卡](./15-payments-virtual-cards.md) | 支付适配器、卡、限额、Webhook、失败处理 | 11、14 | 核心已验证 |
| 16 | [发票与会计自动化](./16-invoices-accounting.md) | OCR、发票、匹配、科目映射、会计导出 | 09、13、14 | 核心已验证 |
| 17 | [集成平台](./17-integrations-sync-platform.md) | OAuth、凭证、同步框架、首批适配器 | 04、06 | 部分实现 |
| 18 | [报表与导出](./18-reporting-exports.md) | 指标定义、分析查询、保存报表、定时导出 | 08-17 | 核心已验证 |
| 19 | [安全、合规与隐私](./19-security-compliance-privacy.md) | 审计、保留、DSR、证据库、API 密钥、Webhook、安全基线 | 05、06、12 | 部分实现（6/7） |
| 20 | [套餐、计费与权益](./20-platform-billing-entitlements.md) | 套餐、订阅、权益、用量、账单门户 | 06、15 | 待开发 |
| 21 | [支持、状态页与管理后台](./21-support-status-admin.md) | 工单、诊断授权、状态事件、平台运营后台 | 03-20 | 待开发 |
| 22 | [可观测性与生产发布](./22-observability-production-release.md) | 日志、追踪、告警、性能、安全、灾备、发布 | 01-21 | 待开发 |

## 里程碑

### M0：工程可持续

完成 01-04。仓库具有稳定测试、路径路由、数据库迁移、任务队列和对象存储。

### M1：可登录的核心产品

完成 05-10。用户可注册组织、导入账单、确认应用、发现节省并跟踪结果。

### M2：采购与续订闭环

完成 11-13。软件采购、供应商风险、合同和续订形成端到端流程。

### M3：财务自动化

完成 14-18。预算、交易、支付、发票、会计、集成和报表可投入真实试点。

### M4：企业生产化

完成 19-22。具备安全合规、商业计费、支持后台、可观测性和生产发布能力。

## 全局验证命令

```powershell
# 后端
cd backend
python -m pytest -q
python -m ruff check app tests
python -m mypy app

# 前端
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e

# 容器与迁移
docker compose config
docker compose up -d postgres redis minio
docker compose run --rm backend alembic upgrade head
```

预期结果：所有命令退出码为 `0`，E2E 报告中无失败用例，迁移可在空数据库和已有上一版本数据库上执行。

## 2026-06-13 验证快照

- 01-22 均未达到各自完整验收清单，汇总为 `7` 个核心已验证、`12` 个部分实现、`3` 个待开发。
- Plan 19 已完成不可变审计、数据保留与删除、数据主体请求、合规控制与证据库、作用域 API 密钥、出站 Webhook 与安全基线，共 `6/7` 个任务。
- 后端全量测试 `75 passed`，Ruff 通过，Mypy 对 `140` 个源文件通过。
- 前端 TypeScript 类型检查通过，Vitest `77 passed`，Vite 生产构建通过。
- Alembic head 为 `20260612_0018`，空数据库升级集成测试通过。
- API secret 仅创建时展示且只保存哈希；Webhook secret 加密保存，签名、重试、死信和轮换重叠均有自动化测试。
- CSP、HSTS、Referrer-Policy、Permissions-Policy、request ID、CSRF 防护和日志脱敏已有自动化测试。
- CI 已配置 Python/npm 依赖审计、Gitleaks 和 Trivy 高危阻断，本地 pip-audit 与 npm audit 均为 `0` 个已知漏洞；尚不存在前端 lint、Playwright E2E、性能和 production-like staging 验收入口。

