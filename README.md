# SaaS Assassin

SaaS Assassin 是一个中文企业软件管理平台原型，面向财务、IT、采购和安全团队，覆盖从应用目录、账单审计、采购审批、合同续订、供应商风险、预算交易、支付、发票会计、集成同步到报表导出的工作台闭环。

公开网页端参考 Cledara 的信息架构与交互方式实现，品牌文字位保留为空，后续可替换为正式产品名。

## 当前方案

- 前端：React 18、TypeScript、Vite、React Router、Vitest、Testing Library。
- 后端：FastAPI、SQLAlchemy、Alembic、Pydantic、Pytest、Ruff、Mypy。
- 数据：SQLite 用于本地开发和测试；迁移结构按 PostgreSQL 生产形态组织。
- 交互：公开站为中文页面；登录后进入多租户企业工作台。
- 质量门禁：后端测试、ruff、mypy；前端 typecheck、vitest、build。

## 全面完成方案

后续开发按依赖和风险分为四个波次，每个波次都必须同时交付代码、迁移、权限边界、审计、自动化测试和中文页面，不能只增加静态页面或演示数据。

| 波次 | 计划范围 | 主要目标 | 退出条件 |
|---|---|---|---|
| A：补齐工程门禁 | 01、02 | 前端 lint、Playwright 桌面/移动 E2E、可访问性检查、统一全仓验证命令 | 干净检出环境可一条命令完成前后端、迁移、浏览器测试 |
| B：补齐核心业务缺口 | 03、05-09、11-13、17 | CMS 与线索、完整账号安全、RBAC、搜索通知待办、席位与访问生命周期、文件审计、版本化审批、供应商证据、合同谈判、真实集成适配器 | Alpha/Beta 主流程具备权限、审计、失败恢复和端到端测试 |
| C：企业商业化 | 19、20、21 | 完成 API Key/Webhook、安全基线、合规前端、套餐计费、权益、支持工单、状态页和平台后台 | 企业管理、商业计费和受控支持流程可在试点组织运行 |
| D：生产发布 | 22，并复验 04、10、14-18 | 结构化追踪、SLO、告警、性能、安全扫描、备份恢复、灰度发布和 production-like staging | 全局 Definition of Done 与发布证据全部通过 |

当前执行点：Plan 19 的任务 1-7 与 Plan 20 的任务 1-6 已全部交付并通过本地验证；Plan 21 已完成任务 1-4“支持、状态页与受控平台后台”，下一模块为任务 5“全局目录与规则管理”。

## 计划完成状态

状态基于 2026-06-15 对代码、迁移、路由、页面和自动化测试的逐项复核。这里区分：

- `核心已验证`：已有可运行的主要业务闭环，但尚未完成 plan 内全部生产化验收。
- `部分实现`：只有部分任务或简化流程，不能视为计划完成。
- `未开始`：缺少对应业务域和主要交付。

严格按 `docs/superpowers/plans/*.md` 的完整 Definition of Done，当前 `22` 个计划仍未完成全局生产验收；汇总为 `9` 个核心已验证、`12` 个部分实现、`1` 个未开始。计划文档 checkbox 是任务执行证据之一，但仍须与代码、迁移和自动化验收交叉核对。

| 编号 | 计划 | 实现进度 | 尚缺的关键验收 |
|---|---|---|---|
| 01 | 工程基线 | 部分实现 | 已有后端 CI、前后端测试和 Plan 19 Playwright E2E；缺前端 lint、公开站桌面/移动 E2E、可访问性检查与统一全仓验证入口 |
| 02 | 前端架构与公开站 | 核心已验证 | 路由、中文公开页、2 秒菜单和品牌留空已测试；仍需完整浏览器与可访问性验收 |
| 03 | CMS、SEO 与线索表单 | 部分实现 | 只有静态内容页；缺 CMS 业务域、真实线索提交、CRM Outbox、sitemap/robots/RSS |
| 04 | 数据与异步基础设施 | 核心已验证 | Alembic、Job、Redis 队列、Outbox、对象存储和 Compose 已实现；仍需生产形态联调 |
| 05 | 身份认证与账号安全 | 部分实现 | 注册、登录、会话已实现；缺邮箱验证、重置、重新认证、MFA、OIDC、SSO、SCIM |
| 06 | 组织、多租户与 RBAC | 部分实现 | 组织和成员上下文已实现；缺邀请生命周期、完整权限矩阵、组织维度和全仓租户扫描 |
| 07 | 工作台外壳与全局能力 | 部分实现 | 工作台路由和总览已实现；缺全局搜索、通知中心、待办和可配置小组件 |
| 08 | 应用目录、发现与席位 | 部分实现 | 应用 CRUD 与来源模型已实现；缺合并撤销、席位使用率、入离职访问任务 |
| 09 | AI 账单审计 | 部分实现 | 文本分析运行和结果页已实现；缺完整文件流水线、人工反馈、证据回归和退订 Copilot 闭环 |
| 10 | 节省机会与优化项目 | 核心已验证 | 机会、基线、项目、实现和验证节省闭环已测试；仍需完整业务 E2E 验收 |
| 11 | 采购申请与审批 | 部分实现 | 草稿、提交、批准已实现；缺动态表单、版本化工作流、评论附件、通知和履约 |
| 12 | 供应商与风险 | 部分实现 | 供应商、评估、风险解释和接受已实现；缺问卷模板、证据认证和到期复审 |
| 13 | 合同、续订与谈判 | 部分实现 | 合同版本和续订已实现；缺完整 AI 确认、续订审批与谈判工作流 |
| 14 | 预算与交易 | 核心已验证 | 预算、交易导入、分摊、异常和月结闭环已测试；仍需大数据量与生产汇率验收 |
| 15 | 支付与虚拟卡 | 核心已验证 | Provider 契约、虚拟卡、限额和 Webhook 防重放已测试；真实支付仅可在合规供应商下启用 |
| 16 | 发票与会计自动化 | 核心已验证 | OCR 结果、确认、匹配、映射、导出和重同步闭环已测试；仍需真实 Provider 契约验收 |
| 17 | 集成平台 | 部分实现 | 连接、OAuth 状态、同步、诊断和测试适配器已实现；缺真实 Google/Microsoft、Slack/Teams、HRIS 等适配器 |
| 18 | 报表与导出 | 核心已验证 | 指标、查询、保存、快照、XLSX、订阅和前端工作区已测试；仍需异步调度与生产权限验收 |
| 19 | 安全、合规与隐私 | 核心已验证（7/7） | 7 个任务均已实现；审计、保留、DSR、合规控制/证据库、安全事件、API Key、Webhook、安全基线和中文管理页面已有自动化验证，仍需远程 CI 与 production-like staging 证据 |
| 20 | 套餐、计费与权益 | 核心已验证（6/6） | 套餐权益、试用、Provider Webhook、套餐变更、七项用量计量、中文定价页、账单设置/用量/发票页面、统一权益提示和完整浏览器账单流程均已验证；仍需真实计费 Provider 与 production-like staging 证据 |
| 21 | 支持、状态页与管理后台 | 部分实现（4/6） | 支持工单、SLA、客户授权诊断、公开状态事件和受控平台后台已验证；缺版本化全局目录与支持/后台前端 |
| 22 | 可观测性与生产发布 | 未开始 | 缺结构化追踪、SLO、告警、性能门禁、灾备、发布流水线和生产验收 |

### 本次复核结果

- 后端：`104 passed`，Ruff 通过，Mypy 对 `166` 个源文件通过。
- 前端：TypeScript 类型检查通过，Vitest `93 passed`，Playwright Chromium `7 passed`，Vite 生产构建通过。
- 迁移：当前 head 为 `20260615_0023`，迁移集成测试通过；新增用户平台角色、功能开关、邮件投递元数据和不可变平台审计表。
- 计费权益：Starter 默认限制为 5 个活跃应用；第 6 个应用由 `EntitlementService` 在后端返回稳定的 `entitlement_exceeded` 错误，组织权益覆盖与用量 `source_key` 幂等已验证。
- 订阅生命周期：注册和新增工作区在同一事务启动 14 天试用；3 天/1 天提醒使用稳定 Outbox 聚合键防重复，试用可记录原因后延期，到期进入 `trial_expired` 只读状态且不删除组织数据。
- 计费同步：新增客户、结账、账单门户和 Webhook 验签 Adapter 契约；客户、订阅、发票、付款成功/失败、退款和争议事件均在事务内同步，事件 ID 幂等且旧 `provider_version` 不会覆盖新订阅状态。
- 套餐变更：Pro 升级立即生效并计算剩余周期按比例费用；降到 Starter 默认周期末生效，预览可列出 43 个应用和 8 个成员超限，执行后原有 48 个应用和 13 个成员仍全部保留；周期末取消可撤销。
- 用量计量：统一覆盖成员、应用、存储、AI 页数、集成连接、导出行数和 API 调用；80%/100% 阈值使用稳定 Outbox 键只通知一次，硬上限写入前拒绝，软上限保留超额并告警；集成创建、文件完成上传、报表导出和 API Key 调用已接入。
- 客户账单体验：新增公共定价页，以及组织账单总览、产品用量和发票页面；支持付款失败提示、升级/降级影响预览、周期末取消与撤销、Provider 账单门户，统一展示 `entitlement_exceeded` 的中文套餐说明和升级入口。
- 账单浏览器验收：Playwright 已覆盖 14 天试用、模拟 sandbox 升级与 Webhook 激活、80% 用量阈值、发票、降级超限影响、周期末切换、取消和撤销；账单入口与后端接口同时限制为 owner、admin 和财务授权角色。
- 支持工单：新增组织隔离的工单列表、详情、消息、状态、解决和满意度接口；按支持套餐和优先级计算首次响应/解决目标，等待客户期间暂停 SLA，违约前通知使用稳定 Outbox 聚合键防重复。
- 客户授权诊断：owner/admin 可创建最长 7 天、具有明确范围和原因的 SupportGrant；支持人员只能读取获批的同步诊断元数据，每次使用均写入访问日志与不可变审计，客户撤销或授权过期后立即拒绝访问。
- 系统状态页：新增公开组件状态、事件列表和订阅接口；事件遵循 investigating、identified、monitoring、resolved 时间线，活跃事件自动降低组件状态，解决后恢复，并通过独立公开 schema 排除内部摘要和内部备注。
- 状态页浏览器验收：新增中文 `/status` 页面，展示整体可用性、组件状态、事件更新时间线和邮件订阅；Playwright 已验证桌面与 390px 移动端无横向溢出，订阅反馈可用。
- 平台管理后台：新增独立 `platform_admin` 角色和组织、用户、订阅、功能开关、任务、集成、Webhook、邮件投递、软件目录与取消路径 10 个受控 API 入口；普通组织管理员访问统一返回 403。
- 高风险后台操作：暂停组织、封禁用户、重放任务、修改套餐和启用功能开关必须提交原因、确认并实际校验当前密码；每次操作写入数据库级不可变平台审计，错误密码返回 428。
- 受控运维命令：新增 `set-platform-role --email --role --reason` 显式 CLI，用于首位平台管理员和支持角色引导；后台与 CLI 均不提供任意 SQL 入口。
- 安全接口：API secret 仅创建时返回，数据库只保存哈希；Webhook secret 加密保存，并已验证 HMAC 签名、重试、死信和轮换重叠。
- 安全基线：统一设置 CSP、HSTS、Referrer-Policy、Permissions-Policy、request ID 和跨站 Cookie 请求防护；API 与 worker 日志统一脱敏。
- CI 安全门禁：已配置 Python/npm 依赖审计、Gitleaks 秘密扫描和 Trivy 容器高危漏洞阻断；本地 pip-audit 与 npm audit 均为 `0` 个已知漏洞。
- 合规前端：新增审计、合规控制、安全事件、数据保留、API 密钥、Webhook 与个人隐私 7 个中文页面；危险操作具备影响说明、确认和结果反馈，并验证桌面/移动端无横向溢出。
- 计划清单：Plan 19 为 `checked=38, unchecked=0`，Plan 20 为 `checked=32, unchecked=0`，Plan 21 为 `checked=26, unchecked=7`，其余计划仍为 `checked=0`；勾选只代表对应项已有本地代码与验证证据。
- 未执行：仓库目前仍没有前端 lint、完整公开站/全业务 Playwright 矩阵、性能和 production-like staging 验收脚本；新增 CI 安全门禁仍需远程运行结果作为发布证据。

本次对 22 个计划逐项对照了目标、任务和完成验收，并交叉检查业务域、迁移、API 路由、前端路由、测试文件、CI 与 package scripts。结论是：Plan 19 的 7 个开发任务、Plan 20 的 6 个开发任务和 Plan 21 的前 4 个开发任务已交付，但 22 个计划仍未完成全局生产验收；状态汇总为 `9` 个核心已验证、`12` 个部分实现、`1` 个未开始。

## 本地启动

### 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

打开：

- API 首页：http://127.0.0.1:8000/
- 健康检查：http://127.0.0.1:8000/health
- 接口文档：http://127.0.0.1:8000/docs

### 前端

```powershell
cd frontend
npm install
copy .env.example .env
npm.cmd run dev
```

打开前端：http://localhost:5173

## 验证命令

### 后端

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe app
```

### 前端

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
```

### 计划状态复核

```powershell
$files = Get-ChildItem docs\superpowers\plans -Filter '*.md' |
  Where-Object { $_.Name -match '^\d{2}-' } |
  Sort-Object Name

foreach ($file in $files) {
  $lines = Get-Content -Encoding UTF8 -LiteralPath $file.FullName
  $done = ($lines | Select-String -Pattern '^- \[[xX]\]').Count
  $todo = ($lines | Select-String -Pattern '^- \[ \]').Count
  "{0}: checked={1}, unchecked={2}" -f $file.Name, $done, $todo
}
```

当前计划文档 checkbox 统计结果为 Plan 19 `checked=38, unchecked=0`、Plan 20 `checked=32, unchecked=0`、Plan 21 `checked=26, unchecked=7`，其余计划 `checked=0`；完成度以本 README 的“计划完成状态”、代码交付和实际验证命令共同为准。
