"""Validate committed Marketplace Record Representation v1 conformance vectors."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from olp import RecordV1, record_identity, record_identity_bytes, record_identity_text
from olp.transport import materialize_map, unproject_abstract

from marketplace_record_v1 import MarketplaceConformanceError, STRUCTURE_VALIDATORS, validate_market_record

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "record-representation-v1.json"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    errors = []

    for item in data["positive_records"]:
        try:
            mapping = decode(item["record"])
            record = RecordV1.from_mapping(mapping)
            validate_market_record(record)
            actual_text = record_identity_text(record)
            actual_hex = record_identity(record).hex()
            actual_preimage = record_identity_bytes(record).hex()
            if actual_text != item["expected_record_identity"]: errors.append(f"{item['id']}: text identity mismatch")
            if actual_hex != item["expected_record_identity_hex"]: errors.append(f"{item['id']}: hex identity mismatch")
            if actual_preimage != item["expected_identity_preimage_hex"]: errors.append(f"{item['id']}: identity preimage mismatch")
        except Exception as exc:
            errors.append(f"{item['id']}: unexpected positive failure: {exc}")

    for item in data["negative_records"]:
        try:
            mapping = decode(item["record"])
            record = RecordV1.from_mapping(mapping)
            validate_market_record(record)
        except MarketplaceConformanceError as exc:
            if exc.code != item["expected_error"]:
                errors.append(f"{item['id']}: expected {item['expected_error']} got {exc.code}: {exc}")
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception type: {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: negative vector unexpectedly accepted")

    for item in data["positive_structures"]:
        try:
            STRUCTURE_VALIDATORS[item["structure"]](decode(item["value"]), item["id"])
        except Exception as exc:
            errors.append(f"{item['id']}: unexpected structure failure: {exc}")

    for item in data["negative_structures"]:
        try:
            STRUCTURE_VALIDATORS[item["structure"]](decode(item["value"]), item["id"])
        except MarketplaceConformanceError as exc:
            if exc.code != item["expected_error"]:
                errors.append(f"{item['id']}: expected {item['expected_error']} got {exc.code}: {exc}")
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception type: {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: negative structure unexpectedly accepted")

    if errors:
        print("Marketplace vector validation FAILED")
        for error in errors: print("-", error)
        return 1
    total = sum(len(data[k]) for k in ("positive_records", "negative_records", "positive_structures", "negative_structures"))
    print(f"Marketplace vector validation PASS: {total} vectors")
    print("OLP source commit:", data["olp_reference_source_commit"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
