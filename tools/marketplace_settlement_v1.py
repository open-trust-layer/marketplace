"""Non-normative Marketplace settlement interfaces v1 helpers.

The helpers evaluate rail-neutral settlement evidence over immutable Agreements
and MarketEvents. They do not execute payments or establish universal finality.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Mapping

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import parse_relationship_record, record_ref as olp_record_ref
from olp.errors import ConformanceError, UnsupportedFeatureError
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.values import is_absolute_uri

from marketplace_record_v1 import (
    BASE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    validate_market_record,
    validate_value_expression,
)
EVENT_SETTLEMENT_ATTEMPT = f"{BASE}/event/settlement-attempt"
EVENT_SETTLEMENT_COMPLETION = f"{BASE}/event/settlement-completion"
EVENT_SETTLEMENT_FAILURE = f"{BASE}/event/settlement-failure"
EVENT_SETTLEMENT_REVERSAL = f"{BASE}/event/settlement-reversal"
EVENT_SETTLEMENT_REFUND = f"{BASE}/event/settlement-refund"
EVENT_ESCROW_HOLD = f"{BASE}/event/escrow-hold"
EVENT_ESCROW_RELEASE = f"{BASE}/event/escrow-release"
EVENT_ASSET_TRANSFER = f"{BASE}/event/asset-transfer"

OUTCOME_SETTLEMENT_EVIDENCE = f"{BASE}/outcome/settlement-evidence"
EXTENT_PARTIAL = f"{BASE}/settlement/extent/partial"
EXTENT_CLAIMED_COMPLETE = f"{BASE}/settlement/extent/claimed-complete"
SETTLEMENT_EVALUATION_CORE = f"{BASE}/settlement/evaluation/core-evidence-v1"

SETTLEMENT_EVENTS = {
    EVENT_SETTLEMENT_ATTEMPT,
    EVENT_SETTLEMENT_COMPLETION,
    EVENT_SETTLEMENT_FAILURE,
    EVENT_SETTLEMENT_REVERSAL,
    EVENT_SETTLEMENT_REFUND,
    EVENT_ESCROW_HOLD,
    EVENT_ESCROW_RELEASE,
    EVENT_ASSET_TRANSFER,
}
EXTENT_EVENTS = {
    EVENT_SETTLEMENT_COMPLETION,
    EVENT_SETTLEMENT_REVERSAL,
    EVENT_SETTLEMENT_REFUND,
    EVENT_ESCROW_RELEASE,
    EVENT_ASSET_TRANSFER,
}
CAUSAL_EVENTS = {
    EVENT_SETTLEMENT_REVERSAL,
    EVENT_SETTLEMENT_REFUND,
    EVENT_ESCROW_RELEASE,
}
MAX_EVIDENCE_ITEMS = 4096
MAX_UNDERSTOOD_CRITICAL = 128
MAX_REFERENCE_TEXT = 1024


class MarketplaceSettlementError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceSettlementError(code, message)


@dataclass(frozen=True)
class SettlementEvidence:
    record: RecordV1
    attribution_accepted: bool
    authority_accepted: bool
    rail_evidence_accepted: bool

    @property
    def accepted_for_method(self) -> bool:
        return self.attribution_accepted and self.authority_accepted and self.rail_evidence_accepted


@dataclass(frozen=True)
class RelationshipEvidence:
    record: RecordV1
    accepted_for_method: bool


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_URI", f"{path} MUST be an absolute URI")
    return value


def _bounded_tuple(values: Iterable[Any], limit: int, code: str) -> tuple[Any, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        fail("INVALID_RESOURCE_LIMIT", "resource limit MUST be a positive integer")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail(code, f"evidence exceeds configured limit {limit}")
    return items


def _agreement_commitment(agreement: RecordV1, commitment_id: str) -> Mapping[str, Any]:
    validate_market_record(agreement)
    if agreement.type != TYPE_AGREEMENT:
        fail("AGREEMENT_REQUIRED", "settlement evaluation requires MarketAgreement")
    if not isinstance(commitment_id, str) or not commitment_id:
        fail("COMMITMENT_ID_REQUIRED", "commitment_id MUST be non-empty text")
    for commitment in agreement.content["commitments"]:
        if commitment["id"] == commitment_id:
            return commitment
    fail("COMMITMENT_NOT_FOUND", "commitment_id is not present in the Agreement")


def _record_ref_from_value(value: Any, path: str) -> EvidenceRefV1:
    try:
        ref = EvidenceRefV1.from_value(value)
    except ConformanceError as exc:
        fail("INVALID_RECORD_REF", f"{path}: {exc}")
    if ref.kind != EvidenceKind.RECORD:
        fail("WRONG_REFERENCE_KIND", f"{path} MUST reference an OLP Record")
    return ref


def _event_commitment_target(event: RecordV1) -> tuple[EvidenceRefV1, str]:
    refs = tuple(event.content.get("commitment_refs", ()))
    if len(refs) != 1:
        fail("SETTLEMENT_EVENT_TARGET", "settlement event MUST target exactly one CommitmentRef")
    item = refs[0]
    if not isinstance(item, Mapping) or set(item) != {"record", "id"}:
        fail("SETTLEMENT_EVENT_TARGET", "commitment target MUST use CommitmentRefV1")
    return _record_ref_from_value(item["record"], "commitment_ref.record"), item["id"]


def _settlement_details(event: RecordV1) -> dict[str, Any]:
    outcome = event.content.get("outcome")
    if not isinstance(outcome, Mapping) or outcome.get("type") != OUTCOME_SETTLEMENT_EVIDENCE:
        fail("SETTLEMENT_OUTCOME_REQUIRED", "settlement event requires settlement-evidence outcome")
    details = outcome.get("details")
    if not isinstance(details, Mapping):
        fail("SETTLEMENT_DETAILS_REQUIRED", "settlement outcome details MUST be a map")
    allowed = {"method", "extent", "value", "reference"}
    if set(details) - allowed or "method" not in details:
        fail("INVALID_SETTLEMENT_DETAILS", "settlement details fields are invalid")
    result = dict(details)
    result["method"] = _require_uri(details["method"], "outcome.details.method")
    if "extent" in details and details["extent"] not in {EXTENT_PARTIAL, EXTENT_CLAIMED_COMPLETE}:
        fail("INVALID_SETTLEMENT_EXTENT", "settlement extent is invalid")
    if "value" in details:
        try:
            validate_value_expression(details["value"], "outcome.details.value")
        except Exception as exc:
            code = getattr(exc, "code", "INVALID_SETTLEMENT_VALUE")
            fail(code, str(exc))
    if "reference" in details:
        ref = details["reference"]
        if not isinstance(ref, str) or not ref or len(ref) > MAX_REFERENCE_TEXT:
            fail("INVALID_SETTLEMENT_REFERENCE", "reference MUST be non-empty bounded text")
    return result


def _related_record_target(event: RecordV1) -> str | None:
    if event.content["event"] not in CAUSAL_EVENTS:
        return None
    refs = tuple(event.content.get("related_records", ()))
    if len(refs) != 1:
        fail("SETTLEMENT_CAUSAL_TARGET", "reversal/refund/release MUST reference exactly one prior event")
    ref = _record_ref_from_value(refs[0], "related_records[0]")
    return record_identity_text(ref.identity_digest)


def validate_settlement_event(
    event: RecordV1,
    agreement: RecordV1,
    commitment_id: str,
) -> dict[str, Any]:
    _agreement_commitment(agreement, commitment_id)
    validate_market_record(event)
    if event.type != TYPE_EVENT:
        fail("MARKET_EVENT_REQUIRED", "settlement evidence MUST be a MarketEvent")
    event_type = event.content["event"]
    if event_type not in SETTLEMENT_EVENTS:
        fail("UNSUPPORTED_SETTLEMENT_EVENT", "event is not a core settlement event")
    ref, local_id = _event_commitment_target(event)
    if ref != olp_record_ref(agreement) or local_id != commitment_id:
        fail("SETTLEMENT_EVENT_TARGET", "event targets a different Agreement commitment")
    details = _settlement_details(event)
    if event_type in EXTENT_EVENTS and "extent" not in details:
        fail("SETTLEMENT_EXTENT_REQUIRED", "this settlement event requires an extent")
    if event_type not in EXTENT_EVENTS and "extent" in details:
        fail("SETTLEMENT_EXTENT_FORBIDDEN", "this settlement event MUST NOT carry an extent")
    causal_target = _related_record_target(event)
    return {
        "event": event_type,
        "record": record_identity_text(event),
        "commitment_id": commitment_id,
        "issuer": event.content["issuer"]["principal"],
        "rail_method": details["method"],
        "extent": details.get("extent"),
        "value": details.get("value"),
        "reference": details.get("reference"),
        "causal_target": causal_target,
    }


def _critical_uris(record: RecordV1) -> set[str]:
    values = record.content.get("critical", ())
    return set(values) if isinstance(values, (tuple, list)) else set()


def settlement_preference_status(agreement: RecordV1, rail_method: str) -> str:
    rail_method = _require_uri(rail_method, "rail_method")
    preferences = tuple(agreement.content.get("settlement_preferences", ()))
    exact = tuple(item for item in preferences if item["method"] == rail_method)
    if any(item["mode"] == "excluded" and "parameters" not in item for item in exact):
        return "EXCLUDED"
    if any(item["mode"] == "excluded" and "parameters" in item for item in exact):
        return "PARAMETERS_UNEVALUATED"
    required = tuple(item for item in preferences if item["mode"] == "required")
    if not required:
        return "ADMISSIBLE"
    matching_required = tuple(item for item in required if item["method"] == rail_method)
    if not matching_required:
        return "REQUIRED_METHOD_MISMATCH"
    if any("parameters" in item for item in matching_required):
        return "PARAMETERS_UNEVALUATED"
    return "ADMISSIBLE"


def _accepted_disputes(
    relationships: Iterable[RelationshipEvidence],
    event_ids: set[str],
    *,
    max_items: int,
) -> set[str]:
    disputed: set[str] = set()
    for item in _bounded_tuple(relationships, max_items, "RESOURCE_LIMIT_EXCEEDED"):
        if not isinstance(item.accepted_for_method, bool):
            fail("INVALID_EVIDENCE_ACCEPTANCE", "relationship acceptance MUST be boolean")
        try:
            statement = parse_relationship_record(item.record)
        except (ConformanceError, UnsupportedFeatureError) as exc:
            fail("INVALID_OLP_RELATIONSHIP", f"invalid OLP relationship: {exc}")
        if statement.relation_type != "disputes" or not item.accepted_for_method:
            continue
        for target in statement.objects:
            if target.kind == EvidenceKind.RECORD:
                identity = record_identity_text(target.identity_digest)
                if identity in event_ids:
                    disputed.add(identity)
    return disputed


def evaluate_commitment_settlement(
    agreement: RecordV1,
    commitment_id: str,
    evidence: Iterable[SettlementEvidence],
    *,
    method: str = SETTLEMENT_EVALUATION_CORE,
    understood_critical: Iterable[str] = (),
    disputes: Iterable[RelationshipEvidence] = (),
    max_evidence: int = MAX_EVIDENCE_ITEMS,
) -> dict[str, Any]:
    _agreement_commitment(agreement, commitment_id)
    method = _require_uri(method, "method")
    if method != SETTLEMENT_EVALUATION_CORE:
        fail("UNSUPPORTED_SETTLEMENT_EVALUATION_METHOD", "reference evaluator implements only core-evidence-v1")
    understood_values = _bounded_tuple(
        understood_critical,
        MAX_UNDERSTOOD_CRITICAL,
        "RESOURCE_LIMIT_EXCEEDED",
    )
    understood = {_require_uri(uri, "understood_critical[]") for uri in understood_values}
    required_critical = _critical_uris(agreement)

    accepted: list[tuple[RecordV1, dict[str, Any]]] = []
    accepted_ids: set[str] = set()
    seen_context: dict[str, tuple[bool, bool, bool]] = {}
    duplicate_event_count = 0
    ignored_nonsettlement = 0
    rejected_by_method = 0
    rejected_by_preference = 0
    preference_indeterminate = 0
    for item in _bounded_tuple(evidence, max_evidence, "RESOURCE_LIMIT_EXCEEDED"):
        flags = (item.attribution_accepted, item.authority_accepted, item.rail_evidence_accepted)
        if any(not isinstance(flag, bool) for flag in flags):
            fail("INVALID_EVIDENCE_ACCEPTANCE", "settlement acceptance dimensions MUST be boolean")
        validate_market_record(item.record)
        if item.record.type != TYPE_EVENT:
            fail("MARKET_EVENT_REQUIRED", "settlement evidence input MUST contain MarketEvent records")
        identity = record_identity_text(item.record)
        prior = seen_context.get(identity)
        if prior is not None:
            if prior != flags:
                fail("DUPLICATE_EVIDENCE_CONTEXT_CONFLICT", "same event identity has conflicting evaluator context")
            duplicate_event_count += 1
            continue
        seen_context[identity] = flags
        if item.record.content["event"] not in SETTLEMENT_EVENTS:
            ignored_nonsettlement += 1
            continue
        metadata = validate_settlement_event(item.record, agreement, commitment_id)
        preference = settlement_preference_status(agreement, metadata["rail_method"])
        if preference in {"EXCLUDED", "REQUIRED_METHOD_MISMATCH"}:
            rejected_by_preference += 1
            continue
        if preference == "PARAMETERS_UNEVALUATED":
            preference_indeterminate += 1
            continue
        if not item.accepted_for_method:
            rejected_by_method += 1
            continue
        accepted.append((item.record, metadata))
        accepted_ids.add(identity)
        required_critical.update(_critical_uris(item.record))
    unsupported_critical = sorted(required_critical - understood, key=lambda value: value.encode("utf-8"))
    event_by_id = {metadata["record"]: metadata for _, metadata in accepted}
    causal_missing = 0
    causal_wrong_type = 0
    valid_causal: set[str] = set()
    for _, metadata in accepted:
        target = metadata["causal_target"]
        if target is None:
            continue
        target_meta = event_by_id.get(target)
        if target_meta is None:
            causal_missing += 1
            continue
        event_type = metadata["event"]
        target_type = target_meta["event"]
        allowed_targets = (
            {EVENT_SETTLEMENT_COMPLETION, EVENT_ASSET_TRANSFER}
            if event_type in {EVENT_SETTLEMENT_REVERSAL, EVENT_SETTLEMENT_REFUND}
            else {EVENT_ESCROW_HOLD}
        )
        if target_type not in allowed_targets:
            causal_wrong_type += 1
            continue
        valid_causal.add(metadata["record"])

    disputed_ids = _accepted_disputes(disputes, accepted_ids, max_items=max_evidence)
    rail_methods = sorted({metadata["rail_method"] for _, metadata in accepted})
    attempts = failures = escrow_holds = 0
    complete = partial = 0
    reversals_complete = reversals_partial = 0
    refunds_complete = refunds_partial = 0
    escrow_releases = asset_transfers = 0
    for _, metadata in accepted:
        event_type = metadata["event"]
        extent = metadata["extent"]
        if event_type == EVENT_SETTLEMENT_ATTEMPT:
            attempts += 1
        elif event_type == EVENT_SETTLEMENT_FAILURE:
            failures += 1
        elif event_type == EVENT_ESCROW_HOLD:
            escrow_holds += 1
        elif event_type == EVENT_SETTLEMENT_COMPLETION:
            if extent == EXTENT_CLAIMED_COMPLETE:
                complete += 1
            else:
                partial += 1
        elif event_type == EVENT_ASSET_TRANSFER:
            asset_transfers += 1
            if extent == EXTENT_CLAIMED_COMPLETE:
                complete += 1
            else:
                partial += 1
        elif event_type == EVENT_SETTLEMENT_REVERSAL and metadata["record"] in valid_causal:
            if extent == EXTENT_CLAIMED_COMPLETE:
                reversals_complete += 1
            else:
                reversals_partial += 1
        elif event_type == EVENT_SETTLEMENT_REFUND and metadata["record"] in valid_causal:
            if extent == EXTENT_CLAIMED_COMPLETE:
                refunds_complete += 1
            else:
                refunds_partial += 1
        elif event_type == EVENT_ESCROW_RELEASE and metadata["record"] in valid_causal:
            escrow_releases += 1
    if unsupported_critical or preference_indeterminate or causal_missing or causal_wrong_type:
        conclusion = "INDETERMINATE"
    elif disputed_ids:
        conclusion = "DISPUTED_EVIDENCE"
    elif complete and failures:
        conclusion = "CONFLICTING_EVIDENCE"
    elif (complete or partial) and (reversals_complete or refunds_complete):
        conclusion = "REVERSED_OR_REFUNDED_UNDER_METHOD"
    elif (complete or partial) and (reversals_partial or refunds_partial):
        conclusion = "PARTIALLY_REVERSED_OR_REFUNDED_UNDER_METHOD"
    elif complete:
        conclusion = "SETTLED_UNDER_METHOD"
    elif partial:
        conclusion = "PARTIALLY_SETTLED_UNDER_METHOD"
    elif escrow_holds and not escrow_releases:
        conclusion = "HELD_IN_ESCROW_UNDER_METHOD"
    elif attempts:
        conclusion = "ATTEMPTED_UNDER_METHOD"
    elif failures:
        conclusion = "NOT_SETTLED_UNDER_METHOD"
    else:
        conclusion = "INDETERMINATE"

    return {
        "agreement": record_identity_text(agreement),
        "commitment_id": commitment_id,
        "method": method,
        "conclusion": conclusion,
        "accepted_event_count": len(accepted),
        "duplicate_event_count": duplicate_event_count,
        "ignored_nonsettlement_event_count": ignored_nonsettlement,
        "rejected_by_method_count": rejected_by_method,
        "rejected_by_preference_count": rejected_by_preference,
        "preference_indeterminate_count": preference_indeterminate,
        "attempts": attempts,
        "failures": failures,
        "partial_settlement_assertions": partial,
        "complete_settlement_assertions": complete,
        "escrow_holds": escrow_holds,
        "escrow_releases": escrow_releases,
        "asset_transfer_assertions": asset_transfers,
        "complete_reversals": reversals_complete,
        "partial_reversals": reversals_partial,
        "complete_refunds": refunds_complete,
        "partial_refunds": refunds_partial,
        "rail_methods": rail_methods,
        "multi_rail": len(rail_methods) > 1,
        "causal_target_missing_count": causal_missing,
        "causal_target_wrong_type_count": causal_wrong_type,
        "unsupported_critical_semantics": unsupported_critical,
        "disputed_event_ids": sorted(disputed_ids),
        "universal_truth": False,
        "cross_rail_arithmetic_performed": False,
        "fulfillment_evaluated": False,
        "ownership_or_title_evaluated": False,
        "legal_finality_evaluated": False,
    }
