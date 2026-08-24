"""Validate committed Marketplace matching and discovery v1 vectors."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_matching_v1 import (
    MarketplaceDiscoveryError,
    evaluate_discovery,
    evaluate_match,
    merge_federated_views,
    validate_cursor_binding,
    validate_ranked_view,
    verify_index_entry,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "matching-discovery-v1.json"
EXPECTED_FORMAT = "marketplace-matching-discovery-v1-conformance-vectors"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))


def actual_olp_commit() -> str:
    import olp

    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def select(result, expected):
    if not isinstance(expected, dict):
        return result
    return {key: result[key] for key in expected}


def run_case(item):
    kind = item["kind"]
    if kind == "discovery":
        result = evaluate_discovery(
            tuple(record_from(value) for value in item["records"]),
            decode(item["query"]),
            source=item["source"],
            completeness=item["completeness"],
            freshness=item["freshness"],
            max_records=item.get("max_records", 10_000),
        )
        return select(result, item.get("expected", {}))
    if kind == "index":
        result = verify_index_entry(decode(item["entry"]), record_from(item["record"]))
        return select(result, item.get("expected", result))
    if kind == "match":
        result = evaluate_match(
            record_from(item["left"]),
            record_from(item["right"]),
            method=item["method"],
            base_status=item["base_status"],
            observations=decode(item["observations"]),
            evidence_completeness=item["evidence_completeness"],
            understood_critical=tuple(item.get("understood_critical", ())),
        )
        return select(result, item.get("expected", {}))
    if kind == "ranking":
        result = validate_ranked_view(item["method"], tuple(decode(value) for value in item["record_refs"]))
        return select(result, item.get("expected", result))
    if kind == "federation":
        result = merge_federated_views(tuple(decode(value) for value in item["views"]))
        return select(result, item.get("expected", {}))
    if kind == "cursor":
        return validate_cursor_binding(
            decode(item["binding"]),
            source=item["source"],
            method=item["method"],
            query=decode(item["query"]),
        )
    raise MarketplaceDiscoveryError("UNSUPPORTED_VECTOR_KIND", f"unsupported vector kind {kind!r}")


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("format") != EXPECTED_FORMAT:
        errors.append(f"unexpected vector format: {data.get('format')!r}")
    all_cases = tuple(data.get("cases", ())) + tuple(data.get("negative_cases", ()))
    ids = [item.get("id") for item in all_cases]
    if len(ids) != len(set(ids)) or any(not isinstance(item, str) or not item for item in ids):
        errors.append("vector ids MUST be unique non-empty strings")

    active_commit = actual_olp_commit()
    if active_commit != "unknown" and active_commit != data.get("olp_reference_source_commit"):
        errors.append(
            f"OLP source pin mismatch: vectors={data.get('olp_reference_source_commit')} active={active_commit}"
        )

    for item in data.get("cases", ()):
        try:
            actual = run_case(item)
        except Exception as exc:
            errors.append(f"{item['id']}: unexpected failure: {type(exc).__name__}: {exc}")
            continue
        if actual != item["expected"]:
            errors.append(f"{item['id']}: expected {item['expected']!r} got {actual!r}")
    for item in data.get("negative_cases", ()):
        try:
            run_case(item)
        except MarketplaceDiscoveryError as exc:
            if exc.code != item["expected_error"]:
                errors.append(f"{item['id']}: expected {item['expected_error']} got {exc.code}: {exc}")
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception type: {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: negative case unexpectedly accepted")

    if errors:
        print("Marketplace matching/discovery vector validation FAILED")
        for error in errors:
            print("-", error)
        return 1
    total = len(data.get("cases", ())) + len(data.get("negative_cases", ()))
    print(f"Marketplace matching/discovery vector validation PASS: {total} vectors")
    print("OLP source commit:", data["olp_reference_source_commit"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
