import json, logging
import re
from pydantic import ValidationError
from .config import get_settings
from .privacy import redact_sensitive_text
from .schemas import ExtractedSubscriptionsPayload
from .heuristic_extractor import extract_with_heuristics
from openai import OpenAI
from typing import Any

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

def extract_json_form_text(text: str) -> Any:
    """
    兼容模型返回:
    1. '''json...
    2. {"items":[...]}
    3. [...]
    """
    cleaned =text.strip()

    if cleaned.startswith("'''"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"'''$", "", cleaned).strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    #兜底：从文本中提取第一个json作为数组或者对象
    array_match = re.search(r"\[[\s\S]*\]", cleaned)
    if array_match:
        return json.loads(array_match.group(0))

    object_match = re.search(r"\{[\s\S]*\}", cleaned)
    if object_match:
        return json.loads(object_match.group(0))

    raise ValueError("LLM response is not valid JSON")

def normalize_llm_item(raw: dict, default_source_hint: str = "unknown") -> dict:
    """
    把 MIMO 可能返回的不标准字段清洗成 Pydantic 能接收的结构。
    """
    item = dict(raw)

    # amount: "$20.00" -> 20.0
    amount = item.get("amount", 0)
    if isinstance(amount, str):
        amount = amount.replace("$", "").replace(",", "").strip()
        try:
            item["amount"] = float(amount)
        except ValueError:
            item["amount"] = 0.0

    # confidence: "90%" -> 0.9
    confidence = item.get("confidence", 0.7)
    if isinstance(confidence, str):
        confidence = confidence.replace("%", "").strip()
        try:
            confidence = float(confidence)
            if confidence > 1:
                confidence = confidence / 100
        except ValueError:
            confidence = 0.7
    item["confidence"] = max(0.0, min(float(confidence), 1.0))

    # billing_cycle 映射
    cycle_map = {
        "month": "monthly",
        "monthly": "monthly",
        "月": "monthly",
        "月付": "monthly",
        "每月": "monthly",
        "year": "yearly",
        "yearly": "yearly",
        "annual": "yearly",
        "annually": "yearly",
        "年": "yearly",
        "年付": "yearly",
        "每年": "yearly",
        "week": "weekly",
        "weekly": "weekly",
        "周": "weekly",
        "quarter": "quarterly",
        "quarterly": "quarterly",
        "季": "quarterly",
        "unknown": "unknown",
    }
    cycle = str(item.get("billing_cycle", "unknown")).lower().strip()
    item["billing_cycle"] = cycle_map.get(cycle, "unknown")

    # source_type 映射
    source_map = {
        "csv": "csv",
        "credit_card_csv": "csv",
        "credit_card": "csv",
        "bank_csv": "csv",
        "apple": "apple_mail",
        "apple_mail": "apple_mail",
        "stripe": "stripe_mail",
        "stripe_mail": "stripe_mail",
        "paypal": "paypal_mail",
        "paypal_mail": "paypal_mail",
        "google": "google_play",
        "google_play": "google_play",
        "unknown": "unknown",
    }
    source = str(item.get("source_type") or default_source_hint or "unknown").lower().strip()
    item["source_type"] = source_map.get(source, "unknown")

    # risk_type 映射
    risk_map = {
        "idle": "possible_idle",
        "possible_idle": "possible_idle",
        "duplicate": "possible_duplicate",
        "possible_duplicate": "possible_duplicate",
        "hidden": "hidden_fee",
        "hidden_fee": "hidden_fee",
        "api": "api_usage",
        "api_usage": "api_usage",
        "apple": "apple_unresolved",
        "apple_unresolved": "apple_unresolved",
        "none": "none",
        "unknown": "none",
    }
    risk = str(item.get("risk_type", "none")).lower().strip()
    item["risk_type"] = risk_map.get(risk, "none")

    # currency 标准化
    currency = str(item.get("currency", "USD")).upper().strip()
    currency_alias = {
        "美元": "USD",
        "美金": "USD",
        "$": "USD",
        "人民币": "CNY",
        "元": "CNY",
        "台币": "TWD",
        "新台币": "TWD",
        "港币": "HKD",
    }
    item["currency"] = currency_alias.get(currency, currency)

    # 字段兜底
    item["software_name"] = item.get("software_name") or item.get("name") or item.get("software") or "Unknown SaaS"
    item["merchant_name"] = item.get("merchant_name") or item.get("merchant") or item.get("vendor")
    item["transaction_date"] = item.get("transaction_date") or item.get("date")
    item["evidence"] = item.get("evidence") or "LLM extracted from billing text."
    item["needs_user_confirmation"] = bool(item.get("needs_user_confirmation", True))

    return item


def normalize_llm_payload(payload: Any, default_source_hint: str = "unknown") -> list[dict]:
    """
    兼容：
    1. [...]
    2. {"items": [...]}
    3. {"subscriptions": [...]}
    4. {"data": [...]}
    """
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            raw_items = payload["items"]
        elif isinstance(payload.get("subscriptions"), list):
            raw_items = payload["subscriptions"]
        elif isinstance(payload.get("data"), list):
            raw_items = payload["data"]
        else:
            raw_items = [payload]
    elif isinstance(payload, list):
        raw_items = payload
    else:
        raw_items = []

    return [
        normalize_llm_item(x, default_source_hint=default_source_hint)
        for x in raw_items
        if isinstance(x, dict)
    ]

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
            logger.warning(
                "LLM extraction failed attempt=%s error=%s",
                attempt,
                type(exc).__name__,
                str(exc)[:2000],
            )
    logger.error("LLM failed after retries, fallback heuristic: %s", last_error)
    return ExtractedSubscriptionsPayload(items=extract_with_heuristics(safe_text, source_hint))
