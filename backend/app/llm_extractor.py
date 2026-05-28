import json, logging
from pydantic import ValidationError
from .config import get_settings
from .privacy import redact_sensitive_text
from .schemas import ExtractedSubscriptionsPayload
from .heuristic_extractor import extract_with_heuristics
from openai import OpenAI
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
你是企业 SaaS / AI 工具订阅账单审计助手。只提取软件、SaaS、AI 工具、订阅服务相关扣费。
规则：
1. 过滤餐饮、交通、普通购物、酒店、机票。
2. OPENAI *API 是 API 按量消耗，risk_type=api_usage，不要误判为 ChatGPT Plus。
3. APPLE.COM/BILL 或 APL* APPLE ITUNES STORE 不能猜具体 App，software_name=Apple App Store Unknown Subscription，risk_type=apple_unresolved。
4. 不要生成 id、cancel_url、monthly_cost_usd，这些由系统生成。
5. 不确定时降低 confidence，并将 needs_user_confirmation=true。
6. billing_cycle 只能是 monthly/yearly/weekly/quarterly/unknown。
"""

def _schema_for_openai() -> dict:
    return ExtractedSubscriptionsPayload.model_json_schema()

def extract_subscriptions(raw_text: str, source_hint="unknown") -> ExtractedSubscriptionsPayload:
    settings = get_settings()
    safe_text = redact_sensitive_text(raw_text)
    if not settings.use_llm or not settings.openai_api_key:
        return ExtractedSubscriptionsPayload(items=extract_with_heuristics(safe_text, source_hint))
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed, fallback to heuristic extractor")
        return ExtractedSubscriptionsPayload(items=extract_with_heuristics(safe_text, source_hint))

    client_kwargs = {
        "api_key": settings.openai_api_key,
    }

    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url

    client = OpenAI(**client_kwargs)

    user_prompt = f"source_hint: {source_hint}\n\n待分析文本：\n{safe_text}"
    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":user_prompt}],
                temperature=0,
                response_format={"type":"json_schema","json_schema":{"name":"subscription_extraction","schema":_schema_for_openai(),"strict":True}},
            )
            content = response.choices[0].message.content or "{}"
            return ExtractedSubscriptionsPayload.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            last_error = exc
            logger.warning("LLM extraction failed attempt=%s error=%s", attempt + 1, type(exc).__name__)
    logger.error("LLM failed after retries, fallback heuristic: %s", last_error)
    return ExtractedSubscriptionsPayload(items=extract_with_heuristics(safe_text, source_hint))
