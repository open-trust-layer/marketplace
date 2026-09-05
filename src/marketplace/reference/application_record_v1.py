"""Pinned-OLP adapters for canonical Marketplace application-record state.

This module performs only deterministic in-process record validation, identity
derivation, serialization, decoding, response-parent extraction, and intent
classification. It does not initialize persistence, load files or environment,
select providers, or activate any server/runtime capability.
"""
from __future__ import annotations

from collections.abc import Mapping

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import encode_identity_text

from ..application.postgres_state import PreparedApplicationRecord
from .record_serving_v1 import (
    make_record_transport_envelope,
    market_record_transport_payload,
)
from .record_v1 import TYPE_INTENT, validate_market_record
from .transport_json_v1 import (
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)

class MarketplaceApplicationRecordError(ValueError):
    """Stable fail-closed reference adapter error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise MarketplaceApplicationRecordError(code, message)


def _review_record(record: object) -> RecordV1:
    if type(record) is not RecordV1:
        _fail("APPLICATION_RECORD_INVALID", "application record MUST be exact RecordV1")
    try:
        validate_market_record(record)
    except Exception:
        _fail(
            "APPLICATION_RECORD_INVALID",
            "application record failed pinned OLP or Marketplace validation",
        )
    return record


def _canonical_record_bytes(record: RecordV1, *, record_id: str) -> bytes:
    try:
        payload = market_record_transport_payload(
            record,
            expected_record_identity=record_id,
        )
        envelope = make_record_transport_envelope(payload)
        return encode_transport_envelope_json(envelope)
    except Exception:
        _fail(
            "APPLICATION_RECORD_ENCODING_FAILED",
            "application record could not be serialized through the reviewed OLP transport boundary",
        )


def marketplace_response_parent_ids(record: object) -> tuple[str, ...]:
    """Return canonical Record Identity parents from validated Proposal response_to."""

    reviewed = _review_record(record)
    if reviewed.type != TYPE_INTENT:
        return ()
    content = reviewed.content
    if not isinstance(content, Mapping) or "response_to" not in content:
        return ()
    try:
        refs = tuple(EvidenceRefV1.from_value(value) for value in content["response_to"])
        if any(ref.kind != EvidenceKind.RECORD for ref in refs):
            raise ValueError("response_to reference kind mismatch")
        parents = tuple(
            encode_identity_text("record", ref.identity_digest)
            for ref in refs
        )
    except Exception:
        _fail(
            "APPLICATION_RESPONSE_PARENT_INVALID",
            "validated Marketplace response_to references could not be materialized",
        )
    if len(set(parents)) != len(parents):
        _fail(
            "APPLICATION_RESPONSE_PARENT_INVALID",
            "validated Marketplace response_to references contain duplicates",
        )
    return parents


def is_marketplace_intent_record(record: object) -> bool:
    """Classify only a fully valid exact Marketplace RecordV1 intent."""

    if type(record) is not RecordV1:
        return False
    try:
        validate_market_record(record)
    except Exception:
        return False
    return record.type == TYPE_INTENT


def prepare_marketplace_application_record(record: object) -> PreparedApplicationRecord:
    """Validate and deterministically serialize one record for application persistence."""

    reviewed = _review_record(record)
    try:
        record_id = record_identity_text(reviewed)
    except Exception:
        _fail(
            "APPLICATION_RECORD_IDENTITY_FAILED",
            "application record identity could not be derived",
        )
    canonical_record = _canonical_record_bytes(reviewed, record_id=record_id)
    response_to = marketplace_response_parent_ids(reviewed)
    try:
        return PreparedApplicationRecord(
            record_id=record_id,
            canonical_record=canonical_record,
            response_to=response_to,
        )
    except Exception:
        _fail(
            "APPLICATION_RECORD_PREPARATION_FAILED",
            "application record exceeds reviewed application-state bounds",
        )


def decode_marketplace_application_record(canonical_record: bytes) -> RecordV1:
    """Decode only the exact deterministic representation emitted by the preparer."""

    if type(canonical_record) is not bytes or not canonical_record:
        _fail(
            "APPLICATION_RECORD_DECODING_FAILED",
            "canonical application record MUST be non-empty exact bytes",
        )
    try:
        envelope = decode_transport_envelope_json(canonical_record)
        if not isinstance(envelope, tuple) or len(envelope) != 4:
            raise ValueError("invalid transport envelope")
        marker, version, message_type, payload = envelope
        if marker != "OLP-TRANSPORT" or version != 1 or message_type != "record":
            raise ValueError("record transport envelope required")
        if not isinstance(payload, Mapping) or any(type(key) is not str for key in payload):
            raise ValueError("record payload must be a string-keyed mapping")
        record = RecordV1.from_mapping(dict(payload))
        reviewed = _review_record(record)
        record_id = record_identity_text(reviewed)
        expected = _canonical_record_bytes(reviewed, record_id=record_id)
    except MarketplaceApplicationRecordError:
        raise
    except Exception:
        _fail(
            "APPLICATION_RECORD_DECODING_FAILED",
            "canonical application record could not be reconstructed safely",
        )
    if canonical_record != expected:
        _fail(
            "APPLICATION_RECORD_NON_CANONICAL",
            "application record bytes are valid but not the reviewed deterministic representation",
        )
    return reviewed


__all__ = [
    "MarketplaceApplicationRecordError",
    "decode_marketplace_application_record",
    "is_marketplace_intent_record",
    "marketplace_response_parent_ids",
    "prepare_marketplace_application_record",
]
