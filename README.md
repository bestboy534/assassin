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
