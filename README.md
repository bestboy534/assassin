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

当前执行点：Plan 19 已完成任务 1-6，下一模块为任务 7“前端合规与隐私页面”。

## 计划完成状态

状态基于 2026-06-13 对代码、迁移、路由、页面和自动化测试的逐项复核。这里区分：

- `核心已验证`：已有可运行的主要业务闭环，但尚未完成 plan 内全部生产化验收。
- `部分实现`：只有部分任务或简化流程，不能视为计划完成。
- `未开始`：缺少对应业务域和主要交付。

严格按 `docs/superpowers/plans/*.md` 的完整 Definition of Done，当前 `22` 个计划均未达到“全部完成”；汇总为 `7` 个核心已验证、`12` 个部分实现、`3` 个未开始。计划文档 checkbox 均仍为执行模板，不能用勾选数量替代代码验收。

| 编号 | 计划 | 实现进度 | 尚缺的关键验收 |
|---|---|---|---|
| 01 | 工程基线 | 部分实现 | 已有后端 CI 和前后端测试；缺前端 lint、Playwright E2E 与统一全仓验证入口 |
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
| 19 | 安全、合规与隐私 | 部分实现（6/7） | 审计、保留、DSR、合规控制/证据库、安全事件、作用域 API Key、出站 Webhook 和安全基线已实现；缺前端合规与隐私页面 |
| 20 | 套餐、计费与权益 | 未开始 | 缺 billing/entitlements 业务域、订阅生命周期、用量和账单门户 |
| 21 | 支持、状态页与管理后台 | 未开始 | 只有公开支持展示页；缺工单、诊断授权、状态事件和平台后台 |
| 22 | 可观测性与生产发布 | 未开始 | 缺结构化追踪、SLO、告警、性能门禁、灾备、发布流水线和生产验收 |

### 本次复核结果

- 后端：`75 passed`，Ruff 通过，Mypy 对 `140` 个源文件通过。
- 前端：TypeScript 类型检查通过，Vitest `77 passed`，Vite 生产构建通过。
- 迁移：当前 head 为 `20260612_0018`，迁移集成测试通过；新增 API 密钥、Webhook 端点和 Webhook 投递表。
- 安全接口：API secret 仅创建时返回，数据库只保存哈希；Webhook secret 加密保存，并已验证 HMAC 签名、重试、死信和轮换重叠。
- 安全基线：统一设置 CSP、HSTS、Referrer-Policy、Permissions-Policy、request ID 和跨站 Cookie 请求防护；API 与 worker 日志统一脱敏。
- CI 安全门禁：已配置 Python/npm 依赖审计、Gitleaks 秘密扫描和 Trivy 容器高危漏洞阻断；本地 pip-audit 与 npm audit 均为 `0` 个已知漏洞。
- 计划清单：01-22 均为 `checked=0`；这是模板状态，不代表实现为零。
- 未执行：仓库目前没有前端 lint、Playwright E2E、性能和 production-like staging 验收脚本；新增 CI 安全门禁仍需远程运行结果作为发布证据。

本次对 22 个计划逐项对照了目标、任务和完成验收，并交叉检查业务域、迁移、API 路由、前端路由、测试文件、CI 与 package scripts。结论是：当前没有计划达到完整 Definition of Done，状态汇总仍为 `7` 个核心已验证、`12` 个部分实现、`3` 个未开始。

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

当前计划文档 checkbox 统计结果为 01-22 全部 `checked=0`，因此完成度以本 README 的“计划完成状态”和实际验证命令为准。
