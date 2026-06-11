import re
from typing import cast

from .schemas import BillingCycle, ExtractedSubscription, RiskType, SourceType

AMOUNT_RE = re.compile(
    r"(?P<currency>USD|HKD|TWD|CNY|RMB|EUR|GBP|\$|¥|€|£)?\s*(?P<amount>\d+(?:\.\d{1,2})?)", re.I
)
DATE_RE = re.compile(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2})\b")


def normalize_currency(raw: str | None, fallback: str = "USD") -> str:
    if not raw:
        return fallback
    return {"$": "USD", "¥": "CNY", "€": "EUR", "£": "GBP", "RMB": "CNY"}.get(
        raw.upper(), raw.upper()
    )


def guess_cycle(text: str) -> BillingCycle:
    lower = text.lower()
    if any(x in lower for x in ["year", "annual", "yearly", "包年"]):
        return "yearly"
    if any(x in lower for x in ["quarter", "季度"]):
        return "quarterly"
    if any(x in lower for x in ["week", "weekly"]):
        return "weekly"
    if any(x in lower for x in ["month", "monthly", "subscription", "subscrip", "包月"]):
        return "monthly"
    return "unknown"


def classify_line(
    line: str,
    source_hint: SourceType = "unknown",
) -> ExtractedSubscription | None:
    lower = line.lower()
    software = merchant = None
    risk = "possible_idle"
    confidence = 0.7
    currency = "USD"
    if "openai" in lower and "api" in lower and "chatgpt" not in lower:
        software, merchant, risk, confidence = "OpenAI API", "OPENAI", "api_usage", 0.85
    elif "chatgpt" in lower or ("openai" in lower and "subscrip" in lower):
        software, merchant, confidence = "ChatGPT Plus", "OPENAI", 0.9
    elif "anthropic" in lower or "claude" in lower:
        software, merchant, confidence = "Claude Pro", "ANTHROPIC PBC", 0.9
    elif "midjourney" in lower:
        software, merchant, confidence = "Midjourney", "MIDJOURNEY", 0.9
    elif "apple.com/bill" in lower or "apple itunes" in lower:
        software, merchant, risk, confidence = (
            "Apple App Store Unknown Subscription",
            "APPLE.COM/BILL",
            "apple_unresolved",
            0.95,
        )
    elif "github" in lower and "copilot" in lower:
        software, merchant, confidence = "GitHub Copilot", "GITHUB", 0.85
    elif "github" in lower:
        software, merchant, risk, confidence = "GitHub", "GITHUB", "possible_duplicate", 0.55
    elif "cursor" in lower:
        software, merchant, confidence = "Cursor", "CURSOR", 0.85
    elif "canva" in lower:
        software, merchant, confidence = "Canva", "CANVA", 0.85
    elif "notion" in lower:
        software, merchant, confidence = "Notion", "NOTION", 0.85
    elif "perplexity" in lower:
        software, merchant, confidence = "Perplexity", "PERPLEXITY", 0.85
    elif "runway" in lower:
        software, merchant, confidence = "Runway", "RUNWAY", 0.85
    elif "gamma" in lower:
        software, merchant, confidence = "Gamma", "GAMMA", 0.85
    if not software:
        return None
    matches = list(AMOUNT_RE.finditer(line))
    amount = None
    for m in reversed(matches):
        val = float(m.group("amount"))
        if val > 0:
            amount = val
            if m.group("currency"):
                currency = normalize_currency(m.group("currency"))
            break
    if amount is None:
        return None
    for token in ["USD", "HKD", "TWD", "CNY", "EUR", "GBP"]:
        if token.lower() in lower:
            currency = token
    dm = DATE_RE.search(line)
    date = dm.group(1).replace("/", "-") if dm else None
    allowed = {"csv", "apple_mail", "stripe_mail", "paypal_mail", "google_play"}
    return ExtractedSubscription(
        software_name=software,
        merchant_name=merchant,
        amount=amount,
        currency=currency,
        billing_cycle=guess_cycle(line),
        transaction_date=date,
        source_type=source_hint if source_hint in allowed else "unknown",
        risk_type=cast(RiskType, risk),
        confidence=confidence,
        evidence=f"Matched billing text: {line[:160]}",
        needs_user_confirmation=True,
    )


def extract_with_heuristics(
    raw_text: str,
    source_hint: SourceType = "unknown",
) -> list[ExtractedSubscription]:
    items = [x for line in raw_text.splitlines() if (x := classify_line(line.strip(), source_hint))]
    seen: set[tuple[str, str, float, str, str]] = set()
    unique: list[ExtractedSubscription] = []
    for item in items:
        key = (
            item.software_name.lower(),
            item.merchant_name or "",
            item.amount,
            item.currency,
            item.transaction_date or "",
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
