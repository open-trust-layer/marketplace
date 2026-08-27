"""Pinned-OLP verification for one M27 immutable Record retrieval result.

Transport success is intentionally insufficient.  This reference boundary
reconstructs RecordV1, recomputes the authoritative OLP Record Identity locally,
requires exact equality with the requested textual identity, and only then runs
Marketplace semantic validation.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.transport import decode_identity_text

from .record_v1 import validate_market_record


class RetrievedRecordVerificationError(ValueError):
    """Fail-closed M27 record reconstruction/identity/semantic verification error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise RetrievedRecordVerificationError(code, message)


@dataclass(frozen=True)
class VerifiedRetrievedRecord:
    """Locally reconstructed Marketplace Record with exact OLP identity equality."""

    record: RecordV1
    requested_record_identity: str
    recomputed_record_identity: str
    identity_verified: bool = True
    marketplace_semantics_verified: bool = True
    proofs_verified: bool = False
    establishes_truth: bool = False
    establishes_ownership: bool = False
    establishes_authority: bool = False
    establishes_trust: bool = False
    establishes_authorization: bool = False
    automatically_ingested: bool = False


def _canonical_expected_identity(value: object) -> str:
    if not isinstance(value, str):
        _fail("INVALID_EXPECTED_RECORD_IDENTITY", "expected Record Identity MUST be text")
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


def verify_retrieved_market_record(
    envelope: Any,
    *,
    expected_record_identity: str,
) -> VerifiedRetrievedRecord:
    """Reconstruct, identity-check and semantically validate one retrieved Record."""
    expected = _canonical_expected_identity(expected_record_identity)
    if not isinstance(envelope, (tuple, list)) or len(envelope) != 4:
        _fail("INVALID_RECORD_ENVELOPE", "retrieval result MUST be one OLP transport envelope")
    marker, version, message_type, payload = envelope
    if marker != "OLP-TRANSPORT":
        _fail("INVALID_RECORD_ENVELOPE", "retrieval envelope marker is invalid")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        _fail("INVALID_RECORD_ENVELOPE", "retrieval envelope version MUST equal integer 1")
    if message_type != "record":
        _fail("RECORD_MESSAGE_TYPE_REQUIRED", "retrieval envelope MUST use OLP message type 'record'")
    if not isinstance(payload, Mapping) or any(not isinstance(key, str) for key in payload):
        _fail("INVALID_RECORD_PAYLOAD", "retrieved Record payload MUST be a string-keyed map")

    try:
        record = RecordV1.from_mapping(dict(payload))
        record.validate()
    except Exception as exc:
        _fail("INVALID_OLP_RECORD", f"pinned OLP rejected retrieved Record: {type(exc).__name__}")

    try:
        recomputed = record_identity_text(record)
    except Exception as exc:
        _fail("RECORD_IDENTITY_RECOMPUTE_FAILED", f"Record Identity recomputation failed: {type(exc).__name__}")
    if recomputed != expected:
        _fail(
            "RECORD_IDENTITY_MISMATCH",
            "locally recomputed Record Identity does not match the requested immutable identity",
        )

    try:
        validate_market_record(record)
    except Exception as exc:
        code = getattr(exc, "code", None)
        suffix = f": {code}" if isinstance(code, str) else ""
        _fail("INVALID_MARKETPLACE_RECORD", f"retrieved Record failed Marketplace semantics{suffix}")

    return VerifiedRetrievedRecord(
        record=record,
        requested_record_identity=expected,
        recomputed_record_identity=recomputed,
    )
