"""Replay Marketplace deployment-profile v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_deployment_v1 import (
    PROFILE_CORE,
    deployment_config_fingerprint,
    evaluate_deployment_readiness,
    evaluate_deployment_reuse,
    validate_deployment_profile,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "conformance" / "vectors" / "deployment-profiles-v1.json"
EXPECTED_FORMAT = "marketplace-deployment-profiles-v1-conformance-vectors"
EXPECTED_OLP_COMMIT = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"
EXPECTED_POSITIVE = 31
EXPECTED_NEGATIVE = 56


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
            "profile": validate_deployment_profile(value),
            "fingerprint": deployment_config_fingerprint(value),
        }
    if kind == "evaluation":
        return evaluate_deployment_readiness(
            case["profile"],
            case.get("observations", ()),
            case.get("understood_critical", ()),
        )
    if kind == "reuse":
        return evaluate_deployment_reuse(
            case["prior_result"],
            case["profile"],
            case.get("observations", ()),
            case.get("understood_critical", ()),
        )
    if kind == "synthetic-component-limit":
        value = deepcopy(case["base_profile"])
        template = deepcopy(value["components"][0])
        value["components"] = [
            {**template, "id": f"https://example.test/deployment/component/{index:04d}"}
            for index in range(case["count"])
        ]
        return validate_deployment_profile(value)
    if kind == "synthetic-service-limit":
        value = deepcopy(case["base_profile"])
        template = deepcopy(value["services"][0])
        value["services"] = [
            {**template, "id": f"https://example.test/deployment/service/{index:04d}"}
            for index in range(case["count"])
        ]
        return validate_deployment_profile(value)
    if kind == "synthetic-observation-limit":
        value = case["base_profile"]
        template = {
            "component_id": value["components"][0]["id"],
            "adapter": value["components"][0]["adapter"],
            "status": "READY", "critical": [],
        }
        return evaluate_deployment_readiness(value, [template] * case["count"])
    if kind == "synthetic-context-limit":
        value = deepcopy(case["base_profile"])
        value["context"] = {
            f"https://example.test/deployment/context/{index}": index
            for index in range(case["count"])
        }
        return validate_deployment_profile(value)
    if kind == "synthetic-uri-limit":
        value = deepcopy(case["base_profile"])
        prefix = "https://example.test/"
        value["operator"] = prefix + (
            "a" * (case["utf8_bytes"] - len(prefix.encode("utf-8")))
        )
        return validate_deployment_profile(value)
    if kind == "synthetic-endpoint-limit":
        value = deepcopy(case["base_profile"])
        value["services"][0]["endpoints"] = [
            f"https://node.example/endpoint/{index:04d}"
            for index in range(case["count"])
        ]
        return validate_deployment_profile(value)
    raise AssertionError(f"unknown M14 vector kind {kind!r}")


def main() -> None:
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT:
        raise SystemExit("unexpected M14 vector format")
    if data.get("profile") != PROFILE_CORE:
        raise SystemExit("unexpected M14 deployment profile")
    if data.get("olp_reference_source_commit") != EXPECTED_OLP_COMMIT:
        raise SystemExit("M14 vector OLP pin mismatch")
    if olp_commit() != EXPECTED_OLP_COMMIT:
        raise SystemExit("active OLP source commit mismatch")

    cases = data.get("cases", ())
    negatives = data.get("negative_cases", ())
    if len(cases) != EXPECTED_POSITIVE or len(negatives) != EXPECTED_NEGATIVE:
        raise SystemExit(
            f"unexpected M14 vector composition: positive={len(cases)} negative={len(negatives)}"
        )
    ids = [item.get("id") for item in list(cases) + list(negatives)]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate M14 vector id")
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

    print(f"Marketplace deployment-profile vector validation PASS: {passed} vectors")
    print(f"OLP source commit: {EXPECTED_OLP_COMMIT}")


if __name__ == "__main__":
    main()
