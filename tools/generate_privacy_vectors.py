"""Generate Marketplace privacy/selective-disclosure v1 conformance vectors."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity
from olp.evidence import record_ref
from olp.model.bundle import ResourceRefV1
from olp.model.evidence import EvidenceRefV1
from olp.transport import project_abstract

from marketplace_fulfillment_v1 import EVENT_COMMITMENT_DELIVERY
from marketplace_privacy_v1 import (
    CORE_TASKS, MAX_CAPABILITIES, MAX_INVENTORY_ITEMS, MAX_RESOURCE_ITEMS, MAX_ROOTS,
    TASK_DISCOVERY, TASK_FEDERATION, TASK_FULFILLMENT, TASK_NEGOTIATION,
    TASK_SETTLEMENT, TASK_TRUST, plan_marketplace_disclosure,
)
from marketplace_record_v1 import BASE, CORE_PROFILE, PROPOSAL_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT, validate_market_record
from marketplace_settlement_v1 import EVENT_SETTLEMENT_COMPLETION

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "privacy-selective-disclosure-v1.json"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_record(record_type: str, content: dict, profiles=(CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(envelope_version=1, type=record_type, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {"envelope_version": record.envelope_version, "type": record.type, "content": record.content}
    if record.semantic_bindings: value["semantic_bindings"] = record.semantic_bindings
    if record.profiles: value["profiles"] = record.profiles
    if record.relationships: value["relationships"] = record.relationships
    if record.extensions: value["extensions"] = record.extensions
    return value


def jsonable(value):
    if isinstance(value, tuple): return [jsonable(v) for v in value]
    if isinstance(value, list): return [jsonable(v) for v in value]
    if isinstance(value, dict): return {k: jsonable(v) for k, v in value.items()}
    return value


def projected_payload(payload: dict) -> dict:
    def convert(value):
        if isinstance(value, RecordV1):
            return record_mapping(value)
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(convert(item) for item in value)
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value
    return project_abstract(convert(payload))


def req(task, roots, *, options=None, capabilities=(), version=1):
    return [
        "OLP-DISCLOSURE-REQUEST", version, task,
        [root.to_value() for root in roots], list(capabilities), {}, {}, options or {},
    ]


def inv(record: RecordV1, *, dependencies=(), privacy_warnings=()):
    return {
        "ref": record_ref(record).to_value(),
        "record": record,
        "dependencies": list(dependencies),
        "privacy_warnings": list(privacy_warnings),
    }


def opaque_inv(ref: EvidenceRefV1, *, dependencies=()):
    return {"ref": ref.to_value(), "dependencies": list(dependencies), "privacy_warnings": []}


def base_payload(task, root_record, **overrides):
    payload = {
        "request": req(task, [record_ref(root_record)]),
        "inventory": [inv(root_record)],
        "resources": [],
        "manifested": False,
        "network_resolution_planned": False,
    }
    payload.update(overrides)
    return payload


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:job:42"}
    action = {"id": "https://example.test/actions/build"}
    settlement_pref = {"method": "https://example.test/payments/bank", "mode": "preferred"}
    intent = market_record(TYPE_INTENT, {
        "version": 1, "issuer": alice, "subjects": (subject,), "action": action,
        "terms": {}, "settlement_preferences": (settlement_pref,),
    })
    proposal = market_record(TYPE_INTENT, {
        "version": 1, "issuer": bob, "subjects": (subject,), "action": action,
        "terms": {}, "response_to": (record_ref(intent).to_value(),),
    }, profiles=sort_set((CORE_PROFILE, PROPOSAL_PROFILE)))
    commitment = {"id": "c1", "party": bob, "action": action, "subjects": (subject,)}
    agreement = market_record(TYPE_AGREEMENT, {
        "version": 1, "parties": sort_set((alice, bob)), "subjects": (subject,),
        "actions": (action,), "terms": {}, "commitments": (commitment,),
        "source_records": sort_set((record_ref(intent).to_value(), record_ref(proposal).to_value())),
        "settlement_preferences": (settlement_pref,),
    })
    cref = {"record": record_ref(agreement).to_value(), "id": "c1"}
    fulfillment = market_record(TYPE_EVENT, {
        "version": 1, "issuer": bob, "event": EVENT_COMMITMENT_DELIVERY,
        "commitment_refs": (cref,),
    })
    settlement = market_record(TYPE_EVENT, {
        "version": 1, "issuer": alice, "event": EVENT_SETTLEMENT_COMPLETION,
        "commitment_refs": (cref,),
    })
    support = RecordV1(
        envelope_version=1,
        type="claim",
        content={"statement": "supporting evidence", "subject": "urn:example:job:42"},
    )
    support_ref = EvidenceRefV1(EvidenceKind.RECORD, record_identity(support))
    sibling = RecordV1(
        envelope_version=1,
        type="claim",
        content={"statement": "unrelated sibling", "subject": "urn:example:other"},
    )
    sibling_ref = EvidenceRefV1(EvidenceKind.RECORD, record_identity(sibling))

    cases: list[dict] = []
    negative: list[dict] = []

    def add_case(case_id: str, payload: dict):
        result = plan_marketplace_disclosure(payload)
        cases.append({"id": case_id, "kind": "plan", "payload": projected_payload(payload), "expected": jsonable(result)})

    def add_negative(case_id: str, payload: dict, expected_error: str):
        negative.append({"id": case_id, "kind": "plan", "payload": projected_payload(payload), "expected_error": expected_error})
    for task in sorted(CORE_TASKS):
        add_case("task-" + task.rsplit("/", 1)[-1], base_payload(task, intent))

    add_case("proposal-negotiation-warning", base_payload(TASK_NEGOTIATION, proposal))
    add_case("agreement-multiparty-negotiation-warnings", base_payload(TASK_NEGOTIATION, agreement))
    add_case("fulfillment-history-warning", base_payload(TASK_FULFILLMENT, fulfillment))
    add_case("settlement-history-warning", base_payload(TASK_SETTLEMENT, settlement))

    metadata_payload = base_payload(TASK_TRUST, agreement)
    metadata_payload["workflow_metadata"] = {
        "query_scope_disclosed": True,
        "federation_cursor_disclosed": True,
        "trust_trace_disclosed": True,
        "recipient_identifier_disclosed": True,
    }
    add_case("workflow-metadata-warnings", metadata_payload)
    add_case("manifest-correlation-warning", base_payload(TASK_FEDERATION, intent, manifested=True))
    add_case("network-resolution-warning", base_payload(TASK_DISCOVERY, intent, network_resolution_planned=True))

    dep = ["evidence", support_ref.to_value(), "protocol"]
    subset_payload = base_payload(TASK_TRUST, agreement)
    subset_payload["inventory"] = [
        inv(agreement, dependencies=[dep]),
        {"ref": support_ref.to_value(), "record": support, "dependencies": [], "privacy_warnings": []},
        {"ref": sibling_ref.to_value(), "record": sibling, "dependencies": [], "privacy_warnings": []},
    ]
    add_case("graph-subset-selects-required-support-only", subset_payload)
    missing_ref = EvidenceRefV1(EvidenceKind.RECORD, b"\x44" * 32)
    partial_payload = base_payload(TASK_TRUST, agreement)
    partial_payload["inventory"] = [
        inv(agreement, dependencies=[["evidence", missing_ref.to_value(), "policy"]])
    ]
    add_case("unresolved-dependency-is-partial", partial_payload)

    root_missing = base_payload(TASK_DISCOVERY, intent)
    root_missing["inventory"] = []
    add_case("missing-root-is-unsatisfiable", root_missing)

    cap_payload = base_payload(TASK_DISCOVERY, intent)
    cap_payload["request"] = req(TASK_DISCOVERY, [record_ref(intent)], capabilities=("olp.proof-verification.v1",))
    cap_payload["available_capabilities"] = ["olp.record-identity.v1"]
    add_case("required-capability-unavailable", cap_payload)
    resource_content = b"verification-method-document"
    resource_ref = ResourceRefV1(None, "application/json", -16, hashlib.sha256(resource_content).digest())
    offline_payload = base_payload(TASK_TRUST, agreement)
    offline_payload["request"] = req(TASK_TRUST, [record_ref(agreement)], options={1: True})
    offline_payload["inventory"] = [
        inv(agreement, dependencies=[["resource", resource_ref.to_value(), "offline"]])
    ]
    offline_payload["resources"] = [{"ref": resource_ref.to_value(), "content": resource_content}]
    add_case("offline-support-overdisclosure-warning", offline_payload)

    online_payload = dict(offline_payload)
    online_payload["request"] = req(TASK_TRUST, [record_ref(agreement)])
    add_case("online-omits-offline-only-resource", online_payload)

    sd_content = b"native-selective-disclosure-presentation"
    sd_ref = ResourceRefV1(None, "application/sd-jwt", -16, hashlib.sha256(sd_content).digest())
    sd_payload = base_payload(TASK_TRUST, agreement)
    sd_payload["inventory"] = [inv(agreement, dependencies=[["resource", sd_ref.to_value(), "protocol"]])]
    sd_payload["resources"] = [{"ref": sd_ref.to_value(), "content": sd_content, "native_presentation": True}]
    add_case("native-presentation-blocked-unless-permitted", sd_payload)
    sd_allowed = dict(sd_payload)
    sd_allowed["request"] = req(TASK_TRUST, [record_ref(agreement)], options={3: True})
    add_case("native-presentation-permitted-preserves-warning", sd_allowed)

    bundle_limit = base_payload(TASK_DISCOVERY, intent)
    bundle_limit["request"] = req(TASK_DISCOVERY, [record_ref(intent)], options={2: 100})
    add_case("bundle-byte-limit-deferred-to-packaging", bundle_limit)

    altered_intent = market_record(TYPE_INTENT, {
        "version": 1, "issuer": alice, "subjects": (subject,), "action": action,
        "terms": {"https://example.test/term/derived": True},
        "settlement_preferences": (settlement_pref,),
    })
    redaction_payload = base_payload(TASK_DISCOVERY, intent)
    redaction_payload["inventory"] = [{
        "ref": record_ref(intent).to_value(), "record": altered_intent,
        "dependencies": [], "privacy_warnings": [],
    }]
    add_case("field-deletion-or-change-cannot-retain-record-identity", redaction_payload)
    unknown_task = base_payload("https://example.test/privacy/task/unknown", intent)
    add_negative("unsupported-marketplace-task", unknown_task, "UNSUPPORTED_MARKETPLACE_DISCLOSURE_TASK")

    nonmarket = RecordV1(envelope_version=1, type="claim", content={"statement": "not marketplace"})
    nonmarket_payload = {
        "request": req(TASK_DISCOVERY, [record_ref(nonmarket)]),
        "inventory": [{"ref": record_ref(nonmarket).to_value(), "record": nonmarket, "dependencies": [], "privacy_warnings": []}],
        "resources": [], "manifested": False, "network_resolution_planned": False,
    }
    add_negative("nonmarketplace-root", nonmarket_payload, "INVALID_MARKETPLACE_ROOT")

    proof_ref = EvidenceRefV1(EvidenceKind.PROOF, b"\x55" * 32)
    proof_payload = {
        "request": req(TASK_TRUST, [proof_ref]), "inventory": [opaque_inv(proof_ref)],
        "resources": [], "manifested": False, "network_resolution_planned": False,
    }
    add_negative("proof-root-not-marketplace-record", proof_payload, "MARKETPLACE_ROOT_MUST_BE_RECORD")
    body_missing = base_payload(TASK_DISCOVERY, intent)
    body_missing["inventory"] = [opaque_inv(record_ref(intent))]
    add_negative("available-root-body-required", body_missing, "MARKETPLACE_ROOT_BODY_REQUIRED")

    missing_flags = base_payload(TASK_DISCOVERY, intent)
    missing_flags.pop("manifested")
    add_negative("explicit-privacy-context-required", missing_flags, "EXPLICIT_PRIVACY_CONTEXT_REQUIRED")

    bad_flag = base_payload(TASK_DISCOVERY, intent)
    bad_flag["manifested"] = 1
    add_negative("privacy-flag-must-be-boolean", bad_flag, "INVALID_PRIVACY_FLAG")

    bad_metadata = base_payload(TASK_TRUST, intent)
    bad_metadata["workflow_metadata"] = {"unknown": True}
    add_negative("unknown-workflow-metadata", bad_metadata, "INVALID_WORKFLOW_METADATA")
    bad_metadata_type = base_payload(TASK_TRUST, intent)
    bad_metadata_type["workflow_metadata"] = {"trust_trace_disclosed": 1}
    add_negative("workflow-metadata-flag-must-be-boolean", bad_metadata_type, "INVALID_PRIVACY_FLAG")
    bad_inventory = base_payload(TASK_DISCOVERY, intent)
    bad_inventory["inventory"] = "not-an-array"
    add_negative("inventory-must-be-array", bad_inventory, "INVALID_DISCLOSURE_INVENTORY")
    bad_resources = base_payload(TASK_DISCOVERY, intent)
    bad_resources["resources"] = "not-an-array"
    add_negative("resources-must-be-array", bad_resources, "INVALID_DISCLOSURE_RESOURCES")

    duplicate_inventory = base_payload(TASK_DISCOVERY, intent)
    duplicate_inventory["inventory"] = [inv(intent), inv(intent)]
    add_negative("duplicate-inventory-reference", duplicate_inventory, "INVALID_DISCLOSURE_INVENTORY")

    bad_available = base_payload(TASK_DISCOVERY, intent)
    bad_available["available_capabilities"] = "not-an-array"
    add_negative("available-capabilities-must-be-array", bad_available, "INVALID_AVAILABLE_CAPABILITIES")
    bad_available_item = base_payload(TASK_DISCOVERY, intent)
    bad_available_item["available_capabilities"] = [1]
    add_negative("available-capability-must-be-text", bad_available_item, "INVALID_AVAILABLE_CAPABILITIES")
    bad_version_bool = base_payload(TASK_DISCOVERY, intent)
    bad_version_bool["request"] = req(TASK_DISCOVERY, [record_ref(intent)], version=True)
    add_negative("boolean-request-version-rejected", bad_version_bool, "MALFORMED_DISCLOSURE_REQUEST")
    bad_version = base_payload(TASK_DISCOVERY, intent)
    bad_version["request"] = req(TASK_DISCOVERY, [record_ref(intent)], version=2)
    add_negative("unsupported-request-version", bad_version, "UNSUPPORTED_DISCLOSURE_REQUEST_VERSION")

    unsorted_caps = base_payload(TASK_DISCOVERY, intent)
    unsorted_caps["request"] = req(
        TASK_DISCOVERY, [record_ref(intent)],
        capabilities=("olp.proof-verification.v1", "olp.bundle.v1"),
    )
    add_negative("required-capabilities-must-be-canonical", unsorted_caps, "MALFORMED_DISCLOSURE_REQUEST")

    bad_bundle_limit = base_payload(TASK_DISCOVERY, intent)
    bad_bundle_limit["request"] = req(TASK_DISCOVERY, [record_ref(intent)], options={2: True})
    add_negative("boolean-max-bundle-bytes-rejected", bad_bundle_limit, "MALFORMED_DISCLOSURE_REQUEST")
    invalid_support = RecordV1(envelope_version=1, type=TYPE_EVENT, content={"version": 1, "issuer": alice, "event": f"{BASE}/event/privacy-invalid"})
    invalid_support_payload = base_payload(TASK_TRUST, intent)
    invalid_support_payload["inventory"] = [
        inv(intent, dependencies=[["evidence", record_ref(invalid_support).to_value(), "protocol"]]),
        inv(invalid_support),
    ]
    add_negative("invalid-selected-supporting-marketplace-record", invalid_support_payload, "INVALID_SELECTED_MARKETPLACE_RECORD")

    related_event = market_record(TYPE_EVENT, {"version": 1, "issuer": alice, "event": f"{BASE}/event/privacy-related", "related_records": (record_ref(intent).to_value(),)})
    add_case("related-record-correlation-warning", base_payload(TASK_TRUST, related_event))

    evidence_event = market_record(TYPE_EVENT, {"version": 1, "issuer": alice, "event": f"{BASE}/event/privacy-evidence", "subjects": (subject,), "evidence": (support_ref.to_value(),)})
    add_case("event-evidence-reference-correlation-warning", base_payload(TASK_TRUST, evidence_event))

    pairwise_alice = {"principal": "did:example:pairwise-alice", "role": "https://example.test/roles/requester"}
    pairwise_intent = market_record(TYPE_INTENT, {"version": 1, "issuer": pairwise_alice, "subjects": (subject,), "action": action, "terms": {}})
    add_case("pairwise-identifier-does-not-establish-global-linkability", base_payload(TASK_DISCOVERY, pairwise_intent))

    for case_id, target in (
        ("root-count-limit", "roots"),
        ("inventory-count-limit", "inventory"),
        ("resource-count-limit", "resources"),
        ("required-capability-count-limit", "required_capabilities"),
        ("available-capability-count-limit", "available_capabilities"),
        ("dependency-count-limit", "dependencies"),
        ("item-privacy-warning-count-limit", "item_privacy_warnings"),
        ("resource-privacy-warning-count-limit", "resource_privacy_warnings"),
    ):
        negative.append({
            "id": case_id,
            "kind": "synthetic-limit",
            "target": target,
            "base_payload": projected_payload(base_payload(TASK_DISCOVERY, intent)),
            "expected_error": "PRIVACY_RESOURCE_LIMIT_EXCEEDED",
        })

    return {
        "format": "marketplace-privacy-selective-disclosure-v1-conformance-vectors",
        "profile": "https://open-trust-layer.github.io/marketplace/semantics/v1/privacy/profile/core-v1",
        "olp_reference_source_commit": olp_commit(),
        "cases": cases,
        "negative_cases": negative,
    }


from olp.model.evidence import EvidenceKind


def main() -> int:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
