"""Inert source-only canonical-origin ASGI boundary for a future HTTPS host.

No listener, provider, network, database, credentials, proxy trust, deployment
or runtime graph is selected here. The constructor does not call the application.
A future production composition must explicitly and separately approve wiring.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Final

CANONICAL_HOST: Final = b"marketplace.open-trust-layer.org"
CANONICAL_ORIGIN: Final = b"https://marketplace.open-trust-layer.org"
_ALLOWED_HOSTS: Final = frozenset((CANONICAL_HOST, CANONICAL_HOST + b":443"))
_SAFE_METHODS: Final = frozenset(("GET", "HEAD", "OPTIONS"))
_UNSAFE_METHODS: Final = frozenset(("POST", "PUT", "PATCH", "DELETE"))
_ALLOWED_METHODS: Final = _SAFE_METHODS | _UNSAFE_METHODS
_HTTP_NAME_BYTES: Final = frozenset(
    b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
_FORBIDDEN_PROXY_HEADERS: Final = frozenset((
    b"forwarded", b"x-forwarded-for", b"x-forwarded-host", b"x-forwarded-proto",
    b"x-forwarded-port", b"x-forwarded-prefix", b"x-forwarded-scheme",
    b"x-real-ip", b"x-original-host", b"x-original-url", b"x-rewrite-url",
    b"x-scheme",
))
MAX_HEADERS: Final = 64
MAX_HEADER_BYTES: Final = 32768
MAX_VALUE_BYTES: Final = 8192

AsgiReceive = Callable[[], Awaitable[dict[str, Any]]]
AsgiSend = Callable[[dict[str, Any]], Awaitable[None]]
AsgiApplication = Callable[[dict[str, Any], AsgiReceive, AsgiSend], Awaitable[None]]


def _reject_code(scope: object) -> tuple[int, bytes] | None:
    if type(scope) is not dict:
        return (400, b"INVALID_SCOPE")
    if (
        scope.get("type") != "http"
        or type(scope.get("asgi")) is not dict
        or scope["asgi"].get("version") != "3.0"
        or scope.get("root_path", "") != ""
    ):
        return (400, b"INVALID_SCOPE")
    if scope.get("scheme") != "https":
        # Never infer TLS from untrusted Forwarded / X-Forwarded-Proto.
        return (403, b"HTTPS_REQUIRED")
    method = scope.get("method")
    if type(method) is not str or method not in _ALLOWED_METHODS:
        return (405, b"METHOD_REJECTED")
    headers = scope.get("headers")
    if type(headers) not in (list, tuple) or len(headers) > MAX_HEADERS:
        return (400, b"INVALID_HEADERS")

    authority: bytes | None = None
    origin: bytes | None = None
    total = 0
    for pair in headers:
        if type(pair) not in (list, tuple) or len(pair) != 2:
            return (400, b"INVALID_HEADERS")
        raw_name, raw_value = pair
        if type(raw_name) is not bytes or type(raw_value) is not bytes:
            return (400, b"INVALID_HEADERS")
        total += len(raw_name) + len(raw_value) + 4
        if (
            total > MAX_HEADER_BYTES
            or not raw_name
            or len(raw_value) > MAX_VALUE_BYTES
            or any(c not in _HTTP_NAME_BYTES for c in raw_name)
            or any(c in raw_value for c in (0, 10, 13))
        ):
            return (400, b"INVALID_HEADERS")
        name = raw_name.lower()
        if name in _FORBIDDEN_PROXY_HEADERS:
            return (400, b"PROXY_METADATA_FORBIDDEN")
        if name == b"host":
            if authority is not None:
                return (400, b"DUPLICATE_HOST")
            authority = raw_value
        elif name == b"origin":
            if origin is not None:
                return (400, b"DUPLICATE_ORIGIN")
            origin = raw_value

    if authority not in _ALLOWED_HOSTS:
        return (421, b"CANONICAL_HOST_REQUIRED")
    if origin is not None and origin != CANONICAL_ORIGIN:
        return (403, b"ORIGIN_REJECTED")
    if method in _UNSAFE_METHODS and origin is None:
        return (403, b"ORIGIN_REQUIRED")
    return None


class MarketplaceCanonicalOriginAsgiGuard:
    """Protect an injected ASGI application only when explicitly composed.

    Accepts no target hostname, scheme, caller-supplied proxy allowlist or
    insecure fallback. Rejection occurs before body receive or app invocation.
    """

    __slots__ = ("_app",)

    def __init__(self, *, app: AsgiApplication) -> None:
        if not callable(app):
            raise TypeError("canonical guard requires a callable ASGI application")
        self._app = app

    async def __call__(self, scope: dict[str, Any], receive: AsgiReceive, send: AsgiSend) -> None:
        if not callable(receive) or not callable(send):
            raise TypeError("ASGI receive and send must be callable")
        denied = _reject_code(scope)
        if denied is None:
            await self._app(scope, receive, send)
            return

        status, code = denied
        headers = [
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"content-length", str(len(code)).encode("ascii")),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": code, "more_body": False})


__all__ = [
    "CANONICAL_HOST", "CANONICAL_ORIGIN",
    "MarketplaceCanonicalOriginAsgiGuard",
]
