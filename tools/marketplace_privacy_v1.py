"""Non-normative Marketplace privacy/disclosure profile v1 helpers.

Marketplace profiles OLP Specification 0010 instead of inventing a parallel
privacy envelope or field-redaction mechanism. Exact immutable evidence is
planned by ``olp.disclosure``; this module adds Marketplace task and warning
semantics only.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import islice
from typing import Any

from olp import RecordV1
from olp.disclosure import DisclosureRequestV1, plan_disclosure
from olp.model.evidence import EvidenceKind, EvidenceRefV1

from marketplace_fulfillment_v1 import FULFILLMENT_EVENTS
from marketplace_record_v1 import (
    BASE,
    RECORD_TYPES,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    TYPE_INTENT,
    validate_market_record,
)
from marketplace_settlement_v1 import SETTLEMENT_EVENTS

PROFILE_CORE = f"{BASE}/privacy/profile/core-v1"
TASK_DISCOVERY = f"{BASE}/privacy/task/discovery"
TASK_NEGOTIATION = f"{BASE}/privacy/task/negotiation"
TASK_FULFILLMENT = f"{BASE}/privacy/task/fulfillment-verification"
TASK_SETTLEMENT = f"{BASE}/privacy/task/settlement-verification"
TASK_FEDERATION = f"{BASE}/privacy/task/federation-exchange"
TASK_TRUST = f"{BASE}/privacy/task/trust-evaluation"

CORE_TASKS = frozenset({
    TASK_DISCOVERY,
    TASK_NEGOTIATION,
    TASK_FULFILLMENT,
    TASK_SETTLEMENT,
    TASK_FEDERATION,
    TASK_TRUST,
})

MAX_ROOTS = 256
MAX_INVENTORY_ITEMS = 4096
MAX_RESOURCE_ITEMS = 4096
MAX_CAPABILITIES = 256
MAX_DEPENDENCIES_PER_ITEM = 4096
MAX_PRIVACY_WARNINGS_PER_ITEM = 64

WORKFLOW_METADATA_KEYS = frozenset({
    "query_scope_disclosed",
    "federation_cursor_disclosed",
    "trust_trace_disclosed",
    "recipient_identifier_disclosed",
})
MARKETPLACE_WARNING_CODES = frozenset({
    "MARKETPLACE_PRINCIPAL_IDENTIFIER_CORRELATION",
    "MARKETPLACE_SUBJECT_REFERENCE_CORRELATION",
    "MARKETPLACE_MULTIPARTY_RELATIONSHIP_DISCLOSURE",
    "MARKETPLACE_NEGOTIATION_GRAPH_DISCLOSURE",
    "MARKETPLACE_COMMITMENT_REFERENCE_CORRELATION",
    "MARKETPLACE_FULFILLMENT_HISTORY_DISCLOSURE",
    "MARKETPLACE_SETTLEMENT_HISTORY_DISCLOSURE",
    "MARKETPLACE_SETTLEMENT_PREFERENCE_DISCLOSURE",
    "MARKETPLACE_QUERY_SCOPE_DISCLOSURE",
    "MARKETPLACE_FEDERATION_CURSOR_DISCLOSURE",
    "MARKETPLACE_TRUST_TRACE_DISCLOSURE",
    "MARKETPLACE_RECIPIENT_IDENTIFIER_CORRELATION",
    "MARKETPLACE_ROLE_BINDING_DISCLOSURE",
    "MARKETPLACE_EVIDENCE_REFERENCE_CORRELATION",
    "MARKETPLACE_RELATED_RECORD_CORRELATION",
})


class MarketplacePrivacyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplacePrivacyError(code, message)


def _bounded_tuple(values: Iterable[Any], limit: int, path: str) -> tuple[Any, ...]:
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds M10 v1 limit {limit}")
    return items


def _preflight_request_cardinality(value: Any) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 8:
        return
    roots, capabilities = value[3], value[4]
    if isinstance(roots, (list, tuple)) and len(roots) > MAX_ROOTS:
        fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", f"roots exceed M10 v1 limit {MAX_ROOTS}")
    if isinstance(capabilities, (list, tuple)) and len(capabilities) > MAX_CAPABILITIES:
        fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", f"required capabilities exceed M10 v1 limit {MAX_CAPABILITIES}")


def _require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail("INVALID_PRIVACY_FLAG", f"{path} MUST be boolean")
    return value


def _normalize_workflow_metadata(value: Any) -> dict[str, bool]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        fail("INVALID_WORKFLOW_METADATA", "workflow_metadata MUST be a map")
    unknown = set(value) - WORKFLOW_METADATA_KEYS
    if unknown:
        fail("INVALID_WORKFLOW_METADATA", f"unknown workflow metadata keys {sorted(unknown)!r}")
    return {
        key: _require_bool(value[key], f"workflow_metadata.{key}")
        for key in sorted(value)
    }


def _inventory_items(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = payload.get("inventory", ())
    if not isinstance(raw, (tuple, list)):
        fail("INVALID_DISCLOSURE_INVENTORY", "inventory MUST be an array")
    items = _bounded_tuple(raw, MAX_INVENTORY_ITEMS, "inventory")
    if any(not isinstance(item, Mapping) for item in items):
        fail("INVALID_DISCLOSURE_INVENTORY", "inventory items MUST be maps")
    for item in items:
        deps = item.get("dependencies", ())
        warnings = item.get("privacy_warnings", ())
        if isinstance(deps, (list, tuple)) and len(deps) > MAX_DEPENDENCIES_PER_ITEM:
            fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", "inventory item dependencies exceed M10 v1 limit")
        if isinstance(warnings, (list, tuple)) and len(warnings) > MAX_PRIVACY_WARNINGS_PER_ITEM:
            fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", "inventory item privacy warnings exceed M10 v1 limit")
    return items


def _resource_items(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = payload.get("resources", ())
    if not isinstance(raw, (tuple, list)):
        fail("INVALID_DISCLOSURE_RESOURCES", "resources MUST be an array")
    items = _bounded_tuple(raw, MAX_RESOURCE_ITEMS, "resources")
    if any(not isinstance(item, Mapping) for item in items):
        fail("INVALID_DISCLOSURE_RESOURCES", "resource items MUST be maps")
    for item in items:
        warnings = item.get("privacy_warnings", ())
        if isinstance(warnings, (list, tuple)) and len(warnings) > MAX_PRIVACY_WARNINGS_PER_ITEM:
            fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", "resource item privacy warnings exceed M10 v1 limit")
    return items


def _ref_key(ref: EvidenceRefV1) -> tuple[int, str]:
    return int(ref.kind), ref.identity_digest.hex()


def _record_principals(record: RecordV1) -> set[str]:
    content = record.content
    if not isinstance(content, Mapping):
        return set()
    principals: set[str] = set()
    for field in ("issuer",):
        value = content.get(field)
        if isinstance(value, Mapping) and isinstance(value.get("principal"), str):
            principals.add(value["principal"])
    for field in ("parties", "commitments"):
        values = content.get(field, ())
        if isinstance(values, (list, tuple)):
            for item in values:
                if not isinstance(item, Mapping):
                    continue
                party = item.get("party") if field == "commitments" else item
                if isinstance(party, Mapping) and isinstance(party.get("principal"), str):
                    principals.add(party["principal"])
    return principals


def _marketplace_warnings_for_record(record: RecordV1) -> set[str]:
    validate_market_record(record)
    content = record.content
    assert isinstance(content, Mapping)
    warnings: set[str] = set()
    principals = _record_principals(record)
    if principals:
        warnings.add("MARKETPLACE_PRINCIPAL_IDENTIFIER_CORRELATION")
    if len(principals) > 1:
        warnings.add("MARKETPLACE_MULTIPARTY_RELATIONSHIP_DISCLOSURE")
    if content.get("subjects"):
        warnings.add("MARKETPLACE_SUBJECT_REFERENCE_CORRELATION")
    if content.get("settlement_preferences"):
        warnings.add("MARKETPLACE_SETTLEMENT_PREFERENCE_DISCLOSURE")
    party_values = [content.get("issuer")] + list(content.get("parties", ())) + [item.get("party") for item in content.get("commitments", ()) if isinstance(item, Mapping)]
    if any(isinstance(item, Mapping) and item.get("role") for item in party_values):
        warnings.add("MARKETPLACE_ROLE_BINDING_DISCLOSURE")
    if content.get("evidence"):
        warnings.add("MARKETPLACE_EVIDENCE_REFERENCE_CORRELATION")
    if content.get("related_records"):
        warnings.add("MARKETPLACE_RELATED_RECORD_CORRELATION")
    if record.type == TYPE_INTENT and content.get("response_to"):
        warnings.add("MARKETPLACE_NEGOTIATION_GRAPH_DISCLOSURE")
    if record.type == TYPE_AGREEMENT and content.get("source_records"):
        warnings.add("MARKETPLACE_NEGOTIATION_GRAPH_DISCLOSURE")
    if record.type == TYPE_EVENT:
        if content.get("commitment_refs"):
            warnings.add("MARKETPLACE_COMMITMENT_REFERENCE_CORRELATION")
        event = content.get("event")
        if event in FULFILLMENT_EVENTS:
            warnings.add("MARKETPLACE_FULFILLMENT_HISTORY_DISCLOSURE")
        if event in SETTLEMENT_EVENTS:
            warnings.add("MARKETPLACE_SETTLEMENT_HISTORY_DISCLOSURE")
    return warnings


def plan_marketplace_disclosure(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        fail("INVALID_MARKETPLACE_DISCLOSURE_INPUT", "input MUST be a map")
    if "request" not in payload:
        fail("INVALID_MARKETPLACE_DISCLOSURE_INPUT", "request is required")
    _preflight_request_cardinality(payload["request"])
    if "manifested" not in payload or "network_resolution_planned" not in payload:
        fail("EXPLICIT_PRIVACY_CONTEXT_REQUIRED", "manifested and network_resolution_planned are required")
    manifested = _require_bool(payload["manifested"], "manifested")
    network_planned = _require_bool(payload["network_resolution_planned"], "network_resolution_planned")
    metadata = _normalize_workflow_metadata(payload.get("workflow_metadata"))

    try:
        request = DisclosureRequestV1.from_value(payload["request"])
    except Exception:
        raise
    if request.purpose not in CORE_TASKS:
        fail("UNSUPPORTED_MARKETPLACE_DISCLOSURE_TASK", "request purpose is not an M10 core task")
    if len(request.roots) > MAX_ROOTS:
        fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", f"roots exceed M10 v1 limit {MAX_ROOTS}")
    if len(request.required_capabilities) > MAX_CAPABILITIES:
        fail("PRIVACY_RESOURCE_LIMIT_EXCEEDED", f"required capabilities exceed M10 v1 limit {MAX_CAPABILITIES}")

    inventory = _inventory_items(payload)
    resources = _resource_items(payload)
    available = payload.get("available_capabilities")
    if available is not None:
        if not isinstance(available, (list, tuple)):
            fail("INVALID_AVAILABLE_CAPABILITIES", "available_capabilities MUST be an array")
        available_items = _bounded_tuple(available, MAX_CAPABILITIES, "available_capabilities")
        if any(not isinstance(item, str) for item in available_items):
            fail("INVALID_AVAILABLE_CAPABILITIES", "available capabilities MUST be text identifiers")

    inventory_by_ref: dict[EvidenceRefV1, Mapping[str, Any]] = {}
    for raw in inventory:
        if "ref" not in raw:
            fail("INVALID_DISCLOSURE_INVENTORY", "inventory item is missing ref")
        try:
            ref = EvidenceRefV1.from_value(raw["ref"])
        except Exception as exc:
            fail("INVALID_DISCLOSURE_INVENTORY", f"invalid inventory ref: {exc}")
        if ref in inventory_by_ref:
            fail("INVALID_DISCLOSURE_INVENTORY", "duplicate inventory reference")
        inventory_by_ref[ref] = raw
    for root in request.roots:
        if root.kind != EvidenceKind.RECORD:
            fail("MARKETPLACE_ROOT_MUST_BE_RECORD", "M10 core roots MUST reference Marketplace Records")
        raw = inventory_by_ref.get(root)
        if raw is None:
            continue
        record = raw.get("record")
        if record is None:
            fail("MARKETPLACE_ROOT_BODY_REQUIRED", "available Marketplace root requires decoded Record body")
        if not isinstance(record, RecordV1):
            fail("INVALID_MARKETPLACE_ROOT", "root record body MUST be RecordV1")
        try:
            validate_market_record(record)
        except Exception as exc:
            fail("INVALID_MARKETPLACE_ROOT", f"root is not a conforming core Marketplace record: {exc}")

    delegated = dict(payload)
    delegated["inventory"] = list(inventory)
    delegated["resources"] = list(resources)
    delegated["manifested"] = manifested
    delegated["network_resolution_planned"] = network_planned
    result = plan_disclosure(delegated)
    selected_keys = {
        (int(entry["kind"]), entry["identity_digest_hex"])
        for entry in result["selected_evidence"]
    }
    marketplace_warnings: set[str] = set()
    for ref, raw in inventory_by_ref.items():
        if _ref_key(ref) not in selected_keys:
            continue
        record = raw.get("record")
        if isinstance(record, RecordV1) and record.type in RECORD_TYPES:
            try:
                marketplace_warnings.update(_marketplace_warnings_for_record(record))
            except Exception as exc:
                fail("INVALID_SELECTED_MARKETPLACE_RECORD", f"selected supporting Marketplace record is invalid: {exc}")

    metadata_warnings = {
        "query_scope_disclosed": "MARKETPLACE_QUERY_SCOPE_DISCLOSURE",
        "federation_cursor_disclosed": "MARKETPLACE_FEDERATION_CURSOR_DISCLOSURE",
        "trust_trace_disclosed": "MARKETPLACE_TRUST_TRACE_DISCLOSURE",
        "recipient_identifier_disclosed": "MARKETPLACE_RECIPIENT_IDENTIFIER_CORRELATION",
    }
    for key, warning in metadata_warnings.items():
        if metadata.get(key, False):
            marketplace_warnings.add(warning)
    return {
        "profile": PROFILE_CORE,
        "task": request.purpose,
        "olp_result": result,
        "marketplace_privacy_warnings": tuple(sorted(marketplace_warnings)),
        "withheld_evidence_is_negative_evidence": False,
        "global_minimality_claimed": False,
        "global_completeness_established": False,
        "field_redaction_performed": False,
        "hidden_network_fallback_permitted": False,
        "authorization_evaluated": False,
        "consent_or_lawful_basis_evaluated": False,
        "trust_evaluated": False,
        "global_identifier_linkability_established": False,
        "audience_binding_evaluated": False,
        "external_undisclosed_claims_synthesized": False,
    }
