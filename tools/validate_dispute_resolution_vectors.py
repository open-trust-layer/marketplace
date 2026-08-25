"""Replay Marketplace dispute-resolution v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from olp import RecordV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_dispute_resolution_v1 import (
    METHOD_CORE,
    DisputeEvidence,
    ResolutionObservation,
    evaluate_dispute_resolution,
    evaluate_resolution_reuse,
    resolution_request_fingerprint,
    validate_resolution_request,
)

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / "conformance" / "vectors" / "dispute-resolution-v1.json"
EXPECTED_FORMAT = "marketplace-dispute-resolution-v1-conformance-vectors"
EXPECTED_OLP_COMMIT = "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c"
EXPECTED_POSITIVE = 39
EXPECTED_NEGATIVE = 43


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def dispute_from_wire(value: dict) -> DisputeEvidence:
    return DisputeEvidence(
        record=record_from(value["record"]),
        source=value["source"],
        authority=value["authority"],
        proof_status=value["proof_status"],
        attribution_status=value["attribution_status"],
        authority_status=value["authority_status"],
        lifecycle_status=value["lifecycle_status"],
    )


def resolution_from_wire(value: dict) -> ResolutionObservation:
    return ResolutionObservation(
        resolution_record_id=value["resolution_record_id"],
        dispute_record_ids=tuple(value["dispute_record_ids"]),
        target_record_ids=tuple(value["target_record_ids"]),
        outcome=value["outcome"],
        source=value["source"],
        authority=value["authority"],
        proof_status=value["proof_status"],
        attribution_status=value["attribution_status"],
        authority_status=value["authority_status"],
        lifecycle_status=value["lifecycle_status"],
        critical_uris=tuple(value["critical_uris"]),
        reason_uris=tuple(value["reason_uris"]),
    )


def disputes_from_wire(values) -> tuple[DisputeEvidence, ...]:
    return tuple(dispute_from_wire(item) for item in values)


def resolutions_from_wire(values):
    # Preserve raw mappings so malformed-vector cases reach the actual M13
    # validation boundary instead of failing in the replay harness.
    return tuple(values)


def error_code(exc: Exception) -> str:
    return getattr(exc, "code", type(exc).__name__)


def replay(case: dict):
    kind = case["kind"]
    if kind == "request":
        req = case["request"]
        return {
            "request": validate_resolution_request(req),
            "fingerprint": resolution_request_fingerprint(req),
        }
    if kind == "evaluation":
        return evaluate_dispute_resolution(
            case["request"],
            disputes_from_wire(case.get("disputes", ())),
            resolutions_from_wire(case.get("resolutions", ())),
        )
    if kind == "reuse":
        return evaluate_resolution_reuse(
            case["prior_result"],
            case["request"],
            disputes_from_wire(case.get("disputes", ())),
            resolutions_from_wire(case.get("resolutions", ())),
        )
    if kind == "synthetic-context-limit":
        req = deepcopy(case["base_request"])
        req["context"] = {
            f"https://example.test/context/{index}": index
            for index in range(case["count"])
        }
        return validate_resolution_request(req)
    if kind == "synthetic-uri-limit":
        req = deepcopy(case["base_request"])
        prefix = "https://example.test/"
        req["purpose"] = prefix + ("a" * (case["utf8_bytes"] - len(prefix.encode("utf-8"))))
        return validate_resolution_request(req)
    if kind == "synthetic-dispute-limit":
        dispute = dispute_from_wire(case["dispute"])
        return evaluate_dispute_resolution(
            case["base_request"],
            [dispute] * case["count"],
            (),
        )
    if kind == "synthetic-resolution-limit":
        dispute = dispute_from_wire(case["dispute"])
        resolution = case["resolution"]
        return evaluate_dispute_resolution(
            case["base_request"],
            (dispute,),
            [resolution] * case["count"],
        )
    raise AssertionError(f"unknown M13 vector kind {kind!r}")


def main() -> None:
    data = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT:
        raise SystemExit("unexpected M13 vector format")
    if data.get("method") != METHOD_CORE:
        raise SystemExit("unexpected M13 method")
    if data.get("olp_reference_source_commit") != EXPECTED_OLP_COMMIT:
        raise SystemExit("M13 vector OLP pin mismatch")
    if olp_commit() != EXPECTED_OLP_COMMIT:
        raise SystemExit("active OLP source commit mismatch")

    cases = data.get("cases", ())
    negatives = data.get("negative_cases", ())
    if len(cases) != EXPECTED_POSITIVE or len(negatives) != EXPECTED_NEGATIVE:
        raise SystemExit(
            f"unexpected M13 vector composition: positive={len(cases)} negative={len(negatives)}"
        )
    ids = [item.get("id") for item in list(cases) + list(negatives)]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate M13 vector id")

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

    print(f"Marketplace dispute-resolution vector validation PASS: {passed} vectors")
    print(f"OLP source commit: {EXPECTED_OLP_COMMIT}")


if __name__ == "__main__":
    main()
