"""Source-only, unattached Caddy-to-Marketplace ASGI edge normalization.

Requires a separately implemented and reviewed per-connection trusted transport
verifier. This code never assumes that loopback IP or HTTP forwarding headers
alone prove Caddy identity or HTTPS. No listener or deployment is created.
"""
from __future__ import annotations

from typing import Any, Final, Protocol

from .canonical_origin_guard import (
    CANONICAL_HOST,
    MarketplaceCanonicalOriginAsgiGuard,
)
from .linux_unix_caddy_peer import ACCEPTED_UNIX_SOCKET_SCOPE_KEY

_MAX_HEADERS: Final = 64
_MAX_BYTES: Final = 32768
_MAX_VALUE_BYTES: Final = 8192
_ALLOWED_FORWARDED: Final = frozenset((
    b"x-forwarded-host", b"x-forwarded-proto", b"x-forwarded-for",
))
_REJECTED_METADATA: Final = frozenset((
    b"forwarded", b"x-real-ip", b"x-original-host", b"x-original-url",
    b"x-rewrite-url", b"x-scheme",
))
_HOST_VALUES: Final = frozenset((CANONICAL_HOST, CANONICAL_HOST + b":443"))
_TOKEN_BYTES: Final = frozenset(
    b"!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)


class MarketplaceVerifiedCaddyConnection(Protocol):
    """Vetted outside this module against actual transport identity, NOT headers."""

    def verify_connection(self, scope: dict[str, Any]) -> bool:
        """Return exactly True only with trustworthy per-request peer evidence."""


def _normalized_scope(scope: object) -> dict[str, Any] | None:
    if (
        type(scope) is not dict
        or scope.get("type") != "http"
        or type(scope.get("asgi")) is not dict
        or scope["asgi"].get("version") != "3.0"
        or scope.get("scheme") != "http"
        or scope.get("root_path", "") != ""
    ):
        return None
    headers = scope.get("headers")
    if type(headers) not in (list, tuple) or len(headers) > _MAX_HEADERS:
        return None
    host: bytes | None = None
    forwarded_host: bytes | None = None
    forwarded_proto: bytes | None = None
    known: set[bytes] = set()
    retained: list[tuple[bytes, bytes]] = []
    total = 0
    for pair in headers:
        if type(pair) not in (list, tuple) or len(pair) != 2:
            return None
        name, value = pair
        if type(name) is not bytes or type(value) is not bytes:
            return None
        total += len(name) + len(value) + 4
        if (
            not name
            or any(char not in _TOKEN_BYTES for char in name)
            or len(value) > _MAX_VALUE_BYTES
            or total > _MAX_BYTES
            or any(char in value for char in (0, 10, 13))
        ):
            return None
        normalized_name = name.lower()
        if (
            normalized_name in _REJECTED_METADATA
            or normalized_name.startswith(b"x-forwarded-")
            and normalized_name not in _ALLOWED_FORWARDED
        ):
            return None
        if normalized_name in _ALLOWED_FORWARDED | {b"host"}:
            if normalized_name in known:
                return None
            known.add(normalized_name)
        if normalized_name == b"host":
            host = value
            retained.append((name, value))
        elif normalized_name == b"x-forwarded-host":
            forwarded_host = value
        elif normalized_name == b"x-forwarded-proto":
            forwarded_proto = value
        elif normalized_name == b"x-forwarded-for":
            # The client chain is deliberately NOT passed to product auth or
            # interpreted as identity; Caddy's trust policy is separate.
            continue
        else:
            retained.append((name, value))
    if (
        host not in _HOST_VALUES
        or forwarded_host != host
        or forwarded_proto != b"https"
    ):
        return None
    result = dict(scope)
    # Transport socket evidence must never reach auth/application handlers.
    result.pop(ACCEPTED_UNIX_SOCKET_SCOPE_KEY, None)
    result["headers"] = retained
    result["scheme"] = "https"
    return result


async def _deny(send) -> None:
    body = b"TRUSTED_EDGE_REQUIRED"
    await send({
        "type": "http.response.start",
        "status": 403,
        "headers": (
            (b"content-type", b"text/plain; charset=utf-8"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
        ),
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})


class MarketplaceAttestedCaddyEdgeAsgiAdapter:
    """Normalize known Caddy-generated metadata ONLY for attested connections.

    The verifier is a required, separately reviewed capability. A future
    production transport must give it trustworthy connection evidence, e.g.
    peer credentials on an access-controlled Unix socket; unchecked ASGI client
    IP/headers are not sufficient. No verifier is supplied by this module.
    """

    __slots__ = ("_guard", "_verifier")

    def __init__(
        self,
        *,
        guard: MarketplaceCanonicalOriginAsgiGuard,
        verifier: MarketplaceVerifiedCaddyConnection,
    ) -> None:
        if type(guard) is not MarketplaceCanonicalOriginAsgiGuard:
            raise TypeError("exact Marketplace canonical origin guard required")
        if not callable(getattr(verifier, "verify_connection", None)):
            raise TypeError("explicit attested transport verifier required")
        self._guard = guard
        self._verifier = verifier

    async def __call__(self, scope, receive, send) -> None:
        if not callable(receive) or not callable(send):
            raise TypeError("ASGI receive and send must be callable")
        normalized = _normalized_scope(scope)
        if normalized is None:
            await _deny(send)
            return
        try:
            authorized = self._verifier.verify_connection(scope)
        except Exception:
            authorized = False
        if authorized is not True:
            await _deny(send)
            return
        await self._guard(normalized, receive, send)


__all__ = ["MarketplaceVerifiedCaddyConnection", "MarketplaceAttestedCaddyEdgeAsgiAdapter"]
