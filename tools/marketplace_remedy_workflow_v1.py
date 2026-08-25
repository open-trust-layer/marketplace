"""Pure, non-normative Marketplace remedy/workflow coordination planner."""
from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Iterable, Mapping
from itertools import islice
from typing import Any

from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import BASE

PROFILE_REMEDY_WORKFLOW = f"{BASE}/remedy-workflow/profile/outcome-rules-v1"
OBSERVATION_STATES = frozenset({"PRESENT", "ABSENT", "UNKNOWN", "UNSUPPORTED"})
WORKFLOW_STATUSES = frozenset({
    "PROPOSED", "PARTIAL", "REQUIRE_ADDITIONAL_EVIDENCE",
    "REQUIRE_HUMAN_REVIEW", "INDETERMINATE",
})
MAX_RULES = 128
MAX_STEPS = 256
MAX_DEPENDENCIES = 256
MAX_OBSERVATIONS = 512
MAX_TARGETS = 128
MAX_SET_ITEMS = 256
MAX_CONTEXT_ENTRIES = 128
MAX_URI_BYTES = 2048
_FINGERPRINT_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")

_BOUNDARY_FIELDS = (
    "legal_remedy_established", "legal_obligation_established",
    "universal_workflow_established", "universal_case_state_established",
    "source_outcome_truth_established", "dispute_resolution_evaluated",
    "settlement_evaluated", "fulfillment_evaluated", "authorization_evaluated",
    "protected_side_effect_authorized", "protected_side_effect_executed",
    "settlement_evidence_created", "fulfillment_evidence_created",
    "result_authentication_established",
)


class MarketplaceRemedyWorkflowError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceRemedyWorkflowError(code, message)


def _fingerprint(value: Any) -> str:
    digest = hashlib.sha256(olp_encode(value)).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _collection(value: Any, limit: int, path: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray, Mapping)) or not isinstance(value, Iterable):
        fail("INVALID_WORKFLOW_COLLECTION", f"{path} MUST be an ordered collection")
    items = tuple(islice(value, limit + 1))
    if len(items) > limit:
        fail("WORKFLOW_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds limit {limit}")
    return items


def _uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_WORKFLOW_URI", f"{path} MUST be an absolute URI")
    if len(value.encode("utf-8")) > MAX_URI_BYTES:
        fail("WORKFLOW_RESOURCE_LIMIT_EXCEEDED", f"{path} URI exceeds resource limit")
    return value


def _uris(value: Any, path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(_uri(item, f"{path}[]") for item in _collection(value, MAX_SET_ITEMS, path))
    if not items and not allow_empty:
        fail("EMPTY_WORKFLOW_SET", f"{path} MUST be non-empty")
    if len(items) != len(set(items)) or items != tuple(sorted(items, key=lambda x: x.encode("utf-8"))):
        fail("NONCANONICAL_WORKFLOW_SET", f"{path} MUST be UTF-8 sorted and unique")
    return items


def _record_identity(value: Any, path: str) -> str:
    if not isinstance(value, str):
        fail("INVALID_WORKFLOW_RECORD_ID", f"{path} MUST be canonical Record Identity text")
    try:
        decode_identity_text(value, expected_kind="record")
    except Exception:
        fail("INVALID_WORKFLOW_RECORD_ID", f"{path} MUST be canonical Record Identity text")
    return value


def _record_ids(value: Any, path: str) -> tuple[str, ...]:
    items = tuple(_record_identity(item, path) for item in _collection(value, MAX_TARGETS, path))
    if not items:
        fail("EMPTY_WORKFLOW_SET", f"{path} MUST be non-empty")
    if len(items) != len(set(items)) or items != tuple(sorted(items, key=lambda x: x.encode("utf-8"))):
        fail("NONCANONICAL_WORKFLOW_SET", f"{path} MUST be UTF-8 sorted and unique")
    return items


def _context(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_WORKFLOW_CONTEXT", "context MUST be a bounded semantic map")
    output: dict[str, Any] = {}
    for key, item in value.items():
        uri = _uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{uri!r}]")
        except Exception as exc:
            fail("INVALID_WORKFLOW_CONTEXT", f"invalid OLP context value: {exc}")
        output[uri] = item
    return dict(sorted(output.items(), key=lambda pair: pair[0].encode("utf-8")))


def _step(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "id", "action", "depends_on", "protected", "conflict_group", "critical",
    }:
        fail("INVALID_WORKFLOW_STEP", "workflow step shape is invalid")
    if not isinstance(value["protected"], bool):
        fail("INVALID_WORKFLOW_STEP", "step.protected MUST be boolean")
    conflict_group = value["conflict_group"]
    if conflict_group is not None:
        conflict_group = _uri(conflict_group, "step.conflict_group")
    return {
        "id": _uri(value["id"], "step.id"),
        "action": _uri(value["action"], "step.action"),
        "depends_on": _uris(value["depends_on"], "step.depends_on"),
        "protected": value["protected"],
        "conflict_group": conflict_group,
        "critical": _uris(value["critical"], "step.critical"),
    }


def _rule(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "id", "trigger", "required", "steps", "critical",
    }:
        fail("INVALID_WORKFLOW_RULE", "workflow rule shape is invalid")
    if not isinstance(value["required"], bool):
        fail("INVALID_WORKFLOW_RULE", "rule.required MUST be boolean")
    steps = tuple(_step(item) for item in _collection(value["steps"], MAX_STEPS, "rule.steps"))
    if not steps:
        fail("EMPTY_WORKFLOW_SET", "rule.steps MUST be non-empty")
    ids = tuple(item["id"] for item in steps)
    if len(ids) != len(set(ids)) or ids != tuple(sorted(ids, key=lambda x: x.encode("utf-8"))):
        fail("NONCANONICAL_WORKFLOW_SET", "rule.steps MUST be sorted and unique")
    return {
        "id": _uri(value["id"], "rule.id"),
        "trigger": _uri(value["trigger"], "rule.trigger"),
        "required": value["required"],
        "steps": steps,
        "critical": _uris(value["critical"], "rule.critical"),
    }


def _topological_steps(steps: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    dependency_count = sum(len(item["depends_on"]) for item in steps.values())
    if dependency_count > MAX_DEPENDENCIES:
        fail("WORKFLOW_RESOURCE_LIMIT_EXCEEDED", "workflow dependency count exceeds limit")
    missing = sorted({dependency for item in steps.values() for dependency in item["depends_on"] if dependency not in steps})
    if missing:
        fail("WORKFLOW_DANGLING_DEPENDENCY", "workflow step dependency does not exist")
    pending = {key: set(item["depends_on"]) for key, item in steps.items()}
    ordered: list[str] = []
    while pending:
        ready = sorted((key for key, dependencies in pending.items() if not dependencies), key=lambda x: x.encode("utf-8"))
        if not ready:
            fail("WORKFLOW_DEPENDENCY_CYCLE", "workflow dependency graph contains a cycle")
        for key in ready:
            ordered.append(key)
            del pending[key]
        for dependencies in pending.values():
            dependencies.difference_update(ready)
    return tuple(ordered)


def validate_remedy_workflow_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "version", "profile", "method", "domain", "purposes", "rules", "critical",
    }:
        fail("INVALID_WORKFLOW_PROFILE", "workflow profile shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_WORKFLOW_PROFILE", "workflow profile version MUST be integer 1")
    processing_profile = _uri(value["profile"], "profile")
    if processing_profile != PROFILE_REMEDY_WORKFLOW:
        fail("UNSUPPORTED_WORKFLOW_PROFILE", "reference planner supports outcome-rules-v1 only")
    rules = tuple(_rule(item) for item in _collection(value["rules"], MAX_RULES, "rules"))
    if not rules:
        fail("EMPTY_WORKFLOW_SET", "rules MUST be non-empty")
    rule_ids = tuple(item["id"] for item in rules)
    if len(rule_ids) != len(set(rule_ids)) or rule_ids != tuple(sorted(rule_ids, key=lambda x: x.encode("utf-8"))):
        fail("NONCANONICAL_WORKFLOW_SET", "rules MUST be sorted and unique")
    steps: dict[str, dict[str, Any]] = {}
    for rule in rules:
        for item in rule["steps"]:
            if item["id"] in steps:
                fail("DUPLICATE_WORKFLOW_STEP", "workflow step identifiers MUST be globally unique")
            steps[item["id"]] = item
    if len(steps) > MAX_STEPS:
        fail("WORKFLOW_RESOURCE_LIMIT_EXCEEDED", "workflow total step count exceeds limit")
    _topological_steps(steps)
    return {
        "version": 1,
        "profile": processing_profile,
        "method": _uri(value["method"], "method"),
        "domain": _uri(value["domain"], "domain"),
        "purposes": _uris(value["purposes"], "purposes", allow_empty=False),
        "rules": rules,
        "critical": _uris(value["critical"], "critical"),
    }


def remedy_workflow_profile_fingerprint(value: Any) -> str:
    return _fingerprint(validate_remedy_workflow_profile(value))


def validate_remedy_workflow_request(value: Any, profile: Any) -> dict[str, Any]:
    normalized = validate_remedy_workflow_profile(profile)
    if not isinstance(value, Mapping) or set(value) != {
        "version", "method", "domain", "purpose", "target_record_ids", "context", "understood_critical",
    }:
        fail("INVALID_WORKFLOW_REQUEST", "workflow request shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_WORKFLOW_REQUEST", "workflow request version MUST be integer 1")
    method, domain, purpose = (_uri(value[field], f"request.{field}") for field in ("method", "domain", "purpose"))
    if method != normalized["method"]:
        fail("WORKFLOW_METHOD_BINDING_MISMATCH", "request method does not match workflow profile")
    if domain != normalized["domain"]:
        fail("WORKFLOW_DOMAIN_BINDING_MISMATCH", "request domain does not match workflow profile")
    if purpose not in normalized["purposes"]:
        fail("WORKFLOW_PURPOSE_NOT_SUPPORTED", "request purpose is not declared by workflow profile")
    return {
        "version": 1, "method": method, "domain": domain, "purpose": purpose,
        "target_record_ids": _record_ids(value["target_record_ids"], "target_record_ids"),
        "context": _context(value["context"]),
        "understood_critical": _uris(value["understood_critical"], "understood_critical"),
    }


def _observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "trigger", "state", "target_record_id", "source_result_fingerprint", "critical",
    }:
        fail("INVALID_WORKFLOW_OBSERVATION", "workflow outcome observation shape is invalid")
    state = value["state"]
    if not isinstance(state, str) or state not in OBSERVATION_STATES:
        fail("INVALID_WORKFLOW_OBSERVATION_STATE", "workflow outcome observation state is invalid")
    fingerprint = value["source_result_fingerprint"]
    if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
        fail("INVALID_WORKFLOW_SOURCE_FINGERPRINT", "source-result fingerprint MUST be 43 characters")
    return {
        "trigger": _uri(value["trigger"], "observation.trigger"),
        "state": state,
        "target_record_id": _record_identity(value["target_record_id"], "observation.target_record_id"),
        "source_result_fingerprint": fingerprint,
        "critical": _uris(value["critical"], "observation.critical"),
    }


def _normalize_observations(values: Any, profile: Mapping[str, Any], request: Mapping[str, Any]) -> tuple[tuple[dict[str, Any], ...], int]:
    triggers = {rule["trigger"] for rule in profile["rules"]}
    targets = set(request["target_record_ids"])
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates = 0
    for raw in _collection(values, MAX_OBSERVATIONS, "observations"):
        item = _observation(raw)
        if item["trigger"] not in triggers:
            fail("UNKNOWN_WORKFLOW_TRIGGER", "observation trigger is not declared by the profile")
        if item["target_record_id"] not in targets:
            fail("WORKFLOW_TARGET_BINDING_MISMATCH", "observation target is outside the request")
        key = (item["trigger"], item["target_record_id"])
        previous = by_key.get(key)
        if previous is None:
            by_key[key] = item
        elif previous == item:
            duplicates += 1
        else:
            fail("WORKFLOW_OBSERVATION_CONFLICT", "conflicting observations share one trigger and target")
    return tuple(by_key[key] for key in sorted(by_key)), duplicates


def _normalized_input(profile: Any, request: Any, observations: Any):
    normalized_profile = validate_remedy_workflow_profile(profile)
    normalized_request = validate_remedy_workflow_request(request, normalized_profile)
    observed, duplicates = _normalize_observations(observations, normalized_profile, normalized_request)
    return normalized_profile, normalized_request, observed, duplicates


def _proposal(profile: Mapping[str, Any], request: Mapping[str, Any], observations: tuple[dict[str, Any], ...]):
    understood = set(request["understood_critical"])
    observed = {(item["trigger"], item["target_record_id"]): item for item in observations}
    unknown = set(profile["critical"]) - understood
    unresolved: list[str] = []
    trace: list[dict[str, Any]] = []
    selected: dict[str, dict[str, Any]] = {}
    for rule in profile["rules"]:
        candidates = [observed.get((rule["trigger"], target)) for target in request["target_record_ids"]]
        present = [item for item in candidates if item is not None and item["state"] == "PRESENT"]
        rule_unknown = set(rule["critical"])
        for item in present:
            rule_unknown.update(item["critical"])
        rule_unknown.difference_update(understood)
        unknown.update(rule_unknown)
        if rule_unknown:
            decision = "UNRESOLVED_CRITICAL"
        elif present:
            decision = "APPLICABLE"
            for item in rule["steps"]:
                unknown.update(set(item["critical"]) - understood)
                selected[item["id"]] = item
        elif rule["required"] and not all(item is not None and item["state"] == "ABSENT" for item in candidates):
            decision = "UNRESOLVED_REQUIRED"
            unresolved.append(rule["id"])
        elif any(item is not None and item["state"] == "ABSENT" for item in candidates):
            decision = "TRIGGER_ABSENT"
        else:
            decision = "IGNORED_OPTIONAL_MISSING"
        trace.append({"rule": rule["id"], "trigger": rule["trigger"], "required": rule["required"], "decision": decision})
    unavailable_dependencies = sorted({dependency for item in selected.values() for dependency in item["depends_on"] if dependency not in selected})
    by_group: dict[str, list[str]] = {}
    for item in selected.values():
        group = item["conflict_group"]
        if group is not None:
            by_group.setdefault(group, []).append(item["id"])
    conflicts = tuple({"group": group, "steps": tuple(sorted(ids))} for group, ids in sorted(by_group.items()) if len(ids) > 1)
    order = () if unavailable_dependencies else _topological_steps(selected)
    proposed = tuple({
        "id": selected[key]["id"], "action": selected[key]["action"],
        "depends_on": selected[key]["depends_on"], "protected": selected[key]["protected"],
        "conflict_group": selected[key]["conflict_group"],
        "requires_fresh_authorization": selected[key]["protected"],
        "authorized": False, "executed": False,
    } for key in order)
    if unknown:
        status, final_rule = "INDETERMINATE", "UNKNOWN_CRITICAL_SEMANTICS"
    elif conflicts:
        status, final_rule = "REQUIRE_HUMAN_REVIEW", "CONFLICTING_PROPOSED_ACTIONS"
    elif unresolved or unavailable_dependencies:
        status, final_rule = "REQUIRE_ADDITIONAL_EVIDENCE", "REQUIRED_TRIGGER_OR_DEPENDENCY_UNRESOLVED"
    elif proposed:
        status, final_rule = "PROPOSED", "APPLICABLE_RULES_PROPOSED"
    else:
        status, final_rule = "PARTIAL", "NO_APPLICABLE_SUPPLIED_TRIGGER"
    return {
        "workflow_status": status, "final_rule": final_rule, "rule_trace": tuple(trace),
        "proposed_steps": proposed, "conflicts": conflicts,
        "unresolved_required_rules": tuple(sorted(unresolved)),
        "unavailable_dependencies": tuple(unavailable_dependencies),
        "unknown_critical_uris": tuple(sorted(unknown)),
    }


_RESULT_FIELDS = (
    "version", "profile", "method", "domain", "purpose", "target_record_ids", "context",
    "understood_critical", "method_profile_fingerprint", "request_fingerprint",
    "input_fingerprint", "rule_trace", "proposed_steps", "conflicts",
    "unresolved_required_rules", "unavailable_dependencies", "unknown_critical_uris",
    "workflow_status", "final_rule", "duplicate_observations",
)


def evaluate_remedy_workflow(profile: Any, request: Any, observations: Any) -> dict[str, Any]:
    normalized_profile, normalized_request, observed, duplicates = _normalized_input(profile, request, observations)
    proposal = _proposal(normalized_profile, normalized_request, observed)
    core = {
        "version": 1, "profile": normalized_profile["profile"],
        "method": normalized_profile["method"], "domain": normalized_profile["domain"],
        "purpose": normalized_request["purpose"], "target_record_ids": normalized_request["target_record_ids"],
        "context": normalized_request["context"], "understood_critical": normalized_request["understood_critical"],
        "method_profile_fingerprint": _fingerprint(normalized_profile),
        "request_fingerprint": _fingerprint(normalized_request),
        "input_fingerprint": _fingerprint({"profile": normalized_profile, "request": normalized_request, "observations": observed}),
        **proposal, "duplicate_observations": duplicates,
    }
    semantic = {key: core[key] for key in _RESULT_FIELDS if key != "duplicate_observations"}
    return {**core, "result_fingerprint": _fingerprint(semantic), **{key: False for key in _BOUNDARY_FIELDS}}


def validate_remedy_workflow_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_RESULT_FIELDS) | set(_BOUNDARY_FIELDS) | {"result_fingerprint"}:
        fail("INVALID_PRIOR_WORKFLOW_RESULT", "workflow result shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1 or value["profile"] != PROFILE_REMEDY_WORKFLOW:
        fail("INVALID_PRIOR_WORKFLOW_RESULT", "workflow result version or profile is invalid")
    if not isinstance(value["workflow_status"], str) or value["workflow_status"] not in WORKFLOW_STATUSES:
        fail("INVALID_PRIOR_WORKFLOW_RESULT", "workflow result status is invalid")
    if any(value[key] is not False for key in _BOUNDARY_FIELDS):
        fail("INVALID_PRIOR_WORKFLOW_RESULT", "workflow result constitutional boundary flags are invalid")
    for key in ("method_profile_fingerprint", "request_fingerprint", "input_fingerprint", "result_fingerprint"):
        if not isinstance(value[key], str) or not _FINGERPRINT_RE.fullmatch(value[key]):
            fail("INVALID_PRIOR_WORKFLOW_RESULT", f"{key} MUST be a SHA-256 fingerprint")
    duplicates = value["duplicate_observations"]
    if isinstance(duplicates, bool) or not isinstance(duplicates, int) or duplicates < 0:
        fail("INVALID_PRIOR_WORKFLOW_RESULT", "duplicate observation count is invalid")
    semantic = {key: value[key] for key in _RESULT_FIELDS if key != "duplicate_observations"}
    if _fingerprint(semantic) != value["result_fingerprint"]:
        fail("WORKFLOW_RESULT_INTEGRITY_MISMATCH", "workflow result fingerprint does not match its content")
    return dict(value)


def evaluate_remedy_workflow_reuse(prior: Any, profile: Any, request: Any, observations: Any) -> dict[str, Any]:
    previous = validate_remedy_workflow_result(prior)
    current = evaluate_remedy_workflow(profile, request, observations)
    reasons: list[str] = []
    if previous["method_profile_fingerprint"] != current["method_profile_fingerprint"]:
        reasons.append("WORKFLOW_METHOD_PROFILE_CHANGED")
    if previous["request_fingerprint"] != current["request_fingerprint"]:
        reasons.append("WORKFLOW_REQUEST_CHANGED")
    if previous["input_fingerprint"] != current["input_fingerprint"]:
        reasons.append("WORKFLOW_INPUT_CHANGED")
    if previous["result_fingerprint"] != current["result_fingerprint"]:
        reasons.append("WORKFLOW_RESULT_CHANGED")
    return {"reuse_status": "NOT_REUSABLE" if reasons else "REUSABLE", "reasons": tuple(reasons)}
