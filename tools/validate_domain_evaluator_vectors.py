"""Replay Marketplace domain-evaluator method v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_domain_evaluator_v1 import (
    PROFILE_CRITERION_THRESHOLD,
    domain_method_profile_fingerprint,
    evaluate_domain_method,
    evaluate_domain_method_reuse,
    validate_domain_evaluation_request,
    validate_domain_method_profile,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "conformance" / "vectors" / "domain-evaluator-methods-v1.json"
EXPECTED_FORMAT = "marketplace-domain-evaluator-methods-v1-conformance-vectors"
EXPECTED_OLP_COMMIT = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"
EXPECTED_POSITIVE = 28
EXPECTED_NEGATIVE = 76


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


def error_code(exc: Exception) -> str:
    return getattr(exc, "code", type(exc).__name__)


def replay(case: dict):
    kind = case["kind"]
    if kind == "profile":
        value = case["profile"]
        return {
            "profile": validate_domain_method_profile(value),
            "fingerprint": domain_method_profile_fingerprint(value),
        }
    if kind == "request":
        return validate_domain_evaluation_request(case["request"], case["profile"])
    if kind == "evaluation":
        return evaluate_domain_method(
            case["profile"], case["request"], case.get("observations", ())
        )
    if kind == "reuse":
        return evaluate_domain_method_reuse(
            case["prior_result"], case["profile"],
            case["request"], case.get("observations", ()),
        )
    if kind == "synthetic-invalid-context-value":
        value = deepcopy(case["request"])
        value["context"] = {"https://example.test/domain-method/context/value": object()}
        return validate_domain_evaluation_request(value, case["profile"])
    if kind == "synthetic-unhashable-observation-state":
        observed = [{
            "criterion": "https://example.test/domain-method/criterion/a",
            "state": [], "critical": [], "reason_uris": [],
        }]
        return evaluate_domain_method(case["profile"], case["request"], observed)
    if kind == "synthetic-unhashable-prior-status":
        prior = deepcopy(case["prior_result"])
        prior["domain_status"] = []
        return evaluate_domain_method_reuse(
            prior, case["profile"], case["request"], case["observations"]
        )
    if kind == "synthetic-criteria-limit":
        value = deepcopy(case["base_profile"])
        template = deepcopy(value["criteria"][0])
        value["criteria"] = [
            {**template, "id": f"https://example.test/domain-method/criterion/{index:04d}"}
            for index in range(case["count"])
        ]
        return validate_domain_method_profile(value)
    if kind == "synthetic-observation-limit":
        observed = [{
            "criterion": case["profile"]["criteria"][0]["id"],
            "state": "SUPPORTS", "critical": [], "reason_uris": [],
        }] * case["count"]
        return evaluate_domain_method(case["profile"], case["request"], observed)
    if kind == "synthetic-context-limit":
        value = deepcopy(case["request"])
        value["context"] = {
            f"https://example.test/domain-method/context/{index:04d}": index
            for index in range(case["count"])
        }
        return validate_domain_evaluation_request(value, case["profile"])
    if kind == "synthetic-understood-critical-limit":
        value = deepcopy(case["request"])
        value["understood_critical"] = [
            f"https://example.test/domain-method/critical/{index:04d}"
            for index in range(case["count"])
        ]
        return validate_domain_evaluation_request(value, case["profile"])
    if kind == "synthetic-uri-limit":
        value = deepcopy(case["base_profile"])
        prefix = "https://example.test/"
        value["method"] = prefix + (
            "a" * (case["utf8_bytes"] - len(prefix.encode("utf-8")))
        )
        return validate_domain_method_profile(value)
    raise AssertionError(f"unknown M15 vector kind {kind!r}")


def main() -> None:
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT:
        raise SystemExit("unexpected M15 vector format")
    if data.get("profile") != PROFILE_CRITERION_THRESHOLD:
        raise SystemExit("unexpected M15 domain evaluator profile")
    if data.get("olp_reference_source_commit") != EXPECTED_OLP_COMMIT:
        raise SystemExit("M15 vector OLP pin mismatch")
    if olp_commit() != EXPECTED_OLP_COMMIT:
        raise SystemExit("active OLP source commit mismatch")

    cases = data.get("cases", ())
    negatives = data.get("negative_cases", ())
    if len(cases) != EXPECTED_POSITIVE or len(negatives) != EXPECTED_NEGATIVE:
        raise SystemExit(
            f"unexpected M15 vector composition: positive={len(cases)} negative={len(negatives)}"
        )
    ids = [item.get("id") for item in list(cases) + list(negatives)]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate M15 vector id")

    passed = 0
    for case in cases:
        actual = jsonable(replay(case))
        if actual != case["expected"]:
            raise AssertionError(
                f"{case['id']}: result mismatch\nexpected={case['expected']!r}\nactual={actual!r}"
            )
        passed += 1
    for case in negatives:
        try:
            replay(case)
        except Exception as exc:
            actual = error_code(exc)
            if actual != case["expected_error"]:
                raise AssertionError(
                    f"{case['id']}: expected {case['expected_error']}, got {actual}: {exc}"
                ) from exc
            passed += 1
        else:
            raise AssertionError(f"{case['id']}: expected error {case['expected_error']}")

    print(f"Marketplace domain-evaluator vector validation PASS: {passed} vectors")
    print(f"OLP source commit: {EXPECTED_OLP_COMMIT}")


if __name__ == "__main__":
    main()
