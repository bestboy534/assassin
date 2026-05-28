import json, pathlib, httpx
ROOT = pathlib.Path(__file__).resolve().parents[1]
payload = json.loads((ROOT / "samples" / "analyze_payload.json").read_text(encoding="utf-8"))
res = httpx.post("http://localhost:8000/api/analyze", json=payload, timeout=30)
print("status:", res.status_code)
print(json.dumps(res.json(), indent=2, ensure_ascii=False))
res.raise_for_status()
