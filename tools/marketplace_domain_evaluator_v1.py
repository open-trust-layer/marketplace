"""Non-normative Marketplace domain-evaluator method v1 helpers.

M15 derives a method-relative domain_status for one exact Marketplace/OLP
Record Identity. M9 remains authoritative for evidence selection and the
larger proof/identity/authority/lifecycle/source/dispute trust lattice.
"""
from __future__ import annotations

import base64
import hashlib
from collections.abc import Iterable, Mapping
from itertools import islice
from typing import Any

from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import BASE

PROFILE_CRITERION_THRESHOLD = f"{BASE}/domain-evaluator/profile/criterion-threshold-v1"
DOMAIN_STATUSES = frozenset({"SUPPORTS", "OPPOSES", "NEUTRAL", "UNKNOWN"})
OBSERVATION_STATES = frozenset({
    "SUPPORTS", "OPPOSES", "NEUTRAL", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE",
})
MAX_CRITERIA = 256
MAX_OBSERVATIONS = 512
MAX_SET_ITEMS = 256
MAX_CONTEXT_ENTRIES = 128
MAX_URI_BYTES = 2048
MAX_WEIGHT = 1000
MAX_TOTAL_POINTS = MAX_CRITERIA * MAX_WEIGHT

_BOUNDARY_FIELDS = (
    "proof_evaluated",
    "identity_evaluated",
    "authority_evaluated",
    "lifecycle_evaluated",
    "source_policy_evaluated",
    "dispute_evaluated",
    "authorization_evaluated",
    "protected_side_effect_authorized",
    "truth_established",
    "universal_trust_score_established",
    "numeric_confidence_standardized",
    "cross_method_comparability_established",
    "marketplace_record_identity_affected",
    "method_authority_established",
    "result_authentication_established",
)

class MarketplaceDomainEvaluatorError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceDomainEvaluatorError(code, message)


def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def _bounded_tuple(values: Iterable[Any], limit: int, path: str) -> tuple[Any, ...]:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        fail("INVALID_DOMAIN_RESOURCE_LIMIT", f"{path} limit MUST be a positive integer")
    if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, Iterable):
        fail("INVALID_DOMAIN_COLLECTION", f"{path} MUST be an ordered collection")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail("DOMAIN_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds limit {limit}")
    return items


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_DOMAIN_URI", f"{path} MUST be an absolute URI")
    if len(value.encode("utf-8")) > MAX_URI_BYTES:
        fail("DOMAIN_RESOURCE_LIMIT_EXCEEDED", f"{path} URI exceeds {MAX_URI_BYTES} bytes")
    return value


def _record_identity(value: Any, path: str = "target_record_id") -> str:
    if not isinstance(value, str):
        fail("INVALID_DOMAIN_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    try:
        decode_identity_text(value, expected_kind="record")
    except Exception:
        fail("INVALID_DOMAIN_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    return value


def _sorted_unique_uris(values: Iterable[Any], path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_SET_ITEMS, path)
    if not items and not allow_empty:
        fail("EMPTY_DOMAIN_SET", f"{path} MUST be non-empty")
    out = tuple(_require_uri(item, f"{path}[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_DOMAIN_SET", f"{path} MUST be duplicate-free")
    if out != tuple(sorted(out, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_DOMAIN_SET", f"{path} MUST be UTF-8 sorted")
    return out


def _semantic_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_DOMAIN_CONTEXT", "context MUST be a bounded semantic map")
    out: dict[str, Any] = {}
    for key, item in value.items():
        uri = _require_uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{uri!r}]")
        except Exception as exc:
            fail("INVALID_DOMAIN_CONTEXT", f"invalid OLP context value: {exc}")
        out[uri] = item
    return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-8")))


def _positive_int(value: Any, path: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= maximum):
        fail("INVALID_DOMAIN_WEIGHT", f"{path} MUST be an integer in 1..{maximum}")
    return value


def _validate_criterion(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DOMAIN_CRITERION", "criterion MUST be a map")
    required = {"id", "required", "weight", "critical"}
    if set(value) != required or not isinstance(value["required"], bool):
        fail("INVALID_DOMAIN_CRITERION", "criterion shape is invalid")
    return {
        "id": _require_uri(value["id"], "criterion.id"),
        "required": value["required"],
        "weight": _positive_int(value["weight"], "criterion.weight", maximum=MAX_WEIGHT),
        "critical": _sorted_unique_uris(value["critical"], "criterion.critical"),
    }


def validate_domain_method_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DOMAIN_METHOD", "domain method profile MUST be a map")
    required = {
        "version", "profile", "method", "domain", "purposes", "criteria",
        "support_threshold", "oppose_threshold", "critical",
    }
    if set(value) != required:
        fail("INVALID_DOMAIN_METHOD", "domain method profile shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_DOMAIN_METHOD", "version MUST be exact integer 1")
    profile = _require_uri(value["profile"], "profile")
    if profile != PROFILE_CRITERION_THRESHOLD:
        fail("UNSUPPORTED_DOMAIN_METHOD_PROFILE", "reference helper supports only criterion-threshold-v1")
    criteria_raw = _bounded_tuple(value["criteria"], MAX_CRITERIA, "criteria")
    if not criteria_raw:
        fail("EMPTY_DOMAIN_SET", "criteria MUST be non-empty")
    criteria = tuple(_validate_criterion(item) for item in criteria_raw)
    ids = tuple(item["id"] for item in criteria)
    if len(ids) != len(set(ids)):
        fail("DUPLICATE_DOMAIN_CRITERION", "criterion ids MUST be unique")
    if ids != tuple(sorted(ids, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_DOMAIN_SET", "criteria MUST be sorted by criterion id")
    total_weight = sum(item["weight"] for item in criteria)
    if total_weight > MAX_TOTAL_POINTS:
        fail("DOMAIN_RESOURCE_LIMIT_EXCEEDED", "criterion total weight exceeds portable limit")
    support = value["support_threshold"]
    oppose = value["oppose_threshold"]
    for threshold, path in ((support, "support_threshold"), (oppose, "oppose_threshold")):
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not (1 <= threshold <= total_weight):
            fail("INVALID_DOMAIN_THRESHOLD", f"{path} MUST be in 1..total criterion weight")
    return {
        "version": 1,
        "profile": profile,
        "method": _require_uri(value["method"], "method"),
        "domain": _require_uri(value["domain"], "domain"),
        "purposes": _sorted_unique_uris(value["purposes"], "purposes", allow_empty=False),
        "criteria": criteria,
        "support_threshold": support,
        "oppose_threshold": oppose,
        "critical": _sorted_unique_uris(value["critical"], "critical"),
    }


def domain_method_profile_fingerprint(value: Any) -> str:
    return _b64url_digest(olp_encode(validate_domain_method_profile(value)))


def validate_domain_evaluation_request(value: Any, profile: Any) -> dict[str, Any]:
    normalized_profile = validate_domain_method_profile(profile)
    if not isinstance(value, Mapping):
        fail("INVALID_DOMAIN_REQUEST", "domain evaluation request MUST be a map")
    required = {
        "version", "method", "domain", "purpose", "target_record_id",
        "context", "understood_critical",
    }
    if set(value) != required:
        fail("INVALID_DOMAIN_REQUEST", "domain evaluation request shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_DOMAIN_REQUEST", "version MUST be exact integer 1")
    method = _require_uri(value["method"], "request.method")
    domain = _require_uri(value["domain"], "request.domain")
    purpose = _require_uri(value["purpose"], "request.purpose")
    if method != normalized_profile["method"]:
        fail("DOMAIN_METHOD_BINDING_MISMATCH", "request method does not match method profile")
    if domain != normalized_profile["domain"]:
        fail("DOMAIN_SCOPE_BINDING_MISMATCH", "request domain does not match method profile")
    if purpose not in normalized_profile["purposes"]:
        fail("DOMAIN_PURPOSE_NOT_SUPPORTED", "request purpose is not declared by method profile")
    return {
        "version": 1,
        "method": method,
        "domain": domain,
        "purpose": purpose,
        "target_record_id": _record_identity(value["target_record_id"]),
        "context": _semantic_context(value["context"]),
        "understood_critical": _sorted_unique_uris(
            value["understood_critical"], "understood_critical"
        ),
    }


def domain_request_fingerprint(value: Any, profile: Any) -> str:
    return _b64url_digest(olp_encode(validate_domain_evaluation_request(value, profile)))


def _validate_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DOMAIN_OBSERVATION", "criterion observation MUST be a map")
    required = {"criterion", "state", "critical", "reason_uris"}
    if set(value) != required:
        fail("INVALID_DOMAIN_OBSERVATION", "criterion observation shape is invalid")
    state = value["state"]
    if not isinstance(state, str) or state not in OBSERVATION_STATES:
        fail("INVALID_DOMAIN_OBSERVATION_STATE", "criterion observation state is unsupported")
    return {
        "criterion": _require_uri(value["criterion"], "observation.criterion"),
        "state": state,
        "critical": _sorted_unique_uris(value["critical"], "observation.critical"),
        "reason_uris": _sorted_unique_uris(value["reason_uris"], "observation.reason_uris"),
    }


def _normalize_observations(values: Iterable[Any], profile: Mapping[str, Any]) -> tuple[tuple[dict[str, Any], ...], int]:
    items = _bounded_tuple(values, MAX_OBSERVATIONS, "observations")
    declared = {item["id"] for item in profile["criteria"]}
    by_criterion: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for raw in items:
        item = _validate_observation(raw)
        criterion = item["criterion"]
        if criterion not in declared:
            fail("UNKNOWN_DOMAIN_CRITERION", "observation references undeclared criterion")
        prior = by_criterion.get(criterion)
        if prior is None:
            by_criterion[criterion] = item
        elif prior == item:
            duplicate_count += 1
        else:
            fail("DOMAIN_OBSERVATION_CONFLICT", "criterion has conflicting observations")
    ordered = tuple(
        by_criterion[key]
        for key in sorted(by_criterion, key=lambda item: item.encode("utf-8"))
    )
    return ordered, duplicate_count


def _criterion_trace(
    profile: Mapping[str, Any],
    observations: tuple[dict[str, Any], ...],
    understood_critical: set[str],
) -> tuple[dict[str, Any], ...]:
    by_criterion = {item["criterion"]: item for item in observations}
    traces: list[dict[str, Any]] = []
    for criterion in profile["criteria"]:
        observation = by_criterion.get(criterion["id"])
        if observation is None:
            state = "MISSING"
            observation_critical: tuple[str, ...] = ()
            reason_uris: tuple[str, ...] = ()
            unknown_critical: tuple[str, ...] = ()
            decision = "UNRESOLVED_REQUIRED" if criterion["required"] else "IGNORED_OPTIONAL_MISSING"
        else:
            state = observation["state"]
            observation_critical = observation["critical"]
            reason_uris = observation["reason_uris"]
            unknown_critical = tuple(sorted(
                (set(criterion["critical"]) | set(observation_critical)) - understood_critical,
                key=lambda item: item.encode("utf-8"),
            ))
            if unknown_critical:
                decision = "UNRESOLVED_CRITICAL"
            elif state == "SUPPORTS":
                decision = "COUNT_SUPPORTS"
            elif state == "OPPOSES":
                decision = "COUNT_OPPOSES"
            elif state == "NEUTRAL":
                decision = "COUNT_NEUTRAL"
            elif criterion["required"]:
                decision = "UNRESOLVED_REQUIRED"
            else:
                decision = "IGNORED_OPTIONAL_UNRESOLVED"
        traces.append({
            "criterion": criterion["id"],
            "required": criterion["required"],
            "weight": criterion["weight"],
            "state": state,
            "decision": decision,
            "critical": criterion["critical"],
            "observation_critical": observation_critical,
            "unknown_critical": unknown_critical,
            "reason_uris": reason_uris,
        })
    return tuple(traces)


def _aggregate(
    profile: Mapping[str, Any],
    trace: tuple[dict[str, Any], ...],
    understood_critical: set[str],
) -> dict[str, Any]:
    method_unknown = tuple(sorted(
        set(profile["critical"]) - understood_critical,
        key=lambda item: item.encode("utf-8"),
    ))
    trace_unknown = tuple(sorted({
        uri for item in trace for uri in item["unknown_critical"]
    }, key=lambda item: item.encode("utf-8")))
    unknown_critical = tuple(sorted(
        set(method_unknown) | set(trace_unknown),
        key=lambda item: item.encode("utf-8"),
    ))
    unresolved_required = tuple(
        item["criterion"] for item in trace
        if item["decision"] == "UNRESOLVED_REQUIRED"
    )
    support_points = sum(
        item["weight"] for item in trace if item["decision"] == "COUNT_SUPPORTS"
    )
    oppose_points = sum(
        item["weight"] for item in trace if item["decision"] == "COUNT_OPPOSES"
    )
    support_met = support_points >= profile["support_threshold"]
    oppose_met = oppose_points >= profile["oppose_threshold"]
    conflict = support_met and oppose_met
    if unknown_critical:
        domain_status = "UNKNOWN"
        final_rule = "UNKNOWN_CRITICAL_SEMANTICS"
    elif unresolved_required:
        domain_status = "UNKNOWN"
        final_rule = "REQUIRED_CRITERIA_UNRESOLVED"
    elif conflict:
        domain_status = "UNKNOWN"
        final_rule = "CONFLICTING_CRITERIA"
    elif support_met:
        domain_status = "SUPPORTS"
        final_rule = "SUPPORT_THRESHOLD_MET"
    elif oppose_met:
        domain_status = "OPPOSES"
        final_rule = "OPPOSE_THRESHOLD_MET"
    else:
        domain_status = "NEUTRAL"
        final_rule = "NO_DIRECTIONAL_THRESHOLD_MET"
    return {
        "support_points": support_points,
        "oppose_points": oppose_points,
        "support_threshold_met": support_met,
        "oppose_threshold_met": oppose_met,
        "conflict_detected": conflict,
        "unresolved_required_criteria": unresolved_required,
        "unknown_critical_uris": unknown_critical,
        "domain_status": domain_status,
        "final_rule": final_rule,
    }


def _normalized_input(
    profile: Any,
    request: Any,
    observations: Iterable[Any],
) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...], int]:
    normalized_profile = validate_domain_method_profile(profile)
    normalized_request = validate_domain_evaluation_request(request, normalized_profile)
    normalized_observations, duplicates = _normalize_observations(observations, normalized_profile)
    return normalized_profile, normalized_request, normalized_observations, duplicates


def domain_input_fingerprint(profile: Any, request: Any, observations: Iterable[Any]) -> str:
    normalized_profile, normalized_request, normalized_observations, _ = _normalized_input(
        profile, request, observations
    )
    return _b64url_digest(olp_encode({
        "method_profile": normalized_profile,
        "request": normalized_request,
        "observations": normalized_observations,
    }))


_RESULT_CORE_FIELDS = (
    "version", "profile", "method", "domain", "purpose", "target_record_id", "context",
    "understood_critical", "method_profile_fingerprint", "request_fingerprint",
    "input_fingerprint", "criterion_trace", "support_points", "oppose_points",
    "support_threshold", "oppose_threshold", "support_threshold_met",
    "oppose_threshold_met", "conflict_detected", "unresolved_required_criteria",
    "unknown_critical_uris", "domain_status", "final_rule", "duplicate_observations",
)

_RESULT_FINGERPRINT_FIELDS = tuple(
    field for field in _RESULT_CORE_FIELDS if field != "duplicate_observations"
)


def evaluate_domain_method(
    profile: Any,
    request: Any,
    observations: Iterable[Any],
) -> dict[str, Any]:
    normalized_profile, normalized_request, normalized_observations, duplicates = _normalized_input(
        profile, request, observations
    )
    understood = set(normalized_request["understood_critical"])
    trace = _criterion_trace(normalized_profile, normalized_observations, understood)
    aggregate = _aggregate(normalized_profile, trace, understood)
    profile_fp = _b64url_digest(olp_encode(normalized_profile))
    request_fp = _b64url_digest(olp_encode(normalized_request))
    input_fp = _b64url_digest(olp_encode({
        "method_profile": normalized_profile,
        "request": normalized_request,
        "observations": normalized_observations,
    }))
    core = {
        "version": 1,
        "profile": normalized_profile["profile"],
        "method": normalized_profile["method"],
        "domain": normalized_profile["domain"],
        "purpose": normalized_request["purpose"],
        "target_record_id": normalized_request["target_record_id"],
        "context": normalized_request["context"],
        "understood_critical": normalized_request["understood_critical"],
        "method_profile_fingerprint": profile_fp,
        "request_fingerprint": request_fp,
        "input_fingerprint": input_fp,
        "criterion_trace": trace,
        "support_points": aggregate["support_points"],
        "oppose_points": aggregate["oppose_points"],
        "support_threshold": normalized_profile["support_threshold"],
        "oppose_threshold": normalized_profile["oppose_threshold"],
        "support_threshold_met": aggregate["support_threshold_met"],
        "oppose_threshold_met": aggregate["oppose_threshold_met"],
        "conflict_detected": aggregate["conflict_detected"],
        "unresolved_required_criteria": aggregate["unresolved_required_criteria"],
        "unknown_critical_uris": aggregate["unknown_critical_uris"],
        "domain_status": aggregate["domain_status"],
        "final_rule": aggregate["final_rule"],
        "duplicate_observations": duplicates,
    }
    result_fp = _b64url_digest(olp_encode({field: core[field] for field in _RESULT_FINGERPRINT_FIELDS}))
    return {**core, "result_fingerprint": result_fp, **{field: False for field in _BOUNDARY_FIELDS}}


def validate_domain_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result MUST be a map")
    required = set(_RESULT_CORE_FIELDS) | set(_BOUNDARY_FIELDS) | {"result_fingerprint"}
    if set(value) != required:
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result version is invalid")
    if value["profile"] != PROFILE_CRITERION_THRESHOLD:
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result profile is unsupported")
    if not isinstance(value["domain_status"], str) or value["domain_status"] not in DOMAIN_STATUSES:
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result status is invalid")
    if any(value[field] is not False for field in _BOUNDARY_FIELDS):
        fail("INVALID_PRIOR_DOMAIN_RESULT", "domain result boundary flags are inconsistent")
    _require_uri(value["method"], "result.method")
    _require_uri(value["domain"], "result.domain")
    _require_uri(value["purpose"], "result.purpose")
    _record_identity(value["target_record_id"], "result.target_record_id")
    _semantic_context(value["context"])
    _sorted_unique_uris(value["understood_critical"], "result.understood_critical")
    _sorted_unique_uris(value["unresolved_required_criteria"], "result.unresolved_required_criteria")
    _sorted_unique_uris(value["unknown_critical_uris"], "result.unknown_critical_uris")
    for field in ("support_points", "oppose_points", "support_threshold", "oppose_threshold", "duplicate_observations"):
        if isinstance(value[field], bool) or not isinstance(value[field], int) or value[field] < 0:
            fail("INVALID_PRIOR_DOMAIN_RESULT", f"{field} is invalid")
    for field in ("support_threshold_met", "oppose_threshold_met", "conflict_detected"):
        if not isinstance(value[field], bool):
            fail("INVALID_PRIOR_DOMAIN_RESULT", f"{field} MUST be boolean")
    if not isinstance(value["criterion_trace"], (tuple, list)):
        fail("INVALID_PRIOR_DOMAIN_RESULT", "criterion_trace MUST be a collection")
    for field in ("method_profile_fingerprint", "request_fingerprint", "input_fingerprint", "result_fingerprint"):
        if not isinstance(value[field], str) or len(value[field]) != 43:
            fail("INVALID_PRIOR_DOMAIN_RESULT", f"{field} MUST be a SHA-256 base64url fingerprint")
    core = {field: value[field] for field in _RESULT_CORE_FIELDS}
    expected = _b64url_digest(olp_encode({field: core[field] for field in _RESULT_FINGERPRINT_FIELDS}))
    if value["result_fingerprint"] != expected:
        fail("DOMAIN_RESULT_INTEGRITY_MISMATCH", "result fingerprint does not match result content")
    return dict(value)


def evaluate_domain_method_reuse(
    prior_result: Any,
    current_profile: Any,
    current_request: Any,
    current_observations: Iterable[Any],
) -> dict[str, Any]:
    prior = validate_domain_result(prior_result)
    current = evaluate_domain_method(current_profile, current_request, current_observations)
    reasons: list[str] = []
    if prior["method_profile_fingerprint"] != current["method_profile_fingerprint"]:
        reasons.append("DOMAIN_METHOD_PROFILE_CHANGED")
    if prior["request_fingerprint"] != current["request_fingerprint"]:
        reasons.append("DOMAIN_REQUEST_BINDING_CHANGED")
    if prior["input_fingerprint"] != current["input_fingerprint"]:
        reasons.append("DOMAIN_OBSERVATIONS_CHANGED")
    if prior["result_fingerprint"] != current["result_fingerprint"]:
        reasons.append("DOMAIN_RESULT_CHANGED")
    return {
        "reuse_status": "REUSABLE" if not reasons else "NOT_REUSABLE",
        "reasons": tuple(reasons),
        "current_method_profile_fingerprint": current["method_profile_fingerprint"],
        "current_request_fingerprint": current["request_fingerprint"],
        "current_input_fingerprint": current["input_fingerprint"],
        "current_result_fingerprint": current["result_fingerprint"],
        "prior_result_fingerprint": prior["result_fingerprint"],
        "reuse_establishes_method_authority": False,
        "reuse_establishes_truth": False,
        "reuse_authorizes_protected_side_effect": False,
    }
