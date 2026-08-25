from __future__ import annotations

import json
import subprocess
from pathlib import Path

from marketplace_policy_v1 import (
    METHOD_CORE,
    OP_LOCAL_INSPECTION,
    PolicyObservation,
    evaluate_decision_reuse,
    evaluate_policy,
    policy_request_fingerprint,
    validate_policy_request,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "conformance" / "vectors" / "safety-policy-authorization-v1.json"
EXPECTED_OLP_COMMIT = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"
RECORD_ID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"


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


def observation_from_wire(value: dict) -> PolicyObservation:
    return PolicyObservation(
        dimension=value["dimension"],
        status=value["status"],
        source=value["source"],
        reason=value["reason"],
        evidence_ids=tuple(value.get("evidence_ids", ())),
        valid_from=value.get("valid_from"),
        valid_until=value.get("valid_until"),
        subject_fingerprint=value.get("subject_fingerprint"),
    )


def observations_from_wire(values) -> tuple[PolicyObservation, ...]:
    return tuple(observation_from_wire(item) for item in values)


def error_code(exc: Exception) -> str:
    return getattr(exc, "code", type(exc).__name__)


def base_local_request() -> dict:
    return {
        "version": 1,
        "method": METHOD_CORE,
        "decision_scope": "https://example.test/policy/local-v1",
        "operation": OP_LOCAL_INSPECTION,
        "actor": "https://example.test/principal/alice",
        "target": {"kind": "resource-uri", "value": "https://example.test/resource/1"},
        "context": {},
        "evaluation_time": "2026-08-24T19:00:00Z",
        "required_dimensions": [],
    }

def replay(case: dict):
    kind = case["kind"]
    if kind == "request":
        req = case["request"]
        return {
            "request": validate_policy_request(req),
            "fingerprint": policy_request_fingerprint(req),
        }
    if kind == "evaluation":
        return evaluate_policy(
            case["request"],
            observations_from_wire(case["observations"]),
        )
    if kind == "reuse":
        return evaluate_decision_reuse(
            case["prior_result"],
            case["request"],
            observations_from_wire(case["observations"]),
        )
    if kind == "synthetic-observation-limit":
        item = PolicyObservation(
            "safety", "SATISFIED", "https://policy.example/source", "https://policy.example/reason"
        )
        return evaluate_policy(base_local_request(), [item] * case["count"])
    if kind == "synthetic-evidence-limit":
        item = PolicyObservation(
            "safety", "SATISFIED", "https://policy.example/source", "https://policy.example/reason",
            evidence_ids=(RECORD_ID,) * case["count"],
        )
        return evaluate_policy(base_local_request(), [item])
    if kind == "synthetic-context-limit":
        req = base_local_request()
        req["context"] = {
            f"https://example.test/context/{index}": index
            for index in range(case["count"])
        }
        return validate_policy_request(req)
    if kind == "synthetic-uri-limit":
        req = base_local_request()
        prefix = "https://example.test/"
        req["actor"] = prefix + ("a" * (case["utf8_bytes"] - len(prefix.encode("utf-8"))))
        return validate_policy_request(req)
    raise AssertionError(f"unknown vector kind {kind!r}")

def main() -> None:
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    if data.get("format") != "marketplace-safety-policy-authorization-v1":
        raise SystemExit("unexpected M11 vector format")
    if data.get("method") != METHOD_CORE:
        raise SystemExit("unexpected M11 policy method")
    if data.get("olp_reference_source_commit") != EXPECTED_OLP_COMMIT:
        raise SystemExit("M11 vector OLP pin mismatch")
    if olp_commit() != EXPECTED_OLP_COMMIT:
        raise SystemExit("active OLP source commit mismatch")

    all_cases = data["cases"] + data["negative_cases"]
    ids = [case["id"] for case in all_cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate M11 vector id")
    if len(data["cases"]) != 35 or len(data["negative_cases"]) != 42:
        raise SystemExit("unexpected initial M11 vector composition")

    passed = 0
    for case in data["cases"]:
        actual = jsonable(replay(case))
        if actual != case["expected"]:
            raise AssertionError(
                f"{case['id']}: result mismatch\nexpected={case['expected']!r}\nactual={actual!r}"
            )
        passed += 1

    for case in data["negative_cases"]:
        try:
            replay(case)
        except Exception as exc:
            actual_code = error_code(exc)
            if actual_code != case["expected_error"]:
                raise AssertionError(
                    f"{case['id']}: expected {case['expected_error']}, got {actual_code}: {exc}"
                ) from exc
            passed += 1
        else:
            raise AssertionError(f"{case['id']}: expected error {case['expected_error']}")

    print(f"Marketplace safety/policy vector validation PASS: {passed} vectors")
    print(f"OLP source commit: {EXPECTED_OLP_COMMIT}")


if __name__ == "__main__":
    main()
