# SaaS Assassin

SaaS Assassin 是一个中文企业软件管理平台原型，面向财务、IT、采购和安全团队，覆盖从应用目录、账单审计、采购审批、合同续订、供应商风险、预算交易、支付、发票会计、集成同步到报表导出的工作台闭环。

公开网页端参考 Cledara 的信息架构与交互方式实现，品牌文字位保留为空，后续可替换为正式产品名。

## 当前方案

- 前端：React 18、TypeScript、Vite、React Router、Vitest、Testing Library。
- 后端：FastAPI、SQLAlchemy、Alembic、Pydantic、Pytest、Ruff、Mypy。
- 数据：SQLite 用于本地开发和测试；迁移结构按 PostgreSQL 生产形态组织。
- 交互：公开站为中文页面；登录后进入多租户企业工作台。
- 质量门禁：后端测试、ruff、mypy；前端 typecheck、vitest、build。

## 计划完成状态

状态基于 2026-06-12 的代码、迁移、测试和页面复核。`docs/superpowers/plans/*.md` 中的 checkbox 是执行清单模板，当前未逐项勾选，不能单独代表真实完成度。

| 编号 | 计划 | 当前状态 | 验证依据 |
|---|---|---|---|
| 01 | 工程基线 | 已落地 | 前后端验证脚本、测试与类型检查配置存在 |
| 02 | 前端架构与公开站 | 已落地 | 路由、中文公开页、导航与品牌留空组件 |
| 03 | CMS、SEO 与线索表单 | 已落地 | 公开站内容模型、预约/联系表单与页面路由 |
| 04 | 数据与异步基础设施 | 已落地 | Alembic、数据库、Job、Outbox、文件存储测试 |
| 05 | 身份认证与账号安全 | 已落地 | 注册、登录、会话与组织上下文测试 |
| 06 | 组织、多租户与 RBAC | 已落地 | 组织、成员、角色与租户隔离服务 |
| 07 | 工作台外壳与全局能力 | 已落地 | `/app/:org/*` 工作台导航与总览 |
| 08 | 应用目录、发现与席位 | 已落地 | applications 领域、迁移、API 与页面流程 |
| 09 | AI 账单审计 | 已落地 | audit_ai 领域、解析确认与账单审计页面 |
| 10 | 节省机会与优化项目 | 已落地 | savings 领域、验证节省和工作台页面 |
| 11 | 采购申请与审批 | 已落地 | procurement 领域、审批流程和工作台页面 |
| 12 | 供应商与风险 | 已落地 | vendors 领域、风险解释与接受流程 |
| 13 | 合同、续订与谈判 | 已落地 | contracts 领域、签署版本和续订提醒 |
| 14 | 预算与交易 | 已落地 | spend 领域、预算、交易、分摊和月结 |
| 15 | 支付与虚拟卡 | 已落地 | payments 领域、虚拟卡、限额和 Webhook 处理 |
| 16 | 发票与会计自动化 | 已落地 | accounting 领域、OCR 结果、匹配、会计导出 |
| 17 | 集成平台 | 已落地 | integrations 领域、连接、同步、诊断和适配器 |
| 18 | 报表与导出 | 已落地 | reports 领域、指标查询、保存报表、快照、XLSX 导出、订阅和工作台页面 |
| 19 | 安全、合规与隐私 | 待开发 | 尚无独立 security/compliance/privacy 后端业务域 |
| 20 | 套餐、计费与权益 | 待开发 | 尚无 billing/entitlements 后端业务域 |
| 21 | 支持、状态页与管理后台 | 待开发 | 目前仅有公开支持页面，缺少工单/后台业务域 |
| 22 | 可观测性与生产发布 | 待开发 | 尚未接入追踪、SLO、告警、灾备和发布门禁 |

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
