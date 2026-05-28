import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .privacy import trim_input
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, HistoryListResponse, HistoryDetailResponse
from .llm_extractor import extract_subscriptions
from .service import to_subscription_item
from .database import init_db, save_analysis_run, list_history_runs, get_history_run

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)
app = FastAPI(title="SaaS Assassin API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
    )

@app.on_event("startup")
def startup() -> None:
    if settings.enable_database:
        init_db(settings.sqlite_path)
        logger.info("SQLite database initialized at %s", settings.sqlite_path)

@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!doctype html>
    <html lang=\"zh-CN\">
      <head><meta charset=\"utf-8\"><title>SaaS Assassin API</title></head>
      <body style=\"font-family: system-ui; max-width: 760px; margin: 40px auto; line-height: 1.7;\">
        <h1>🗡️ SaaS Assassin API 已启动</h1>
        <p>你现在访问的是后端 API 服务，不是前端页面。</p>
        <ul>
          <li><a href=\"/health\">/health</a>：健康检查</li>
          <li><a href=\"/docs\">/docs</a>：FastAPI 接口文档</li>
          <li><code>POST /api/analyze</code>：账单解析接口</li>
          <li><a href=\"/api/history\">/api/history</a>：最近解析记录，开启 SQLite 后可用</li>
        </ul>
        <p>前端默认地址：<code>http://localhost:5173</code></p>
      </body>
    </html>
    """

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(database=(settings.sqlite_path if settings.enable_database else "disabled"))

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    if len(req.raw_text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail=f"Input too long. Max {settings.max_input_chars} characters.")
    trimmed = trim_input(req.raw_text, settings.max_input_chars)
    logger.info("Analyze request input_length=%s source_hint=%s use_llm=%s", len(trimmed), req.source_hint, settings.use_llm)
    payload = extract_subscriptions(trimmed, source_hint=req.source_hint)
    items = [to_subscription_item(item) for item in payload.items]
    run_id = None
    if settings.enable_database:
        # 不保存原始账单，只保存结构化订阅项，便于开发阶段验证历史记录。
        run_id = save_analysis_run(settings.sqlite_path, req.source_hint, items)
    logger.info("Analyze response items_count=%s run_id=%s", len(items), run_id)
    return AnalyzeResponse(items=items, run_id=run_id)

@app.get("/api/history", response_model=HistoryListResponse)
def history(limit: int = 20) -> HistoryListResponse:
    if not settings.enable_database:
        raise HTTPException(status_code=400, detail="Database is disabled. Set ENABLE_DATABASE=true.")
    return HistoryListResponse(items=list_history_runs(settings.sqlite_path, limit=limit))

@app.get("/api/history/{run_id}", response_model=HistoryDetailResponse)
def history_detail(run_id: str) -> HistoryDetailResponse:
    if not settings.enable_database:
        raise HTTPException(status_code=400, detail="Database is disabled. Set ENABLE_DATABASE=true.")
    result = get_history_run(settings.sqlite_path, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run, items = result
    return HistoryDetailResponse(run=run, items=items)
