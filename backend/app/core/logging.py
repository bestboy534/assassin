import copy
import logging
import re
from collections.abc import Mapping
from typing import Any

from app.privacy import CARD_RE

from .security import current_request_id

REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = (
    "authorization",
    "card",
    "cookie",
    "credential",
    "cvv",
    "passphrase",
    "password",
    "raw_bill",
    "raw_text",
    "secret",
    "token",
)
AUTHORIZATION_RE = re.compile(
    r"(?i)\b(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"
)
COOKIE_RE = re.compile(r"(?i)\b((?:set-)?cookie\s*[:=]\s*)[^\r\n,;]+")
RAW_DATA_RE = re.compile(
    r"(?i)\b(raw[_-]?(?:text|bill)\s*[:=]\s*)[^,;\r\n]+"
)
KEY_VALUE_RE = re.compile(
    r"(?i)\b("
    r"password|passphrase|api[_-]?token|access[_-]?token|refresh[_-]?token|"
    r"token|secret|credential|cvv|card(?:[_-]?number)?"
    r")(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^,\s;]+)"
)
DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
)


class SecureLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        safe_record = copy.copy(record)
        safe_record.request_id = getattr(record, "request_id", current_request_id())
        safe_record.msg = redact_log_value(record.msg)
        safe_record.args = redact_log_value(record.args)
        safe_record.exc_text = None
        return redact_log_text(super().format(safe_record))


def configure_secure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper())
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    formatter = SecureLogFormatter(DEFAULT_LOG_FORMAT)
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def redact_log_value(value: Any, *, key: str = "") -> Any:
    if key and _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            nested_key: redact_log_value(nested_value, key=str(nested_key))
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_log_value(item) for item in value)
    if isinstance(value, list):
        return [redact_log_value(item) for item in value]
    if isinstance(value, str):
        return redact_log_text(value)
    return value


def redact_log_text(value: str) -> str:
    redacted = AUTHORIZATION_RE.sub(rf"\1{REDACTED}", value)
    redacted = COOKIE_RE.sub(rf"\1{REDACTED}", redacted)
    redacted = RAW_DATA_RE.sub(rf"\1{REDACTED}", redacted)
    redacted = KEY_VALUE_RE.sub(rf"\1\2{REDACTED}", redacted)
    return CARD_RE.sub("[REDACTED_CARD]", redacted)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
