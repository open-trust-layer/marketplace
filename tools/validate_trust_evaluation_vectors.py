from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_trust_evaluation_v1 import (
    EvidenceCandidate, MarketplaceTrustEvaluationError,
    evaluate_trust, query_fingerprint, select_evidence,
    validate_evidence_query,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "trust-evaluation-v1.json"
EXPECTED_FORMAT = "marketplace-trust-evaluation-v1-conformance-vectors"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))

def candidate_from(value) -> EvidenceCandidate:
    return EvidenceCandidate(record=record_from(value["record"]), source=value["source"])


def candidates_from(values):
    return tuple(candidate_from(item) for item in values)


def actual_olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def run_case(item):
    kind = item["kind"]
    if kind == "query":
        query = item["query"]
        return {"query": validate_evidence_query(query), "fingerprint": query_fingerprint(query)}
    if kind == "selection":
        return select_evidence(candidates_from(item["candidates"]), item["query"])
    if kind == "evaluation":
        return evaluate_trust(candidates_from(item["candidates"]), tuple(item["observations"]), item["query"])
    raise MarketplaceTrustEvaluationError("UNSUPPORTED_VECTOR_KIND", f"unsupported vector kind {kind!r}")

def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT:
        print("wrong vector format", file=sys.stderr)
        return 1
    actual_pin = actual_olp_commit()
    if data.get("olp_reference_source_commit") != actual_pin:
        print("OLP source pin mismatch", file=sys.stderr)
        return 1
    ids = [item["id"] for item in data.get("cases", []) + data.get("negative_cases", [])]
    if len(ids) != len(set(ids)):
        print("duplicate vector ids", file=sys.stderr)
        return 1
    failures = []
    for item in data.get("cases", []):
        try:
            actual = jsonable(run_case(item))
        except Exception as exc:
            failures.append(f"{item['id']}: unexpected {type(exc).__name__}: {exc}")
            continue
        if actual != item["expected"]:
            failures.append(f"{item['id']}: expected {item['expected']!r}, got {actual!r}")
    for item in data.get("negative_cases", []):
        try:
            run_case(item)
        except MarketplaceTrustEvaluationError as exc:
            if exc.code != item["expected_error"]:
                failures.append(f"{item['id']}: expected {item['expected_error']}, got {exc.code}")
        except Exception as exc:
            failures.append(f"{item['id']}: unexpected {type(exc).__name__}: {exc}")
        else:
            failures.append(f"{item['id']}: expected error {item['expected_error']} but succeeded")
    if failures:
        print("Marketplace trust evaluation vector validation FAIL", file=sys.stderr)
        for failure in failures:
            print("-", failure, file=sys.stderr)
        return 1
    total = len(data.get("cases", [])) + len(data.get("negative_cases", []))
    print(f"Marketplace trust evaluation vector validation PASS: {total} vectors")
    print(f"OLP source commit: {actual_pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
