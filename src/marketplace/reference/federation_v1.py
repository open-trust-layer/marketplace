"""Non-normative Marketplace federation/interoperability v1 helpers.

The helpers profile OLP transport and immutable Marketplace records. They do not
create a global server, replication authority, transport identity, or trust state.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Mapping

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.errors import ConformanceError
from olp.transport import TransportEnvelopeV1, decode_identity_text
from olp.values import is_absolute_uri

from .record_v1 import (
    BASE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    TYPE_INTENT,
    MarketplaceConformanceError,
    validate_market_record,
)
CAP_SNAPSHOT = f"{BASE}/federation/capability/snapshot-v1"
CAP_SYNC = f"{BASE}/federation/capability/incremental-sync-v1"
CAP_SUBMISSION = f"{BASE}/federation/capability/submission-v1"

OP_SNAPSHOT = f"{BASE}/federation/operation/snapshot-v1"
OP_SYNC = f"{BASE}/federation/operation/incremental-sync-v1"
OP_SUBMISSION = f"{BASE}/federation/operation/submission-v1"

MSG_SNAPSHOT_REQUEST = f"{BASE}/federation/message/snapshot-request-v1"
MSG_SNAPSHOT_RESULT = f"{BASE}/federation/message/snapshot-result-v1"
MSG_SYNC_REQUEST = f"{BASE}/federation/message/sync-request-v1"
MSG_SYNC_RESULT = f"{BASE}/federation/message/sync-result-v1"
MSG_SUBMISSION_RESULT = f"{BASE}/federation/message/submission-result-v1"
CORE_MESSAGE_TYPES = {
    MSG_SNAPSHOT_REQUEST, MSG_SNAPSHOT_RESULT, MSG_SYNC_REQUEST,
    MSG_SYNC_RESULT, MSG_SUBMISSION_RESULT,
}

CORE_RECORD_TYPES = {TYPE_INTENT, TYPE_AGREEMENT, TYPE_EVENT}
COMPLETENESS = {"COMPLETE_FOR_DECLARED_SOURCE", "PARTIAL_SOURCE", "UNKNOWN_SOURCE"}
SUBMISSION_STATUSES = {
    "RECEIVER_ACCEPTED",
    "RECEIVER_REJECTED",
    "RECEIVER_IGNORED",
    "RECEIVER_DEFERRED",
}
MAX_PAGE_RECORDS = 10_000
MAX_SUBMISSION_RECORDS = 1_000
MAX_CURSOR_BYTES = 4_096
MAX_CAPABILITIES = 128
MAX_IDEMPOTENCY_KEY = 256


class MarketplaceFederationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceFederationError(code, message)


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_URI", f"{path} MUST be an absolute URI")
    return value


def _bounded_tuple(values: Iterable[Any], limit: int, code: str) -> tuple[Any, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        fail("INVALID_RESOURCE_LIMIT", "resource limit MUST be a positive integer")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail(code, f"input exceeds configured limit {limit}")
    return items


def _page_limit(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_PAGE_RECORDS:
        fail("INVALID_RESOURCE_LIMIT", "page record limit MUST be within the M8 v1 bound")
    return value


def _sorted_unique_uris(values: Iterable[Any], path: str) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_CAPABILITIES, "RESOURCE_LIMIT_EXCEEDED")
    if not items:
        fail("EMPTY_SET", f"{path} MUST be non-empty")
    normalized = tuple(_require_uri(value, f"{path}[]") for value in items)
    if len(normalized) != len(set(normalized)):
        fail("NONCANONICAL_SET", f"{path} MUST contain unique values")
    if normalized != tuple(sorted(normalized, key=lambda value: value.encode("utf-8"))):
        fail("NONCANONICAL_SET", f"{path} MUST be UTF-8 sorted")
    return normalized


def validate_capability_advertisement(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_CAPABILITY_ADVERTISEMENT", "capability advertisement MUST be a map")
    required = {"version", "source", "implemented", "enabled", "configured", "limits"}
    if set(value) != required or not isinstance(value.get("version"), int) or isinstance(value.get("version"), bool) or value["version"] != 1:
        fail("INVALID_CAPABILITY_ADVERTISEMENT", "capability advertisement shape/version is invalid")
    source = _require_uri(value["source"], "source")
    implemented = _sorted_unique_uris(value["implemented"], "implemented")
    enabled = _sorted_unique_uris(value["enabled"], "enabled")
    configured = _sorted_unique_uris(value["configured"], "configured")
    if not set(enabled).issubset(implemented) or not set(configured).issubset(implemented):
        fail("CAPABILITY_STATE_INCONSISTENT", "enabled/configured capabilities MUST be implemented")
    limits = value["limits"]
    if not isinstance(limits, Mapping) or set(limits) != {
        "max_page_records", "max_cursor_bytes", "max_submission_records"
    }:
        fail("INVALID_CAPABILITY_LIMITS", "capability limits shape is invalid")
    for key, maximum in (
        ("max_page_records", MAX_PAGE_RECORDS),
        ("max_cursor_bytes", MAX_CURSOR_BYTES),
        ("max_submission_records", MAX_SUBMISSION_RECORDS),
    ):
        item = limits[key]
        if not isinstance(item, int) or isinstance(item, bool) or item < 1 or item > maximum:
            fail("INVALID_CAPABILITY_LIMITS", f"{key} is outside the v1 bound")
    return {
        "version": 1,
        "source": source,
        "implemented": implemented,
        "enabled": enabled,
        "configured": configured,
        "limits": dict(limits),
    }


def negotiate_capabilities(advertisement: Any, required_capabilities: Iterable[Any]) -> dict[str, Any]:
    ad = validate_capability_advertisement(advertisement)
    required = _sorted_unique_uris(required_capabilities, "required_capabilities")
    implemented = set(ad["implemented"])
    available = set(ad["enabled"]) & set(ad["configured"])
    unsupported = tuple(item for item in required if item not in implemented)
    unavailable = tuple(item for item in required if item in implemented and item not in available)
    if unsupported:
        status = "UNSUPPORTED"
    elif unavailable:
        status = "UNAVAILABLE"
    else:
        status = "SUPPORTED"
    return {
        "status": status,
        "required_capabilities": required,
        "unsupported_capabilities": unsupported,
        "unavailable_capabilities": unavailable,
        "no_silent_downgrade": True,
    }


def validate_scope(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_FEDERATION_SCOPE", "federation scope MUST be a map")
    if set(value) - {"version", "record_types", "profiles_all"} or not isinstance(value.get("version"), int) or isinstance(value.get("version"), bool) or value["version"] != 1:
        fail("INVALID_FEDERATION_SCOPE", "federation scope shape/version is invalid")
    record_types = _sorted_unique_uris(value.get("record_types", ()), "record_types")
    if any(item not in CORE_RECORD_TYPES for item in record_types):
        fail("UNSUPPORTED_RECORD_TYPE", "federation scope contains a non-core Marketplace record type")
    result: dict[str, Any] = {"version": 1, "record_types": record_types}
    if "profiles_all" in value:
        result["profiles_all"] = _sorted_unique_uris(value["profiles_all"], "profiles_all")
    return result


def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def scope_fingerprint(scope: Any) -> str:
    normalized = validate_scope(scope)
    return _b64url_digest(olp_encode(normalized))


def _scope_matches(record: RecordV1, scope: Mapping[str, Any]) -> bool:
    if record.type not in scope["record_types"]:
        return False
    required_profiles = set(scope.get("profiles_all", ()))
    return required_profiles.issubset(set(record.profiles))


def _validated_market_record(record: Any) -> RecordV1:
    if not isinstance(record, RecordV1):
        fail("INVALID_MARKETPLACE_RECORD", "federation item MUST be a RecordV1")
    try:
        validate_market_record(record)
    except Exception as exc:
        fail("INVALID_MARKETPLACE_RECORD", f"nonconforming Marketplace record: {exc}")
    return record


def _record_set(records: Iterable[Any], limit: int) -> tuple[dict[str, RecordV1], int]:
    unique: dict[str, RecordV1] = {}
    duplicate_count = 0
    for record in _bounded_tuple(records, limit, "RESOURCE_LIMIT_EXCEEDED"):
        record = _validated_market_record(record)
        identity = record_identity_text(record)
        prior = unique.get(identity)
        if prior is not None:
            if prior != record:
                fail("IDENTITY_COLLISION_OR_CONFLICT", "same Record Identity maps to different records")
            duplicate_count += 1
            continue
        unique[identity] = record
    return unique, duplicate_count


@dataclass(frozen=True)
class CursorBinding:
    source: str
    operation: str
    scope_fingerprint: str
    cursor: bytes


def bind_cursor(source: Any, operation: Any, scope: Any, cursor: Any) -> CursorBinding:
    source = _require_uri(source, "source")
    operation = _require_uri(operation, "operation")
    if operation not in {OP_SNAPSHOT, OP_SYNC}:
        fail("UNSUPPORTED_FEDERATION_OPERATION", "cursor operation is not snapshot or sync")
    if not isinstance(cursor, bytes) or not 1 <= len(cursor) <= MAX_CURSOR_BYTES:
        fail("INVALID_CURSOR", "cursor MUST be opaque bytes within the v1 bound")
    return CursorBinding(source, operation, scope_fingerprint(scope), cursor)


def validate_cursor_binding(
    binding: CursorBinding,
    source: Any,
    operation: Any,
    scope: Any,
) -> dict[str, Any]:
    if not isinstance(binding, CursorBinding):
        fail("INVALID_CURSOR_BINDING", "cursor binding has the wrong type")
    if binding.source != _require_uri(source, "source"):
        fail("CURSOR_SOURCE_MISMATCH", "cursor cannot be reused for another source")
    if binding.operation != _require_uri(operation, "operation"):
        fail("CURSOR_OPERATION_MISMATCH", "cursor cannot be reused for another operation")
    if binding.scope_fingerprint != scope_fingerprint(scope):
        fail("CURSOR_SCOPE_MISMATCH", "cursor cannot be reused for another scope")
    return {
        "status": "CURSOR_BOUND_TO_SOURCE_OPERATION_SCOPE",
        "cursor_bytes": len(binding.cursor),
        "authorization_proof": False,
        "source_completeness_proof": False,
    }


def _validate_page_controls(
    completeness: Any,
    has_more: Any,
    next_cursor: Any,
) -> tuple[str, bool, bytes | None]:
    if completeness not in COMPLETENESS:
        fail("INVALID_COMPLETENESS", "source completeness value is invalid")
    if not isinstance(has_more, bool):
        fail("INVALID_PAGE_STATE", "has_more MUST be boolean")
    if has_more:
        if not isinstance(next_cursor, bytes) or not 1 <= len(next_cursor) <= MAX_CURSOR_BYTES:
            fail("INVALID_CURSOR", "a truncated page requires a bounded opaque next cursor")
    elif next_cursor is not None:
        fail("UNEXPECTED_CURSOR", "a final page MUST NOT carry a next cursor")
    return completeness, has_more, next_cursor


def evaluate_exchange_page(
    records: Iterable[Any],
    *,
    source: Any,
    operation: Any,
    scope: Any,
    completeness: Any,
    has_more: Any,
    next_cursor: Any = None,
    max_records: int = MAX_PAGE_RECORDS,
) -> dict[str, Any]:
    source = _require_uri(source, "source")
    operation = _require_uri(operation, "operation")
    if operation not in {OP_SNAPSHOT, OP_SYNC}:
        fail("UNSUPPORTED_FEDERATION_OPERATION", "page operation is not snapshot or sync")
    normalized_scope = validate_scope(scope)
    max_records = _page_limit(max_records)
    completeness, has_more, next_cursor = _validate_page_controls(completeness, has_more, next_cursor)
    unique, duplicate_count = _record_set(records, max_records)
    for record in unique.values():
        if not _scope_matches(record, normalized_scope):
            fail("RECORD_OUTSIDE_SCOPE", "federation page contains a record outside the declared scope")
    record_ids = tuple(sorted(unique))
    return {
        "source": source,
        "operation": operation,
        "scope_fingerprint": scope_fingerprint(normalized_scope),
        "record_ids": record_ids,
        "record_count": len(record_ids),
        "duplicate_record_count": duplicate_count,
        "source_completeness": completeness,
        "page_truncated": has_more,
        "next_cursor_present": next_cursor is not None,
        "global_completeness": "UNKNOWN",
        "absence_is_deletion_evidence": False,
        "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_CHRONOLOGY",
    }


def merge_received_records(
    existing: Iterable[Any],
    incoming: Iterable[Any],
    *,
    max_records: int = MAX_PAGE_RECORDS,
) -> dict[str, Any]:
    max_records = _page_limit(max_records)
    existing_map, existing_duplicates = _record_set(existing, max_records)
    incoming_map, incoming_duplicates = _record_set(incoming, max_records)
    added: list[str] = []
    replayed: list[str] = []
    merged = dict(existing_map)
    for identity, record in incoming_map.items():
        prior = merged.get(identity)
        if prior is not None:
            if prior != record:
                fail("IDENTITY_COLLISION_OR_CONFLICT", "same Record Identity maps to different records")
            replayed.append(identity)
            continue
        merged[identity] = record
        added.append(identity)
    if len(merged) > max_records:
        fail("RESOURCE_LIMIT_EXCEEDED", "merged record set exceeds configured limit")
    return {
        "record_ids": tuple(sorted(merged)),
        "added_record_ids": tuple(sorted(added)),
        "replayed_record_ids": tuple(sorted(replayed)),
        "duplicate_input_count": existing_duplicates + incoming_duplicates,
        "immutable_records_mutated": False,
        "transport_exactly_once_claimed": False,
    }


def _idempotency_key(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_IDEMPOTENCY_KEY:
        fail("INVALID_IDEMPOTENCY_KEY", "idempotency key MUST be non-empty bounded text")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        fail("INVALID_IDEMPOTENCY_KEY", "idempotency key MUST NOT contain control characters")
    return value


def submission_payload_fingerprint(records: Iterable[Any]) -> str:
    unique, _ = _record_set(records, MAX_SUBMISSION_RECORDS)
    identities = tuple(sorted(unique))
    if not identities:
        fail("EMPTY_SUBMISSION", "submission MUST contain at least one record")
    return _b64url_digest(olp_encode(identities))


@dataclass(frozen=True)
class IdempotencyBinding:
    endpoint: str
    operation: str
    key: str
    payload_fingerprint: str


def bind_idempotency(
    endpoint: Any,
    operation: Any,
    key: Any,
    records: Iterable[Any],
) -> IdempotencyBinding:
    endpoint = _require_uri(endpoint, "endpoint")
    operation = _require_uri(operation, "operation")
    if operation != OP_SUBMISSION:
        fail("UNSUPPORTED_FEDERATION_OPERATION", "idempotency binding is defined for submission-v1")
    return IdempotencyBinding(
        endpoint=endpoint,
        operation=operation,
        key=_idempotency_key(key),
        payload_fingerprint=submission_payload_fingerprint(records),
    )


def validate_idempotency_replay(
    binding: IdempotencyBinding,
    endpoint: Any,
    operation: Any,
    key: Any,
    records: Iterable[Any],
) -> dict[str, Any]:
    if not isinstance(binding, IdempotencyBinding):
        fail("INVALID_IDEMPOTENCY_BINDING", "idempotency binding has the wrong type")
    if binding.endpoint != _require_uri(endpoint, "endpoint"):
        fail("IDEMPOTENCY_ENDPOINT_MISMATCH", "idempotency key cannot cross endpoint scope")
    if binding.operation != _require_uri(operation, "operation"):
        fail("IDEMPOTENCY_OPERATION_MISMATCH", "idempotency key cannot cross operation scope")
    replay_key = _idempotency_key(key)
    if binding.key != replay_key:
        fail("IDEMPOTENCY_KEY_MISMATCH", "replay key does not match the original binding")
    fingerprint = submission_payload_fingerprint(records)
    if binding.payload_fingerprint != fingerprint:
        fail("IDEMPOTENCY_PAYLOAD_MISMATCH", "same idempotency binding cannot carry different records")
    return {
        "status": "REPLAY_SAME_PAYLOAD",
        "payload_fingerprint": fingerprint,
        "duplicate_side_effects_required": False,
        "transport_exactly_once_claimed": False,
    }


def validate_submission_outcomes(
    records: Iterable[Any],
    outcomes: Iterable[Any],
) -> dict[str, Any]:
    unique, duplicate_count = _record_set(records, MAX_SUBMISSION_RECORDS)
    expected = set(unique)
    if not expected:
        fail("EMPTY_SUBMISSION", "submission MUST contain at least one record")
    seen: dict[str, str] = {}
    for item in _bounded_tuple(outcomes, MAX_SUBMISSION_RECORDS, "RESOURCE_LIMIT_EXCEEDED"):
        if not isinstance(item, Mapping) or set(item) != {"record_id", "status"}:
            fail("INVALID_SUBMISSION_OUTCOME", "submission outcome shape is invalid")
        record_id = item["record_id"]
        status = item["status"]
        if not isinstance(record_id, str) or record_id not in expected:
            fail("SUBMISSION_OUTCOME_UNKNOWN_RECORD", "outcome references a record outside the submission")
        if status not in SUBMISSION_STATUSES:
            fail("INVALID_SUBMISSION_STATUS", "submission outcome status is invalid")
        if record_id in seen:
            fail("DUPLICATE_SUBMISSION_OUTCOME", "submission result repeats a record outcome")
        seen[record_id] = status
    if set(seen) != expected:
        fail("INCOMPLETE_SUBMISSION_OUTCOMES", "submission result MUST cover each unique submitted record exactly once")
    counts = {status: 0 for status in sorted(SUBMISSION_STATUSES)}
    for status in seen.values():
        counts[status] += 1
    return {
        "record_count": len(expected),
        "duplicate_submission_record_count": duplicate_count,
        "status_counts": counts,
        "receiver_policy_is_protocol_validity": False,
        "receiver_policy_is_truth": False,
        "receiver_policy_is_trust": False,
    }


def validate_exchange_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_FEDERATION_RESULT", "federation result MUST be a map")
    required = {"version", "source", "operation", "scope_fingerprint", "record_ids", "source_completeness", "page_truncated"}
    allowed = required | {"next_cursor"}
    version = value.get("version")
    if set(value) - allowed or not required.issubset(value) or not isinstance(version, int) or isinstance(version, bool) or version != 1:
        fail("INVALID_FEDERATION_RESULT", "federation result shape/version is invalid")
    source = _require_uri(value["source"], "source")
    operation = _require_uri(value["operation"], "operation")
    if operation not in {OP_SNAPSHOT, OP_SYNC}:
        fail("UNSUPPORTED_FEDERATION_OPERATION", "result operation is unsupported")
    fingerprint = value["scope_fingerprint"]
    if not isinstance(fingerprint, str) or len(fingerprint) != 43:
        fail("INVALID_SCOPE_FINGERPRINT", "scope fingerprint MUST be canonical SHA-256 base64url text")
    try:
        raw = base64.urlsafe_b64decode(fingerprint + "=")
    except Exception:
        fail("INVALID_SCOPE_FINGERPRINT", "scope fingerprint is malformed")
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if len(raw) != 32 or canonical != fingerprint:
        fail("INVALID_SCOPE_FINGERPRINT", "scope fingerprint is non-canonical")
    record_ids = _bounded_tuple(value["record_ids"], MAX_PAGE_RECORDS, "RESOURCE_LIMIT_EXCEEDED")
    if len(record_ids) != len(set(record_ids)) or record_ids != tuple(sorted(record_ids)):
        fail("NONCANONICAL_RECORD_ID_SET", "result record_ids MUST be sorted and unique")
    for identity in record_ids:
        if not isinstance(identity, str):
            fail("INVALID_RECORD_ID", "result record id MUST be text")
        try:
            decode_identity_text(identity, expected_kind="record")
        except Exception:
            fail("INVALID_RECORD_ID", "result record id MUST be canonical OLP Record Identity text")
    completeness, truncated, next_cursor = _validate_page_controls(value["source_completeness"], value["page_truncated"], value.get("next_cursor"))
    return {"version": 1, "source": source, "operation": operation, "scope_fingerprint": fingerprint,
            "record_ids": record_ids, "source_completeness": completeness, "page_truncated": truncated,
            "next_cursor_present": next_cursor is not None, "global_completeness": "UNKNOWN",
            "absence_is_deletion_evidence": False}


def make_transport_envelope(message_type: Any, payload: Any) -> tuple[Any, ...]:
    message_type = _require_uri(message_type, "message_type")
    if message_type not in CORE_MESSAGE_TYPES:
        fail("UNSUPPORTED_FEDERATION_MESSAGE_TYPE", "message type is not an M8 core federation message")
    try:
        envelope = TransportEnvelopeV1(message_type=message_type, payload=payload)
    except Exception as exc:
        fail("INVALID_OLP_TRANSPORT_ENVELOPE", f"cannot construct OLP transport envelope: {exc}")
    return envelope.to_abstract()


def validate_exchange_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_FEDERATION_REQUEST", "federation request MUST be a map")
    required_fields = {"version", "source", "operation", "scope", "required_capabilities", "page_size"}
    allowed = required_fields | {"cursor"}
    if set(value) - allowed or not required_fields.issubset(value) or not isinstance(value.get("version"), int) or isinstance(value.get("version"), bool) or value["version"] != 1:
        fail("INVALID_FEDERATION_REQUEST", "federation request shape/version is invalid")
    source = _require_uri(value["source"], "source")
    operation = _require_uri(value["operation"], "operation")
    operation_capability = {
        OP_SNAPSHOT: CAP_SNAPSHOT,
        OP_SYNC: CAP_SYNC,
    }.get(operation)
    if operation_capability is None:
        fail("UNSUPPORTED_FEDERATION_OPERATION", "request operation is unsupported")
    scope = validate_scope(value["scope"])
    required = _sorted_unique_uris(value["required_capabilities"], "required_capabilities")
    if operation_capability not in required:
        fail("MISSING_OPERATION_CAPABILITY", "required capabilities MUST include the requested operation capability")
    page_size = value["page_size"]
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= MAX_PAGE_RECORDS:
        fail("INVALID_PAGE_SIZE", "page_size is outside the v1 bound")
    cursor = value.get("cursor")
    if cursor is not None and (not isinstance(cursor, bytes) or not 1 <= len(cursor) <= MAX_CURSOR_BYTES):
        fail("INVALID_CURSOR", "request cursor MUST be bounded opaque bytes")
    return {
        "version": 1,
        "source": source,
        "operation": operation,
        "scope": scope,
        "scope_fingerprint": scope_fingerprint(scope),
        "required_capabilities": required,
        "page_size": page_size,
        "cursor_present": cursor is not None,
    }


def validate_transport_envelope(value: Any, expected_message_type: Any) -> dict[str, Any]:
    expected = _require_uri(expected_message_type, "expected_message_type")
    if expected not in CORE_MESSAGE_TYPES:
        fail("UNSUPPORTED_FEDERATION_MESSAGE_TYPE", "expected message type is not an M8 core federation message")
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        fail("INVALID_OLP_TRANSPORT_ENVELOPE", "OLP transport envelope MUST have four elements")
    marker, version, message_type, payload = value
    if marker != "OLP-TRANSPORT":
        fail("INVALID_OLP_TRANSPORT_ENVELOPE", "transport marker is invalid")
    if not isinstance(version, int) or isinstance(version, bool):
        fail("INVALID_OLP_TRANSPORT_ENVELOPE", "transport envelope version MUST be integer")
    if version != 1:
        fail("UNSUPPORTED_TRANSPORT_ENVELOPE_VERSION", "Marketplace M8 requires OLP transport envelope v1")
    if message_type not in CORE_MESSAGE_TYPES:
        fail("UNSUPPORTED_FEDERATION_MESSAGE_TYPE", "received message type is not an M8 core federation message")
    try:
        envelope = TransportEnvelopeV1(message_type=message_type, payload=payload)
    except Exception as exc:
        fail("INVALID_OLP_TRANSPORT_ENVELOPE", f"invalid OLP transport envelope: {exc}")
    if envelope.message_type != expected:
        fail("FEDERATION_MESSAGE_TYPE_MISMATCH", "unexpected Marketplace federation message type")
    return {
        "message_type": envelope.message_type,
        "payload": envelope.payload,
        "transport_defines_record_identity": False,
        "transport_authentication_is_object_proof": False,
    }
