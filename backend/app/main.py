import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .core.database import get_database
from .database import get_history_run, list_history_runs, save_analysis_run
from .domains.applications.router import router as applications_router
from .domains.audit_ai.router import router as billing_audit_router
from .domains.contracts.router import contracts_router, renewals_router
from .domains.files.router import router as files_router
from .domains.identity.router import router as identity_router
from .domains.jobs.router import router as jobs_router
from .domains.organizations.router import router as organizations_router
from .domains.procurement.router import (
    approval_tasks_router,
    purchase_requests_router,
)
from .domains.spend.router import router as spend_router
from .domains.vendors.router import risk_findings_router, vendors_router
from .infrastructure.queue.client import JobQueue, build_queue
from .infrastructure.storage.base import ObjectStorage
from .infrastructure.storage.factory import build_storage
from .llm_extractor import extract_subscriptions
from .privacy import trim_input
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ComponentHealth,
    HealthResponse,
    HistoryDetailResponse,
    HistoryListResponse,
    ReadinessResponse,
)
from .service import to_subscription_item

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.queue = build_queue(settings)
    app.state.storage = build_storage(settings)
    database = get_database()
    if settings.enable_database and settings.auto_create_schema:
        await database.create_schema()
        logger.info("Local database schema is ready")
    yield
    await cast(JobQueue, app.state.queue).close()
    await database.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router, prefix=settings.api_v1_prefix)
app.include_router(files_router, prefix=settings.api_v1_prefix)
app.include_router(identity_router, prefix=settings.api_v1_prefix)
app.include_router(organizations_router, prefix=settings.api_v1_prefix)
app.include_router(applications_router, prefix=settings.api_v1_prefix)
app.include_router(billing_audit_router, prefix=settings.api_v1_prefix)
app.include_router(purchase_requests_router, prefix=settings.api_v1_prefix)
app.include_router(approval_tasks_router, prefix=settings.api_v1_prefix)
app.include_router(contracts_router, prefix=settings.api_v1_prefix)
app.include_router(renewals_router, prefix=settings.api_v1_prefix)
app.include_router(vendors_router, prefix=settings.api_v1_prefix)
app.include_router(risk_findings_router, prefix=settings.api_v1_prefix)
app.include_router(spend_router, prefix=settings.api_v1_prefix)


async def optional_session() -> AsyncIterator[AsyncSession | None]:
    if not settings.enable_database:
        yield None
        return
    database = get_database()
    async with database.session_factory() as session:
        yield session


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!doctype html>
    <html lang="zh-CN">
      <head><meta charset="utf-8"><title>SaaS Assassin API</title></head>
      <body style="font-family: system-ui; max-width: 760px; margin: 40px auto; line-height: 1.7;">
        <h1>SaaS Assassin API 已启动</h1>
        <p>你现在访问的是后端 API 服务，不是前端页面。</p>
        <ul>
          <li><a href="/health">/health</a>：存活检查</li>
          <li><a href="/ready">/ready</a>：依赖就绪检查</li>
          <li><a href="/docs">/docs</a>：FastAPI 接口文档</li>
          <li><code>POST /api/analyze</code>：账单解析接口</li>
          <li><a href="/api/history">/api/history</a>：最近解析记录</li>
        </ul>
        <p>前端默认地址：<code>http://localhost:5173</code></p>
      </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        database="configured" if settings.enable_database else "disabled",
    )


@app.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    database_status = ComponentHealth(status="disabled")
    if settings.enable_database:
        database_status = ComponentHealth(status="ok" if await get_database().ping() else "error")

    queue_state = getattr(request.app.state, "queue", None)
    queue = cast(JobQueue, queue_state) if queue_state is not None else build_queue(settings)
    queue_status = ComponentHealth(status="ok" if await queue.ping() else "error")
    storage_state = getattr(request.app.state, "storage", None)
    storage = (
        cast(ObjectStorage, storage_state) if storage_state is not None else build_storage(settings)
    )
    storage_status = ComponentHealth(status="ok" if storage.ping() else "error")
    components = {
        "database": database_status,
        "queue": queue_status,
        "storage": storage_status,
    }
    is_ready = all(component.status != "error" for component in components.values())
    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ReadinessResponse(
                status="not_ready",
                components=components,
            ).model_dump(),
        )
    return ReadinessResponse(status="ready", components=components)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    req: AnalyzeRequest,
    session: Annotated[AsyncSession | None, Depends(optional_session)],
) -> AnalyzeResponse:
    if len(req.raw_text) > settings.max_input_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input too long. Max {settings.max_input_chars} characters.",
        )
    trimmed = trim_input(req.raw_text, settings.max_input_chars)
    logger.info(
        "Analyze request input_length=%s source_hint=%s use_llm=%s",
        len(trimmed),
        req.source_hint,
        settings.use_llm,
    )
    payload = extract_subscriptions(trimmed, source_hint=req.source_hint)
    items = [to_subscription_item(item) for item in payload.items]
    run_id = None
    if session is not None:
        run_id = await save_analysis_run(session, req.source_hint, items)
    logger.info("Analyze response items_count=%s run_id=%s", len(items), run_id)
    return AnalyzeResponse(items=items, run_id=run_id)


@app.get("/api/history", response_model=HistoryListResponse)
async def history(
    session: Annotated[AsyncSession | None, Depends(optional_session)],
    limit: int = 20,
) -> HistoryListResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database is disabled. Set ENABLE_DATABASE=true.",
        )
    return HistoryListResponse(items=await list_history_runs(session, limit=limit))


@app.get("/api/history/{run_id}", response_model=HistoryDetailResponse)
async def history_detail(
    run_id: str,
    session: Annotated[AsyncSession | None, Depends(optional_session)],
) -> HistoryDetailResponse:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database is disabled. Set ENABLE_DATABASE=true.",
        )
    result = await get_history_run(session, run_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    run, items = result
    return HistoryDetailResponse(run=run, items=items)
