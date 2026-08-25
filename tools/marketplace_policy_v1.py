"""Non-normative Marketplace safety/policy/authorization v1 helpers.

M11 aggregates explicit local policy observations into a reproducible,
method-relative PolicyDecision process result. It does not turn OLP authority
evidence, proof validity, trust, legality, moderation, or Marketplace validity
into universal permission or prohibition.
"""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Mapping

from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.model.proof import parse_rfc3339
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import BASE

METHOD_CORE = f"{BASE}/policy/method/core-authorization-v1"

OP_LOCAL_INSPECTION = f"{BASE}/policy/operation/local-inspection"
OP_DISCOVERY_VISIBILITY = f"{BASE}/policy/operation/discovery-visibility"
OP_DISPLAY = f"{BASE}/policy/operation/display"
OP_SUBMISSION = f"{BASE}/policy/operation/submission-ingestion"
OP_NEGOTIATION = f"{BASE}/policy/operation/negotiation-handling"
OP_AUTONOMOUS_EXECUTION = f"{BASE}/policy/operation/autonomous-execution"
OP_FULFILLMENT_SIDE_EFFECT = f"{BASE}/policy/operation/fulfillment-side-effect"
OP_SETTLEMENT_SIDE_EFFECT = f"{BASE}/policy/operation/settlement-side-effect"
OP_FEDERATION_EXCHANGE = f"{BASE}/policy/operation/federation-exchange"
OP_DISCLOSURE = f"{BASE}/policy/operation/disclosure"
OP_TRUST_RESULT_CONSUMPTION = f"{BASE}/policy/operation/trust-result-consumption"

CORE_OPERATIONS = frozenset({
    OP_LOCAL_INSPECTION,
    OP_DISCOVERY_VISIBILITY,
    OP_DISPLAY,
    OP_SUBMISSION,
    OP_NEGOTIATION,
    OP_AUTONOMOUS_EXECUTION,
    OP_FULFILLMENT_SIDE_EFFECT,
    OP_SETTLEMENT_SIDE_EFFECT,
    OP_FEDERATION_EXCHANGE,
    OP_DISCLOSURE,
    OP_TRUST_RESULT_CONSUMPTION,
})
PROTECTED_OPERATIONS = CORE_OPERATIONS - {OP_LOCAL_INSPECTION}
SIDE_EFFECT_OPERATIONS = frozenset({
    OP_SUBMISSION,
    OP_AUTONOMOUS_EXECUTION,
    OP_FULFILLMENT_SIDE_EFFECT,
    OP_SETTLEMENT_SIDE_EFFECT,
    OP_FEDERATION_EXCHANGE,
    OP_DISCLOSURE,
})

DIM_EVIDENCE_VALIDITY = "evidence-validity"
DIM_PROOF_VALIDITY = "proof-validity"
DIM_AUTHENTICATION = "authentication"
DIM_ATTRIBUTION = "attribution"
DIM_IDENTITY = "identity"
DIM_AUTHORITY = "authority"
DIM_DELEGATION = "delegation"
DIM_LIFECYCLE = "lifecycle"
DIM_AUTHORIZATION = "authorization"
DIM_TRUST = "trust"
DIM_LEGAL_COMPLIANCE = "legal-compliance"
DIM_SAFETY = "safety"
DIM_BUSINESS_POLICY = "business-policy"
DIM_MODERATION = "moderation"
CORE_DIMENSIONS = frozenset({
    DIM_EVIDENCE_VALIDITY,
    DIM_PROOF_VALIDITY,
    DIM_AUTHENTICATION,
    DIM_ATTRIBUTION,
    DIM_IDENTITY,
    DIM_AUTHORITY,
    DIM_DELEGATION,
    DIM_LIFECYCLE,
    DIM_AUTHORIZATION,
    DIM_TRUST,
    DIM_LEGAL_COMPLIANCE,
    DIM_SAFETY,
    DIM_BUSINESS_POLICY,
    DIM_MODERATION,
})

OBS_SATISFIED = "SATISFIED"
OBS_UNSATISFIED = "UNSATISFIED"
OBS_UNKNOWN = "UNKNOWN"
OBS_UNSUPPORTED = "UNSUPPORTED"
OBS_NOT_APPLICABLE = "NOT_APPLICABLE"
OBS_ADDITIONAL_EVIDENCE = "REQUIRE_ADDITIONAL_EVIDENCE"
OBS_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"
OBS_QUARANTINE = "QUARANTINE"
OBSERVATION_STATUSES = frozenset({
    OBS_SATISFIED,
    OBS_UNSATISFIED,
    OBS_UNKNOWN,
    OBS_UNSUPPORTED,
    OBS_NOT_APPLICABLE,
    OBS_ADDITIONAL_EVIDENCE,
    OBS_HUMAN_REVIEW,
    OBS_QUARANTINE,
})

OUTCOME_ALLOW = "ALLOW"
OUTCOME_DENY = "DENY"
OUTCOME_ADDITIONAL_EVIDENCE = "REQUIRE_ADDITIONAL_EVIDENCE"
OUTCOME_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"
OUTCOME_QUARANTINE = "QUARANTINE"
OUTCOME_CONFLICTING = "CONFLICTING_POLICY"
OUTCOME_INDETERMINATE = "INDETERMINATE"
OUTCOME_NOT_APPLICABLE = "NOT_APPLICABLE"

OUTCOMES = frozenset({
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    OUTCOME_ADDITIONAL_EVIDENCE,
    OUTCOME_HUMAN_REVIEW,
    OUTCOME_QUARANTINE,
    OUTCOME_CONFLICTING,
    OUTCOME_INDETERMINATE,
    OUTCOME_NOT_APPLICABLE,
})
MAX_REQUIRED_DIMENSIONS = 32
MAX_OBSERVATIONS = 4096
MAX_EVIDENCE_IDS_PER_OBSERVATION = 256
MAX_CONTEXT_ENTRIES = 128
MAX_URI_BYTES = 2048


class MarketplacePolicyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplacePolicyError(code, message)


def _bounded_tuple(values: Iterable[Any], limit: int, path: str) -> tuple[Any, ...]:
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail("POLICY_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds M11 v1 limit {limit}")
    return items


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_POLICY_URI", f"{path} MUST be an absolute URI")
    if len(value.encode("utf-8")) > MAX_URI_BYTES:
        fail("POLICY_RESOURCE_LIMIT_EXCEEDED", f"{path} URI is too long")
    return value
def _canonical_time(value: Any, path: str) -> str:
    if not isinstance(value, str):
        fail("INVALID_POLICY_TIME", f"{path} MUST be RFC 3339 text")
    try:
        parse_rfc3339(value)
    except Exception as exc:
        fail("INVALID_POLICY_TIME", f"{path} MUST be valid RFC 3339: {exc}")
    return value


def _record_identity(value: Any, path: str) -> str:
    if not isinstance(value, str):
        fail("INVALID_POLICY_TARGET", f"{path} MUST be canonical OLP Record Identity text")
    try:
        decode_identity_text(value, expected_kind="record")
    except Exception:
        fail("INVALID_POLICY_TARGET", f"{path} MUST be canonical OLP Record Identity text")
    return value


def _semantic_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_POLICY_CONTEXT", "context MUST be a bounded map")
    out: dict[str, Any] = {}
    for key, item in value.items():
        key = _require_uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{key!r}]")
        except Exception as exc:
            fail("INVALID_POLICY_CONTEXT", f"invalid OLP context value: {exc}")
        out[key] = item
    return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-8")))
def _target(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"kind", "value"}:
        fail("INVALID_POLICY_TARGET", "target MUST contain exactly kind and value")
    kind = value["kind"]
    raw = value["value"]
    if kind == "record":
        return {"kind": kind, "value": _record_identity(raw, "target.value")}
    if kind in {"principal", "subject-uri", "resource-uri"}:
        return {"kind": kind, "value": _require_uri(raw, "target.value")}
    fail("INVALID_POLICY_TARGET", "target.kind is unsupported")


def _sorted_dimensions(values: Iterable[Any]) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_REQUIRED_DIMENSIONS, "required_dimensions")
    out: list[str] = []
    for item in items:
        if not isinstance(item, str) or item not in CORE_DIMENSIONS:
            fail("UNSUPPORTED_POLICY_DIMENSION", "required_dimensions contains unsupported dimension")
        out.append(item)
    result = tuple(out)
    if len(result) != len(set(result)):
        fail("NONCANONICAL_POLICY_SET", "required_dimensions MUST be duplicate-free")
    if result != tuple(sorted(result, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_POLICY_SET", "required_dimensions MUST be UTF-8 sorted")
    return result


def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
def validate_policy_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_POLICY_REQUEST", "policy request MUST be a map")
    required = {
        "version",
        "method",
        "decision_scope",
        "operation",
        "actor",
        "target",
        "evaluation_time",
        "required_dimensions",
    }
    allowed = required | {"context"}
    if set(value) - allowed or not required.issubset(value):
        fail("INVALID_POLICY_REQUEST", "policy request shape is invalid")
    version = value["version"]
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        fail("INVALID_POLICY_REQUEST", "policy request version MUST be exact integer 1")
    operation = _require_uri(value["operation"], "operation")
    if operation not in CORE_OPERATIONS:
        fail("UNSUPPORTED_POLICY_OPERATION", "operation is not an M11 core operation")
    dimensions = _sorted_dimensions(value["required_dimensions"])
    if operation in PROTECTED_OPERATIONS and not dimensions:
        fail("POLICY_DIMENSION_REQUIRED", "protected operation requires explicit policy dimensions")
    if operation in SIDE_EFFECT_OPERATIONS and DIM_AUTHORIZATION not in dimensions:
        fail("AUTHORIZATION_DIMENSION_REQUIRED", "protected side effect requires authorization dimension")
    return {
        "version": 1,
        "method": _require_uri(value["method"], "method"),
        "decision_scope": _require_uri(value["decision_scope"], "decision_scope"),
        "operation": operation,
        "actor": _require_uri(value["actor"], "actor"),
        "target": _target(value["target"]),
        "context": _semantic_context(value.get("context")),
        "evaluation_time": _canonical_time(value["evaluation_time"], "evaluation_time"),
        "required_dimensions": dimensions,
    }
def policy_request_fingerprint(value: Any) -> str:
    return _b64url_digest(olp_encode(validate_policy_request(value)))


def policy_subject_fingerprint(value: Any) -> str:
    request = validate_policy_request(value)
    projection = {
        key: request[key]
        for key in ("version", "method", "decision_scope", "operation", "actor", "target", "context", "required_dimensions")
    }
    return _b64url_digest(olp_encode(projection))


def _canonical_fingerprint(value: Any, path: str) -> str:
    if not isinstance(value, str) or len(value) != 43:
        fail("INVALID_POLICY_FINGERPRINT", f"{path} MUST be canonical SHA-256 base64url text")
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except Exception:
        fail("INVALID_POLICY_FINGERPRINT", f"{path} MUST be canonical SHA-256 base64url text")
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if len(decoded) != 32 or canonical != value:
        fail("INVALID_POLICY_FINGERPRINT", f"{path} MUST be canonical SHA-256 base64url text")
    return value


@dataclass(frozen=True)
class PolicyObservation:
    dimension: str
    status: str
    source: str
    reason: str
    evidence_ids: tuple[str, ...] = ()
    valid_from: str | None = None
    valid_until: str | None = None
    subject_fingerprint: str | None = None


def _observation_evidence_ids(values: Iterable[Any]) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_EVIDENCE_IDS_PER_OBSERVATION, "observation.evidence_ids")
    out = tuple(_record_identity(item, "observation.evidence_ids[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_POLICY_SET", "observation.evidence_ids MUST be duplicate-free")
    if out != tuple(sorted(out, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_POLICY_SET", "observation.evidence_ids MUST be UTF-8 sorted")
    return out


def _normalize_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, PolicyObservation):
        fail("INVALID_POLICY_OBSERVATION", "observation MUST be PolicyObservation")
    if value.dimension not in CORE_DIMENSIONS:
        fail("UNSUPPORTED_POLICY_DIMENSION", "observation dimension is unsupported")
    if value.status not in OBSERVATION_STATUSES:
        fail("INVALID_POLICY_OBSERVATION", "observation status is unsupported")
    source = _require_uri(value.source, "observation.source")
    reason = _require_uri(value.reason, "observation.reason")
    valid_from = None if value.valid_from is None else _canonical_time(value.valid_from, "observation.valid_from")
    valid_until = None if value.valid_until is None else _canonical_time(value.valid_until, "observation.valid_until")
    if valid_from is not None and valid_until is not None:
        if parse_rfc3339(valid_from) >= parse_rfc3339(valid_until):
            fail("INVALID_POLICY_INTERVAL", "observation valid_from MUST be before valid_until")
    return {
        "dimension": value.dimension,
        "status": value.status,
        "source": source,
        "reason": reason,
        "evidence_ids": _observation_evidence_ids(value.evidence_ids),
        "valid_from": valid_from,
        "valid_until": valid_until,
        "subject_fingerprint": _canonical_fingerprint(value.subject_fingerprint, "observation.subject_fingerprint"),
    }


def _observation_sort_key(item: Mapping[str, Any]) -> bytes:
    return olp_encode(item)


def normalize_policy_observations(values: Iterable[Any]) -> dict[str, Any]:
    items = _bounded_tuple(values, MAX_OBSERVATIONS, "observations")
    unique: dict[bytes, dict[str, Any]] = {}
    duplicate_count = 0
    for item in items:
        normalized = _normalize_observation(item)
        key = _observation_sort_key(normalized)
        if key in unique:
            duplicate_count += 1
            continue
        unique[key] = normalized
    ordered = tuple(unique[key] for key in sorted(unique))
    return {"observations": ordered, "duplicate_observations": duplicate_count}


def _effective_status(item: Mapping[str, Any], evaluation_time: str) -> str:
    now = parse_rfc3339(evaluation_time)
    if item["valid_from"] is not None and now < parse_rfc3339(item["valid_from"]):
        return "STALE"
    if item["valid_until"] is not None and now >= parse_rfc3339(item["valid_until"]):
        return "STALE"
    return item["status"]

_DECISIVE_STATUSES = frozenset({
    OBS_SATISFIED,
    OBS_UNSATISFIED,
    OBS_ADDITIONAL_EVIDENCE,
    OBS_HUMAN_REVIEW,
    OBS_QUARANTINE,
})


def _aggregate_dimension(
    dimension: str,
    observations: tuple[Mapping[str, Any], ...],
    evaluation_time: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    trace: list[dict[str, Any]] = []
    current_statuses: set[str] = set()
    stale_seen = False
    for item in observations:
        if item["dimension"] != dimension:
            continue
        effective = _effective_status(item, evaluation_time)
        trace.append({**item, "effective_status": effective})
        if effective == "STALE":
            stale_seen = True
        elif effective != OBS_NOT_APPLICABLE:
            current_statuses.add(effective)
    if not current_statuses:
        return ("STALE" if stale_seen else "MISSING"), tuple(trace)
    decisive = current_statuses & _DECISIVE_STATUSES
    if len(decisive) > 1:
        return "CONFLICT", tuple(trace)
    if len(decisive) == 1:
        decision = next(iter(decisive))
        if decision == OBS_SATISFIED:
            if OBS_UNSUPPORTED in current_statuses:
                return OBS_UNSUPPORTED, tuple(trace)
            if OBS_UNKNOWN in current_statuses:
                return OBS_UNKNOWN, tuple(trace)
        return decision, tuple(trace)
    if OBS_UNSUPPORTED in current_statuses:
        return OBS_UNSUPPORTED, tuple(trace)
    if OBS_UNKNOWN in current_statuses:
        return OBS_UNKNOWN, tuple(trace)
    return "MISSING", tuple(trace)

def _require_observation_subject_binding(
    normalized_request: Mapping[str, Any],
    observations: tuple[Mapping[str, Any], ...],
) -> str:
    expected = policy_subject_fingerprint(normalized_request)
    for item in observations:
        if item["subject_fingerprint"] != expected:
            fail("POLICY_OBSERVATION_SUBJECT_MISMATCH", "policy observation is bound to a different request subject")
    return expected


def policy_input_fingerprint(request: Any, observations: Iterable[Any]) -> str:
    normalized_request = validate_policy_request(request)
    normalized = normalize_policy_observations(observations)
    _require_observation_subject_binding(normalized_request, normalized["observations"])
    projection = {
        "request": normalized_request,
        "observations": normalized["observations"],
    }
    return _b64url_digest(olp_encode(projection))


def _dimension_summary(
    dimension: str,
    state: str,
    trace: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    sources = tuple(sorted({item["source"] for item in trace}, key=lambda item: item.encode("utf-8")))
    reasons = tuple(sorted({item["reason"] for item in trace}, key=lambda item: item.encode("utf-8")))
    evidence_ids = tuple(sorted({rid for item in trace for rid in item["evidence_ids"]}, key=lambda item: item.encode("utf-8")))
    return {
        "dimension": dimension,
        "state": state,
        "sources": sources,
        "reasons": reasons,
        "evidence_ids": evidence_ids,
        "observation_count": len(trace),
    }

def _outcome_for_states(states: tuple[str, ...]) -> str:
    if not states:
        return OUTCOME_NOT_APPLICABLE
    if "CONFLICT" in states:
        return OUTCOME_CONFLICTING
    if OBS_UNSATISFIED in states:
        return OUTCOME_DENY
    if OBS_QUARANTINE in states:
        return OUTCOME_QUARANTINE
    if OBS_HUMAN_REVIEW in states:
        return OUTCOME_HUMAN_REVIEW
    if OBS_UNSUPPORTED in states or "STALE" in states:
        return OUTCOME_INDETERMINATE
    if OBS_ADDITIONAL_EVIDENCE in states or OBS_UNKNOWN in states or "MISSING" in states:
        return OUTCOME_ADDITIONAL_EVIDENCE
    if all(state == OBS_SATISFIED for state in states):
        return OUTCOME_ALLOW
    return OUTCOME_INDETERMINATE


def _full_observation_trace(
    observations: tuple[Mapping[str, Any], ...],
    evaluation_time: str,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {**item, "effective_status": _effective_status(item, evaluation_time)}
        for item in observations
    )

def evaluate_policy(request: Any, observations: Iterable[Any]) -> dict[str, Any]:
    normalized_request = validate_policy_request(request)
    if normalized_request["method"] != METHOD_CORE:
        fail("UNSUPPORTED_POLICY_METHOD", "core evaluator supports only METHOD_CORE")
    normalized = normalize_policy_observations(observations)
    items = normalized["observations"]
    subject_fp = _require_observation_subject_binding(normalized_request, items)
    summaries: list[dict[str, Any]] = []
    for dimension in normalized_request["required_dimensions"]:
        state, trace = _aggregate_dimension(
            dimension,
            items,
            normalized_request["evaluation_time"],
        )
        summaries.append(_dimension_summary(dimension, state, trace))
    state_tuple = tuple(item["state"] for item in summaries)
    outcome = _outcome_for_states(state_tuple)
    input_projection = {
        "request": normalized_request,
        "observations": items,
    }
    input_fp = _b64url_digest(olp_encode(input_projection))
    request_fp = _b64url_digest(olp_encode(normalized_request))
    result_core = {
        "version": 1,
        "method": normalized_request["method"],
        "decision_scope": normalized_request["decision_scope"],
        "operation": normalized_request["operation"],
        "actor": normalized_request["actor"],
        "target": normalized_request["target"],
        "evaluation_time": normalized_request["evaluation_time"],
        "required_dimensions": normalized_request["required_dimensions"],
        "outcome": outcome,
        "dimension_summaries": tuple(summaries),
        "observation_trace": _full_observation_trace(items, normalized_request["evaluation_time"]),
        "duplicate_observations": normalized["duplicate_observations"],
        "request_fingerprint": request_fp,
        "policy_subject_fingerprint": subject_fp,
        "policy_input_fingerprint": input_fp,
        "protected_operation": normalized_request["operation"] in PROTECTED_OPERATIONS,
        "protected_side_effect": normalized_request["operation"] in SIDE_EFFECT_OPERATIONS,
        "local_policy_allows_operation": outcome == OUTCOME_ALLOW,
    }
    result_fp = _b64url_digest(olp_encode(result_core))
    return {
        **result_core,
        "result_fingerprint": result_fp,
        "policy_decision_is_universal": False,
        "authority_evidence_is_final_permission": False,
        "trust_is_policy_permission": False,
        "legal_finality_established": False,
        "decision_is_marketplace_record": False,
        "hidden_network_fallback_permitted": False,
        "policy_observation_authentication_established": False,
        "result_authentication_established": False,
        "evaluation_time_trust_established": False,
    }
_RESULT_CORE_FIELDS = (
    "version", "method", "decision_scope", "operation", "actor", "target",
    "evaluation_time", "required_dimensions", "outcome", "dimension_summaries",
    "observation_trace", "duplicate_observations", "request_fingerprint",
    "policy_subject_fingerprint", "policy_input_fingerprint", "protected_operation", "protected_side_effect",
    "local_policy_allows_operation",
)
_RESULT_BOUNDARY_FIELDS = (
    "policy_decision_is_universal", "authority_evidence_is_final_permission",
    "trust_is_policy_permission", "legal_finality_established",
    "decision_is_marketplace_record", "hidden_network_fallback_permitted",
    "policy_observation_authentication_established", "result_authentication_established",
    "evaluation_time_trust_established",
)


def validate_policy_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_PRIOR_POLICY_RESULT", "policy result MUST be a map")
    required = set(_RESULT_CORE_FIELDS) | set(_RESULT_BOUNDARY_FIELDS) | {"result_fingerprint"}
    if set(value) != required:
        fail("INVALID_PRIOR_POLICY_RESULT", "policy result shape MUST contain exactly the M11 v1 fields")
    if value["outcome"] not in OUTCOMES:
        fail("INVALID_PRIOR_POLICY_RESULT", "policy result outcome is unsupported")
    if value["local_policy_allows_operation"] != (value["outcome"] == OUTCOME_ALLOW):
        fail("INVALID_PRIOR_POLICY_RESULT", "policy result allow flag is inconsistent")
    if any(value[field] is not False for field in _RESULT_BOUNDARY_FIELDS):
        fail("INVALID_PRIOR_POLICY_RESULT", "policy result boundary flags are inconsistent")
    projection = {field: value[field] for field in _RESULT_CORE_FIELDS}
    expected = _b64url_digest(olp_encode(projection))
    if value["result_fingerprint"] != expected:
        fail("POLICY_RESULT_INTEGRITY_MISMATCH", "policy result fingerprint does not match result content")
    return dict(value)


def evaluate_decision_reuse(
    prior_result: Any,
    current_request: Any,
    current_observations: Iterable[Any],
) -> dict[str, Any]:
    prior = validate_policy_result(prior_result)
    current_request_fp = policy_request_fingerprint(current_request)
    current_input_fp = policy_input_fingerprint(current_request, current_observations)
    reasons: list[str] = []
    if prior["outcome"] != OUTCOME_ALLOW:
        reasons.append("PRIOR_DECISION_NOT_ALLOW")
    if prior["request_fingerprint"] != current_request_fp:
        reasons.append("DECISION_REQUEST_BINDING_CHANGED")
    if prior["policy_input_fingerprint"] != current_input_fp:
        reasons.append("DECISION_EVIDENCE_BINDING_CHANGED")
    return {
        "reuse_status": "REUSABLE" if not reasons else "NOT_REUSABLE",
        "reasons": tuple(reasons),
        "current_request_fingerprint": current_request_fp,
        "current_policy_input_fingerprint": current_input_fp,
        "prior_result_fingerprint": prior["result_fingerprint"],
        "prior_result_authentication_evaluated": False,
        "prior_allow_is_universal_permission": False,
        "changed_execution_assumptions_require_reevaluation": True,
    }
