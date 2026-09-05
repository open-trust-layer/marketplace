"""Reference application Record JSON profile over pinned OLP value encoding.

The application HTTP surface deliberately exposes a compact Record-shaped JSON
object rather than an OLP transport envelope. Ordinary string-keyed maps remain
ordinary JSON objects so current Web/Android clients can consume ``content``
directly. Values that JSON cannot represent safely reuse pinned OLP OJVE-1.

This module performs deterministic in-process validation/encoding only. It owns
no persistence, filesystem, environment, network, server, browser, or Android
runtime authority.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.transport import OJVEMap, decode_ojve, encode_ojve, materialize_map

from ..application.http import MAX_APPLICATION_HTTP_BODY_BYTES
from .record_serving_v1 import market_record_transport_payload
from .record_v1 import validate_market_record


_RECORD_FIELDS = frozenset(
    {
        "envelope_version",
        "type",
        "content",
        "semantic_bindings",
        "profiles",
        "relationships",
        "extensions",
    }
)
_REQUIRED_RECORD_FIELDS = frozenset({"envelope_version", "type", "content"})
_RESERVED_OJVE_MEMBERS = frozenset({"$olp", "v"})


class MarketplaceApplicationRecordJsonError(ValueError):
    """Stable fail-closed application Record JSON profile error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise MarketplaceApplicationRecordJsonError(code, message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(
                "APPLICATION_RECORD_JSON_DUPLICATE_NAME",
                "application Record JSON contains a duplicate member name",
            )
        result[key] = value
    return result


def _reserved_ojve_shape(value: Mapping[str, Any]) -> bool:
    return frozenset(value) == _RESERVED_OJVE_MEMBERS


def _encode_application_value(value: Any) -> Any:
    """Keep normal text-key maps compact; delegate exceptional values to OJVE."""

    if isinstance(value, Mapping):
        keys = tuple(value.keys())
        direct = all(type(key) is str for key in keys) and not _reserved_ojve_shape(value)
        if direct:
            return {key: _encode_application_value(item) for key, item in value.items()}
        try:
            return encode_ojve(value)
        except Exception:
            _fail(
                "APPLICATION_RECORD_JSON_ENCODING_FAILED",
                "application Record contains a value outside the reviewed JSON profile",
            )
    if isinstance(value, (tuple, list)):
        return [_encode_application_value(item) for item in value]
    try:
        return encode_ojve(value)
    except Exception:
        _fail(
            "APPLICATION_RECORD_JSON_ENCODING_FAILED",
            "application Record contains a value outside the reviewed JSON profile",
        )


def _decode_application_value(value: Any) -> Any:
    if type(value) is list:
        return tuple(_decode_application_value(item) for item in value)
    if type(value) is dict:
        if _reserved_ojve_shape(value):
            try:
                decoded = decode_ojve(value)
                if isinstance(decoded, OJVEMap):
                    return materialize_map(decoded, allowed_key_types=(str, int))
                return decoded
            except Exception:
                _fail(
                    "APPLICATION_RECORD_JSON_OJVE_INVALID",
                    "application Record JSON contains an invalid OJVE value",
                )
        return {key: _decode_application_value(item) for key, item in value.items()}
    try:
        return decode_ojve(value)
    except Exception:
        _fail(
            "APPLICATION_RECORD_JSON_VALUE_INVALID",
            "application Record JSON contains a value outside the reviewed profile",
        )


def encode_marketplace_application_record_json(record: object) -> bytes:
    """Encode one valid Marketplace RecordV1 to deterministic application JSON."""

    if type(record) is not RecordV1:
        _fail(
            "APPLICATION_RECORD_JSON_RECORD_INVALID",
            "application Record JSON encoder requires exact RecordV1",
        )
    try:
        validate_market_record(record)
        record_id = record_identity_text(record)
        payload = market_record_transport_payload(
            record,
            expected_record_identity=record_id,
        )
        document = {
            key: _encode_application_value(payload[key])
            for key in (
                "envelope_version",
                "type",
                "content",
                "semantic_bindings",
                "profiles",
                "relationships",
                "extensions",
            )
        }
        body = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except MarketplaceApplicationRecordJsonError:
        raise
    except Exception:
        _fail(
            "APPLICATION_RECORD_JSON_ENCODING_FAILED",
            "application Record could not be encoded safely",
        )
    if not body or len(body) > MAX_APPLICATION_HTTP_BODY_BYTES:
        _fail(
            "APPLICATION_RECORD_JSON_TOO_LARGE",
            "application Record JSON exceeds the reviewed HTTP body bound",
        )
    return body


def decode_marketplace_application_record_json(body: bytes) -> RecordV1:
    """Decode strict application Record JSON and rerun pinned Marketplace validation."""

    if type(body) is not bytes or not body or len(body) > MAX_APPLICATION_HTTP_BODY_BYTES:
        _fail(
            "APPLICATION_RECORD_JSON_BYTES_INVALID",
            "application Record JSON must be non-empty bounded exact bytes",
        )
    if body.startswith(b"\xef\xbb\xbf"):
        _fail(
            "APPLICATION_RECORD_JSON_BOM_FORBIDDEN",
            "application Record JSON must not contain a UTF-8 BOM",
        )
    try:
        text = body.decode("utf-8", "strict")
        document = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda _value: _fail(
                "APPLICATION_RECORD_JSON_NUMBER_INVALID",
                "application Record JSON contains a non-finite number",
            ),
        )
    except MarketplaceApplicationRecordJsonError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail(
            "APPLICATION_RECORD_JSON_MALFORMED",
            "application Record JSON is malformed",
        )
    if type(document) is not dict:
        _fail(
            "APPLICATION_RECORD_JSON_SHAPE_INVALID",
            "application Record JSON top level must be an object",
        )
    fields = frozenset(document)
    if not _REQUIRED_RECORD_FIELDS.issubset(fields) or not fields.issubset(_RECORD_FIELDS):
        _fail(
            "APPLICATION_RECORD_JSON_SHAPE_INVALID",
            "application Record JSON has an invalid top-level field set",
        )
    try:
        mapping = {key: _decode_application_value(value) for key, value in document.items()}
        record = RecordV1.from_mapping(mapping)
        validate_market_record(record)
    except MarketplaceApplicationRecordJsonError:
        raise
    except Exception:
        _fail(
            "APPLICATION_RECORD_JSON_RECORD_INVALID",
            "application Record JSON does not reconstruct a valid Marketplace Record",
        )
    return record


__all__ = [
    "MarketplaceApplicationRecordJsonError",
    "decode_marketplace_application_record_json",
    "encode_marketplace_application_record_json",
]
