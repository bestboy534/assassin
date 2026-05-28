import re
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
LONG_NUMBER_RE = re.compile(r"\b\d{10,}\b")

def redact_sensitive_text(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = CARD_RE.sub("[REDACTED_CARD]", text)
    text = LONG_NUMBER_RE.sub("[REDACTED_NUMBER]", text)
    return text

def trim_input(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars]
