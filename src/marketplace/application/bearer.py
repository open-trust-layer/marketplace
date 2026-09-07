"""Canonical M17.5C bearer-session wire parsing without runtime ownership."""
from __future__ import annotations

import base64
from typing import Final


MARKETPLACE_BEARER_PREFIX: Final = b"Bearer mkt1_"
MARKETPLACE_BEARER_VALUE_BYTES: Final = 55
MARKETPLACE_BEARER_PAYLOAD_CHARS: Final = 43
_BASE64URL = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


class MarketplaceBearerTransportError(ValueError):
    """Stable fail-closed bearer syntax error without credential reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail() -> None:
    raise MarketplaceBearerTransportError(
        "AUTH_SESSION_INVALID",
        "application bearer credential is invalid",
    ) from None


def parse_marketplace_bearer_authorization(value: object) -> bytes:
    """Decode exactly one MARKETPLACE_APPLICATION_BEARER_V1 header value."""
    if type(value) is not bytes or len(value) != MARKETPLACE_BEARER_VALUE_BYTES:
        _fail()
    if not value.startswith(MARKETPLACE_BEARER_PREFIX):
        _fail()
    payload = value[len(MARKETPLACE_BEARER_PREFIX):]
    if len(payload) != MARKETPLACE_BEARER_PAYLOAD_CHARS:
        _fail()
    if any(byte not in _BASE64URL for byte in payload):
        _fail()
    try:
        token = base64.b64decode(payload + b"=", altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        _fail()
    if len(token) != 32:
        _fail()
    if base64.urlsafe_b64encode(token).rstrip(b"=") != payload:
        _fail()
    return token


__all__ = [
    "MARKETPLACE_BEARER_PAYLOAD_CHARS",
    "MARKETPLACE_BEARER_PREFIX",
    "MARKETPLACE_BEARER_VALUE_BYTES",
    "MarketplaceBearerTransportError",
    "parse_marketplace_bearer_authorization",
]
