"""Pinned OLP OJVE carriers for Agreement assent HTTP byte values."""
from __future__ import annotations

from typing import Any

from olp.transport import decode_ojve, encode_ojve


MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES = 4096
AGREEMENT_ASSENT_SIGNATURE_BYTES = 64


class AgreementAssentHttpTransportError(ValueError):
    """Stable carrier error without reflected byte material."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentHttpTransportError(code, message) from None


def encode_agreement_assent_signing_input(value: bytes) -> dict[str, str]:
    if (
        type(value) is not bytes
        or not 1 <= len(value) <= MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES
    ):
        _fail(
            "AGREEMENT_ASSENT_SIGNING_INPUT_INVALID",
            "Agreement assent signing input is invalid",
        )
    try:
        carrier = encode_ojve(value)
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SIGNING_INPUT_ENCODING_FAILED",
            "Agreement assent signing input could not be encoded",
        )
    if (
        type(carrier) is not dict
        or frozenset(carrier) != {"$olp", "v"}
        or carrier.get("$olp") != "bytes"
        or type(carrier.get("v")) is not str
    ):
        _fail(
            "AGREEMENT_ASSENT_SIGNING_INPUT_ENCODING_FAILED",
            "Agreement assent signing input carrier is invalid",
        )
    return carrier


def decode_agreement_assent_signature(value: Any) -> bytes:
    try:
        decoded = decode_ojve(value)
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SIGNATURE_ENCODING_INVALID",
            "Agreement assent signature carrier is invalid",
        )
    if type(decoded) is not bytes or len(decoded) != AGREEMENT_ASSENT_SIGNATURE_BYTES:
        _fail(
            "AGREEMENT_ASSENT_SIGNATURE_ENCODING_INVALID",
            "Agreement assent signature carrier is invalid",
        )
    return decoded


__all__ = [
    "AGREEMENT_ASSENT_SIGNATURE_BYTES",
    "AgreementAssentHttpTransportError",
    "MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES",
    "decode_agreement_assent_signature",
    "encode_agreement_assent_signing_input",
]
