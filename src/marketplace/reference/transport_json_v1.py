"""Strict JSON codec for OLP single-object transport envelopes used by M26.

This reference adapter deliberately lives under ``marketplace.reference`` so the
base runtime remains importable without OLP installed. It reuses the separately
supplied pinned OLP ``TransportEnvelopeV1`` / OJVE implementation and adds only
the JSON text boundary needed by the reference HTTPS adapter.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from olp.transport import TransportEnvelopeV1


class MarketplaceTransportJsonError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise MarketplaceTransportJsonError(code, message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_NAME", f"JSON object repeats member name {key!r}")
        result[key] = value
    return result


def encode_transport_envelope_json(envelope: Any) -> bytes:
    """Encode an abstract OLP transport envelope to deterministic JSON bytes."""
    if not isinstance(envelope, (tuple, list)) or len(envelope) != 4:
        _fail("INVALID_ABSTRACT_ENVELOPE", "OLP transport envelope MUST contain exactly four elements")
    marker, version, message_type, payload = envelope
    if marker != "OLP-TRANSPORT" or version != 1:
        _fail("INVALID_ABSTRACT_ENVELOPE", "OLP transport envelope marker/version is invalid")
    try:
        materialized = TransportEnvelopeV1(message_type=message_type, payload=payload)
        wire = materialized.to_json()
    except Exception as exc:
        _fail("INVALID_ABSTRACT_ENVELOPE", f"pinned OLP rejected transport envelope: {type(exc).__name__}")
    try:
        text = json.dumps(
            wire,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        _fail("JSON_ENCODING_FAILED", f"OLP JSON envelope could not be encoded: {type(exc).__name__}")
    return text.encode("utf-8")


def decode_transport_envelope_json(body: bytes) -> tuple[Any, ...]:
    """Decode strict UTF-8 JSON and delegate OJVE/envelope validation to pinned OLP."""
    if not isinstance(body, bytes) or not body:
        _fail("INVALID_JSON_BYTES", "transport JSON body MUST be non-empty bytes")
    if body.startswith(b"\xef\xbb\xbf"):
        _fail("JSON_BOM_FORBIDDEN", "transport JSON MUST NOT contain a UTF-8 BOM")
    try:
        text = body.decode("utf-8", "strict")
    except UnicodeDecodeError:
        _fail("INVALID_UTF8", "transport JSON MUST be strict UTF-8")
    try:
        document = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: _fail("INVALID_JSON_NUMBER", f"non-finite JSON number {value!r} is forbidden"),
        )
    except MarketplaceTransportJsonError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        _fail("MALFORMED_JSON", f"transport JSON parse failed: {type(exc).__name__}")
    if not isinstance(document, Mapping):
        _fail("INVALID_JSON_ENVELOPE", "transport JSON top level MUST be an object")
    try:
        envelope = TransportEnvelopeV1.from_json(document)
        abstract = envelope.to_abstract()
    except Exception as exc:
        _fail("INVALID_OLP_ENVELOPE", f"pinned OLP rejected transport JSON: {type(exc).__name__}")
    if not isinstance(abstract, tuple) or len(abstract) != 4:
        _fail("INVALID_OLP_ENVELOPE", "pinned OLP returned an invalid abstract envelope")
    return abstract
