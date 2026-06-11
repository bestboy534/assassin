import hashlib
import re

from .schemas import ExtractedSubscription


def normalize_key(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def make_subscription_id(item: ExtractedSubscription) -> str:
    raw = "|".join(
        [
            normalize_key(item.software_name),
            normalize_key(item.merchant_name),
            f"{item.amount:.2f}",
            item.currency.upper().strip(),
            item.billing_cycle,
            item.transaction_date or "",
            item.source_type,
        ]
    )
    return "sub_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
