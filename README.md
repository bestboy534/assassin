# SaaS Assassin MVP

AI 订阅账单审计 + 退订 Copilot + 节省金额看板。

## 快速启动

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

没有 OpenAI Key 时，保持 `USE_LLM=false`，系统会使用本地规则解析器跑通 MVP。

### 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

打开 `http://localhost:5173`。

## MVP 边界

做：账单文本/CSV/Apple/Stripe/PayPal 解析、订阅识别、月化金额、状态机、退订指引、LocalStorage 保存。

不做：托管账号、抓 Cookie、自动登录、自动点击退订、读取邮箱、保存原始账单、企业权限系统。


## Windows 本地启动修正版

后端启动后，`http://127.0.0.1:8000/` 会显示 API 首页；真正的前端页面在 `http://localhost:5173`。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python init_db.py
uvicorn app.main:app --reload --port 8000
```

打开：

- API 首页：http://127.0.0.1:8000/
- 健康检查：http://127.0.0.1:8000/health
- 接口文档：http://127.0.0.1:8000/docs
- 历史记录：http://127.0.0.1:8000/api/history

前端：

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

打开前端：`http://localhost:5173`

## SQLite 说明

MVP 原则仍然是不保存原始账单。当前版本只把结构化后的订阅项保存到 SQLite，便于开发阶段查看历史记录。
数据库文件默认自动创建在：`backend/data/saas_assassin.db`。

关闭数据库：把 `backend/.env` 中的 `ENABLE_DATABASE=true` 改为 `false`。
