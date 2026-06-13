import re
from collections.abc import Sequence
from contextvars import ContextVar, Token
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
SESSION_COOKIE = "session"
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'none'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "connect-src 'self'",
        "font-src 'self' https://cdn.jsdelivr.net",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'self'",
    )
)
DOCS_CONTENT_SECURITY_POLICY = CONTENT_SECURITY_POLICY.replace(
    "script-src 'self'",
    "script-src 'self' 'unsafe-inline'",
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=()",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, allowed_origins: Sequence[str]) -> None:
        super().__init__(app)
        self.allowed_origins = frozenset(
            origin
            for value in allowed_origins
            if (origin := _normalized_origin(value)) is not None
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            if self._is_cross_site_cookie_request(request):
                response: Response = JSONResponse(
                    status_code=403,
                    content={"detail": "跨站请求已被阻止"},
                )
            else:
                response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            for name, value in SECURITY_HEADERS.items():
                response.headers[name] = value
            if request.url.path.startswith(("/docs", "/redoc")):
                response.headers["Content-Security-Policy"] = (
                    DOCS_CONTENT_SECURITY_POLICY
                )
            return response
        finally:
            _reset_request_id(token)

    def _is_cross_site_cookie_request(self, request: Request) -> bool:
        if request.method.upper() in SAFE_METHODS:
            return False
        if SESSION_COOKIE not in request.cookies:
            return False
        if request.headers.get("authorization", "").casefold().startswith("bearer "):
            return False

        origin = request.headers.get("origin")
        if origin is not None:
            return _normalized_origin(origin) not in self.allowed_origins

        referer = request.headers.get("referer")
        if referer is not None:
            return _normalized_origin(referer) not in self.allowed_origins

        return request.headers.get("sec-fetch-site", "").casefold() == "cross-site"


def current_request_id() -> str:
    return request_id_context.get()


def _request_id(value: str | None) -> str:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


def _normalized_origin(value: str) -> str | None:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.casefold()}://{parsed.netloc.casefold()}"


def _reset_request_id(token: Token[str]) -> None:
    request_id_context.reset(token)
