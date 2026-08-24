from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from olp import RecordV1
from olp.transport import materialize_map, unproject_abstract

from marketplace_federation_v1 import (
    MarketplaceFederationError,
    bind_cursor, bind_idempotency, evaluate_exchange_page,
    make_transport_envelope, merge_received_records, negotiate_capabilities,
    scope_fingerprint, validate_capability_advertisement, validate_cursor_binding,
    validate_exchange_request, validate_idempotency_replay, validate_scope,
    validate_submission_outcomes, validate_transport_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "conformance" / "vectors" / "federation-transport-v1.json"
EXPECTED_FORMAT = "marketplace-federation-transport-v1-conformance-vectors"


def decode(value):
    return materialize_map(unproject_abstract(value), allowed_key_types=(str, int))


def record_from(value) -> RecordV1:
    return RecordV1.from_mapping(decode(value))


def records_from(values):
    return tuple(record_from(item) for item in values)


def actual_olp_commit() -> str:
    try:
        import olp
        repo = Path(olp.__file__).resolve().parents[2]
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


def page_cursor(item):
    value = item.get("next_cursor")
    return None if value is None else value.encode("utf-8")


def run_case(item):
    kind = item["kind"]
    if kind == "capability_advertisement":
        return validate_capability_advertisement(item["advertisement"])
    if kind == "capability_negotiation":
        return negotiate_capabilities(item["advertisement"], tuple(item["required"]))
    if kind == "scope":
        return {"scope": validate_scope(item["scope"]), "fingerprint": scope_fingerprint(item["scope"])}
    if kind == "request":
        request = dict(item["request"])
        if isinstance(request.get("cursor"), str):
            request["cursor"] = request["cursor"].encode("utf-8")
        return validate_exchange_request(request)
    if kind == "page":
        return evaluate_exchange_page(
            records_from(item["records"]),
            source=item["source"],
            operation=item["operation"],
            scope=item["scope"],
            completeness=item["completeness"],
            has_more=item["has_more"],
            next_cursor=page_cursor(item),
            max_records=item.get("max_records", 10_000),
        )
    if kind == "merge":
        return merge_received_records(
            records_from(item["existing"]),
            records_from(item["incoming"]),
            max_records=item.get("max_records", 10_000),
        )
    if kind == "cursor_bind":
        return bind_cursor(
            item["source"], item["operation"], item["scope"], item["cursor"].encode("utf-8")
        )
    if kind == "cursor":
        binding = bind_cursor(
            item["origin_source"], item["origin_operation"], item["origin_scope"],
            item["cursor"].encode("utf-8"),
        )
        return validate_cursor_binding(
            binding, item["check_source"], item["check_operation"], item["check_scope"]
        )
    if kind == "idempotency_bind":
        return bind_idempotency(
            item["endpoint"], item["operation"], item["key"], records_from(item["records"])
        )
    if kind == "idempotency":
        binding = bind_idempotency(
            item["origin_endpoint"], item["origin_operation"], item["origin_key"],
            records_from(item["origin_records"]),
        )
        return validate_idempotency_replay(
            binding, item["check_endpoint"], item["check_operation"], item["check_key"],
            records_from(item["check_records"]),
        )
    if kind == "submission":
        return validate_submission_outcomes(records_from(item["records"]), tuple(item["outcomes"]))
    if kind == "envelope_make":
        return make_transport_envelope(item["message_type"], item["payload"])
    if kind == "envelope":
        envelope = make_transport_envelope(item["message_type"], item["payload"])
        return validate_transport_envelope(envelope, item["expected_message_type"])
    if kind == "envelope_raw":
        return validate_transport_envelope(item["envelope"], item["expected_message_type"])
    raise MarketplaceFederationError("UNSUPPORTED_VECTOR_KIND", f"unsupported vector kind {kind!r}")


def main() -> int:
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("format") != EXPECTED_FORMAT:
        errors.append("unexpected federation vector format discriminator")
    all_items = list(data.get("cases", ())) + list(data.get("negative_cases", ()))
    ids = [item.get("id") for item in all_items]
    if len(ids) != len(set(ids)):
        errors.append("federation vector ids MUST be unique")
    active_commit = actual_olp_commit()
    expected_commit = data.get("olp_reference_source_commit")
    if active_commit != "unknown" and active_commit != expected_commit:
        errors.append(f"OLP source pin mismatch: vectors={expected_commit} active={active_commit}")

    for item in data.get("cases", ()):
        try:
            actual = jsonable(run_case(item))
        except Exception as exc:
            errors.append(f"{item['id']}: unexpected failure: {type(exc).__name__}: {exc}")
            continue
        if actual != item["expected"]:
            errors.append(f"{item['id']}: expected {item['expected']!r} got {actual!r}")
    for item in data.get("negative_cases", ()):
        try:
            run_case(item)
        except MarketplaceFederationError as exc:
            if exc.code != item["expected_error"]:
                errors.append(
                    f"{item['id']}: expected error {item['expected_error']} got {exc.code}: {exc}"
                )
        except Exception as exc:
            errors.append(f"{item['id']}: wrong exception {type(exc).__name__}: {exc}")
        else:
            errors.append(f"{item['id']}: expected failure {item['expected_error']} but succeeded")

    if errors:
        print("Marketplace federation transport vector validation FAIL")
        for error in errors:
            print("-", error)
        return 1
    print(f"Marketplace federation transport vector validation PASS: {len(all_items)} vectors")
    print(f"OLP source commit: {expected_commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
