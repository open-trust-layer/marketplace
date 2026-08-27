"""Pinned-OLP preparation/verification for one M33 immutable Record response."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.transport import TransportEnvelopeV1, decode_identity_text

from .record_retrieval_v1 import verify_retrieved_market_record
from .record_v1 import validate_market_record


class RecordServingReferenceError(ValueError):
    """Fail-closed M33 reference preparation/verification error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise RecordServingReferenceError(code, message)


def _expected_identity(value: object) -> str:
    if type(value) is not str:
        _fail("INVALID_EXPECTED_RECORD_IDENTITY", "expected Record Identity MUST be exact text")
    try:
        kind, _ = decode_identity_text(value, expected_kind="record")
    except Exception as exc:
        _fail(
            "INVALID_EXPECTED_RECORD_IDENTITY",
            f"expected Record Identity is not canonical OLP record identity text: {type(exc).__name__}",
        )
    if kind != "record":
        _fail("INVALID_EXPECTED_RECORD_IDENTITY", "expected identity MUST be a Record Identity")
    return value


def _plain(value: Any) -> Any:
    """Convert frozen OLP host containers into bounded-runtime-compatible values."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def market_record_transport_payload(
    record: Any,
    *,
    expected_record_identity: str,
) -> dict[str, Any]:
    """Validate one local Record and materialize a transport-safe mapping."""
    expected = _expected_identity(expected_record_identity)
    if not isinstance(record, RecordV1):
        _fail("INVALID_OLP_RECORD", "local Record MUST be RecordV1")
    try:
        record.validate()
        validate_market_record(record)
        derived = record_identity_text(record)
    except Exception as exc:
        code = getattr(exc, "code", None)
        suffix = f": {code}" if type(code) is str else ""
        _fail("INVALID_MARKETPLACE_RECORD", f"local Record validation failed{suffix}")
    if derived != expected:
        _fail("RECORD_IDENTITY_MISMATCH", "local Record identity does not match requested identity")

    payload = {
        "envelope_version": record.envelope_version,
        "type": record.type,
        "content": _plain(record.content),
        "semantic_bindings": _plain(record.semantic_bindings),
        "profiles": _plain(record.profiles),
        "relationships": _plain(record.relationships),
        "extensions": _plain(record.extensions),
    }

    try:
        reconstructed = RecordV1.from_mapping(payload)
        reconstructed.validate()
        validate_market_record(reconstructed)
        recomputed = record_identity_text(reconstructed)
    except Exception as exc:
        code = getattr(exc, "code", None)
        suffix = f": {code}" if type(code) is str else ""
        _fail("PAYLOAD_RECONSTRUCTION_FAILED", f"prepared payload failed Record reconstruction{suffix}")
    if recomputed != expected:
        _fail("PAYLOAD_IDENTITY_DRIFT", "prepared payload does not preserve Record Identity")
    return payload


def make_record_transport_envelope(payload: Any) -> tuple[Any, ...]:
    """Create one abstract OLP transport envelope with message type ``record``."""
    if not isinstance(payload, Mapping) or any(type(key) is not str for key in payload):
        _fail("INVALID_RECORD_PAYLOAD", "Record transport payload MUST be a string-keyed map")
    try:
        return TransportEnvelopeV1(message_type="record", payload=payload).to_abstract()
    except Exception as exc:
        _fail("INVALID_RECORD_ENVELOPE", f"cannot construct OLP record transport envelope: {type(exc).__name__}")


def verify_prepared_record_transport_envelope(
    envelope: Any,
    *,
    expected_record_identity: str,
) -> dict[str, Any]:
    """Reuse the M27 verifier and expose only bounded scalar verification facts."""
    verified = verify_retrieved_market_record(
        envelope,
        expected_record_identity=expected_record_identity,
    )
    return {
        "requested_record_identity": verified.requested_record_identity,
        "recomputed_record_identity": verified.recomputed_record_identity,
        "identity_verified": verified.identity_verified,
        "marketplace_semantics_verified": verified.marketplace_semantics_verified,
        "proofs_verified": verified.proofs_verified,
        "establishes_truth": verified.establishes_truth,
        "establishes_ownership": verified.establishes_ownership,
        "establishes_authority": verified.establishes_authority,
        "establishes_trust": verified.establishes_trust,
        "establishes_authorization": verified.establishes_authorization,
        "automatically_ingested": verified.automatically_ingested,
    }
