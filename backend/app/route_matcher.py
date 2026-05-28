import json
from pathlib import Path
from urllib.parse import quote_plus
DATA_DIR = Path(__file__).parent / "data"

def load_routes() -> dict:
    return json.loads((DATA_DIR / "cancel_routes.json").read_text(encoding="utf-8"))

def find_route(software_name: str, merchant_name: str | None = None) -> dict:
    haystack = f"{software_name} {merchant_name or ''}".lower()
    for key, route in load_routes().items():
        names = [key, route.get("software_name", ""), route.get("vendor", "")] + route.get("aliases", [])
        if any(name and name.lower() in haystack for name in names):
            return route
    return {}

def fallback_search_url(software_name: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(f"how to cancel {software_name} subscription")
