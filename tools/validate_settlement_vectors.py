"""Replay Marketplace settlement interfaces v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_settlement_v1 import (
    MAX_EVIDENCE_ITEMS,
    MarketplaceSettlementError,
    RelationshipEvidence,
    SettlementEvidence,
    evaluate_commitment_settlement,
    validate_settlement_event,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "settlement-interfaces-v1.json"
EXPECTED_FORMAT = "marketplace-settlement-interfaces-v1-conformance-vectors"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))


def actual_olp_commit() -> str:
    try:
        import olp

        repo = Path(olp.__file__).resolve().parents[2]
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def settlement_evidence(items) -> tuple[SettlementEvidence, ...]:
    return tuple(
        SettlementEvidence(
            record_from(item["record"]),
            item["attribution_accepted"],
            item["authority_accepted"],
            item["rail_evidence_accepted"],
        )
        for item in items
    )


def relationship_evidence(items) -> tuple[RelationshipEvidence, ...]:
    return tuple(
        RelationshipEvidence(record_from(item["record"]), item["accepted_for_method"])
        for item in items
    )


def select(result, expected):
    if not isinstance(expected, dict):
        return result
    return {key: result[key] for key in expected}


def run_case(item):
    kind = item["kind"]
    if kind == "settlement":
        result = evaluate_commitment_settlement(
            record_from(item["agreement"]),
            item["commitment_id"],
            settlement_evidence(item.get("events", ())),
            method=item["method"],
            understood_critical=tuple(item.get("understood_critical", ())),
            disputes=relationship_evidence(item.get("relationships", ())),
            max_evidence=item.get("max_evidence", MAX_EVIDENCE_ITEMS),
        )
        return select(result, item.get("expected", {}))
    if kind == "event_validation":
        result = validate_settlement_event(
            record_from(item["event"]),
            record_from(item["agreement"]),
            item["commitment_id"],
        )
        return select(result, item.get("expected", result))
    raise MarketplaceSettlementError("UNSUPPORTED_VECTOR_KIND", f"unsupported vector kind {kind!r}")


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("format") != EXPECTED_FORMAT:
        errors.append("unexpected settlement vector format discriminator")

    all_items = list(data.get("cases", ())) + list(data.get("negative_cases", ()))
    ids = [item.get("id") for item in all_items]
    if len(ids) != len(set(ids)):
        errors.append("settlement vector ids MUST be unique")

    active_commit = actual_olp_commit()
    expected_commit = data.get("olp_reference_source_commit")
    if active_commit != "unknown" and active_commit != expected_commit:
        errors.append(f"OLP source pin mismatch: vectors={expected_commit} active={active_commit}")
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
        except MarketplaceSettlementError as exc:
            if exc.code != item["expected_error"]:
                errors.append(
                    f"{item['id']}: expected error {item['expected_error']} got {exc.code}: {exc}"
                )
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: expected failure {item['expected_error']} but succeeded")
    if errors:
        print("Marketplace settlement interfaces vector validation FAIL")
        for error in errors:
            print("-", error)
        return 1
    print(f"Marketplace settlement interfaces vector validation PASS: {len(all_items)} vectors")
    print(f"OLP source commit: {active_commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
