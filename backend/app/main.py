import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .privacy import trim_input
from .schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from .llm_extractor import extract_subscriptions
from .service import to_subscription_item
settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)
app = FastAPI(title="SaaS Assassin API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    if len(req.raw_text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail=f"Input too long. Max {settings.max_input_chars} characters.")
    trimmed = trim_input(req.raw_text, settings.max_input_chars)
    logger.info("Analyze request input_length=%s source_hint=%s use_llm=%s", len(trimmed), req.source_hint, settings.use_llm)
    payload = extract_subscriptions(trimmed, source_hint=req.source_hint)
    items = [to_subscription_item(item) for item in payload.items]
    logger.info("Analyze response items_count=%s", len(items))
    return AnalyzeResponse(items=items)
