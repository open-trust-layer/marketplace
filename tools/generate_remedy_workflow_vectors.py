"""Generate deterministic Marketplace remedy/workflow coordination vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_remedy_workflow_v1 import (
    MAX_CONTEXT_ENTRIES,
    MAX_OBSERVATIONS,
    MAX_RULES,
    MAX_URI_BYTES,
    PROFILE_REMEDY_WORKFLOW,
    evaluate_remedy_workflow,
    evaluate_remedy_workflow_reuse,
    remedy_workflow_profile_fingerprint,
    validate_remedy_workflow_profile,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "remedy-workflow-v1.json"
BASE = "https://example.test/remedy"
METHOD = f"{BASE}/method/software-remedy-v1"
DOMAIN = f"{BASE}/domain/software"
PURPOSE = f"{BASE}/purpose/post-dispute-coordination"
CRITICAL = f"{BASE}/critical/human-approval-v1"
RID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def jsonable(value):
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def step(name, *, protected=False, depends_on=(), conflict_group=None, critical=()):
    return {
        "id": f"{BASE}/step/{name}", "action": f"{BASE}/action/{name}",
        "depends_on": sorted(depends_on), "protected": protected,
        "conflict_group": conflict_group, "critical": sorted(critical),
    }


def rule(name, *, required=False, steps=None, critical=()):
    return {
        "id": f"{BASE}/rule/{name}", "trigger": f"{BASE}/trigger/{name}",
        "required": required, "steps": steps or [step(name)], "critical": sorted(critical),
    }


def profile(*, rules=None, critical=()):
    return {
        "version": 1, "profile": PROFILE_REMEDY_WORKFLOW, "method": METHOD,
        "domain": DOMAIN, "purposes": [PURPOSE],
        "rules": rules or [rule("refund", required=True, steps=[step("refund", protected=True)])],
        "critical": sorted(critical),
    }


def request(*, understood=(), context=None):
    return {
        "version": 1, "method": METHOD, "domain": DOMAIN, "purpose": PURPOSE,
        "target_record_ids": [RID], "context": {} if context is None else context,
        "understood_critical": sorted(understood),
    }


def observation(name="refund", state="PRESENT", *, critical=(), fingerprint="a" * 43):
    return {
        "trigger": f"{BASE}/trigger/{name}", "state": state, "target_record_id": RID,
        "source_result_fingerprint": fingerprint, "critical": sorted(critical),
    }


def build() -> dict:
    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id, kind, payload, expected):
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id, kind, payload, expected_error):
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": expected_error})

    base, base_request, observed = profile(), request(), [observation()]
    add("profile-valid", "profile", {"profile": base}, {
        "profile": validate_remedy_workflow_profile(base),
        "fingerprint": remedy_workflow_profile_fingerprint(base),
    })

    def evaluation(case_id, method, req, observations):
        result = evaluate_remedy_workflow(method, req, observations)
        add(case_id, "evaluation", {"profile": method, "request": req, "observations": observations}, result)
        return result

    prior = evaluation("evaluation-protected-refund-proposed", base, base_request, observed)
    evaluation("evaluation-required-missing", base, base_request, [])
    evaluation("evaluation-required-unknown", base, base_request, [observation(state="UNKNOWN")])
    evaluation("evaluation-required-unsupported", base, base_request, [observation(state="UNSUPPORTED")])
    evaluation("evaluation-required-absent", base, base_request, [observation(state="ABSENT")])
    optional = profile(rules=[rule("notify")])
    evaluation("evaluation-optional-missing", optional, base_request, [])
    evaluation("evaluation-informational-step", optional, base_request, [observation("notify")])
    duplicates = observed + [deepcopy(observed[0])]
    evaluation("evaluation-duplicate-delivery", base, base_request, duplicates)
    critical_profile = profile(critical=[CRITICAL])
    evaluation("evaluation-profile-critical-unknown", critical_profile, base_request, observed)
    evaluation("evaluation-profile-critical-understood", critical_profile, request(understood=[CRITICAL]), observed)
    evaluation("evaluation-rule-critical-unknown", profile(rules=[rule("refund", required=True, critical=[CRITICAL])]), base_request, observed)
    evaluation("evaluation-step-critical-unknown", profile(rules=[rule("refund", required=True, steps=[step("refund", critical=[CRITICAL])])]), base_request, observed)
    evaluation("evaluation-observation-critical-unknown", base, base_request, [observation(critical=[CRITICAL])])
    evaluation("evaluation-context-bound", base, request(context={f"{BASE}/context/jurisdiction": "NL"}), observed)
    notify, refund = step("notify"), step("refund", protected=True, depends_on=[f"{BASE}/step/notify"])
    graph = profile(rules=[rule("refund", required=True, steps=[notify, refund])])
    evaluation("evaluation-topological-dependencies", graph, base_request, observed)
    group = f"{BASE}/conflict/remedy-choice"
    conflict = profile(rules=[
        rule("refund", steps=[step("refund", protected=True, conflict_group=group)]),
        rule("replace", steps=[step("replace", protected=True, conflict_group=group)]),
    ])
    evaluation("evaluation-conflicting-actions", conflict, base_request, [observation("refund"), observation("replace")])
    dependent = profile(rules=[
        rule("notify", steps=[step("notify")]),
        rule("refund", required=True, steps=[step("refund", protected=True, depends_on=[f"{BASE}/step/notify"])]),
    ])
    evaluation("evaluation-selected-dependency-unavailable", dependent, base_request, observed)

    def reuse(case_id, prior_result, method, req, observations):
        add(case_id, "reuse", {
            "prior_result": prior_result, "profile": method, "request": req, "observations": observations,
        }, evaluate_remedy_workflow_reuse(prior_result, method, req, observations))

    reuse("reuse-exact", prior, base, base_request, observed)
    reuse("reuse-duplicate-delivery", prior, base, base_request, duplicates)
    reuse("reuse-profile-changed", prior, profile(rules=[rule("refund", required=True)]), base_request, observed)
    reuse("reuse-request-changed", prior, base, request(context={f"{BASE}/context/change": True}), observed)
    reuse("reuse-source-result-changed", prior, base, base_request, [observation(fingerprint="b" * 43)])

    negative("profile-not-map", "profile", {"profile": []}, "INVALID_WORKFLOW_PROFILE")
    for field in ("critical", "rules", "method"):
        bad = deepcopy(base); bad.pop(field)
        negative(f"profile-missing-{field}", "profile", {"profile": bad}, "INVALID_WORKFLOW_PROFILE")
    for suffix, version in (("bool", True), ("two", 2)):
        bad = deepcopy(base); bad["version"] = version
        negative(f"profile-version-{suffix}", "profile", {"profile": bad}, "INVALID_WORKFLOW_PROFILE")
    bad = deepcopy(base); bad["profile"] = f"{BASE}/profile/unknown"
    negative("profile-unsupported", "profile", {"profile": bad}, "UNSUPPORTED_WORKFLOW_PROFILE")
    for field in ("method", "domain"):
        bad = deepcopy(base); bad[field] = "relative"
        negative(f"profile-relative-{field}", "profile", {"profile": bad}, "INVALID_WORKFLOW_URI")
    bad = deepcopy(base); bad["purposes"] = []
    negative("profile-empty-purpose", "profile", {"profile": bad}, "EMPTY_WORKFLOW_SET")
    bad = deepcopy(base); bad["purposes"] = [PURPOSE, PURPOSE]
    negative("profile-duplicate-purpose", "profile", {"profile": bad}, "NONCANONICAL_WORKFLOW_SET")
    bad = deepcopy(base); bad["rules"] = []
    negative("profile-empty-rules", "profile", {"profile": bad}, "EMPTY_WORKFLOW_SET")
    bad = deepcopy(base); bad["rules"] = 7
    negative("profile-rules-not-collection", "profile", {"profile": bad}, "INVALID_WORKFLOW_COLLECTION")
    bad = deepcopy(base); bad["rules"][0]["required"] = "yes"
    negative("rule-required-not-boolean", "profile", {"profile": bad}, "INVALID_WORKFLOW_RULE")
    bad = deepcopy(base); bad["rules"][0]["steps"] = []
    negative("rule-empty-steps", "profile", {"profile": bad}, "EMPTY_WORKFLOW_SET")
    bad = deepcopy(base); bad["rules"][0]["steps"][0]["protected"] = 1
    negative("step-protected-not-boolean", "profile", {"profile": bad}, "INVALID_WORKFLOW_STEP")
    bad = deepcopy(base); bad["rules"][0]["steps"][0]["action"] = "relative"
    negative("step-action-relative", "profile", {"profile": bad}, "INVALID_WORKFLOW_URI")
    bad = profile(rules=[rule("refund", steps=[step("refund", depends_on=[f"{BASE}/step/missing"])])])
    negative("dependency-dangling", "profile", {"profile": bad}, "WORKFLOW_DANGLING_DEPENDENCY")
    bad = profile(rules=[rule("refund", steps=[step("a", depends_on=[f"{BASE}/step/b"]), step("b", depends_on=[f"{BASE}/step/a"])])])
    negative("dependency-cycle", "profile", {"profile": bad}, "WORKFLOW_DEPENDENCY_CYCLE")
    bad = profile(rules=[rule("refund", steps=[step("same")]), rule("replace", steps=[step("same")])])
    negative("step-global-duplicate", "profile", {"profile": bad}, "DUPLICATE_WORKFLOW_STEP")

    negative("request-not-map", "request", {"profile": base, "request": []}, "INVALID_WORKFLOW_REQUEST")
    for field in ("context", "target_record_ids"):
        bad = deepcopy(base_request); bad.pop(field)
        negative(f"request-missing-{field}", "request", {"profile": base, "request": bad}, "INVALID_WORKFLOW_REQUEST")
    bad = deepcopy(base_request); bad["version"] = True
    negative("request-version-bool", "request", {"profile": base, "request": bad}, "INVALID_WORKFLOW_REQUEST")
    for field, code in (("method", "WORKFLOW_METHOD_BINDING_MISMATCH"), ("domain", "WORKFLOW_DOMAIN_BINDING_MISMATCH"), ("purpose", "WORKFLOW_PURPOSE_NOT_SUPPORTED")):
        bad = deepcopy(base_request); bad[field] = f"{BASE}/{field}/different"
        negative(f"request-{field}-mismatch", "request", {"profile": base, "request": bad}, code)
    bad = deepcopy(base_request); bad["target_record_ids"] = []
    negative("request-target-empty", "request", {"profile": base, "request": bad}, "EMPTY_WORKFLOW_SET")
    bad = deepcopy(base_request); bad["target_record_ids"] = ["r1_invalid"]
    negative("request-target-invalid", "request", {"profile": base, "request": bad}, "INVALID_WORKFLOW_RECORD_ID")
    bad = deepcopy(base_request); bad["target_record_ids"] = [RID, RID]
    negative("request-target-duplicate", "request", {"profile": base, "request": bad}, "NONCANONICAL_WORKFLOW_SET")
    bad = deepcopy(base_request); bad["context"] = []
    negative("request-context-not-map", "request", {"profile": base, "request": bad}, "INVALID_WORKFLOW_CONTEXT")
    bad = deepcopy(base_request); bad["context"] = {"relative": "x"}
    negative("request-context-relative-key", "request", {"profile": base, "request": bad}, "INVALID_WORKFLOW_URI")

    negative("observations-not-collection", "evaluation", {"profile": base, "request": base_request, "observations": 7}, "INVALID_WORKFLOW_COLLECTION")
    negative("observation-not-map", "evaluation", {"profile": base, "request": base_request, "observations": [[]]}, "INVALID_WORKFLOW_OBSERVATION")
    for field in ("state", "critical", "source_result_fingerprint"):
        bad = observation(); bad.pop(field)
        negative(f"observation-missing-{field}", "evaluation", {"profile": base, "request": base_request, "observations": [bad]}, "INVALID_WORKFLOW_OBSERVATION")
    bad = observation(); bad["state"] = "MAYBE"
    negative("observation-state-invalid", "evaluation", {"profile": base, "request": base_request, "observations": [bad]}, "INVALID_WORKFLOW_OBSERVATION_STATE")
    bad = observation(); bad["source_result_fingerprint"] = "short"
    negative("observation-source-fingerprint-invalid", "evaluation", {"profile": base, "request": base_request, "observations": [bad]}, "INVALID_WORKFLOW_SOURCE_FINGERPRINT")
    bad = observation("missing")
    negative("observation-trigger-unknown", "evaluation", {"profile": base, "request": base_request, "observations": [bad]}, "UNKNOWN_WORKFLOW_TRIGGER")
    negative("observation-conflicting-delivery", "evaluation", {"profile": base, "request": base_request, "observations": [observation(), observation(state="ABSENT")]}, "WORKFLOW_OBSERVATION_CONFLICT")
    negative("synthetic-observation-limit", "synthetic-observation-limit", {"profile": base, "request": base_request, "count": MAX_OBSERVATIONS + 1}, "WORKFLOW_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-rule-limit", "synthetic-rule-limit", {"profile": base, "count": MAX_RULES + 1}, "WORKFLOW_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-context-limit", "synthetic-context-limit", {"profile": base, "request": base_request, "count": MAX_CONTEXT_ENTRIES + 1}, "INVALID_WORKFLOW_CONTEXT")
    negative("synthetic-uri-limit", "synthetic-uri-limit", {"profile": base, "utf8_bytes": MAX_URI_BYTES + 1}, "WORKFLOW_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-unhashable-state", "synthetic-unhashable-state", {"profile": base, "request": base_request}, "INVALID_WORKFLOW_OBSERVATION_STATE")
    negative("synthetic-tampered-result", "synthetic-tampered-result", {"prior_result": prior, "profile": base, "request": base_request, "observations": observed}, "WORKFLOW_RESULT_INTEGRITY_MISMATCH")
    negative("synthetic-authorized-result", "synthetic-authorized-result", {"prior_result": prior, "profile": base, "request": base_request, "observations": observed}, "INVALID_PRIOR_WORKFLOW_RESULT")

    return {
        "format": "marketplace-remedy-workflow-v1-conformance-vectors",
        "profile": PROFILE_REMEDY_WORKFLOW,
        "olp_reference_source_commit": olp_commit(),
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> None:
    data = build()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated Marketplace remedy/workflow vectors: {len(data['cases']) + len(data['negative_cases'])}")


if __name__ == "__main__":
    main()
