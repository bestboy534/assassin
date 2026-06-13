from fastapi.responses import Response
from fastapi.testclient import TestClient

from app.domains.identity.router import set_session_cookie
from app.main import app


def test_security_headers_and_request_id_are_attached() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"X-Request-ID": "request-2026-06-13"},
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-2026-06-13"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=(), payment=()"
    )
    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={"X-Request-ID": "invalid\r\ninjected"},
        )

    request_id = response.headers["x-request-id"]
    assert request_id != "invalid\r\ninjected"
    assert len(request_id) == 36


def test_api_docs_csp_allows_fastapi_inline_bootstrap() -> None:
    with TestClient(app) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    directives = response.headers["content-security-policy"].split(";")
    script_policy = next(
        directive.strip()
        for directive in directives
        if directive.strip().startswith("script-src")
    )
    assert "'unsafe-inline'" in script_policy
    assert "https://cdn.jsdelivr.net" in script_policy


def test_cross_site_cookie_request_is_rejected() -> None:
    with TestClient(app) as client:
        client.cookies.set("session", "browser-session")
        response = client.post(
            "/api/analyze",
            headers={
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
            json={"raw_text": "Figma $12 monthly", "source_hint": "unknown"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "跨站请求已被阻止"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_trusted_origin_cookie_request_is_allowed() -> None:
    with TestClient(app) as client:
        client.cookies.set("session", "browser-session")
        response = client.post(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Sec-Fetch-Site": "same-site",
            },
            json={"raw_text": "Figma $12 monthly", "source_hint": "unknown"},
        )

    assert response.status_code == 200


def test_production_session_cookie_is_secure() -> None:
    response = Response()

    set_session_cookie(response, "opaque-session-token", secure=True)

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" in cookie
