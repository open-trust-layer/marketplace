from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.errors import ConformanceError, UnsupportedFeatureError
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_privacy_v1 import (
    MAX_CAPABILITIES,
    MAX_DEPENDENCIES_PER_ITEM,
    MAX_PRIVACY_WARNINGS_PER_ITEM,
    MAX_INVENTORY_ITEMS,
    MAX_RESOURCE_ITEMS,
    MAX_ROOTS,
    MarketplacePrivacyError,
    plan_marketplace_disclosure,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "privacy-selective-disclosure-v1.json"
EXPECTED_FORMAT = "marketplace-privacy-selective-disclosure-v1-conformance-vectors"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))
def actual_olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def materialize_payload(value):
    payload = decode(value)
    for item in payload.get("inventory", []):
        record = item.get("record") if isinstance(item, dict) else None
        if isinstance(record, dict):
            item["record"] = RecordV1.from_mapping(record)
    return payload


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value
def synthetic_limit_payload(item):
    payload = materialize_payload(item["base_payload"])
    target = item["target"]
    if target == "roots":
        refs = [EvidenceRefV1(EvidenceKind.RECORD, i.to_bytes(32, "big")) for i in range(MAX_ROOTS + 1)]
        request = list(payload["request"])
        request[3] = [ref.to_value() for ref in refs]
        payload["request"] = request
    elif target == "inventory":
        payload["inventory"] = [payload["inventory"][0]] * (MAX_INVENTORY_ITEMS + 1)
    elif target == "resources":
        payload["resources"] = [{}] * (MAX_RESOURCE_ITEMS + 1)
    elif target == "required_capabilities":
        request = list(payload["request"])
        request[4] = [f"https://example.test/capability/{i:04d}" for i in range(MAX_CAPABILITIES + 1)]
        payload["request"] = request
    elif target == "available_capabilities":
        payload["available_capabilities"] = [f"https://example.test/capability/{i:04d}" for i in range(MAX_CAPABILITIES + 1)]
    elif target == "dependencies":
        dep = ["evidence", payload["request"][3][0], "protocol"]
        payload["inventory"][0]["dependencies"] = [dep] * (MAX_DEPENDENCIES_PER_ITEM + 1)
    elif target == "item_privacy_warnings":
        payload["inventory"][0]["privacy_warnings"] = ["GLOBAL_COMPLETENESS_NOT_ESTABLISHED"] * (MAX_PRIVACY_WARNINGS_PER_ITEM + 1)
    elif target == "resource_privacy_warnings":
        payload["resources"] = [{"privacy_warnings": ["GLOBAL_COMPLETENESS_NOT_ESTABLISHED"] * (MAX_PRIVACY_WARNINGS_PER_ITEM + 1)}]
    else:
        raise AssertionError(f"unknown synthetic target {target!r}")
    return payload


def run_case(item):
    if item["kind"] == "plan":
        return plan_marketplace_disclosure(materialize_payload(item["payload"]))
    if item["kind"] == "synthetic-limit":
        return plan_marketplace_disclosure(synthetic_limit_payload(item))
    raise AssertionError(f"unsupported vector kind {item['kind']!r}")
def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    if data.get("format") != EXPECTED_FORMAT:
        print("wrong vector format", file=sys.stderr)
        return 1
    pin = actual_olp_commit()
    if data.get("olp_reference_source_commit") != pin:
        print("OLP source pin mismatch", file=sys.stderr)
        return 1
    ids = [item["id"] for item in data.get("cases", []) + data.get("negative_cases", [])]
    if len(ids) != len(set(ids)):
        print("duplicate vector ids", file=sys.stderr)
        return 1
    failures: list[str] = []
    for item in data.get("cases", []):
        try:
            actual = jsonable(run_case(item))
        except Exception as exc:
            failures.append(f"{item['id']}: unexpected {type(exc).__name__}: {exc}")
            continue
        if actual != item["expected"]:
            failures.append(f"{item['id']}: expected {item['expected']!r}, got {actual!r}")
    expected_errors = (MarketplacePrivacyError, ConformanceError, UnsupportedFeatureError)
    for item in data.get("negative_cases", []):
        try:
            run_case(item)
        except expected_errors as exc:
            if exc.code != item["expected_error"]:
                failures.append(f"{item['id']}: expected {item['expected_error']}, got {exc.code}")
        except Exception as exc:
            failures.append(f"{item['id']}: unexpected {type(exc).__name__}: {exc}")
        else:
            failures.append(f"{item['id']}: expected error {item['expected_error']} but succeeded")
    if failures:
        print("Marketplace privacy vector validation FAIL", file=sys.stderr)
        for failure in failures:
            print("-", failure, file=sys.stderr)
        return 1
    total = len(data.get("cases", [])) + len(data.get("negative_cases", []))
    print(f"Marketplace privacy vector validation PASS: {total} vectors")
    print(f"OLP source commit: {pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
