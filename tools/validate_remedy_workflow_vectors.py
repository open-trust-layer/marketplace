"""Independently replay Marketplace remedy/workflow coordination vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_remedy_workflow_v1 import (
    PROFILE_REMEDY_WORKFLOW,
    evaluate_remedy_workflow,
    evaluate_remedy_workflow_reuse,
    remedy_workflow_profile_fingerprint,
    validate_remedy_workflow_profile,
    validate_remedy_workflow_request,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "conformance" / "vectors" / "remedy-workflow-v1.json"
EXPECTED_FORMAT = "marketplace-remedy-workflow-v1-conformance-vectors"
EXPECTED_OLP_COMMIT = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"
EXPECTED_POSITIVE = 23
EXPECTED_NEGATIVE = 48


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


def replay(case):
    kind = case["kind"]
    if kind == "profile":
        return {"profile": validate_remedy_workflow_profile(case["profile"]), "fingerprint": remedy_workflow_profile_fingerprint(case["profile"])}
    if kind == "request":
        return validate_remedy_workflow_request(case["request"], case["profile"])
    if kind == "evaluation":
        return evaluate_remedy_workflow(case["profile"], case["request"], case.get("observations", ()))
    if kind == "reuse":
        return evaluate_remedy_workflow_reuse(case["prior_result"], case["profile"], case["request"], case["observations"])
    if kind == "synthetic-observation-limit":
        target = case["request"]["target_record_ids"][0]
        trigger = case["profile"]["rules"][0]["trigger"]
        observed = {"trigger": trigger, "state": "PRESENT", "target_record_id": target, "source_result_fingerprint": "a" * 43, "critical": []}
        return evaluate_remedy_workflow(case["profile"], case["request"], [observed] * case["count"])
    if kind == "synthetic-rule-limit":
        value = deepcopy(case["profile"])
        value["rules"] = [deepcopy(value["rules"][0]) for _ in range(case["count"])]
        return validate_remedy_workflow_profile(value)
    if kind == "synthetic-context-limit":
        value = deepcopy(case["request"])
        value["context"] = {f"https://example.test/remedy/context/{index:04d}": index for index in range(case["count"])}
        return validate_remedy_workflow_request(value, case["profile"])
    if kind == "synthetic-uri-limit":
        value = deepcopy(case["profile"])
        prefix = "https://example.test/"
        value["method"] = prefix + "a" * (case["utf8_bytes"] - len(prefix))
        return validate_remedy_workflow_profile(value)
    if kind == "synthetic-unhashable-state":
        target = case["request"]["target_record_ids"][0]
        trigger = case["profile"]["rules"][0]["trigger"]
        return evaluate_remedy_workflow(case["profile"], case["request"], [{"trigger": trigger, "state": [], "target_record_id": target, "source_result_fingerprint": "a" * 43, "critical": []}])
    if kind in {"synthetic-tampered-result", "synthetic-authorized-result"}:
        prior = deepcopy(case["prior_result"])
        if kind == "synthetic-tampered-result":
            prior["workflow_status"] = "PARTIAL"
        else:
            prior["protected_side_effect_authorized"] = True
        return evaluate_remedy_workflow_reuse(prior, case["profile"], case["request"], case["observations"])
    raise AssertionError(f"unknown M16 vector kind {kind!r}")


def main():
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT or data.get("profile") != PROFILE_REMEDY_WORKFLOW:
        raise SystemExit("unexpected M16 vector format or processing profile")
    if data.get("olp_reference_source_commit") != EXPECTED_OLP_COMMIT or olp_commit() != EXPECTED_OLP_COMMIT:
        raise SystemExit("M16 OLP source pin mismatch")
    cases, negatives = data.get("cases", ()), data.get("negative_cases", ())
    if len(cases) != EXPECTED_POSITIVE or len(negatives) != EXPECTED_NEGATIVE:
        raise SystemExit(
            f"unexpected M16 vector composition: positive={len(cases)} negative={len(negatives)}"
        )
    ids = [item.get("id") for item in list(cases) + list(negatives)]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate M16 vector identifier")
    passed = 0
    for case in cases:
        actual = jsonable(replay(case))
        if actual != case["expected"]:
            raise AssertionError(f"{case['id']}: expected {case['expected']!r}, got {actual!r}")
        passed += 1
    for case in negatives:
        try:
            replay(case)
        except Exception as exc:
            actual = getattr(exc, "code", type(exc).__name__)
            if actual != case["expected_error"]:
                raise AssertionError(f"{case['id']}: expected {case['expected_error']}, got {actual}: {exc}") from exc
            passed += 1
        else:
            raise AssertionError(f"{case['id']}: expected error {case['expected_error']}")
    print(f"Marketplace remedy/workflow vector validation PASS: {passed} vectors")
    print(f"OLP source commit: {EXPECTED_OLP_COMMIT}")


if __name__ == "__main__":
    main()
