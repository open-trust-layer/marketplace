from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

from marketplace_policy_v1 import (
    CORE_OPERATIONS,
    DIM_AUTHORIZATION,
    METHOD_CORE,
    OP_AUTONOMOUS_EXECUTION,
    OP_DISCLOSURE,
    OP_DISCOVERY_VISIBILITY,
    OP_DISPLAY,
    OP_FEDERATION_EXCHANGE,
    OP_FULFILLMENT_SIDE_EFFECT,
    OP_LOCAL_INSPECTION,
    OP_NEGOTIATION,
    OP_SETTLEMENT_SIDE_EFFECT,
    OP_SUBMISSION,
    OP_TRUST_RESULT_CONSUMPTION,
    PolicyObservation,
    evaluate_decision_reuse,
    evaluate_policy,
    policy_request_fingerprint,
    policy_subject_fingerprint,
    validate_policy_request,
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "safety-policy-authorization-v1.json"
RECORD_ID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"
DEFAULT_SUBJECT_FP: str | None = None


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def observation_wire(value: PolicyObservation) -> dict:
    return {
        "dimension": value.dimension,
        "status": value.status,
        "source": value.source,
        "reason": value.reason,
        "evidence_ids": list(value.evidence_ids),
        "valid_from": value.valid_from,
        "valid_until": value.valid_until,
        "subject_fingerprint": value.subject_fingerprint,
    }


def obs(
    dimension: str,
    status: str,
    *,
    source: str = "https://policy-a.example/source",
    reason: str = "https://policy-a.example/reason/default",
    evidence_ids: tuple[str, ...] = (),
    valid_from: str | None = None,
    valid_until: str | None = None,
) -> PolicyObservation:
    return PolicyObservation(
        dimension=dimension,
        status=status,
        source=source,
        reason=reason,
        evidence_ids=evidence_ids,
        valid_from=valid_from,
        valid_until=valid_until,
        subject_fingerprint=DEFAULT_SUBJECT_FP,
    )


def request(
    operation: str,
    dimensions: tuple[str, ...],
    *,
    actor: str = "https://example.test/principal/alice",
    target: dict | None = None,
    context: dict | None = None,
    evaluation_time: str = "2026-08-24T19:00:00Z",
) -> dict:
    return {
        "version": 1,
        "method": METHOD_CORE,
        "decision_scope": "https://example.test/policy/local-v1",
        "operation": operation,
        "actor": actor,
        "target": target or {"kind": "resource-uri", "value": "https://example.test/resource/1"},
        "context": context or {},
        "evaluation_time": evaluation_time,
        "required_dimensions": list(dimensions),
    }


def build() -> dict:
    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})

    local = request(OP_LOCAL_INSPECTION, ())
    add("request-local-inspection-valid", "request", {"request": local}, {
        "request": validate_policy_request(local),
        "fingerprint": policy_request_fingerprint(local),
    })

    protected_dims = ("authorization", "safety")
    side_effects = {
        OP_SUBMISSION,
        OP_AUTONOMOUS_EXECUTION,
        OP_FULFILLMENT_SIDE_EFFECT,
        OP_SETTLEMENT_SIDE_EFFECT,
        OP_FEDERATION_EXCHANGE,
        OP_DISCLOSURE,
    }
    for operation in sorted(CORE_OPERATIONS):
        if operation == OP_LOCAL_INSPECTION:
            continue
        dims = protected_dims if operation in side_effects else ("safety",)
        req = request(operation, dims)
        add(f"request-operation-{operation.rsplit('/', 1)[-1]}", "request", {"request": req}, {
            "request": validate_policy_request(req),
            "fingerprint": policy_request_fingerprint(req),
        })

    settlement = request(OP_SETTLEMENT_SIDE_EFFECT, protected_dims)
    global DEFAULT_SUBJECT_FP
    DEFAULT_SUBJECT_FP = policy_subject_fingerprint(settlement)
    satisfied = (
        obs("authorization", "SATISFIED", evidence_ids=(RECORD_ID,)),
        obs("safety", "SATISFIED"),
    )
    allow = evaluate_policy(settlement, satisfied)
    add("evaluation-protected-side-effect-allow", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, allow)
    add("evaluation-local-inspection-not-applicable", "evaluation", {
        "request": local,
        "observations": [],
    }, evaluate_policy(local, ()))
    deny_obs = (obs("authorization", "UNSATISFIED"), obs("safety", "SATISFIED"))
    add("evaluation-explicit-authorization-deny", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in deny_obs],
    }, evaluate_policy(settlement, deny_obs))
    missing_auth = (obs("safety", "SATISFIED"),)
    add("evaluation-missing-authorization-requires-evidence", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in missing_auth],
    }, evaluate_policy(settlement, missing_auth))
    unknown_auth = (obs("authorization", "UNKNOWN"), obs("safety", "SATISFIED"))
    add("evaluation-unknown-authorization-requires-evidence", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in unknown_auth],
    }, evaluate_policy(settlement, unknown_auth))
    unsupported_auth = (obs("authorization", "UNSUPPORTED"), obs("safety", "SATISFIED"))
    add("evaluation-unsupported-authorization-indeterminate", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in unsupported_auth],
    }, evaluate_policy(settlement, unsupported_auth))
    stale_auth = (
        obs("authorization", "SATISFIED", valid_until="2026-08-24T18:00:00Z"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-stale-authorization-indeterminate", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in stale_auth],
    }, evaluate_policy(settlement, stale_auth))
    human_review = (obs("authorization", "SATISFIED"), obs("safety", "REQUIRE_HUMAN_REVIEW"))
    add("evaluation-human-review-preserved", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in human_review],
    }, evaluate_policy(settlement, human_review))
    quarantine = (obs("authorization", "SATISFIED"), obs("safety", "QUARANTINE"))
    add("evaluation-quarantine-preserved", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in quarantine],
    }, evaluate_policy(settlement, quarantine))
    conflict = (
        obs("authorization", "SATISFIED"),
        obs("authorization", "UNSATISFIED", source="https://policy-b.example/source", reason="https://policy-b.example/reason/deny"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-divergent-policy-conflict", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in conflict],
    }, evaluate_policy(settlement, conflict))
    authority_only = (
        obs("authority", "SATISFIED"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-authority-does-not-substitute-authorization", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in authority_only],
    }, evaluate_policy(settlement, authority_only))
    not_applicable_auth = (
        obs("authorization", "NOT_APPLICABLE"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-not-applicable-is-not-deny", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in not_applicable_auth],
    }, evaluate_policy(settlement, not_applicable_auth))
    duplicate = satisfied + (satisfied[0],)
    add("evaluation-exact-observation-replay-deduplicated", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in duplicate],
    }, evaluate_policy(settlement, duplicate))
    add("evaluation-observation-order-invariant", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in reversed(satisfied)],
    }, evaluate_policy(settlement, tuple(reversed(satisfied))))
    two_positive_sources = (
        obs("authorization", "SATISFIED"),
        obs("authorization", "SATISFIED", source="https://policy-b.example/source", reason="https://policy-b.example/reason/allow"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-convergent-policy-sources-allow", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in two_positive_sources],
    }, evaluate_policy(settlement, two_positive_sources))
    stale_and_current = (
        obs("authorization", "UNSATISFIED", valid_until="2026-08-24T18:00:00Z"),
        obs("authorization", "SATISFIED", source="https://policy-b.example/source", reason="https://policy-b.example/reason/current"),
        obs("safety", "SATISFIED"),
    )
    add("evaluation-stale-negative-does-not-override-current", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in stale_and_current],
    }, evaluate_policy(settlement, stale_and_current))
    explicit_more = (
        obs("authorization", "SATISFIED"),
        obs("safety", "REQUIRE_ADDITIONAL_EVIDENCE"),
    )
    add("evaluation-explicit-additional-evidence-preserved", "evaluation", {
        "request": settlement,
        "observations": [observation_wire(item) for item in explicit_more],
    }, evaluate_policy(settlement, explicit_more))

    add("reuse-identical-allow-reusable", "reuse", {
        "prior_result": allow,
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, evaluate_decision_reuse(allow, settlement, satisfied))
    changed_context = dict(settlement)
    changed_context["context"] = {"https://example.test/context/mode": "changed"}
    changed_context_obs = tuple(replace(item, subject_fingerprint=policy_subject_fingerprint(changed_context)) for item in satisfied)
    add("reuse-changed-context-not-reusable", "reuse", {
        "prior_result": allow,
        "request": changed_context,
        "observations": [observation_wire(item) for item in changed_context_obs],
    }, evaluate_decision_reuse(allow, changed_context, changed_context_obs))
    changed_evidence = (
        obs("authorization", "SATISFIED", source="https://policy-b.example/source", reason="https://policy-b.example/reason/allow"),
        obs("safety", "SATISFIED"),
    )
    add("reuse-changed-evidence-not-reusable", "reuse", {
        "prior_result": allow,
        "request": settlement,
        "observations": [observation_wire(item) for item in changed_evidence],
    }, evaluate_decision_reuse(allow, settlement, changed_evidence))
    changed_time = dict(settlement)
    changed_time["evaluation_time"] = "2026-08-24T20:00:00Z"
    add("evaluation-new-time-requires-new-decision", "evaluation", {
        "request": changed_time,
        "observations": [observation_wire(item) for item in satisfied],
    }, evaluate_policy(changed_time, satisfied))
    add("reuse-changed-time-not-reusable", "reuse", {
        "prior_result": allow,
        "request": changed_time,
        "observations": [observation_wire(item) for item in satisfied],
    }, evaluate_decision_reuse(allow, changed_time, satisfied))
    deny_result = evaluate_policy(settlement, deny_obs)
    add("reuse-prior-deny-never-reusable", "reuse", {
        "prior_result": deny_result,
        "request": settlement,
        "observations": [observation_wire(item) for item in deny_obs],
    }, evaluate_decision_reuse(deny_result, settlement, deny_obs))

    record_target = request(
        OP_DISPLAY,
        ("safety",),
        target={"kind": "record", "value": RECORD_ID},
    )
    add("request-record-target-valid", "request", {"request": record_target}, {
        "request": validate_policy_request(record_target),
        "fingerprint": policy_request_fingerprint(record_target),
    })
    negative("request-not-map", "request", {"request": []}, "INVALID_POLICY_REQUEST")
    missing = dict(settlement); missing.pop("actor")
    negative("request-missing-actor", "request", {"request": missing}, "INVALID_POLICY_REQUEST")
    bool_version = dict(settlement); bool_version["version"] = True
    negative("request-boolean-version", "request", {"request": bool_version}, "INVALID_POLICY_REQUEST")
    unknown_operation = dict(settlement); unknown_operation["operation"] = "https://example.test/policy/operation/unknown"
    negative("request-unsupported-operation", "request", {"request": unknown_operation}, "UNSUPPORTED_POLICY_OPERATION")
    no_dims = request(OP_DISPLAY, ())
    negative("request-protected-operation-needs-dimension", "request", {"request": no_dims}, "POLICY_DIMENSION_REQUIRED")
    no_auth = request(OP_SETTLEMENT_SIDE_EFFECT, ("safety",))
    negative("request-side-effect-needs-authorization", "request", {"request": no_auth}, "AUTHORIZATION_DIMENSION_REQUIRED")
    unsorted_dims = request(OP_SETTLEMENT_SIDE_EFFECT, ("authorization", "safety")); unsorted_dims["required_dimensions"] = ["safety", "authorization"]
    negative("request-dimensions-must-be-sorted", "request", {"request": unsorted_dims}, "NONCANONICAL_POLICY_SET")
    duplicate_dims = request(OP_SETTLEMENT_SIDE_EFFECT, ("authorization", "safety")); duplicate_dims["required_dimensions"] = ["authorization", "authorization", "safety"]
    negative("request-dimensions-must-be-unique", "request", {"request": duplicate_dims}, "NONCANONICAL_POLICY_SET")
    unsupported_dim = request(OP_DISPLAY, ("safety",)); unsupported_dim["required_dimensions"] = ["https://example.test/dimension/custom"]
    negative("request-unsupported-dimension", "request", {"request": unsupported_dim}, "UNSUPPORTED_POLICY_DIMENSION")
    bad_actor = dict(settlement); bad_actor["actor"] = "alice"
    negative("request-actor-must-be-uri", "request", {"request": bad_actor}, "INVALID_POLICY_URI")
    bad_scope = dict(settlement); bad_scope["decision_scope"] = "local"
    negative("request-scope-must-be-uri", "request", {"request": bad_scope}, "INVALID_POLICY_URI")
    bad_target_kind = dict(settlement); bad_target_kind["target"] = {"kind": "opaque", "value": "x"}
    negative("request-target-kind-unsupported", "request", {"request": bad_target_kind}, "INVALID_POLICY_TARGET")
    bad_target_uri = dict(settlement); bad_target_uri["target"] = {"kind": "resource-uri", "value": "not-uri"}
    negative("request-target-uri-invalid", "request", {"request": bad_target_uri}, "INVALID_POLICY_URI")
    bad_record_target = dict(record_target); bad_record_target["target"] = {"kind": "record", "value": "r1_bad"}
    negative("request-record-target-invalid", "request", {"request": bad_record_target}, "INVALID_POLICY_TARGET")
    bad_time = dict(settlement); bad_time["evaluation_time"] = "not-time"
    negative("request-evaluation-time-invalid", "request", {"request": bad_time}, "INVALID_POLICY_TIME")
    bad_context = dict(settlement); bad_context["context"] = {"not-uri": "x"}
    negative("request-context-key-invalid", "request", {"request": bad_context}, "INVALID_POLICY_URI")
    unknown_method = dict(settlement); unknown_method["method"] = "https://example.test/policy/method/unknown"
    negative("evaluation-unsupported-method", "evaluation", {
        "request": unknown_method,
        "observations": [observation_wire(item) for item in satisfied],
    }, "UNSUPPORTED_POLICY_METHOD")
    bad_dimension_obs = observation_wire(obs("authorization", "SATISFIED")); bad_dimension_obs["dimension"] = "unknown-dimension"
    negative("observation-dimension-unsupported", "evaluation", {
        "request": settlement, "observations": [bad_dimension_obs],
    }, "UNSUPPORTED_POLICY_DIMENSION")
    bad_status_obs = observation_wire(obs("authorization", "SATISFIED")); bad_status_obs["status"] = "MAYBE"
    negative("observation-status-unsupported", "evaluation", {
        "request": settlement, "observations": [bad_status_obs],
    }, "INVALID_POLICY_OBSERVATION")
    bad_source_obs = observation_wire(obs("authorization", "SATISFIED")); bad_source_obs["source"] = "local"
    negative("observation-source-must-be-uri", "evaluation", {
        "request": settlement, "observations": [bad_source_obs],
    }, "INVALID_POLICY_URI")
    bad_reason_obs = observation_wire(obs("authorization", "SATISFIED")); bad_reason_obs["reason"] = "because"
    negative("observation-reason-must-be-uri", "evaluation", {
        "request": settlement, "observations": [bad_reason_obs],
    }, "INVALID_POLICY_URI")
    bad_interval = observation_wire(obs("authorization", "SATISFIED", valid_from="2026-08-24T20:00:00Z", valid_until="2026-08-24T19:00:00Z"))
    negative("observation-invalid-interval", "evaluation", {
        "request": settlement, "observations": [bad_interval],
    }, "INVALID_POLICY_INTERVAL")
    bad_evidence = observation_wire(obs("authorization", "SATISFIED")); bad_evidence["evidence_ids"] = ["r1_bad"]
    negative("observation-invalid-evidence-id", "evaluation", {
        "request": settlement, "observations": [bad_evidence],
    }, "INVALID_POLICY_TARGET")
    duplicate_evidence = observation_wire(obs("authorization", "SATISFIED")); duplicate_evidence["evidence_ids"] = [RECORD_ID, RECORD_ID]
    negative("observation-duplicate-evidence-ids", "evaluation", {
        "request": settlement, "observations": [duplicate_evidence],
    }, "NONCANONICAL_POLICY_SET")
    second_id = "r1_krAuHnpOl5qW631XJC4ecOQISaB93rVNQ0bFvU0ed1w"
    unsorted_evidence = observation_wire(obs("authorization", "SATISFIED")); unsorted_evidence["evidence_ids"] = [second_id, RECORD_ID]
    negative("observation-evidence-ids-must-be-sorted", "evaluation", {
        "request": settlement, "observations": [unsorted_evidence],
    }, "NONCANONICAL_POLICY_SET")

    replay_actor = dict(settlement); replay_actor["actor"] = "https://example.test/principal/bob"
    negative("observation-replay-cross-actor-rejected", "evaluation", {
        "request": replay_actor, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    replay_target = dict(settlement); replay_target["target"] = {"kind": "resource-uri", "value": "https://example.test/resource/2"}
    negative("observation-replay-cross-target-rejected", "evaluation", {
        "request": replay_target, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    replay_operation = dict(settlement); replay_operation["operation"] = OP_FULFILLMENT_SIDE_EFFECT
    negative("observation-replay-cross-operation-rejected", "evaluation", {
        "request": replay_operation, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    replay_context = dict(settlement); replay_context["context"] = {"https://example.test/context/mode": "other"}
    negative("observation-replay-cross-context-rejected", "evaluation", {
        "request": replay_context, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    replay_dims = dict(settlement); replay_dims["required_dimensions"] = ["authorization", "business-policy", "safety"]
    negative("observation-replay-cross-dimensions-rejected", "evaluation", {
        "request": replay_dims, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    replay_scope = dict(settlement); replay_scope["decision_scope"] = "https://example.test/policy/other-local-v1"
    negative("observation-replay-cross-scope-rejected", "evaluation", {
        "request": replay_scope, "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_OBSERVATION_SUBJECT_MISMATCH")
    malformed_binding = observation_wire(obs("authorization", "SATISFIED")); malformed_binding["subject_fingerprint"] = "A" * 42
    negative("observation-subject-fingerprint-malformed", "evaluation", {
        "request": settlement, "observations": [malformed_binding],
    }, "INVALID_POLICY_FINGERPRINT")
    missing_binding = observation_wire(obs("authorization", "SATISFIED")); missing_binding.pop("subject_fingerprint")
    negative("observation-subject-fingerprint-required", "evaluation", {
        "request": settlement, "observations": [missing_binding],
    }, "INVALID_POLICY_FINGERPRINT")

    tampered = dict(allow); tampered["outcome"] = "DENY"
    negative("reuse-tampered-prior-result-rejected", "reuse", {
        "prior_result": tampered,
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, "INVALID_PRIOR_POLICY_RESULT")
    extra_field = dict(allow); extra_field["unbound_permission"] = True
    negative("reuse-prior-result-extra-field-rejected", "reuse", {
        "prior_result": extra_field,
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, "INVALID_PRIOR_POLICY_RESULT")
    boundary_tamper = dict(allow); boundary_tamper["result_authentication_established"] = True
    negative("reuse-prior-result-boundary-flag-tamper-rejected", "reuse", {
        "prior_result": boundary_tamper,
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, "INVALID_PRIOR_POLICY_RESULT")
    tampered_fp = dict(allow); tampered_fp["result_fingerprint"] = "A" * 43
    negative("reuse-result-fingerprint-mismatch", "reuse", {
        "prior_result": tampered_fp,
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, "POLICY_RESULT_INTEGRITY_MISMATCH")
    negative("resource-observation-count-bounded", "synthetic-observation-limit", {
        "count": 4097,
    }, "POLICY_RESOURCE_LIMIT_EXCEEDED")
    negative("resource-evidence-ids-per-observation-bounded", "synthetic-evidence-limit", {
        "count": 257,
    }, "POLICY_RESOURCE_LIMIT_EXCEEDED")
    negative("resource-context-entries-bounded", "synthetic-context-limit", {
        "count": 129,
    }, "INVALID_POLICY_CONTEXT")
    negative("resource-uri-bytes-bounded", "synthetic-uri-limit", {
        "utf8_bytes": 2049,
    }, "POLICY_RESOURCE_LIMIT_EXCEEDED")
    negative("reuse-prior-result-shape-required", "reuse", {
        "prior_result": {"outcome": "ALLOW"},
        "request": settlement,
        "observations": [observation_wire(item) for item in satisfied],
    }, "INVALID_PRIOR_POLICY_RESULT")

    return {
        "format": "marketplace-safety-policy-authorization-v1",
        "olp_reference_source_commit": olp_commit(),
        "method": METHOD_CORE,
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> None:
    artifact = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")
    print(f"positive/evaluation={len(artifact['cases'])} negative/adversarial={len(artifact['negative_cases'])} total={len(artifact['cases']) + len(artifact['negative_cases'])}")


if __name__ == "__main__":
    main()
