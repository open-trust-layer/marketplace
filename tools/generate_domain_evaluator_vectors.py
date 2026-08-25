"""Generate Marketplace domain-evaluator method v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_domain_evaluator_v1 import (
    MAX_CONTEXT_ENTRIES,
    MAX_CRITERIA,
    MAX_OBSERVATIONS,
    MAX_SET_ITEMS,
    MAX_URI_BYTES,
    MAX_WEIGHT,
    PROFILE_CRITERION_THRESHOLD,
    domain_method_profile_fingerprint,
    evaluate_domain_method,
    evaluate_domain_method_reuse,
    validate_domain_method_profile,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "domain-evaluator-methods-v1.json"
BASE = "https://example.test/domain-method"
METHOD = f"{BASE}/method/software-release-readiness-v1"
DOMAIN = f"{BASE}/domain/software-change"
PURPOSE = f"{BASE}/purpose/release-readiness"
CRITICAL = f"{BASE}/critical/static-analysis-v1"
RID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"


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


def criterion(name: str, *, required: bool, weight: int, critical=()) -> dict:
    return {
        "id": f"{BASE}/criterion/{name}",
        "required": required,
        "weight": weight,
        "critical": sorted(critical),
    }


def method_profile(*, critical=(), method=METHOD, domain=DOMAIN, purpose=PURPOSE) -> dict:
    return {
        "version": 1,
        "profile": PROFILE_CRITERION_THRESHOLD,
        "method": method,
        "domain": domain,
        "purposes": [purpose],
        "criteria": [
            criterion("a", required=True, weight=3),
            criterion("b", required=True, weight=3),
            criterion("c", required=False, weight=1),
        ],
        "support_threshold": 3,
        "oppose_threshold": 3,
        "critical": sorted(critical),
    }


def request(*, understood=(), method=METHOD, domain=DOMAIN, purpose=PURPOSE, context=None) -> dict:
    return {
        "version": 1,
        "method": method,
        "domain": domain,
        "purpose": purpose,
        "target_record_id": RID,
        "context": context or {},
        "understood_critical": sorted(understood),
    }


def observation(name: str, state: str, *, critical=(), reasons=()) -> dict:
    return {
        "criterion": f"{BASE}/criterion/{name}",
        "state": state,
        "critical": sorted(critical),
        "reason_uris": sorted(reasons),
    }


def complete(a="SUPPORTS", b="NEUTRAL", c="NEUTRAL") -> list[dict]:
    return [observation("a", a), observation("b", b), observation("c", c)]


def build() -> dict:
    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})

    base = method_profile()
    base_request = request()
    base_observations = complete()
    add("profile-valid", "profile", {"profile": base}, {
        "profile": validate_domain_method_profile(base),
        "fingerprint": domain_method_profile_fingerprint(base),
    })

    physical = method_profile(
        method=f"{BASE}/method/physical-condition-v1",
        domain=f"{BASE}/domain/physical-goods",
        purpose=f"{BASE}/purpose/condition-assessment",
    )
    add("profile-second-domain-valid", "profile", {"profile": physical}, {
        "profile": validate_domain_method_profile(physical),
        "fingerprint": domain_method_profile_fingerprint(physical),
    })

    def evaluation(case_id: str, p: dict, r: dict, observed) -> dict:
        result = evaluate_domain_method(p, r, observed)
        add(case_id, "evaluation", {"profile": p, "request": r, "observations": observed}, result)
        return result
    ready = evaluation("evaluation-support", base, base_request, base_observations)
    evaluation("evaluation-oppose", base, base_request, complete(a="OPPOSES"))
    evaluation("evaluation-neutral", base, base_request, complete(a="NEUTRAL"))
    evaluation(
        "evaluation-conflict", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "OPPOSES")],
    )
    evaluation(
        "evaluation-missing-required", base, base_request,
        [observation("a", "SUPPORTS")],
    )
    evaluation(
        "evaluation-optional-missing", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "NEUTRAL")],
    )
    evaluation(
        "evaluation-required-unknown", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "UNKNOWN")],
    )
    evaluation(
        "evaluation-required-unsupported", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "UNSUPPORTED")],
    )
    evaluation(
        "evaluation-required-not-applicable", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "NOT_APPLICABLE")],
    )
    evaluation(
        "evaluation-optional-unknown-ignored", base, base_request,
        [observation("a", "SUPPORTS"), observation("b", "NEUTRAL"), observation("c", "UNKNOWN")],
    )
    duplicate_observations = base_observations + [deepcopy(base_observations[0])]
    duplicate_result = evaluation(
        "evaluation-exact-duplicate-deduplicated", base, base_request, duplicate_observations
    )
    assert duplicate_result["duplicate_observations"] == 1
    method_critical_profile = method_profile(critical=(CRITICAL,))
    evaluation(
        "evaluation-method-critical-unknown",
        method_critical_profile,
        request(),
        base_observations,
    )
    evaluation(
        "evaluation-method-critical-understood",
        method_critical_profile,
        request(understood=(CRITICAL,)),
        base_observations,
    )
    criterion_critical_profile = method_profile()
    criterion_critical_profile["criteria"][0]["critical"] = [CRITICAL]
    evaluation(
        "evaluation-criterion-critical-unknown",
        criterion_critical_profile,
        base_request,
        base_observations,
    )
    evaluation(
        "evaluation-criterion-critical-understood",
        criterion_critical_profile,
        request(understood=(CRITICAL,)),
        base_observations,
    )
    observation_critical = deepcopy(base_observations)
    observation_critical[0]["critical"] = [CRITICAL]
    evaluation(
        "evaluation-observation-critical-unknown",
        base,
        base_request,
        observation_critical,
    )
    evaluation(
        "evaluation-observation-critical-understood",
        base,
        request(understood=(CRITICAL,)),
        observation_critical,
    )
    ordered = list(reversed(base_observations))
    evaluation("evaluation-order-normalized", base, base_request, ordered)
    contextual_request = request(
        context={f"{BASE}/context/risk-class": "high"}
    )
    evaluation(
        "evaluation-context-bound",
        base,
        contextual_request,
        base_observations,
    )
    add("reuse-exact", "reuse", {
        "prior_result": ready,
        "profile": base,
        "request": base_request,
        "observations": base_observations,
    }, evaluate_domain_method_reuse(ready, base, base_request, base_observations))

    add("reuse-exact-duplicate-delivery", "reuse", {
        "prior_result": ready,
        "profile": base,
        "request": base_request,
        "observations": duplicate_observations,
    }, evaluate_domain_method_reuse(ready, base, base_request, duplicate_observations))

    changed_profile = deepcopy(base)
    changed_profile["support_threshold"] = 4
    add("reuse-profile-changed", "reuse", {
        "prior_result": ready,
        "profile": changed_profile,
        "request": base_request,
        "observations": base_observations,
    }, evaluate_domain_method_reuse(ready, changed_profile, base_request, base_observations))

    changed_request = request(context={f"{BASE}/context/risk-class": "high"})
    add("reuse-request-changed", "reuse", {
        "prior_result": ready,
        "profile": base,
        "request": changed_request,
        "observations": base_observations,
    }, evaluate_domain_method_reuse(ready, base, changed_request, base_observations))
    changed_observations = complete(a="NEUTRAL")
    add("reuse-observations-changed", "reuse", {
        "prior_result": ready,
        "profile": base,
        "request": base_request,
        "observations": changed_observations,
    }, evaluate_domain_method_reuse(ready, base, base_request, changed_observations))

    physical_request = request(
        method=physical["method"],
        domain=physical["domain"],
        purpose=physical["purposes"][0],
    )
    evaluation(
        "evaluation-second-domain-method",
        physical,
        physical_request,
        base_observations,
    )

    threshold_profile = deepcopy(base)
    threshold_profile["support_threshold"] = 4
    threshold_profile["oppose_threshold"] = 4
    evaluation(
        "evaluation-below-method-threshold-neutral",
        threshold_profile,
        base_request,
        base_observations,
    )
    negative("profile-not-map", "profile", {"profile": []}, "INVALID_DOMAIN_METHOD")
    bad = deepcopy(base); bad.pop("critical")
    negative("profile-missing-field", "profile", {"profile": bad}, "INVALID_DOMAIN_METHOD")
    bad = deepcopy(base); bad["version"] = True
    negative("profile-version-bool", "profile", {"profile": bad}, "INVALID_DOMAIN_METHOD")
    bad = deepcopy(base); bad["version"] = 2
    negative("profile-version-two", "profile", {"profile": bad}, "INVALID_DOMAIN_METHOD")
    bad = deepcopy(base); bad["profile"] = f"{BASE}/profile/unsupported"
    negative("profile-unsupported-profile", "profile", {"profile": bad}, "UNSUPPORTED_DOMAIN_METHOD_PROFILE")
    for field in ("method", "domain"):
        bad = deepcopy(base); bad[field] = "relative"
        negative(f"profile-invalid-{field}", "profile", {"profile": bad}, "INVALID_DOMAIN_URI")
    bad = deepcopy(base); bad["purposes"] = []
    negative("profile-empty-purposes", "profile", {"profile": bad}, "EMPTY_DOMAIN_SET")
    bad = deepcopy(base); bad["purposes"] = [PURPOSE, PURPOSE]
    negative("profile-duplicate-purpose", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["purposes"] = [f"{BASE}/purpose/z", f"{BASE}/purpose/a"]
    negative("profile-unsorted-purposes", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["purposes"] = ["relative"]
    negative("profile-invalid-purpose", "profile", {"profile": bad}, "INVALID_DOMAIN_URI")
    bad = deepcopy(base); bad["criteria"] = 7
    negative("profile-criteria-not-collection", "profile", {"profile": bad}, "INVALID_DOMAIN_COLLECTION")
    bad = deepcopy(base); bad["criteria"] = []
    negative("profile-empty-criteria", "profile", {"profile": bad}, "EMPTY_DOMAIN_SET")
    bad = deepcopy(base); bad["criteria"].append(deepcopy(bad["criteria"][0])); bad["criteria"].sort(key=lambda item: item["id"])
    negative("profile-duplicate-criterion-id", "profile", {"profile": bad}, "DUPLICATE_DOMAIN_CRITERION")
    bad = deepcopy(base); bad["criteria"] = list(reversed(bad["criteria"]))
    negative("profile-unsorted-criteria", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["criteria"][0] = []
    negative("criterion-not-map", "profile", {"profile": bad}, "INVALID_DOMAIN_CRITERION")
    bad = deepcopy(base); bad["criteria"][0].pop("critical")
    negative("criterion-missing-field", "profile", {"profile": bad}, "INVALID_DOMAIN_CRITERION")
    bad = deepcopy(base); bad["criteria"][0]["required"] = "yes"
    negative("criterion-required-not-bool", "profile", {"profile": bad}, "INVALID_DOMAIN_CRITERION")
    bad = deepcopy(base); bad["criteria"][0]["id"] = "relative"
    negative("criterion-invalid-id", "profile", {"profile": bad}, "INVALID_DOMAIN_URI")
    for suffix, weight in (("bool", True), ("zero", 0), ("too-large", MAX_WEIGHT + 1)):
        bad = deepcopy(base); bad["criteria"][0]["weight"] = weight
        negative(f"criterion-weight-{suffix}", "profile", {"profile": bad}, "INVALID_DOMAIN_WEIGHT")
    bad = deepcopy(base); bad["criteria"][0]["critical"] = [CRITICAL, CRITICAL]
    negative("criterion-duplicate-critical", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["criteria"][0]["critical"] = [f"{BASE}/critical/z", f"{BASE}/critical/a"]
    negative("criterion-unsorted-critical", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["criteria"][0]["critical"] = ["relative"]
    negative("criterion-invalid-critical", "profile", {"profile": bad}, "INVALID_DOMAIN_URI")
    for field in ("support_threshold", "oppose_threshold"):
        bad = deepcopy(base); bad[field] = True
        negative(f"profile-{field}-bool", "profile", {"profile": bad}, "INVALID_DOMAIN_THRESHOLD")
        bad = deepcopy(base); bad[field] = 0
        negative(f"profile-{field}-zero", "profile", {"profile": bad}, "INVALID_DOMAIN_THRESHOLD")
        bad = deepcopy(base); bad[field] = 8
        negative(f"profile-{field}-too-high", "profile", {"profile": bad}, "INVALID_DOMAIN_THRESHOLD")
    bad = deepcopy(base); bad["critical"] = [CRITICAL, CRITICAL]
    negative("profile-duplicate-critical", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["critical"] = [f"{BASE}/critical/z", f"{BASE}/critical/a"]
    negative("profile-unsorted-critical", "profile", {"profile": bad}, "NONCANONICAL_DOMAIN_SET")
    bad = deepcopy(base); bad["critical"] = ["relative"]
    negative("profile-invalid-critical", "profile", {"profile": bad}, "INVALID_DOMAIN_URI")

    negative("request-not-map", "request", {"profile": base, "request": []}, "INVALID_DOMAIN_REQUEST")
    bad_request = deepcopy(base_request); bad_request.pop("context")
    negative("request-missing-field", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_REQUEST")
    bad_request = deepcopy(base_request); bad_request["version"] = True
    negative("request-version-bool", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_REQUEST")
    bad_request = deepcopy(base_request); bad_request["version"] = 2
    negative("request-version-two", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_REQUEST")
    for field in ("method", "domain", "purpose"):
        bad_request = deepcopy(base_request); bad_request[field] = "relative"
        negative(f"request-invalid-{field}", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_URI")
    bad_request = deepcopy(base_request); bad_request["method"] = f"{BASE}/method/other"
    negative("request-method-binding-mismatch", "request", {"profile": base, "request": bad_request}, "DOMAIN_METHOD_BINDING_MISMATCH")
    bad_request = deepcopy(base_request); bad_request["domain"] = f"{BASE}/domain/other"
    negative("request-domain-binding-mismatch", "request", {"profile": base, "request": bad_request}, "DOMAIN_SCOPE_BINDING_MISMATCH")
    bad_request = deepcopy(base_request); bad_request["purpose"] = f"{BASE}/purpose/other"
    negative("request-purpose-not-supported", "request", {"profile": base, "request": bad_request}, "DOMAIN_PURPOSE_NOT_SUPPORTED")
    bad_request = deepcopy(base_request); bad_request["target_record_id"] = "r1_invalid"
    negative("request-invalid-record-id", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_RECORD_ID")
    bad_request = deepcopy(base_request); bad_request["context"] = []
    negative("request-context-not-map", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_CONTEXT")
    bad_request = deepcopy(base_request); bad_request["context"] = {"relative": "x"}
    negative("request-invalid-context-key", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_URI")
    bad_request = deepcopy(base_request); bad_request["context"] = {f"{BASE}/context/value": object()}
    negative("request-invalid-context-value", "synthetic-invalid-context-value", {
        "profile": base, "request": base_request,
    }, "INVALID_DOMAIN_CONTEXT")
    bad_request = deepcopy(base_request); bad_request["understood_critical"] = 7
    negative("request-understood-critical-not-collection", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_COLLECTION")
    bad_request = deepcopy(base_request); bad_request["understood_critical"] = [CRITICAL, CRITICAL]
    negative("request-duplicate-understood-critical", "request", {"profile": base, "request": bad_request}, "NONCANONICAL_DOMAIN_SET")
    bad_request = deepcopy(base_request); bad_request["understood_critical"] = [f"{BASE}/critical/z", f"{BASE}/critical/a"]
    negative("request-unsorted-understood-critical", "request", {"profile": base, "request": bad_request}, "NONCANONICAL_DOMAIN_SET")
    bad_request = deepcopy(base_request); bad_request["understood_critical"] = ["relative"]
    negative("request-invalid-understood-critical", "request", {"profile": base, "request": bad_request}, "INVALID_DOMAIN_URI")

    negative("observations-not-collection", "evaluation", {
        "profile": base, "request": base_request, "observations": 7,
    }, "INVALID_DOMAIN_COLLECTION")
    negative("observation-not-map", "evaluation", {
        "profile": base, "request": base_request, "observations": [[]],
    }, "INVALID_DOMAIN_OBSERVATION")
    bad_observation = observation("a", "SUPPORTS"); bad_observation.pop("critical")
    negative("observation-missing-field", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "INVALID_DOMAIN_OBSERVATION")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["state"] = "MAYBE"
    negative("observation-invalid-state", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "INVALID_DOMAIN_OBSERVATION_STATE")
    negative("observation-unhashable-state", "synthetic-unhashable-observation-state", {
        "profile": base, "request": base_request,
    }, "INVALID_DOMAIN_OBSERVATION_STATE")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["criterion"] = "relative"
    negative("observation-invalid-criterion-uri", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "INVALID_DOMAIN_URI")
    bad_observation = observation("unknown", "SUPPORTS")
    negative("observation-unknown-criterion", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "UNKNOWN_DOMAIN_CRITERION")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["critical"] = [CRITICAL, CRITICAL]
    negative("observation-duplicate-critical", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "NONCANONICAL_DOMAIN_SET")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["critical"] = [f"{BASE}/critical/z", f"{BASE}/critical/a"]
    negative("observation-unsorted-critical", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "NONCANONICAL_DOMAIN_SET")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["critical"] = ["relative"]
    negative("observation-invalid-critical", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "INVALID_DOMAIN_URI")
    reason_a = f"{BASE}/reason/a"
    reason_z = f"{BASE}/reason/z"
    bad_observation = observation("a", "SUPPORTS"); bad_observation["reason_uris"] = [reason_a, reason_a]
    negative("observation-duplicate-reason", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "NONCANONICAL_DOMAIN_SET")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["reason_uris"] = [reason_z, reason_a]
    negative("observation-unsorted-reason", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "NONCANONICAL_DOMAIN_SET")
    bad_observation = observation("a", "SUPPORTS"); bad_observation["reason_uris"] = ["relative"]
    negative("observation-invalid-reason", "evaluation", {
        "profile": base, "request": base_request, "observations": [bad_observation],
    }, "INVALID_DOMAIN_URI")
    negative("observation-conflict", "evaluation", {
        "profile": base,
        "request": base_request,
        "observations": [observation("a", "SUPPORTS"), observation("a", "OPPOSES")],
    }, "DOMAIN_OBSERVATION_CONFLICT")

    tampered = jsonable(ready); tampered["domain_status"] = "NEUTRAL"
    negative("reuse-tampered-result", "reuse", {
        "prior_result": tampered, "profile": base,
        "request": base_request, "observations": base_observations,
    }, "DOMAIN_RESULT_INTEGRITY_MISMATCH")
    tampered = jsonable(ready); tampered["protected_side_effect_authorized"] = True
    negative("reuse-tampered-boundary", "reuse", {
        "prior_result": tampered, "profile": base,
        "request": base_request, "observations": base_observations,
    }, "INVALID_PRIOR_DOMAIN_RESULT")
    tampered = jsonable(ready); tampered.pop("final_rule")
    negative("reuse-missing-result-field", "reuse", {
        "prior_result": tampered, "profile": base,
        "request": base_request, "observations": base_observations,
    }, "INVALID_PRIOR_DOMAIN_RESULT")
    tampered = jsonable(ready); tampered["version"] = True
    negative("reuse-invalid-result-version", "reuse", {
        "prior_result": tampered, "profile": base,
        "request": base_request, "observations": base_observations,
    }, "INVALID_PRIOR_DOMAIN_RESULT")
    negative("reuse-unhashable-domain-status", "synthetic-unhashable-prior-status", {
        "prior_result": jsonable(ready), "profile": base,
        "request": base_request, "observations": base_observations,
    }, "INVALID_PRIOR_DOMAIN_RESULT")
    negative("synthetic-criteria-limit", "synthetic-criteria-limit", {
        "count": MAX_CRITERIA + 1, "base_profile": base,
    }, "DOMAIN_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-observation-limit", "synthetic-observation-limit", {
        "count": MAX_OBSERVATIONS + 1, "profile": base, "request": base_request,
    }, "DOMAIN_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-context-limit", "synthetic-context-limit", {
        "count": MAX_CONTEXT_ENTRIES + 1, "profile": base, "request": base_request,
    }, "INVALID_DOMAIN_CONTEXT")
    negative("synthetic-understood-critical-limit", "synthetic-understood-critical-limit", {
        "count": MAX_SET_ITEMS + 1, "profile": base, "request": base_request,
    }, "DOMAIN_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-uri-limit", "synthetic-uri-limit", {
        "utf8_bytes": MAX_URI_BYTES + 1, "base_profile": base,
    }, "DOMAIN_RESOURCE_LIMIT_EXCEEDED")
    return {
        "format": "marketplace-domain-evaluator-methods-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "profile": PROFILE_CRITERION_THRESHOLD,
        "note": "method profiles, requests, criterion observations and results are processing metadata; this JSON file is not a Marketplace wire format",
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> int:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")
    print(f"positive/evaluation={len(data['cases'])} negative/adversarial={len(data['negative_cases'])} total={len(data['cases']) + len(data['negative_cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
