"""Non-normative Marketplace trust/evidence evaluation v1 helpers.

The helper standardizes reproducible evaluation inputs, evidence selection and
explainable traces. It does not define protocol truth, reputation, or a
universal trust score.
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
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import RECORD_TYPES, validate_market_record

BASE = "https://open-trust-layer.github.io/marketplace/semantics/v1"
METHOD_CORE = f"{BASE}/trust-evaluation/method/core-evidence-v1"
MAX_EVIDENCE_RECORDS = 4096
MAX_QUERY_SET = 128
MAX_CONTEXT_ENTRIES = 128
MAX_TRACE_ITEMS = 4096

RESULT_STATUSES = {
    "EVIDENCE_SUFFICIENT_UNDER_METHOD",
    "EVIDENCE_INSUFFICIENT_UNDER_METHOD",
    "CONFLICTING_EVIDENCE",
    "DISPUTED_EVIDENCE",
    "INDETERMINATE",
}
PROOF_STATUSES = {"VERIFIED", "FAILED", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE"}
IDENTITY_STATUSES = {"ACCEPTED", "REJECTED", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE"}
AUTHORITY_STATUSES = {"ACCEPTED", "REJECTED", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE"}
LIFECYCLE_STATUSES = {"ACCEPTABLE", "ADVERSE", "UNKNOWN", "UNSUPPORTED", "NOT_APPLICABLE"}
DOMAIN_STATUSES = {"SUPPORTS", "OPPOSES", "NEUTRAL", "UNKNOWN", "UNSUPPORTED"}


class MarketplaceTrustEvaluationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceTrustEvaluationError(code, message)


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_URI", f"{path} MUST be an absolute URI")
    return value


def _bounded_tuple(values: Iterable[Any], limit: int, code: str = "RESOURCE_LIMIT_EXCEEDED") -> tuple[Any, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        fail("INVALID_RESOURCE_LIMIT", "resource limit MUST be a positive integer")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail(code, f"input exceeds configured limit {limit}")
    return items


def _sorted_unique_uris(values: Iterable[Any], path: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_QUERY_SET)
    if not items and not allow_empty:
        fail("EMPTY_SET", f"{path} MUST be non-empty")
    out = tuple(_require_uri(item, f"{path}[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_SET", f"{path} MUST be duplicate-free")
    if out != tuple(sorted(out, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_SET", f"{path} MUST be UTF-8 sorted")
    return out


def _record_identity(value: Any, path: str = "record_id") -> str:
    if not isinstance(value, str):
        fail("INVALID_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    try:
        decode_identity_text(value, expected_kind="record")
    except Exception:
        fail("INVALID_RECORD_ID", f"{path} MUST be canonical OLP Record Identity text")
    return value


def _semantic_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_EVALUATION_CONTEXT", "context MUST be a bounded semantic map")
    out: dict[str, Any] = {}
    for key, item in value.items():
        key = _require_uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{key!r}]")
        except Exception as exc:
            fail("INVALID_EVALUATION_CONTEXT", f"invalid OLP context value: {exc}")
        out[key] = item
    return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-8")))


def _target(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"kind", "value"}:
        fail("INVALID_EVALUATION_TARGET", "target MUST contain exactly kind and value")
    kind, raw = value["kind"], value["value"]
    if kind in {"principal", "subject-uri"}:
        return {"kind": kind, "value": _require_uri(raw, "target.value")}
    if kind == "record":
        return {"kind": kind, "value": _record_identity(raw, "target.value")}
    fail("INVALID_EVALUATION_TARGET", "target.kind is unsupported")


def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def validate_evidence_query(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_EVIDENCE_QUERY", "evidence query MUST be a map")
    required = {"version", "method", "purpose", "target", "max_records"}
    allowed = required | {"context", "record_types", "profiles_all", "sources_any"}
    version = value.get("version")
    if set(value) - allowed or not required.issubset(value):
        fail("INVALID_EVIDENCE_QUERY", "evidence query shape is invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version != 1:
        fail("INVALID_EVIDENCE_QUERY", "query version MUST be exact integer 1")
    max_records = value["max_records"]
    if not isinstance(max_records, int) or isinstance(max_records, bool):
        fail("INVALID_RESOURCE_LIMIT", "max_records MUST be integer")
    if not 1 <= max_records <= MAX_EVIDENCE_RECORDS:
        fail("INVALID_RESOURCE_LIMIT", "max_records is outside the M9 v1 bound")
    out: dict[str, Any] = {
        "version": 1,
        "method": _require_uri(value["method"], "method"),
        "purpose": _require_uri(value["purpose"], "purpose"),
        "target": _target(value["target"]),
        "context": _semantic_context(value.get("context")),
        "max_records": max_records,
    }
    if "record_types" in value:
        record_types = _sorted_unique_uris(value["record_types"], "record_types")
        if any(item not in RECORD_TYPES for item in record_types):
            fail("UNSUPPORTED_RECORD_TYPE", "record_types contains a non-core Marketplace type")
        out["record_types"] = record_types
    if "profiles_all" in value:
        out["profiles_all"] = _sorted_unique_uris(value["profiles_all"], "profiles_all")
    if "sources_any" in value:
        out["sources_any"] = _sorted_unique_uris(value["sources_any"], "sources_any")
    return out


def query_fingerprint(value: Any) -> str:
    return _b64url_digest(olp_encode(validate_evidence_query(value)))


@dataclass(frozen=True)
class EvidenceCandidate:
    record: RecordV1
    source: str


@dataclass(frozen=True)
class EvidenceObservation:
    record_id: str
    proof_status: str
    identity_status: str
    authority_status: str
    lifecycle_status: str
    domain_status: str
    source_accepted: bool
    critical_understood: bool
    disputed: bool = False


def _validate_candidate(candidate: Any) -> EvidenceCandidate:
    if not isinstance(candidate, EvidenceCandidate):
        fail("INVALID_EVIDENCE_CANDIDATE", "candidate MUST be EvidenceCandidate")
    if not isinstance(candidate.record, RecordV1):
        fail("INVALID_MARKETPLACE_RECORD", "candidate.record MUST be RecordV1")
    try:
        validate_market_record(candidate.record)
    except Exception as exc:
        fail("INVALID_MARKETPLACE_RECORD", f"nonconforming Marketplace record: {exc}")
    _require_uri(candidate.source, "candidate.source")
    return candidate


def _scope_matches(record: RecordV1, query: Mapping[str, Any]) -> bool:
    record_types = set(query.get("record_types", RECORD_TYPES))
    if record.type not in record_types:
        return False
    required_profiles = set(query.get("profiles_all", ()))
    return required_profiles.issubset(set(record.profiles))


def select_evidence(candidates: Iterable[Any], query: Any) -> dict[str, Any]:
    normalized_query = validate_evidence_query(query)
    items = _bounded_tuple(candidates, normalized_query["max_records"])
    records: dict[str, RecordV1] = {}
    sources: dict[str, set[str]] = {}
    excluded_reasons: dict[str, set[str]] = {}
    duplicate_deliveries = 0
    for raw in items:
        candidate = _validate_candidate(raw)
        identity = record_identity_text(candidate.record)
        allowed_sources = set(normalized_query.get("sources_any", ()))
        if allowed_sources and candidate.source not in allowed_sources:
            excluded_reasons.setdefault(identity, set()).add("SOURCE_SCOPE_MISMATCH")
            continue
        if not _scope_matches(candidate.record, normalized_query):
            excluded_reasons.setdefault(identity, set()).add("RECORD_SCOPE_MISMATCH")
            continue
        prior = records.get(identity)
        if prior is not None and prior != candidate.record:
            fail("IDENTITY_COLLISION_OR_CONFLICT", "same Record Identity maps to different records")
        if prior is not None and candidate.source in sources[identity]:
            duplicate_deliveries += 1
        records.setdefault(identity, candidate.record)
        sources.setdefault(identity, set()).add(candidate.source)
    selected_ids = tuple(sorted(records))
    return {
        "query_fingerprint": query_fingerprint(normalized_query),
        "selected_record_ids": selected_ids,
        "excluded_record_ids": tuple(sorted(set(excluded_reasons) - set(records))),
        "excluded_reasons_by_record": {
            identity: tuple(sorted(excluded_reasons[identity]))
            for identity in sorted(set(excluded_reasons) - set(records))
        },
        "source_uris_by_record": {
            identity: tuple(sorted(sources[identity], key=lambda item: item.encode("utf-8")))
            for identity in selected_ids
        },
        "duplicate_delivery_count": duplicate_deliveries,
        "global_completeness": "UNKNOWN",
        "absence_is_negative_evidence": False,
    }


def validate_observation(value: Any) -> EvidenceObservation:
    if isinstance(value, EvidenceObservation):
        obs = value
    elif isinstance(value, Mapping):
        required = {
            "record_id", "proof_status", "identity_status", "authority_status",
            "lifecycle_status", "domain_status", "source_accepted",
            "critical_understood", "disputed",
        }
        if set(value) != required:
            fail("INVALID_EVIDENCE_OBSERVATION", "observation shape is invalid")
        obs = EvidenceObservation(**value)
    else:
        fail("INVALID_EVIDENCE_OBSERVATION", "observation MUST be a map or EvidenceObservation")
    _record_identity(obs.record_id)
    if obs.proof_status not in PROOF_STATUSES:
        fail("INVALID_OBSERVATION_STATUS", "proof_status is invalid")
    if obs.identity_status not in IDENTITY_STATUSES:
        fail("INVALID_OBSERVATION_STATUS", "identity_status is invalid")
    if obs.authority_status not in AUTHORITY_STATUSES:
        fail("INVALID_OBSERVATION_STATUS", "authority_status is invalid")
    if obs.lifecycle_status not in LIFECYCLE_STATUSES:
        fail("INVALID_OBSERVATION_STATUS", "lifecycle_status is invalid")
    if obs.domain_status not in DOMAIN_STATUSES:
        fail("INVALID_OBSERVATION_STATUS", "domain_status is invalid")
    if not isinstance(obs.source_accepted, bool) or not isinstance(obs.critical_understood, bool) or not isinstance(obs.disputed, bool):
        fail("INVALID_EVIDENCE_OBSERVATION", "observation booleans MUST be exact booleans")
    return obs


def _observation_value(obs: EvidenceObservation) -> dict[str, Any]:
    return {
        "record_id": obs.record_id,
        "proof_status": obs.proof_status,
        "identity_status": obs.identity_status,
        "authority_status": obs.authority_status,
        "lifecycle_status": obs.lifecycle_status,
        "domain_status": obs.domain_status,
        "source_accepted": obs.source_accepted,
        "critical_understood": obs.critical_understood,
        "disputed": obs.disputed,
    }


def evaluation_input_fingerprint(
    query: Any,
    observations: Iterable[Any],
    source_uris_by_record: Mapping[str, Iterable[str]] | None = None,
) -> str:
    normalized_query = validate_evidence_query(query)
    items = tuple(validate_observation(item) for item in _bounded_tuple(observations, MAX_TRACE_ITEMS))
    values = tuple(sorted((_observation_value(item) for item in items), key=lambda item: item["record_id"]))
    if len(values) != len({item["record_id"] for item in values}):
        fail("DUPLICATE_EVIDENCE_OBSERVATION", "observations MUST contain one item per Record Identity")
    provenance = {}
    if source_uris_by_record is not None:
        provenance = {
            _record_identity(identity): tuple(sorted((_require_uri(uri, "source") for uri in uris), key=lambda item: item.encode("utf-8")))
            for identity, uris in sorted(source_uris_by_record.items())
        }
    return _b64url_digest(olp_encode({"query": normalized_query, "observations": values, "provenance": provenance}))


def _dimension_reasons(obs: EvidenceObservation) -> tuple[str, ...]:
    reasons: list[str] = []
    if not obs.source_accepted:
        reasons.append("SOURCE_NOT_ACCEPTED")
    if not obs.critical_understood:
        reasons.append("CRITICAL_SEMANTICS_UNDERSTOOD_FALSE")
    if obs.proof_status in {"FAILED", "UNKNOWN", "UNSUPPORTED"}:
        reasons.append(f"PROOF_{obs.proof_status}")
    if obs.identity_status in {"REJECTED", "UNKNOWN", "UNSUPPORTED"}:
        reasons.append(f"IDENTITY_{obs.identity_status}")
    if obs.authority_status in {"REJECTED", "UNKNOWN", "UNSUPPORTED"}:
        reasons.append(f"AUTHORITY_{obs.authority_status}")
    if obs.lifecycle_status in {"ADVERSE", "UNKNOWN", "UNSUPPORTED"}:
        reasons.append(f"LIFECYCLE_{obs.lifecycle_status}")
    if obs.domain_status in {"UNKNOWN", "UNSUPPORTED"}:
        reasons.append(f"DOMAIN_{obs.domain_status}")
    return tuple(reasons)


def _countable(obs: EvidenceObservation) -> bool:
    return (
        obs.source_accepted
        and obs.critical_understood
        and obs.proof_status in {"VERIFIED", "NOT_APPLICABLE"}
        and obs.identity_status in {"ACCEPTED", "NOT_APPLICABLE"}
        and obs.authority_status in {"ACCEPTED", "NOT_APPLICABLE"}
        and obs.lifecycle_status in {"ACCEPTABLE", "NOT_APPLICABLE"}
        and obs.domain_status in {"SUPPORTS", "OPPOSES", "NEUTRAL"}
    )


def evaluate_trust(
    candidates: Iterable[Any],
    observations: Iterable[Any],
    query: Any,
) -> dict[str, Any]:
    normalized_query = validate_evidence_query(query)
    if normalized_query["method"] != METHOD_CORE:
        fail("UNSUPPORTED_EVALUATION_METHOD", "reference helper implements only core-evidence-v1")
    selection = select_evidence(candidates, normalized_query)
    selected = set(selection["selected_record_ids"])
    obs_items = tuple(validate_observation(item) for item in _bounded_tuple(observations, MAX_TRACE_ITEMS))
    obs_by_id: dict[str, EvidenceObservation] = {}
    for obs in obs_items:
        if obs.record_id in obs_by_id:
            fail("DUPLICATE_EVIDENCE_OBSERVATION", "one observation per selected Record Identity is required")
        if obs.record_id not in selected:
            fail("OBSERVATION_OUTSIDE_SELECTED_EVIDENCE", "observation references unselected evidence")
        obs_by_id[obs.record_id] = obs
    if set(obs_by_id) != selected:
        fail("INCOMPLETE_EVIDENCE_OBSERVATIONS", "every selected Record Identity requires one observation")
    supporting: list[str] = []
    opposing: list[str] = []
    neutral: list[str] = []
    disputed: list[str] = []
    unresolved: list[str] = []
    excluded_unusable: list[str] = []
    trace: list[dict[str, Any]] = []
    uncertainty_markers = {"UNKNOWN", "UNSUPPORTED"}
    for identity in sorted(selected):
        obs = obs_by_id[identity]
        reasons = _dimension_reasons(obs)
        is_countable = _countable(obs)
        has_uncertainty = (
            not obs.critical_understood
            or obs.proof_status in uncertainty_markers
            or obs.identity_status in uncertainty_markers
            or obs.authority_status in uncertainty_markers
            or obs.lifecycle_status in uncertainty_markers
            or obs.domain_status in uncertainty_markers
        )
        if is_countable:
            if obs.domain_status == "SUPPORTS": supporting.append(identity)
            elif obs.domain_status == "OPPOSES": opposing.append(identity)
            else: neutral.append(identity)
            if obs.disputed: disputed.append(identity)
            decision = f"COUNT_{obs.domain_status}"
        elif has_uncertainty:
            unresolved.append(identity)
            decision = "UNRESOLVED"
        else:
            excluded_unusable.append(identity)
            decision = "EXCLUDED_UNUSABLE"
        trace.append({
            "record_id": identity,
            "decision": decision,
            "domain_status": obs.domain_status,
            "disputed": obs.disputed,
            "reasons": reasons,
        })
    if disputed:
        status = "DISPUTED_EVIDENCE"
        final_rule = "COUNTABLE_DISPUTED_EVIDENCE_PRESENT"
    elif supporting and opposing:
        status = "CONFLICTING_EVIDENCE"
        final_rule = "COUNTABLE_SUPPORT_AND_OPPOSITION_PRESENT"
    elif unresolved:
        status = "INDETERMINATE"
        final_rule = "SELECTED_EVIDENCE_REMAINS_UNRESOLVED"
    elif supporting:
        status = "EVIDENCE_SUFFICIENT_UNDER_METHOD"
        final_rule = "COUNTABLE_SUPPORT_WITHOUT_OPPOSITION_OR_UNCERTAINTY"
    elif opposing:
        status = "EVIDENCE_INSUFFICIENT_UNDER_METHOD"
        final_rule = "COUNTABLE_OPPOSITION_WITHOUT_SUPPORT_OR_UNCERTAINTY"
    else:
        status = "INDETERMINATE"
        final_rule = "NO_COUNTABLE_DIRECTIONAL_EVIDENCE"
    input_fp = evaluation_input_fingerprint(
        normalized_query, obs_items, selection["source_uris_by_record"]
    )
    result_core = {
        "method": normalized_query["method"],
        "purpose": normalized_query["purpose"],
        "target": normalized_query["target"],
        "query_fingerprint": selection["query_fingerprint"],
        "evaluation_input_fingerprint": input_fp,
        "status": status,
        "final_rule": final_rule,
        "selected_record_ids": selection["selected_record_ids"],
        "excluded_by_query_record_ids": selection["excluded_record_ids"],
        "excluded_by_query_reasons": selection["excluded_reasons_by_record"],
        "supporting_record_ids": tuple(supporting),
        "opposing_record_ids": tuple(opposing),
        "neutral_record_ids": tuple(neutral),
        "disputed_record_ids": tuple(disputed),
        "unresolved_record_ids": tuple(unresolved),
        "excluded_unusable_record_ids": tuple(excluded_unusable),
    }
    result_fp = _b64url_digest(olp_encode(result_core))
    return {
        **result_core,
        "result_fingerprint": result_fp,
        "source_uris_by_record": selection["source_uris_by_record"],
        "duplicate_delivery_count": selection["duplicate_delivery_count"],
        "trace": tuple(trace),
        "global_completeness": "UNKNOWN",
        "absence_is_negative_evidence": False,
        "universal_truth": False,
        "universal_trust_score": False,
        "numeric_confidence_standardized": False,
        "protocol_decision": False,
    }
