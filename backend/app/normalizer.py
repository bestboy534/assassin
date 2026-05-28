import json
from pathlib import Path
from .schemas import ExtractedSubscription
DATA_DIR = Path(__file__).parent / "data"

def load_fx_rates() -> dict[str, float]:
    return json.loads((DATA_DIR / "fx_rates.json").read_text(encoding="utf-8"))

def normalize_amount_to_usd(amount: float, currency: str) -> float:
    rate = load_fx_rates().get(currency.upper().strip(), 1.0)
    return round(amount * rate, 2)

def monthly_cost(amount_usd: float, cycle: str) -> float:
    if cycle == "yearly": return round(amount_usd / 12, 2)
    if cycle == "quarterly": return round(amount_usd / 3, 2)
    if cycle == "weekly": return round(amount_usd * 4.33, 2)
    return round(amount_usd, 2)

def default_status(item: ExtractedSubscription) -> str:
    merchant = (item.merchant_name or "").lower()
    if item.risk_type == "apple_unresolved" or "apple.com/bill" in merchant:
        return "apple_unresolved"
    return "need_confirm"
