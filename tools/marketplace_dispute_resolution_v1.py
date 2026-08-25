"""Non-normative Marketplace dispute-resolution v1 reference helpers.

M13 evaluates exact OLP dispute relationship evidence and attributable
resolution observations under an explicit method. It does not create a court,
mutable case state, legal judgment, remedy, or universal truth.
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
from olp.evidence import parse_relationship_record
from olp.errors import ConformanceError, UnsupportedFeatureError
from olp.model.evidence import EvidenceKind, RelationshipStatementV1
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import BASE

METHOD_CORE = f"{BASE}/dispute-resolution/method/core-evidence-v1"
MAX_DISPUTES = 4096
MAX_RESOLUTIONS = 4096
MAX_SET_ITEMS = 256
MAX_CONTEXT_ENTRIES = 128
MAX_URI_BYTES = 2048

PROOF_STATUSES = frozenset({"VERIFIED", "FAILED", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE"})
ATTRIBUTION_STATUSES = frozenset({"ACCEPTED", "REJECTED", "UNKNOWN", "UNSUPPORTED"})
AUTHORITY_STATUSES = frozenset({"ACCEPTED", "REJECTED", "UNKNOWN", "UNSUPPORTED"})
LIFECYCLE_STATUSES = frozenset({"ACCEPTABLE", "ADVERSE", "UNKNOWN", "UNSUPPORTED"})

OBS_UPHOLD = "UPHOLD"
OBS_REJECT = "REJECT"
OBS_PARTIAL = "PARTIAL"
OBS_ADDITIONAL_EVIDENCE = "REQUIRE_ADDITIONAL_EVIDENCE"
OBS_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"
OBS_UNKNOWN = "UNKNOWN"
OBS_UNSUPPORTED = "UNSUPPORTED"
RESOLUTION_OBSERVATION_OUTCOMES = frozenset({
    OBS_UPHOLD,
    OBS_REJECT,
    OBS_PARTIAL,
    OBS_ADDITIONAL_EVIDENCE,
    OBS_HUMAN_REVIEW,
    OBS_UNKNOWN,
    OBS_UNSUPPORTED,
})

OUTCOME_UPHOLD = "UPHOLD_CHALLENGE_UNDER_METHOD"
OUTCOME_REJECT = "REJECT_CHALLENGE_UNDER_METHOD"
OUTCOME_PARTIAL = "PARTIAL_OR_MIXED_RESOLUTION"
OUTCOME_CONFLICT = "CONFLICTING_RESOLUTION_EVIDENCE"
OUTCOME_ADDITIONAL_EVIDENCE = "REQUIRE_ADDITIONAL_EVIDENCE"
OUTCOME_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"
OUTCOME_INDETERMINATE = "INDETERMINATE"
OUTCOME_NO_DISPUTE = "NO_ADMISSIBLE_DISPUTE"
RESULT_OUTCOMES = frozenset({
    OUTCOME_UPHOLD,
    OUTCOME_REJECT,
    OUTCOME_PARTIAL,
    OUTCOME_CONFLICT,
    OUTCOME_ADDITIONAL_EVIDENCE,
    OUTCOME_HUMAN_REVIEW,
    OUTCOME_INDETERMINATE,
    OUTCOME_NO_DISPUTE,
})


class MarketplaceDisputeResolutionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceDisputeResolutionError(code, message)


def _bounded_tuple(values: Iterable[Any], limit: int, path: str) -> tuple[Any, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        fail("INVALID_RESOURCE_LIMIT", f"{path} limit MUST be a positive integer")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail("DISPUTE_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds configured limit {limit}")
    return items


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_DISPUTE_URI", f"{path} MUST be an absolute URI")
    if len(value.encode("utf-8")) > MAX_URI_BYTES:
        fail("DISPUTE_RESOURCE_LIMIT_EXCEEDED", f"{path} URI is too long")
    return value


def _record_identity(value: Any, path: str) -> str:
    if not isinstance(value, str):
        fail("INVALID_DISPUTE_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    try:
        decode_identity_text(value, expected_kind="record")
    except Exception:
        fail("INVALID_DISPUTE_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    return value


def _sorted_unique_uris(values: Iterable[Any], path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_SET_ITEMS, path)
    if not allow_empty and not items:
        fail("EMPTY_DISPUTE_SET", f"{path} MUST be non-empty")
    out = tuple(_require_uri(item, f"{path}[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_DISPUTE_SET", f"{path} MUST be duplicate-free")
    if out != tuple(sorted(out, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_DISPUTE_SET", f"{path} MUST be UTF-8 sorted")
    return out


def _sorted_unique_record_ids(values: Iterable[Any], path: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_SET_ITEMS, path)
    if not allow_empty and not items:
        fail("EMPTY_DISPUTE_SET", f"{path} MUST be non-empty")
    out = tuple(_record_identity(item, f"{path}[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_DISPUTE_SET", f"{path} MUST be duplicate-free")
    if out != tuple(sorted(out)):
        fail("NONCANONICAL_DISPUTE_SET", f"{path} MUST be lexically sorted")
    return out


def _semantic_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_DISPUTE_CONTEXT", "context MUST be a bounded map")
    out: dict[str, Any] = {}
    for key, item in value.items():
        key = _require_uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{key!r}]")
        except Exception as exc:
            fail("INVALID_DISPUTE_CONTEXT", f"invalid OLP context value: {exc}")
        out[key] = item
    return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-8")))


def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def validate_resolution_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DISPUTE_REQUEST", "resolution request MUST be a map")
    required = {
        "version", "method", "purpose", "challenged_record_ids",
        "max_disputes", "max_resolutions",
    }
    allowed = required | {"context", "accepted_sources", "accepted_authorities", "understood_critical"}
    if set(value) - allowed or not required.issubset(value):
        fail("INVALID_DISPUTE_REQUEST", "resolution request shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_DISPUTE_REQUEST", "request version MUST be exact integer 1")
    for field, ceiling in (("max_disputes", MAX_DISPUTES), ("max_resolutions", MAX_RESOLUTIONS)):
        limit = value[field]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= ceiling:
            fail("INVALID_RESOURCE_LIMIT", f"{field} is outside the M13 v1 bound")
    return {
        "version": 1,
        "method": _require_uri(value["method"], "method"),
        "purpose": _require_uri(value["purpose"], "purpose"),
        "challenged_record_ids": _sorted_unique_record_ids(value["challenged_record_ids"], "challenged_record_ids"),
        "context": _semantic_context(value.get("context")),
        "accepted_sources": _sorted_unique_uris(value.get("accepted_sources", ()), "accepted_sources"),
        "accepted_authorities": _sorted_unique_uris(value.get("accepted_authorities", ()), "accepted_authorities"),
        "understood_critical": _sorted_unique_uris(value.get("understood_critical", ()), "understood_critical"),
        "max_disputes": value["max_disputes"],
        "max_resolutions": value["max_resolutions"],
    }


def resolution_request_fingerprint(value: Any) -> str:
    return _b64url_digest(olp_encode(validate_resolution_request(value)))


@dataclass(frozen=True)
class DisputeEvidence:
    record: RecordV1
    source: str
    authority: str
    proof_status: str
    attribution_status: str
    authority_status: str
    lifecycle_status: str


@dataclass(frozen=True)
class ResolutionObservation:
    resolution_record_id: str
    dispute_record_ids: tuple[str, ...]
    target_record_ids: tuple[str, ...]
    outcome: str
    source: str
    authority: str
    proof_status: str
    attribution_status: str
    authority_status: str
    lifecycle_status: str
    critical_uris: tuple[str, ...] = ()
    reason_uris: tuple[str, ...] = ()


def _validate_status(value: Any, allowed: frozenset[str], path: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        fail("INVALID_DISPUTE_OBSERVATION_STATUS", f"{path} is unsupported")
    return value


def _parse_dispute_record(record: Any) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    if not isinstance(record, RecordV1):
        fail("INVALID_OLP_DISPUTE", "dispute evidence record MUST be RecordV1")
    try:
        statement_preview = RelationshipStatementV1.from_value(record.content)
        statement = parse_relationship_record(
            record,
            understood_critical_qualifiers=frozenset(statement_preview.critical),
        )
    except (ConformanceError, UnsupportedFeatureError) as exc:
        fail("INVALID_OLP_DISPUTE", f"invalid OLP relationship record: {exc}")
    if statement.relation_type != "disputes":
        fail("NOT_A_DISPUTE_RELATIONSHIP", "M13 dispute evidence MUST use OLP disputes")
    if statement.subject is None or statement.subject.kind != EvidenceKind.RECORD:
        fail("INVALID_OLP_DISPUTE", "dispute relationship subject MUST be a RecordRef")
    if any(item.kind != EvidenceKind.RECORD for item in statement.objects):
        fail("INVALID_OLP_DISPUTE", "dispute relationship targets MUST all be RecordRefs")
    return (
        record_identity_text(record),
        record_identity_text(statement.subject.identity_digest),
        tuple(sorted(record_identity_text(item.identity_digest) for item in statement.objects)),
        tuple(statement.critical),
    )


def _dispute_evidence_trace(item: Any, request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(item, DisputeEvidence):
        fail("INVALID_DISPUTE_EVIDENCE", "dispute evidence MUST be DisputeEvidence")
    source = _require_uri(item.source, "dispute.source")
    authority = _require_uri(item.authority, "dispute.authority")
    proof = _validate_status(item.proof_status, PROOF_STATUSES, "dispute.proof_status")
    attribution = _validate_status(item.attribution_status, ATTRIBUTION_STATUSES, "dispute.attribution_status")
    authority_status = _validate_status(item.authority_status, AUTHORITY_STATUSES, "dispute.authority_status")
    lifecycle = _validate_status(item.lifecycle_status, LIFECYCLE_STATUSES, "dispute.lifecycle_status")
    record_id, subject_id, target_ids, critical = _parse_dispute_record(item.record)
    requested_targets = set(request["challenged_record_ids"])
    in_scope = tuple(sorted(requested_targets & set(target_ids)))
    reasons: list[str] = []
    state = "ADMISSIBLE"
    if not in_scope:
        state = "OUT_OF_SCOPE"
        reasons.append("NO_CHALLENGED_TARGET")
    elif request["accepted_sources"] and source not in request["accepted_sources"]:
        state = "EXCLUDED"
        reasons.append("SOURCE_NOT_ACCEPTED")
    elif request["accepted_authorities"] and authority not in request["accepted_authorities"]:
        state = "EXCLUDED"
        reasons.append("AUTHORITY_NOT_ACCEPTED_BY_REQUEST")
    else:
        unknown_critical = sorted(set(critical) - set(request["understood_critical"]), key=lambda v: v.encode("utf-8"))
        rejected = (
            proof == "FAILED" or attribution == "REJECTED" or
            authority_status == "REJECTED" or lifecycle == "ADVERSE"
        )
        unresolved = (
            proof in {"UNKNOWN", "UNSUPPORTED"} or
            attribution in {"UNKNOWN", "UNSUPPORTED"} or
            authority_status in {"UNKNOWN", "UNSUPPORTED"} or
            lifecycle in {"UNKNOWN", "UNSUPPORTED"}
        )
        if unknown_critical:
            state = "UNRESOLVED"
            reasons.append("UNKNOWN_CRITICAL_SEMANTICS")
        if rejected:
            state = "EXCLUDED"
            reasons.append("ADMISSIBILITY_REJECTED")
        elif unresolved and state != "UNRESOLVED":
            state = "UNRESOLVED"
            reasons.append("ADMISSIBILITY_UNRESOLVED")
    return {
        "dispute_record_id": record_id,
        "subject_record_id": subject_id,
        "target_record_ids": target_ids,
        "in_scope_target_ids": in_scope,
        "source": source,
        "authority": authority,
        "proof_status": proof,
        "attribution_status": attribution,
        "authority_status": authority_status,
        "lifecycle_status": lifecycle,
        "critical_uris": critical,
        "state": state,
        "reasons": tuple(sorted(set(reasons))),
    }


def normalize_dispute_evidence(values: Iterable[Any], request: Any) -> dict[str, Any]:
    normalized_request = validate_resolution_request(request)
    items = _bounded_tuple(values, normalized_request["max_disputes"], "disputes")
    unique: dict[bytes, dict[str, Any]] = {}
    records: dict[str, RecordV1] = {}
    duplicate_count = 0
    for raw in items:
        trace = _dispute_evidence_trace(raw, normalized_request)
        record_id = trace["dispute_record_id"]
        prior = records.get(record_id)
        if prior is not None and prior != raw.record:
            fail("DISPUTE_IDENTITY_CONFLICT", "same dispute Record Identity maps to different records")
        records[record_id] = raw.record
        key = olp_encode(trace)
        if key in unique:
            duplicate_count += 1
            continue
        unique[key] = trace
    traces = tuple(unique[key] for key in sorted(unique))
    admitted = {item["dispute_record_id"] for item in traces if item["state"] == "ADMISSIBLE"}
    unresolved = {
        item["dispute_record_id"] for item in traces
        if item["state"] == "UNRESOLVED" and item["dispute_record_id"] not in admitted
    }
    admitted_targets: dict[str, set[str]] = {}
    for item in traces:
        if item["state"] == "ADMISSIBLE":
            admitted_targets.setdefault(item["dispute_record_id"], set()).update(item["in_scope_target_ids"])
    return {
        "traces": traces,
        "admissible_dispute_ids": tuple(sorted(admitted)),
        "unresolved_dispute_ids": tuple(sorted(unresolved)),
        "admissible_target_ids_by_dispute": {
            dispute_id: tuple(sorted(admitted_targets[dispute_id]))
            for dispute_id in sorted(admitted_targets)
        },
        "duplicate_dispute_observations": duplicate_count,
    }


def validate_resolution_observation(value: Any) -> ResolutionObservation:
    if isinstance(value, ResolutionObservation):
        raw = value
    elif isinstance(value, Mapping):
        required = {
            "resolution_record_id", "dispute_record_ids", "target_record_ids", "outcome",
            "source", "authority", "proof_status", "attribution_status", "authority_status",
            "lifecycle_status", "critical_uris", "reason_uris",
        }
        if set(value) != required:
            fail("INVALID_RESOLUTION_OBSERVATION", "resolution observation shape is invalid")
        raw = ResolutionObservation(
            resolution_record_id=value["resolution_record_id"],
            dispute_record_ids=tuple(value["dispute_record_ids"]),
            target_record_ids=tuple(value["target_record_ids"]),
            outcome=value["outcome"],
            source=value["source"],
            authority=value["authority"],
            proof_status=value["proof_status"],
            attribution_status=value["attribution_status"],
            authority_status=value["authority_status"],
            lifecycle_status=value["lifecycle_status"],
            critical_uris=tuple(value["critical_uris"]),
            reason_uris=tuple(value["reason_uris"]),
        )
    else:
        fail("INVALID_RESOLUTION_OBSERVATION", "resolution observation MUST be a map or ResolutionObservation")
    normalized = ResolutionObservation(
        resolution_record_id=_record_identity(raw.resolution_record_id, "resolution_record_id"),
        dispute_record_ids=_sorted_unique_record_ids(raw.dispute_record_ids, "resolution.dispute_record_ids"),
        target_record_ids=_sorted_unique_record_ids(raw.target_record_ids, "resolution.target_record_ids"),
        outcome=_validate_status(raw.outcome, RESOLUTION_OBSERVATION_OUTCOMES, "resolution.outcome"),
        source=_require_uri(raw.source, "resolution.source"),
        authority=_require_uri(raw.authority, "resolution.authority"),
        proof_status=_validate_status(raw.proof_status, PROOF_STATUSES, "resolution.proof_status"),
        attribution_status=_validate_status(raw.attribution_status, ATTRIBUTION_STATUSES, "resolution.attribution_status"),
        authority_status=_validate_status(raw.authority_status, AUTHORITY_STATUSES, "resolution.authority_status"),
        lifecycle_status=_validate_status(raw.lifecycle_status, LIFECYCLE_STATUSES, "resolution.lifecycle_status"),
        critical_uris=_sorted_unique_uris(raw.critical_uris, "resolution.critical_uris"),
        reason_uris=_sorted_unique_uris(raw.reason_uris, "resolution.reason_uris"),
    )
    return normalized


def _resolution_wire(value: ResolutionObservation) -> dict[str, Any]:
    return {
        "resolution_record_id": value.resolution_record_id,
        "dispute_record_ids": value.dispute_record_ids,
        "target_record_ids": value.target_record_ids,
        "outcome": value.outcome,
        "source": value.source,
        "authority": value.authority,
        "proof_status": value.proof_status,
        "attribution_status": value.attribution_status,
        "authority_status": value.authority_status,
        "lifecycle_status": value.lifecycle_status,
        "critical_uris": value.critical_uris,
        "reason_uris": value.reason_uris,
    }


def _resolution_semantic_core(value: ResolutionObservation) -> dict[str, Any]:
    return {
        "resolution_record_id": value.resolution_record_id,
        "dispute_record_ids": value.dispute_record_ids,
        "target_record_ids": value.target_record_ids,
        "outcome": value.outcome,
        "critical_uris": value.critical_uris,
        "reason_uris": value.reason_uris,
    }


def _resolution_trace(
    value: ResolutionObservation,
    request: Mapping[str, Any],
    admitted_targets_by_dispute: Mapping[str, frozenset[str]],
) -> dict[str, Any]:
    reasons: list[str] = []
    state = "ADMISSIBLE"
    requested_targets = set(request["challenged_record_ids"])
    target_set = set(value.target_record_ids)
    dispute_set = set(value.dispute_record_ids)
    admitted_disputes = set(admitted_targets_by_dispute)
    if not (target_set & requested_targets):
        state = "OUT_OF_SCOPE"
        reasons.append("NO_CHALLENGED_TARGET")
    elif not target_set.issubset(requested_targets):
        state = "UNRESOLVED"
        reasons.append("TARGET_SCOPE_MISMATCH")
    elif not dispute_set.issubset(admitted_disputes):
        state = "UNRESOLVED"
        reasons.append("DISPUTE_BINDING_UNRESOLVED")
    else:
        bound_targets: set[str] = set()
        each_dispute_overlaps = True
        for dispute_id in dispute_set:
            dispute_targets = set(admitted_targets_by_dispute[dispute_id])
            bound_targets.update(dispute_targets)
            if not (target_set & dispute_targets):
                each_dispute_overlaps = False
        if not each_dispute_overlaps or not target_set.issubset(bound_targets):
            state = "UNRESOLVED"
            reasons.append("DISPUTE_TARGET_BINDING_MISMATCH")
        elif request["accepted_sources"] and value.source not in request["accepted_sources"]:
            state = "EXCLUDED"
            reasons.append("SOURCE_NOT_ACCEPTED")
        elif request["accepted_authorities"] and value.authority not in request["accepted_authorities"]:
            state = "EXCLUDED"
            reasons.append("AUTHORITY_NOT_ACCEPTED_BY_REQUEST")
        else:
            unknown_critical = set(value.critical_uris) - set(request["understood_critical"])
            rejected = (
                value.proof_status == "FAILED" or value.attribution_status == "REJECTED" or
                value.authority_status == "REJECTED" or value.lifecycle_status == "ADVERSE"
            )
            unresolved = (
                value.proof_status in {"UNKNOWN", "UNSUPPORTED"} or
                value.attribution_status in {"UNKNOWN", "UNSUPPORTED"} or
                value.authority_status in {"UNKNOWN", "UNSUPPORTED"} or
                value.lifecycle_status in {"UNKNOWN", "UNSUPPORTED"} or
                value.outcome in {OBS_UNKNOWN, OBS_UNSUPPORTED}
            )
            if unknown_critical:
                state = "UNRESOLVED"
                reasons.append("UNKNOWN_CRITICAL_SEMANTICS")
            if rejected:
                state = "EXCLUDED"
                reasons.append("ADMISSIBILITY_REJECTED")
            elif unresolved and state != "UNRESOLVED":
                state = "UNRESOLVED"
                reasons.append("ADMISSIBILITY_UNRESOLVED")
    return {**_resolution_wire(value), "state": state, "reasons": tuple(sorted(set(reasons)))}


def normalize_resolution_observations(
    values: Iterable[Any],
    request: Any,
    admissible_targets_by_dispute: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    normalized_request = validate_resolution_request(request)
    items = _bounded_tuple(values, normalized_request["max_resolutions"], "resolutions")
    admitted_targets = {
        dispute_id: frozenset(target_ids)
        for dispute_id, target_ids in admissible_targets_by_dispute.items()
    }
    unique: dict[bytes, dict[str, Any]] = {}
    semantic_by_id: dict[str, bytes] = {}
    duplicate_count = 0
    for raw in items:
        obs = validate_resolution_observation(raw)
        semantic = olp_encode(_resolution_semantic_core(obs))
        prior_semantic = semantic_by_id.get(obs.resolution_record_id)
        if prior_semantic is not None and prior_semantic != semantic:
            fail("RESOLUTION_IDENTITY_CONFLICT", "same resolution Record Identity has conflicting semantic observation")
        semantic_by_id[obs.resolution_record_id] = semantic
        trace = _resolution_trace(obs, normalized_request, admitted_targets)
        key = olp_encode(trace)
        if key in unique:
            duplicate_count += 1
            continue
        unique[key] = trace
    traces = tuple(unique[key] for key in sorted(unique))
    admitted_ids = {item["resolution_record_id"] for item in traces if item["state"] == "ADMISSIBLE"}
    unresolved_ids = {
        item["resolution_record_id"] for item in traces
        if item["state"] == "UNRESOLVED" and item["resolution_record_id"] not in admitted_ids
    }
    admitted_outcomes = tuple(
        sorted({item["outcome"] for item in traces if item["state"] == "ADMISSIBLE"})
    )
    return {
        "traces": traces,
        "admissible_resolution_ids": tuple(sorted(admitted_ids)),
        "unresolved_resolution_ids": tuple(sorted(unresolved_ids)),
        "admissible_outcomes": admitted_outcomes,
        "duplicate_resolution_observations": duplicate_count,
    }


def _aggregate_outcome(
    admissible_disputes: tuple[str, ...],
    unresolved_disputes: tuple[str, ...],
    admissible_outcomes: tuple[str, ...],
    unresolved_resolutions: tuple[str, ...],
) -> str:
    if not admissible_disputes:
        return OUTCOME_INDETERMINATE if unresolved_disputes else OUTCOME_NO_DISPUTE
    outcomes = set(admissible_outcomes)
    if not outcomes:
        return OUTCOME_INDETERMINATE if unresolved_resolutions else OUTCOME_ADDITIONAL_EVIDENCE
    if OBS_UPHOLD in outcomes and OBS_REJECT in outcomes:
        return OUTCOME_CONFLICT
    if OBS_HUMAN_REVIEW in outcomes:
        return OUTCOME_HUMAN_REVIEW
    if OBS_ADDITIONAL_EVIDENCE in outcomes:
        return OUTCOME_ADDITIONAL_EVIDENCE
    if unresolved_resolutions:
        return OUTCOME_INDETERMINATE
    if OBS_PARTIAL in outcomes:
        return OUTCOME_PARTIAL
    if OBS_UPHOLD in outcomes:
        return OUTCOME_UPHOLD
    if OBS_REJECT in outcomes:
        return OUTCOME_REJECT
    return OUTCOME_INDETERMINATE


_BOUNDARY_FIELDS = (
    "universal_truth_established",
    "legal_judgment_established",
    "challenged_record_mutated",
    "dispute_record_erased",
    "remedy_or_side_effect_implied",
    "protected_side_effect_authorized",
    "hidden_network_fallback_used",
    "resolution_is_marketplace_record",
    "result_authentication_established",
    "global_evidence_completeness_established",
)
_RESULT_CORE_FIELDS = (
    "version", "method", "purpose", "challenged_record_ids", "context",
    "admissible_dispute_ids", "unresolved_dispute_ids", "dispute_trace",
    "admissible_resolution_ids", "unresolved_resolution_ids", "resolution_trace",
    "admissible_outcomes", "outcome", "duplicate_dispute_observations",
    "duplicate_resolution_observations", "request_fingerprint", "resolution_input_fingerprint",
)


def _normalized_input(request: Any, disputes: Iterable[Any], resolutions: Iterable[Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    normalized_request = validate_resolution_request(request)
    if normalized_request["method"] != METHOD_CORE:
        fail("UNSUPPORTED_DISPUTE_RESOLUTION_METHOD", "reference evaluator supports only METHOD_CORE")
    dispute_result = normalize_dispute_evidence(disputes, normalized_request)
    resolution_result = normalize_resolution_observations(
        resolutions,
        normalized_request,
        dispute_result["admissible_target_ids_by_dispute"],
    )
    return normalized_request, dispute_result, resolution_result


def resolution_input_fingerprint(request: Any, disputes: Iterable[Any], resolutions: Iterable[Any]) -> str:
    normalized_request, dispute_result, resolution_result = _normalized_input(request, disputes, resolutions)
    projection = {
        "request": normalized_request,
        "dispute_trace": dispute_result["traces"],
        "resolution_trace": resolution_result["traces"],
    }
    return _b64url_digest(olp_encode(projection))


def evaluate_dispute_resolution(request: Any, disputes: Iterable[Any], resolutions: Iterable[Any]) -> dict[str, Any]:
    normalized_request, dispute_result, resolution_result = _normalized_input(request, disputes, resolutions)
    outcome = _aggregate_outcome(
        dispute_result["admissible_dispute_ids"],
        dispute_result["unresolved_dispute_ids"],
        resolution_result["admissible_outcomes"],
        resolution_result["unresolved_resolution_ids"],
    )
    request_fp = _b64url_digest(olp_encode(normalized_request))
    input_projection = {
        "request": normalized_request,
        "dispute_trace": dispute_result["traces"],
        "resolution_trace": resolution_result["traces"],
    }
    input_fp = _b64url_digest(olp_encode(input_projection))
    core = {
        "version": 1,
        "method": normalized_request["method"],
        "purpose": normalized_request["purpose"],
        "challenged_record_ids": normalized_request["challenged_record_ids"],
        "context": normalized_request["context"],
        "admissible_dispute_ids": dispute_result["admissible_dispute_ids"],
        "unresolved_dispute_ids": dispute_result["unresolved_dispute_ids"],
        "dispute_trace": dispute_result["traces"],
        "admissible_resolution_ids": resolution_result["admissible_resolution_ids"],
        "unresolved_resolution_ids": resolution_result["unresolved_resolution_ids"],
        "resolution_trace": resolution_result["traces"],
        "admissible_outcomes": resolution_result["admissible_outcomes"],
        "outcome": outcome,
        "duplicate_dispute_observations": dispute_result["duplicate_dispute_observations"],
        "duplicate_resolution_observations": resolution_result["duplicate_resolution_observations"],
        "request_fingerprint": request_fp,
        "resolution_input_fingerprint": input_fp,
    }
    result_fp = _b64url_digest(olp_encode(core))
    return {
        **core,
        "result_fingerprint": result_fp,
        **{field: False for field in _BOUNDARY_FIELDS},
    }


def validate_dispute_resolution_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_PRIOR_DISPUTE_RESULT", "dispute result MUST be a map")
    required = set(_RESULT_CORE_FIELDS) | set(_BOUNDARY_FIELDS) | {"result_fingerprint"}
    if set(value) != required:
        fail("INVALID_PRIOR_DISPUTE_RESULT", "dispute result shape is invalid")
    if value["outcome"] not in RESULT_OUTCOMES:
        fail("INVALID_PRIOR_DISPUTE_RESULT", "dispute result outcome is unsupported")
    if any(value[field] is not False for field in _BOUNDARY_FIELDS):
        fail("INVALID_PRIOR_DISPUTE_RESULT", "dispute result boundary flags are inconsistent")
    core = {field: value[field] for field in _RESULT_CORE_FIELDS}
    expected = _b64url_digest(olp_encode(core))
    if value["result_fingerprint"] != expected:
        fail("DISPUTE_RESULT_INTEGRITY_MISMATCH", "result fingerprint does not match result content")
    return dict(value)


def evaluate_resolution_reuse(
    prior_result: Any,
    current_request: Any,
    current_disputes: Iterable[Any],
    current_resolutions: Iterable[Any],
) -> dict[str, Any]:
    prior = validate_dispute_resolution_result(prior_result)
    current_request_fp = resolution_request_fingerprint(current_request)
    current_input_fp = resolution_input_fingerprint(current_request, current_disputes, current_resolutions)
    reasons: list[str] = []
    if prior["request_fingerprint"] != current_request_fp:
        reasons.append("RESOLUTION_REQUEST_BINDING_CHANGED")
    if prior["resolution_input_fingerprint"] != current_input_fp:
        reasons.append("RESOLUTION_EVIDENCE_BINDING_CHANGED")
    return {
        "reuse_status": "REUSABLE" if not reasons else "NOT_REUSABLE",
        "reasons": tuple(reasons),
        "current_request_fingerprint": current_request_fp,
        "current_resolution_input_fingerprint": current_input_fp,
        "prior_result_fingerprint": prior["result_fingerprint"],
        "prior_result_authentication_evaluated": False,
        "reuse_is_universal_truth": False,
        "changed_execution_or_policy_assumptions_require_reevaluation": True,
    }
