"""Inert same-origin site routing over reviewed application HTTP semantics."""
from __future__ import annotations

import json
from typing import Protocol

from .http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    MAX_APPLICATION_HTTP_BODY_BYTES,
    MAX_APPLICATION_HTTP_PATH_CHARS,
    MAX_APPLICATION_HTTP_QUERY_ITEMS,
    MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS,
    MAX_APPLICATION_HTTP_RESPONSE_BYTES,
)


_STATIC_CSP = "default-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_STATIC_ROUTES = frozenset(("/", "/index.html", "/app.js", "/styles.css"))


class ApplicationHttpPort(Protocol):
    def handle(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse: ...


def _headers(content_type: str, body: bytes, *, allow: str | None = None) -> tuple[tuple[str, str], ...]:
    values: tuple[tuple[str, str], ...] = (
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", _STATIC_CSP),
        ("Cross-Origin-Resource-Policy", "same-origin"),
    )
    if allow is not None:
        values += (("Allow", allow),)
    return values


def _error(status_code: int, reason: str, code: str, message: str, *, allow: str | None = None) -> ApplicationHttpResponse:
    body = json.dumps(
        {"error": {"code": code, "message": message}},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return ApplicationHttpResponse(status_code, reason, _headers(_JSON_CONTENT_TYPE, body, allow=allow), body)


def _query_shape_is_valid(query: object) -> bool:
    if type(query) is not tuple or len(query) > MAX_APPLICATION_HTTP_QUERY_ITEMS:
        return False
    names: set[str] = set()
    for item in query:
        if type(item) is not tuple or len(item) != 2:
            return False
        name, value = item
        if type(name) is not str or type(value) is not str:
            return False
        if not name or not value or name in names:
            return False
        if len(name) > MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS or len(value) > MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS:
            return False
        if any(ord(char) < 32 or ord(char) == 127 for char in name + value):
            return False
        names.add(name)
    return True


def _metadata_is_valid(request: object) -> bool:
    if type(request) is not ApplicationHttpRequest:
        return False
    if type(request.method) is not str or type(request.path) is not str or type(request.body) is not bytes:
        return False
    if request.content_type is not None and type(request.content_type) is not str:
        return False
    if not request.method or len(request.method) > 8:
        return False
    if not request.path or len(request.path) > MAX_APPLICATION_HTTP_PATH_CHARS:
        return False
    if request.content_type is not None and len(request.content_type) > 128:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in request.method + request.path):
        return False
    return True


def _review_asset(value: object, label: str) -> bytes:
    if type(value) is not bytes:
        raise TypeError(f"{label} MUST be exact bytes")
    if not value or len(value) > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
        raise ValueError(f"{label} MUST be non-empty and within the reviewed response bound")
    return value


class MarketplaceSiteHostAdapter:
    """Join the reviewed Web shell and product API without transport ownership."""

    def __init__(
        self,
        *,
        application_http: ApplicationHttpPort,
        index_html: bytes,
        app_js: bytes,
        styles_css: bytes,
    ) -> None:
        if not callable(getattr(application_http, "handle", None)):
            raise TypeError("application_http MUST expose a callable handle method")
        self._application_http = application_http
        self._assets: dict[str, tuple[bytes, str]] = {
            "/": (_review_asset(index_html, "index_html"), "text/html; charset=utf-8"),
            "/index.html": (_review_asset(index_html, "index_html"), "text/html; charset=utf-8"),
            "/app.js": (_review_asset(app_js, "app_js"), "text/javascript; charset=utf-8"),
            "/styles.css": (_review_asset(styles_css, "styles_css"), "text/css; charset=utf-8"),
        }

    def handle(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        if not _metadata_is_valid(request):
            return _error(400, "Bad Request", "REQUEST_INVALID", "request is invalid")
        if len(request.body) > MAX_APPLICATION_HTTP_BODY_BYTES:
            return _error(413, "Payload Too Large", "PAYLOAD_TOO_LARGE", "request body exceeded the reviewed bound")
        if not _query_shape_is_valid(request.query):
            return _error(400, "Bad Request", "QUERY_INVALID", "query is invalid")

        if request.path.startswith("/api/"):
            return self._application_http.handle(request)

        if request.path not in _STATIC_ROUTES:
            return _error(404, "Not Found", "ROUTE_NOT_FOUND", "route does not exist")
        if request.method != "GET":
            return _error(405, "Method Not Allowed", "METHOD_NOT_ALLOWED", "route does not accept this method", allow="GET")
        if request.query or request.content_type is not None or request.body:
            return _error(400, "Bad Request", "REQUEST_INVALID", "request is invalid")

        body, content_type = self._assets[request.path]
        return ApplicationHttpResponse(200, "OK", _headers(content_type, body), body)


__all__ = ["ApplicationHttpPort", "MarketplaceSiteHostAdapter"]
