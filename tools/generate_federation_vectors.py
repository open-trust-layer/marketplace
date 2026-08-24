"""Generate Marketplace federation transport v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.transport import project_abstract

from marketplace_record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT, validate_market_record
from marketplace_federation_v1 import (
    CAP_SNAPSHOT, CAP_SUBMISSION, CAP_SYNC,
    MSG_SNAPSHOT_REQUEST, MSG_SNAPSHOT_RESULT, MSG_SYNC_REQUEST,
    OP_SNAPSHOT, OP_SUBMISSION, OP_SYNC,
    bind_cursor, bind_idempotency, evaluate_exchange_page,
    make_transport_envelope, merge_received_records, negotiate_capabilities,
    scope_fingerprint, validate_capability_advertisement, validate_cursor_binding,
    validate_exchange_request, validate_idempotency_replay,
    validate_scope, validate_submission_outcomes, validate_transport_envelope,
)

COMPLETE_FOR_DECLARED_SOURCE = 'COMPLETE_FOR_DECLARED_SOURCE'
PARTIAL_SOURCE = 'PARTIAL_SOURCE'
UNKNOWN_SOURCE = 'UNKNOWN_SOURCE'

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "federation-transport-v1.json"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_record(record_type: str, content: dict, profiles=(CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(envelope_version=1, type=record_type, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {"envelope_version": record.envelope_version, "type": record.type, "content": record.content}
    if record.semantic_bindings:
        value["semantic_bindings"] = record.semantic_bindings
    if record.profiles:
        value["profiles"] = record.profiles
    if record.relationships:
        value["relationships"] = record.relationships
    if record.extensions:
        value["extensions"] = record.extensions
    return value


def projected_record(record: RecordV1):
    return project_abstract(record_mapping(record))


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:federation:42"}
    action = {"id": "https://example.test/actions/coordinate"}
    intent = market_record(TYPE_INTENT, {
        "version": 1, "issuer": alice, "subjects": (subject,), "action": action, "terms": {},
    })
    agreement = market_record(TYPE_AGREEMENT, {
        "version": 1, "parties": sort_set((alice, bob)), "subjects": (subject,),
        "actions": (action,), "terms": {},
        "commitments": ({"id": "c1", "party": bob, "action": action, "subjects": (subject,)},),
    })
    event = market_record(TYPE_EVENT, {
        "version": 1,
        "issuer": bob,
        "event": f"{BASE}/event/federation-example",
        "subjects": (subject,),
    })
    extra_profile = "https://example.test/profiles/extra"
    intent_extra = market_record(
        TYPE_INTENT,
        {"version": 1, "issuer": bob, "subjects": (subject,), "action": action, "terms": {}},
        profiles=sort_set((CORE_PROFILE, extra_profile)),
    )

    source_a = "https://peer-a.example/federation"
    source_b = "https://peer-b.example/federation"
    caps = tuple(sorted((CAP_SNAPSHOT, CAP_SUBMISSION, CAP_SYNC)))
    limits = {"max_page_records": 100, "max_cursor_bytes": 256, "max_submission_records": 50}
    ad_all = {
        "version": 1, "source": source_a,
        "implemented": caps, "enabled": caps, "configured": caps,
        "limits": limits,
    }
    ad_sync_disabled = {
        "version": 1, "source": source_a, "implemented": caps,
        "enabled": tuple(sorted((CAP_SNAPSHOT, CAP_SUBMISSION))),
        "configured": caps, "limits": limits,
    }
    ad_no_sync = {
        "version": 1, "source": source_a,
        "implemented": tuple(sorted((CAP_SNAPSHOT, CAP_SUBMISSION))),
        "enabled": tuple(sorted((CAP_SNAPSHOT, CAP_SUBMISSION))),
        "configured": tuple(sorted((CAP_SNAPSHOT, CAP_SUBMISSION))), "limits": limits,
    }
    scope_all = {
        "version": 1,
        "record_types": tuple(sorted((TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT))),
    }
    scope_intent = {"version": 1, "record_types": (TYPE_INTENT,)}
    scope_extra = {
        "version": 1,
        "record_types": (TYPE_INTENT,),
        "profiles_all": tuple(sorted((CORE_PROFILE, extra_profile))),
    }

    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})

    add("capability-advertisement-valid", "capability_advertisement", {"advertisement": ad_all},
        validate_capability_advertisement(ad_all))
    add("capability-negotiation-supported", "capability_negotiation",
        {"advertisement": ad_all, "required": sorted((CAP_SNAPSHOT, CAP_SYNC))},
        negotiate_capabilities(ad_all, tuple(sorted((CAP_SNAPSHOT, CAP_SYNC)))))
    add("capability-negotiation-unavailable", "capability_negotiation",
        {"advertisement": ad_sync_disabled, "required": [CAP_SYNC]},
        negotiate_capabilities(ad_sync_disabled, (CAP_SYNC,)))
    add("capability-negotiation-unsupported", "capability_negotiation",
        {"advertisement": ad_no_sync, "required": [CAP_SYNC]},
        negotiate_capabilities(ad_no_sync, (CAP_SYNC,)))
    add("scope-fingerprint-stable", "scope", {"scope": scope_all}, {
        "scope": validate_scope(scope_all), "fingerprint": scope_fingerprint(scope_all),
    })
    add("scope-profile-filter", "scope", {"scope": scope_extra}, {
        "scope": validate_scope(scope_extra), "fingerprint": scope_fingerprint(scope_extra),
    })

    snapshot_request = {
        "version": 1, "source": source_a, "operation": OP_SNAPSHOT,
        "scope": scope_all, "required_capabilities": (CAP_SNAPSHOT,), "page_size": 50,
    }
    sync_request = {
        "version": 1, "source": source_a, "operation": OP_SYNC,
        "scope": scope_intent, "required_capabilities": (CAP_SYNC,), "page_size": 25,
    }
    add("snapshot-request-valid", "request", {"request": snapshot_request},
        validate_exchange_request(snapshot_request))
    add("sync-request-valid", "request", {"request": sync_request},
        validate_exchange_request(sync_request))
    sync_cursor_request = dict(sync_request)
    sync_cursor_request["cursor"] = b"sync-cursor-1"
    sync_cursor_wire = dict(sync_request)
    sync_cursor_wire["cursor"] = "sync-cursor-1"
    add("sync-request-carries-opaque-cursor", "request", {"request": sync_cursor_wire}, validate_exchange_request(sync_cursor_request))

    page_complete = evaluate_exchange_page(
        (intent, agreement, event), source=source_a, operation=OP_SNAPSHOT,
        scope=scope_all, completeness=COMPLETE_FOR_DECLARED_SOURCE,
        has_more=False,
    )
    add("snapshot-complete-page", "page", {
        "records": [projected_record(intent), projected_record(agreement), projected_record(event)],
        "source": source_a, "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": COMPLETE_FOR_DECLARED_SOURCE, "has_more": False,
    }, page_complete)
    page_truncated = evaluate_exchange_page(
        (intent,), source=source_a, operation=OP_SNAPSHOT,
        scope=scope_all, completeness=PARTIAL_SOURCE,
        has_more=True, next_cursor=b"page-2",
    )
    add("snapshot-truncated-page-explicit", "page", {
        "records": [projected_record(intent)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": True, "next_cursor": "page-2",
    }, page_truncated)

    sync_page = evaluate_exchange_page(
        (intent, intent), source=source_a, operation=OP_SYNC,
        scope=scope_intent, completeness=UNKNOWN_SOURCE,
        has_more=False,
    )
    add("sync-page-deduplicates-record-identity", "page", {
        "records": [projected_record(intent), projected_record(intent)],
        "source": source_a, "operation": OP_SYNC, "scope": scope_intent,
        "completeness": UNKNOWN_SOURCE, "has_more": False,
    }, sync_page)

    profile_page = evaluate_exchange_page(
        (intent_extra,), source=source_a, operation=OP_SNAPSHOT,
        scope=scope_extra, completeness=PARTIAL_SOURCE, has_more=False,
    )
    add("scope-profile-record-accepted", "page", {
        "records": [projected_record(intent_extra)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_extra,
        "completeness": PARTIAL_SOURCE, "has_more": False,
    }, profile_page)
    merge_new = merge_received_records((intent,), (agreement, event))
    add("merge-received-adds-distinct-records", "merge", {
        "existing": [projected_record(intent)],
        "incoming": [projected_record(agreement), projected_record(event)],
    }, merge_new)
    merge_replay = merge_received_records((intent, agreement), (intent, agreement))
    add("merge-replay-is-idempotent", "merge", {
        "existing": [projected_record(intent), projected_record(agreement)],
        "incoming": [projected_record(intent), projected_record(agreement)],
    }, merge_replay)
    merge_duplicate_input = merge_received_records((), (intent, intent, agreement))
    add("merge-duplicate-input-counted-once", "merge", {
        "existing": [],
        "incoming": [projected_record(intent), projected_record(intent), projected_record(agreement)],
    }, merge_duplicate_input)

    cursor = bind_cursor(source_a, OP_SYNC, scope_intent, b"sync-cursor-1")
    add("cursor-bound-to-source-operation-scope", "cursor", {
        "origin_source": source_a, "origin_operation": OP_SYNC, "origin_scope": scope_intent,
        "cursor": "sync-cursor-1", "check_source": source_a,
        "check_operation": OP_SYNC, "check_scope": scope_intent,
    }, validate_cursor_binding(cursor, source_a, OP_SYNC, scope_intent))
    snapshot_cursor = bind_cursor(source_a, OP_SNAPSHOT, scope_all, b"snapshot-page-2")
    add("snapshot-cursor-binding", "cursor", {
        "origin_source": source_a, "origin_operation": OP_SNAPSHOT, "origin_scope": scope_all,
        "cursor": "snapshot-page-2", "check_source": source_a,
        "check_operation": OP_SNAPSHOT, "check_scope": scope_all,
    }, validate_cursor_binding(snapshot_cursor, source_a, OP_SNAPSHOT, scope_all))
    idem = bind_idempotency(source_a, OP_SUBMISSION, "submit-42", (intent, agreement))
    add("idempotency-same-payload-replay", "idempotency", {
        "origin_endpoint": source_a, "origin_operation": OP_SUBMISSION,
        "origin_key": "submit-42", "origin_records": [projected_record(intent), projected_record(agreement)],
        "check_endpoint": source_a, "check_operation": OP_SUBMISSION, "check_key": "submit-42",
        "check_records": [projected_record(agreement), projected_record(intent)],
    }, validate_idempotency_replay(idem, source_a, OP_SUBMISSION, "submit-42", (agreement, intent)))

    outcomes = (
        {"record_id": record_identity_text(intent), "status": "RECEIVER_ACCEPTED"},
        {"record_id": record_identity_text(agreement), "status": "RECEIVER_DEFERRED"},
    )
    add("submission-outcomes-local-policy", "submission", {
        "records": [projected_record(intent), projected_record(agreement)],
        "outcomes": list(outcomes),
    }, validate_submission_outcomes((intent, agreement), outcomes))
    duplicate_submission_outcomes = (
        {"record_id": record_identity_text(intent), "status": "RECEIVER_ACCEPTED"},
    )
    add("duplicate-submitted-record-requires-one-outcome", "submission", {
        "records": [projected_record(intent), projected_record(intent)],
        "outcomes": list(duplicate_submission_outcomes),
    }, validate_submission_outcomes((intent, intent), duplicate_submission_outcomes))

    envelope = make_transport_envelope(MSG_SNAPSHOT_REQUEST, snapshot_request)
    add("olp-extension-envelope-snapshot-request", "envelope", {
        "message_type": MSG_SNAPSHOT_REQUEST, "payload": snapshot_request,
        "expected_message_type": MSG_SNAPSHOT_REQUEST,
    }, validate_transport_envelope(envelope, MSG_SNAPSHOT_REQUEST))
    sync_envelope = make_transport_envelope(MSG_SYNC_REQUEST, sync_request)
    add("olp-extension-envelope-sync-request", "envelope", {
        "message_type": MSG_SYNC_REQUEST, "payload": sync_request,
        "expected_message_type": MSG_SYNC_REQUEST,
    }, validate_transport_envelope(sync_envelope, MSG_SYNC_REQUEST))
    result_payload = {"source": source_a, "record_ids": page_complete["record_ids"]}
    result_envelope = make_transport_envelope(MSG_SNAPSHOT_RESULT, result_payload)
    add("olp-extension-envelope-snapshot-result", "envelope", {
        "message_type": MSG_SNAPSHOT_RESULT, "payload": jsonable(result_payload),
        "expected_message_type": MSG_SNAPSHOT_RESULT,
    }, validate_transport_envelope(result_envelope, MSG_SNAPSHOT_RESULT))

    third_party_cap = "https://example.test/capability/vendor-extension-v1"
    ad_extension = {
        "version": 1, "source": source_a,
        "implemented": tuple(sorted(caps + (third_party_cap,))),
        "enabled": tuple(sorted(caps + (third_party_cap,))),
        "configured": tuple(sorted(caps + (third_party_cap,))), "limits": limits,
    }
    add("absolute-uri-extension-capability-preserved", "capability_advertisement",
        {"advertisement": ad_extension}, validate_capability_advertisement(ad_extension))
    add("unknown-optional-capability-does-not-block-known-required", "capability_negotiation",
        {"advertisement": ad_extension, "required": [CAP_SNAPSHOT]},
        negotiate_capabilities(ad_extension, (CAP_SNAPSHOT,)))

    # Negative/adversarial vectors.
    bad_ad_shape = dict(ad_all)
    bad_ad_shape["extra"] = True
    negative("capability-advertisement-extra-field", "capability_advertisement",
        {"advertisement": bad_ad_shape}, "INVALID_CAPABILITY_ADVERTISEMENT")
    bad_ad_version = dict(ad_all)
    bad_ad_version["version"] = 2
    negative("capability-advertisement-version", "capability_advertisement",
        {"advertisement": bad_ad_version}, "INVALID_CAPABILITY_ADVERTISEMENT")
    bad_ad_source = dict(ad_all)
    bad_ad_source["source"] = "not-a-uri"
    negative("capability-advertisement-source-uri", "capability_advertisement",
        {"advertisement": bad_ad_source}, "INVALID_URI")
    bad_ad_unsorted = dict(ad_all)
    bad_ad_unsorted["implemented"] = tuple(reversed(caps))
    negative("capability-advertisement-unsorted-set", "capability_advertisement",
        {"advertisement": bad_ad_unsorted}, "NONCANONICAL_SET")
    bad_ad_duplicate = dict(ad_all)
    bad_ad_duplicate["implemented"] = tuple(sorted(caps + (CAP_SYNC,)))
    negative("capability-advertisement-duplicate-set", "capability_advertisement",
        {"advertisement": bad_ad_duplicate}, "NONCANONICAL_SET")
    bad_state = dict(ad_no_sync)
    bad_state["enabled"] = caps
    negative("capability-state-unimplemented-enabled", "capability_advertisement",
        {"advertisement": bad_state}, "CAPABILITY_STATE_INCONSISTENT")
    bad_limits = dict(ad_all)
    bad_limits["limits"] = dict(limits)
    bad_limits["limits"]["max_cursor_bytes"] = 5000
    negative("capability-limit-too-large", "capability_advertisement",
        {"advertisement": bad_limits}, "INVALID_CAPABILITY_LIMITS")
    negative("required-capability-duplicate", "capability_negotiation",
        {"advertisement": ad_all, "required": [CAP_SYNC, CAP_SYNC]}, "NONCANONICAL_SET")

    negative("scope-empty-record-types", "scope", {
        "scope": {"version": 1, "record_types": []},
    }, "EMPTY_SET")
    negative("scope-unsupported-record-type", "scope", {
        "scope": {"version": 1, "record_types": [f"{BASE}/record/unknown"]},
    }, "UNSUPPORTED_RECORD_TYPE")
    negative("scope-unsorted-record-types", "scope", {
        "scope": {"version": 1, "record_types": list(reversed(scope_all["record_types"]))},
    }, "NONCANONICAL_SET")
    negative("scope-invalid-profile-uri", "scope", {
        "scope": {"version": 1, "record_types": [TYPE_INTENT], "profiles_all": ["not-a-uri"]},
    }, "INVALID_URI")

    bad_request_cursor = dict(sync_request)
    bad_request_cursor["cursor"] = True
    negative("request-invalid-cursor-type", "request", {"request": bad_request_cursor}, "INVALID_CURSOR")
    empty_request_cursor = dict(sync_request)
    empty_request_cursor["cursor"] = ""
    negative("request-empty-cursor", "request", {"request": empty_request_cursor}, "INVALID_CURSOR")
    bad_request_missing_cap = dict(snapshot_request)
    bad_request_missing_cap["required_capabilities"] = (CAP_SYNC,)
    negative("request-missing-operation-capability", "request",
        {"request": bad_request_missing_cap}, "MISSING_OPERATION_CAPABILITY")
    bad_request_size = dict(snapshot_request)
    bad_request_size["page_size"] = 10001
    negative("request-page-size-limit", "request",
        {"request": bad_request_size}, "INVALID_PAGE_SIZE")
    bad_request_operation = dict(snapshot_request)
    bad_request_operation["operation"] = "https://example.test/operation/unknown"
    negative("request-unsupported-operation", "request",
        {"request": bad_request_operation}, "UNSUPPORTED_FEDERATION_OPERATION")

    negative("page-invalid-completeness", "page", {
        "records": [projected_record(intent)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": "GLOBAL_COMPLETE", "has_more": False,
    }, "INVALID_COMPLETENESS")
    negative("page-truncated-without-cursor", "page", {
        "records": [projected_record(intent)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": True,
    }, "INVALID_CURSOR")
    negative("page-final-with-cursor", "page", {
        "records": [projected_record(intent)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": False, "next_cursor": "extra",
    }, "UNEXPECTED_CURSOR")
    negative("page-record-outside-scope", "page", {
        "records": [projected_record(agreement)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_intent,
        "completeness": PARTIAL_SOURCE, "has_more": False,
    }, "RECORD_OUTSIDE_SCOPE")
    negative("page-resource-limit", "page", {
        "records": [projected_record(intent), projected_record(agreement)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": False, "max_records": 1,
    }, "RESOURCE_LIMIT_EXCEEDED")
    other_record = RecordV1(
        envelope_version=1,
        type="https://example.test/types/not-marketplace",
        content={"value": 1},
    )
    negative("page-non-marketplace-record", "page", {
        "records": [projected_record(other_record)], "source": source_a,
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": False,
    }, "INVALID_MARKETPLACE_RECORD")

    negative("cursor-source-mismatch", "cursor", {
        "origin_source": source_a, "origin_operation": OP_SYNC, "origin_scope": scope_intent,
        "cursor": "sync-cursor-1", "check_source": source_b,
        "check_operation": OP_SYNC, "check_scope": scope_intent,
    }, "CURSOR_SOURCE_MISMATCH")
    negative("cursor-operation-mismatch", "cursor", {
        "origin_source": source_a, "origin_operation": OP_SYNC, "origin_scope": scope_intent,
        "cursor": "sync-cursor-1", "check_source": source_a,
        "check_operation": OP_SNAPSHOT, "check_scope": scope_intent,
    }, "CURSOR_OPERATION_MISMATCH")
    negative("cursor-scope-mismatch", "cursor", {
        "origin_source": source_a, "origin_operation": OP_SYNC, "origin_scope": scope_intent,
        "cursor": "sync-cursor-1", "check_source": source_a,
        "check_operation": OP_SYNC, "check_scope": scope_all,
    }, "CURSOR_SCOPE_MISMATCH")
    negative("cursor-empty", "cursor_bind", {
        "source": source_a, "operation": OP_SYNC, "scope": scope_intent, "cursor": "",
    }, "INVALID_CURSOR")
    negative("cursor-unsupported-operation", "cursor_bind", {
        "source": source_a, "operation": OP_SUBMISSION, "scope": scope_intent, "cursor": "x",
    }, "UNSUPPORTED_FEDERATION_OPERATION")

    negative("idempotency-payload-mismatch", "idempotency", {
        "origin_endpoint": source_a, "origin_operation": OP_SUBMISSION,
        "origin_key": "submit-42", "origin_records": [projected_record(intent)],
        "check_endpoint": source_a, "check_operation": OP_SUBMISSION, "check_key": "submit-42",
        "check_records": [projected_record(agreement)],
    }, "IDEMPOTENCY_PAYLOAD_MISMATCH")
    negative("idempotency-endpoint-mismatch", "idempotency", {
        "origin_endpoint": source_a, "origin_operation": OP_SUBMISSION,
        "origin_key": "submit-42", "origin_records": [projected_record(intent)],
        "check_endpoint": source_b, "check_operation": OP_SUBMISSION, "check_key": "submit-42",
        "check_records": [projected_record(intent)],
    }, "IDEMPOTENCY_ENDPOINT_MISMATCH")
    negative("idempotency-key-mismatch", "idempotency", {
        "origin_endpoint": source_a, "origin_operation": OP_SUBMISSION,
        "origin_key": "submit-42", "origin_records": [projected_record(intent)],
        "check_endpoint": source_a, "check_operation": OP_SUBMISSION, "check_key": "submit-43",
        "check_records": [projected_record(intent)],
    }, "IDEMPOTENCY_KEY_MISMATCH")
    negative("idempotency-operation-mismatch", "idempotency", {
        "origin_endpoint": source_a, "origin_operation": OP_SUBMISSION,
        "origin_key": "submit-42", "origin_records": [projected_record(intent)],
        "check_endpoint": source_a, "check_operation": OP_SYNC, "check_key": "submit-42",
        "check_records": [projected_record(intent)],
    }, "IDEMPOTENCY_OPERATION_MISMATCH")
    negative("idempotency-invalid-key", "idempotency_bind", {
        "endpoint": source_a, "operation": OP_SUBMISSION, "key": "", "records": [projected_record(intent)],
    }, "INVALID_IDEMPOTENCY_KEY")
    negative("idempotency-empty-submission", "idempotency_bind", {
        "endpoint": source_a, "operation": OP_SUBMISSION, "key": "submit-empty", "records": [],
    }, "EMPTY_SUBMISSION")
    negative("idempotency-wrong-bind-operation", "idempotency_bind", {
        "endpoint": source_a, "operation": OP_SYNC, "key": "submit-42", "records": [projected_record(intent)],
    }, "UNSUPPORTED_FEDERATION_OPERATION")

    unknown_outcome = [{"record_id": record_identity_text(event), "status": "RECEIVER_ACCEPTED"}]
    negative("submission-outcome-unknown-record", "submission", {
        "records": [projected_record(intent)], "outcomes": unknown_outcome,
    }, "SUBMISSION_OUTCOME_UNKNOWN_RECORD")
    duplicate_outcomes = [
        {"record_id": record_identity_text(intent), "status": "RECEIVER_ACCEPTED"},
        {"record_id": record_identity_text(intent), "status": "RECEIVER_DEFERRED"},
    ]
    negative("submission-outcome-duplicate", "submission", {
        "records": [projected_record(intent)], "outcomes": duplicate_outcomes,
    }, "DUPLICATE_SUBMISSION_OUTCOME")
    negative("submission-outcome-incomplete", "submission", {
        "records": [projected_record(intent), projected_record(agreement)],
        "outcomes": [{"record_id": record_identity_text(intent), "status": "RECEIVER_ACCEPTED"}],
    }, "INCOMPLETE_SUBMISSION_OUTCOMES")
    negative("submission-outcome-invalid-status", "submission", {
        "records": [projected_record(intent)],
        "outcomes": [{"record_id": record_identity_text(intent), "status": "TRUSTED"}],
    }, "INVALID_SUBMISSION_STATUS")
    negative("submission-outcome-invalid-shape", "submission", {
        "records": [projected_record(intent)],
        "outcomes": [{"record_id": record_identity_text(intent), "status": "RECEIVER_ACCEPTED", "truth": True}],
    }, "INVALID_SUBMISSION_OUTCOME")

    negative("envelope-message-type-mismatch", "envelope", {
        "message_type": MSG_SNAPSHOT_REQUEST, "payload": snapshot_request,
        "expected_message_type": MSG_SYNC_REQUEST,
    }, "FEDERATION_MESSAGE_TYPE_MISMATCH")
    negative("envelope-non-uri-message-type", "envelope_make", {
        "message_type": "marketplaceSnapshot", "payload": snapshot_request,
    }, "INVALID_URI")
    negative("envelope-invalid-marker", "envelope_raw", {
        "envelope": ["MARKETPLACE", 1, MSG_SNAPSHOT_REQUEST, snapshot_request],
        "expected_message_type": MSG_SNAPSHOT_REQUEST,
    }, "INVALID_OLP_TRANSPORT_ENVELOPE")
    negative("envelope-future-version", "envelope_raw", {
        "envelope": ["OLP-TRANSPORT", 2, MSG_SNAPSHOT_REQUEST, snapshot_request],
        "expected_message_type": MSG_SNAPSHOT_REQUEST,
    }, "UNSUPPORTED_TRANSPORT_ENVELOPE_VERSION")
    negative("envelope-wrong-cardinality", "envelope_raw", {
        "envelope": ["OLP-TRANSPORT", 1, MSG_SNAPSHOT_REQUEST],
        "expected_message_type": MSG_SNAPSHOT_REQUEST,
    }, "INVALID_OLP_TRANSPORT_ENVELOPE")

    ad_bool_version = dict(ad_all)
    ad_bool_version["version"] = True
    negative("capability-boolean-version", "capability_advertisement", {"advertisement": ad_bool_version}, "INVALID_CAPABILITY_ADVERTISEMENT")
    scope_bool_version = dict(scope_all)
    scope_bool_version["version"] = True
    negative("scope-boolean-version", "scope", {"scope": scope_bool_version}, "INVALID_FEDERATION_SCOPE")
    request_bool_version = dict(snapshot_request)
    request_bool_version["version"] = True
    negative("request-boolean-version", "request", {"request": request_bool_version}, "INVALID_FEDERATION_REQUEST")
    negative("envelope-boolean-version", "envelope_raw", {
        "envelope": ["OLP-TRANSPORT", True, MSG_SNAPSHOT_REQUEST, snapshot_request],
        "expected_message_type": MSG_SNAPSHOT_REQUEST,
    }, "INVALID_OLP_TRANSPORT_ENVELOPE")
    negative("submission-outcome-empty-submission", "submission", {"records": [], "outcomes": []}, "EMPTY_SUBMISSION")

    bad_request_extra = dict(snapshot_request)
    bad_request_extra["offset"] = 1
    negative("request-undeclared-field", "request", {"request": bad_request_extra},
        "INVALID_FEDERATION_REQUEST")
    negative("page-invalid-source-uri", "page", {
        "records": [projected_record(intent)], "source": "not-a-uri",
        "operation": OP_SNAPSHOT, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": False,
    }, "INVALID_URI")
    negative("page-unsupported-operation", "page", {
        "records": [projected_record(intent)], "source": source_a,
        "operation": OP_SUBMISSION, "scope": scope_all,
        "completeness": PARTIAL_SOURCE, "has_more": False,
    }, "UNSUPPORTED_FEDERATION_OPERATION")
    negative("merge-combined-resource-limit", "merge", {
        "existing": [projected_record(intent)], "incoming": [projected_record(agreement)], "max_records": 1,
    }, "RESOURCE_LIMIT_EXCEEDED")
    negative("merge-resource-limit", "merge", {
        "existing": [], "incoming": [projected_record(intent), projected_record(agreement)], "max_records": 1,
    }, "RESOURCE_LIMIT_EXCEEDED")
    return {
        "format": "marketplace-federation-transport-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "cases": cases,
        "negative_cases": negative_cases,
        "identities": {
            "intent": record_identity_text(intent),
            "agreement": record_identity_text(agreement),
            "event": record_identity_text(event),
        },
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    for key, value in data["identities"].items():
        print(key, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
