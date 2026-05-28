from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_analyze_mock_csv():
    payload = {"source_hint":"csv", "raw_text":"""Transaction Date,Description,Amount,Currency
2026-05-01,OPENAI *CHATGPT SUBSCRIP,20.00,USD
2026-05-02,OPENAI *API,14.52,USD
2026-05-03,APPLE.COM/BILL,680,TWD
"""}
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 2
    assert any(item["risk_type"] == "api_usage" for item in data["items"])
    assert any(item["status"] == "apple_unresolved" for item in data["items"])
