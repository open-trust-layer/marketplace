"""Canonical M17.5D authentication-challenge wire encoding."""
from __future__ import annotations

import base64
from typing import Final

AUTH_CHALLENGE_PREFIX: Final = "mkc1_"
AUTH_CHALLENGE_PAYLOAD_CHARS: Final = 43
AUTH_CHALLENGE_TEXT_CHARS: Final = 48
_BASE64URL = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


class MarketplaceChallengeTransportError(ValueError):
    """Stable fail-closed challenge syntax error without material reflection."""

    def __init__(self) -> None:
        super().__init__("application authentication challenge is invalid")
        self.code = "AUTH_CHALLENGE_INVALID"


def _fail() -> None:
    raise MarketplaceChallengeTransportError() from None


def encode_marketplace_auth_challenge(challenge: object) -> str:
    if type(challenge) is not bytes or len(challenge) != 32:
        _fail()
    payload = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii")
    if len(payload) != AUTH_CHALLENGE_PAYLOAD_CHARS:
        _fail()
    return AUTH_CHALLENGE_PREFIX + payload


def parse_marketplace_auth_challenge(value: object) -> bytes:
    if type(value) is not str or len(value) != AUTH_CHALLENGE_TEXT_CHARS:
        _fail()
    if not value.startswith(AUTH_CHALLENGE_PREFIX):
        _fail()
    payload = value[len(AUTH_CHALLENGE_PREFIX):]
    if len(payload) != AUTH_CHALLENGE_PAYLOAD_CHARS or any(char not in _BASE64URL for char in payload):
        _fail()
    try:
        raw_payload = payload.encode("ascii", "strict")
        challenge = base64.b64decode(raw_payload + b"=", altchars=b"-_", validate=True)
    except (UnicodeEncodeError, ValueError, TypeError):
        _fail()
    if len(challenge) != 32:
        _fail()
    if base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii") != payload:
        _fail()
    return challenge


__all__ = [
    "AUTH_CHALLENGE_PAYLOAD_CHARS",
    "AUTH_CHALLENGE_PREFIX",
    "AUTH_CHALLENGE_TEXT_CHARS",
    "MarketplaceChallengeTransportError",
    "encode_marketplace_auth_challenge",
    "parse_marketplace_auth_challenge",
]
