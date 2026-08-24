"""Generate Marketplace settlement interfaces v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref, relationship_record
from olp.transport import project_abstract

from marketplace_record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, TYPE_EVENT, TYPE_INTENT, validate_market_record
from marketplace_settlement_v1 import (
    EVENT_ASSET_TRANSFER,
    EVENT_ESCROW_HOLD,
    EVENT_ESCROW_RELEASE,
    EVENT_SETTLEMENT_ATTEMPT,
    EVENT_SETTLEMENT_COMPLETION,
    EVENT_SETTLEMENT_FAILURE,
    EVENT_SETTLEMENT_REFUND,
    EVENT_SETTLEMENT_REVERSAL,
    EXTENT_CLAIMED_COMPLETE,
    EXTENT_PARTIAL,
    OUTCOME_SETTLEMENT_EVIDENCE,
    SETTLEMENT_EVALUATION_CORE,
    MarketplaceSettlementError,
    RelationshipEvidence,
    SettlementEvidence,
    evaluate_commitment_settlement,
    validate_settlement_event,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "settlement-interfaces-v1.json"


def olp_commit() -> str:
    import olp

    repo = Path(olp.__file__).resolve().parents[2]
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def sort_set(values):
    return tuple(sorted(tuple(values), key=olp_encode))


def market_record(record_type: str, content: dict, profiles: tuple[str, ...] = (CORE_PROFILE,)) -> RecordV1:
    record = RecordV1(envelope_version=1, type=record_type, content=content, profiles=profiles)
    validate_market_record(record)
    return record


def record_mapping(record: RecordV1) -> dict:
    value = {"envelope_version": record.envelope_version, "type": record.type, "content": record.content}
    if record.semantic_bindings:
        value["semantic_bindings"] = record.semantic_bindings
    if record.profiles:
        value["profiles"] = record.profiles
    if record.relationships:
        value["relationships"] = record.relationships
    if record.extensions:
        value["extensions"] = record.extensions
    return value


def projected_record(record: RecordV1):
    return project_abstract(record_mapping(record))


def expected_subset(result: dict, *keys: str) -> dict:
    return {key: result[key] for key in keys}


def event_item(
    record: RecordV1,
    attribution: bool = True,
    authority: bool = True,
    rail: bool = True,
) -> dict:
    return {
        "record": projected_record(record),
        "attribution_accepted": attribution,
        "authority_accepted": authority,
        "rail_evidence_accepted": rail,
    }


def relationship_item(record: RecordV1, accepted: bool = True) -> dict:
    return {"record": projected_record(record), "accepted_for_method": accepted}


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/payer"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/payee"}
    subject = {"uri": "urn:example:invoice:42"}
    pay_action = {"id": "https://example.test/actions/pay"}
    transfer_action = {"id": "https://example.test/actions/transfer-asset"}
    c1 = {"id": "c1", "party": alice, "action": pay_action, "subjects": (subject,)}
    c2 = {"id": "c2", "party": alice, "action": transfer_action, "subjects": (subject,)}
    rail_a = "https://example.test/settlement/rail-a"
    rail_b = "https://example.test/settlement/rail-b"
    rail_x = "https://example.test/settlement/rail-x"
    usd_100 = {"kind": "monetary", "amount": {"coefficient": 100, "scale": 0}, "currency_code": "USD"}
    token_1 = {
        "kind": "semantic",
        "semantic": "https://example.test/value/token-transfer",
        "value": {"asset": "urn:example:asset:1", "units": 1},
    }

    def agreement_with(preferences=()) -> RecordV1:
        content = {
            "version": 1,
            "parties": sort_set((alice, bob)),
            "subjects": (subject,),
            "actions": sort_set((pay_action, transfer_action)),
            "terms": {},
            "commitments": (c1, c2),
        }
        if preferences:
            content["settlement_preferences"] = sort_set(preferences)
        return market_record(TYPE_AGREEMENT, content)

    agreement = agreement_with()
    agreement_required_a = agreement_with(({"method": rail_a, "mode": "required"},))
    agreement_excluded_a = agreement_with(({"method": rail_a, "mode": "excluded"},))
    agreement_parameterized_a = agreement_with(({
        "method": rail_a,
        "mode": "required",
        "parameters": {"https://example.test/settlement/network": "testnet"},
    },))
    agreement_parameterized_excluded_a = agreement_with(({
        "method": rail_a,
        "mode": "excluded",
        "parameters": {"https://example.test/settlement/network": "testnet"},
    },))
    agreement_excluded_and_parameterized_a = agreement_with((
        {"method": rail_a, "mode": "excluded"},
        {
            "method": rail_a,
            "mode": "excluded",
            "parameters": {"https://example.test/settlement/network": "testnet"},
        },
    ))
    agreement_required_and_excluded_a = agreement_with((
        {"method": rail_a, "mode": "required"},
        {"method": rail_a, "mode": "excluded"},
    ))
    agreement_required_a_b = agreement_with((
        {"method": rail_a, "mode": "required"},
        {"method": rail_b, "mode": "required"},
    ))

    def cref(target_agreement: RecordV1, commitment_id: str) -> dict:
        return {"record": record_ref(target_agreement).to_value(), "id": commitment_id}

    def outcome(method: str, *, extent=None, value=None, reference=None) -> dict:
        details = {"method": method}
        if extent is not None:
            details["extent"] = extent
        if value is not None:
            details["value"] = value
        if reference is not None:
            details["reference"] = reference
        return {"type": OUTCOME_SETTLEMENT_EVIDENCE, "details": details}

    def event(
        target_agreement: RecordV1,
        event_type: str,
        commitment_id: str,
        issuer: dict,
        *,
        outcome_value: dict | None = None,
        related_records: tuple[dict, ...] = (),
        extensions: dict | None = None,
        critical: tuple[str, ...] = (),
    ) -> RecordV1:
        content = {
            "version": 1,
            "issuer": issuer,
            "event": event_type,
            "commitment_refs": (cref(target_agreement, commitment_id),),
        }
        if outcome_value is not None:
            content["outcome"] = outcome_value
        if related_records:
            content["related_records"] = sort_set(related_records)
        if extensions is not None:
            content["extensions"] = extensions
        if critical:
            content["critical"] = critical
        return market_record(TYPE_EVENT, content)

    attempt = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice, outcome_value=outcome(rail_a, value=usd_100, reference="attempt-1"))
    partial = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_PARTIAL, value=usd_100, reference="partial-1"))
    complete_a = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="complete-a"))
    complete_b = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_b, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="complete-b"))
    failure = event(agreement, EVENT_SETTLEMENT_FAILURE, "c1", bob, outcome_value=outcome(rail_a, reference="failure-1"))
    hold = event(agreement, EVENT_ESCROW_HOLD, "c1", bob, outcome_value=outcome(rail_a, value=usd_100, reference="hold-1"))
    release = event(
        agreement,
        EVENT_ESCROW_RELEASE,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="release-1"),
        related_records=(record_ref(hold).to_value(),),
    )
    reversal_full = event(
        agreement,
        EVENT_SETTLEMENT_REVERSAL,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="reversal-full"),
        related_records=(record_ref(complete_a).to_value(),),
    )
    reversal_partial = event(
        agreement,
        EVENT_SETTLEMENT_REVERSAL,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_PARTIAL, value=usd_100, reference="reversal-partial"),
        related_records=(record_ref(complete_a).to_value(),),
    )
    refund_full = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="refund-full"),
        related_records=(record_ref(complete_a).to_value(),),
    )
    refund_partial = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_PARTIAL, value=usd_100, reference="refund-partial"),
        related_records=(record_ref(complete_a).to_value(),),
    )
    refund_full_of_partial = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100, reference="refund-full-of-partial"),
        related_records=(record_ref(partial).to_value(),),
    )
    asset_complete = event(
        agreement,
        EVENT_ASSET_TRANSFER,
        "c2",
        bob,
        outcome_value=outcome(rail_b, extent=EXTENT_CLAIMED_COMPLETE, value=token_1, reference="asset-1"),
    )
    nonsettlement = event(agreement, f"{BASE}/event/commitment-acceptance", "c1", bob)
    critical_uri = "https://example.test/extensions/settlement-finality"
    agreement_critical_content = dict(agreement.content)
    agreement_critical_content["extensions"] = {critical_uri: True}
    agreement_critical_content["critical"] = (critical_uri,)
    agreement_critical = market_record(TYPE_AGREEMENT, agreement_critical_content)
    agreement_critical_complete = event(
        agreement_critical, EVENT_SETTLEMENT_COMPLETION, "c1", bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100),
    )
    complete_critical = event(
        agreement,
        EVENT_SETTLEMENT_COMPLETION,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100),
        extensions={critical_uri: True},
        critical=(critical_uri,),
    )
    required_a_complete = event(agreement_required_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    required_a_wrong = event(agreement_required_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_b, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    excluded_a_complete = event(agreement_excluded_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    parameterized_a_complete = event(agreement_parameterized_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    parameterized_excluded_a_complete = event(agreement_parameterized_excluded_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    excluded_and_parameterized_a_complete = event(agreement_excluded_and_parameterized_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    required_and_excluded_a_complete = event(agreement_required_and_excluded_a, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    required_a_b_complete_a = event(agreement_required_a_b, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100))
    missing_target_refund = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100),
        related_records=(record_ref(required_a_complete).to_value(),),
    )
    dispute = relationship_record(
        "disputes",
        subject=record_ref(failure),
        objects=(record_ref(complete_a),),
    )

    cases: list[dict] = []
    result_keys = (
        "conclusion",
        "accepted_event_count",
        "duplicate_event_count",
        "ignored_nonsettlement_event_count",
        "rejected_by_method_count",
        "rejected_by_preference_count",
        "preference_indeterminate_count",
        "attempts",
        "failures",
        "partial_settlement_assertions",
        "complete_settlement_assertions",
        "escrow_holds",
        "escrow_releases",
        "asset_transfer_assertions",
        "complete_reversals",
        "partial_reversals",
        "complete_refunds",
        "partial_refunds",
    )
    result_keys += (
        "rail_methods",
        "multi_rail",
        "causal_target_missing_count",
        "causal_target_wrong_type_count",
        "unsupported_critical_semantics",
        "disputed_event_ids",
        "universal_truth",
        "cross_rail_arithmetic_performed",
        "fulfillment_evaluated",
        "ownership_or_title_evaluated",
        "legal_finality_evaluated",
    )

    def add_case(
        case_id: str,
        events: tuple[SettlementEvidence, ...],
        *,
        target_agreement: RecordV1 = agreement,
        commitment_id: str = "c1",
        understood: tuple[str, ...] = (),
        relationships: tuple[RelationshipEvidence, ...] = (),
    ) -> None:
        result = evaluate_commitment_settlement(
            target_agreement,
            commitment_id,
            events,
            method=SETTLEMENT_EVALUATION_CORE,
            understood_critical=understood,
            disputes=relationships,
        )
        cases.append({
            "id": case_id,
            "kind": "settlement",
            "agreement": projected_record(target_agreement),
            "commitment_id": commitment_id,
            "events": [event_item(item.record, item.attribution_accepted, item.authority_accepted, item.rail_evidence_accepted) for item in events],
            "method": SETTLEMENT_EVALUATION_CORE,
            "understood_critical": list(understood),
            "relationships": [relationship_item(item.record, item.accepted_for_method) for item in relationships],
            "expected": expected_subset(result, *result_keys),
        })

    SE = SettlementEvidence
    RE = RelationshipEvidence
    add_case("no-settlement-evidence", ())
    add_case("settlement-attempt", (SE(attempt, True, True, True),))
    add_case("settlement-failure", (SE(failure, True, True, True),))
    add_case("partial-settlement", (SE(partial, True, True, True),))
    add_case("complete-settlement", (SE(complete_a, True, True, True),))
    add_case("asset-transfer-complete-is-method-relative-settlement", (SE(asset_complete, True, True, True),), commitment_id="c2")
    add_case("escrow-hold", (SE(hold, True, True, True),))
    add_case("escrow-release-with-hold-does-not-self-settle", (SE(hold, True, True, True), SE(release, True, True, True)))
    add_case("complete-settlement-full-reversal", (SE(complete_a, True, True, True), SE(reversal_full, True, True, True)))
    add_case("complete-settlement-partial-reversal", (SE(complete_a, True, True, True), SE(reversal_partial, True, True, True)))
    add_case("complete-settlement-full-refund", (SE(complete_a, True, True, True), SE(refund_full, True, True, True)))
    add_case("complete-settlement-partial-refund", (SE(complete_a, True, True, True), SE(refund_partial, True, True, True)))
    add_case("partial-settlement-full-refund", (SE(partial, True, True, True), SE(refund_full_of_partial, True, True, True)))
    add_case("complete-and-failure-conflict", (SE(complete_a, True, True, True), SE(failure, True, True, True)))
    add_case("multi-rail-evidence-preserved", (SE(complete_a, True, True, True), SE(complete_b, True, True, True)))
    add_case("duplicate-settlement-evidence-deduplicated", (SE(complete_a, True, True, True), SE(complete_a, True, True, True)))
    add_case("duplicate-nonsettlement-evidence-deduplicated", (SE(nonsettlement, True, True, True), SE(nonsettlement, True, True, True)))
    add_case("unaccepted-authority-does-not-count", (SE(complete_a, True, False, True),))
    add_case("unverified-rail-evidence-does-not-count", (SE(complete_a, True, True, False),))
    add_case(
        "accepted-dispute-prevents-positive-settlement",
        (SE(complete_a, True, True, True),),
        relationships=(RE(dispute, True),),
    )
    add_case("unknown-critical-settlement-semantics", (SE(complete_critical, True, True, True),))
    add_case(
        "understood-critical-settlement-semantics",
        (SE(complete_critical, True, True, True),),
        understood=(critical_uri,),
    )
    add_case(
        "required-settlement-method-matches",
        (SE(required_a_complete, True, True, True),),
        target_agreement=agreement_required_a,
    )
    add_case(
        "required-settlement-method-mismatch",
        (SE(required_a_wrong, True, True, True),),
        target_agreement=agreement_required_a,
    )
    add_case(
        "excluded-settlement-method-rejected",
        (SE(excluded_a_complete, True, True, True),),
        target_agreement=agreement_excluded_a,
    )
    add_case(
        "parameterized-required-preference-is-indeterminate",
        (SE(parameterized_a_complete, True, True, True),),
        target_agreement=agreement_parameterized_a,
    )
    add_case(
        "parameterized-excluded-preference-is-indeterminate",
        (SE(parameterized_excluded_a_complete, True, True, True),),
        target_agreement=agreement_parameterized_excluded_a,
    )
    add_case(
        "unconditional-exclusion-overrides-parameterized-exclusion",
        (SE(excluded_and_parameterized_a_complete, True, True, True),),
        target_agreement=agreement_excluded_and_parameterized_a,
    )
    add_case(
        "exclusion-overrides-required-same-method",
        (SE(required_and_excluded_a_complete, True, True, True),),
        target_agreement=agreement_required_and_excluded_a,
    )
    add_case(
        "multiple-required-methods-form-admissible-set",
        (SE(required_a_b_complete_a, True, True, True),),
        target_agreement=agreement_required_a_b,
    )
    add_case("causal-target-not-supplied-is-indeterminate", (SE(missing_target_refund, True, True, True),))
    negative_cases: list[dict] = []

    def negative(case_id: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, **payload, "expected_error": code})

    def settlement_payload(
        events: list[dict],
        *,
        agreement_record: RecordV1 = agreement,
        commitment_id: str = "c1",
        method: str = SETTLEMENT_EVALUATION_CORE,
        understood: list[str] | None = None,
        relationships: list[dict] | None = None,
        max_evidence: int | None = None,
    ) -> dict:
        payload = {
            "kind": "settlement",
            "agreement": projected_record(agreement_record),
            "commitment_id": commitment_id,
            "events": events,
            "method": method,
            "understood_critical": understood or [],
            "relationships": relationships or [],
        }
        if max_evidence is not None:
            payload["max_evidence"] = max_evidence
        return payload
    intent = market_record(
        TYPE_INTENT,
        {"version": 1, "issuer": alice, "subjects": (subject,), "action": pay_action, "terms": {}},
    )
    wrong_target = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c2", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=token_1))
    multi_target = market_record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": bob,
            "event": EVENT_SETTLEMENT_COMPLETION,
            "commitment_refs": sort_set((cref(agreement, "c1"), cref(agreement, "c2"))),
            "outcome": outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE, value=usd_100),
        },
    )
    missing_outcome = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice)
    bad_method = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice, outcome_value=outcome("not-a-uri"))
    bad_extent = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a, extent="broken"))
    missing_extent = event(agreement, EVENT_SETTLEMENT_COMPLETION, "c1", bob, outcome_value=outcome(rail_a))
    forbidden_extent = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice, outcome_value=outcome(rail_a, extent=EXTENT_PARTIAL))
    bad_details = event(
        agreement,
        EVENT_SETTLEMENT_ATTEMPT,
        "c1",
        alice,
        outcome_value={"type": OUTCOME_SETTLEMENT_EVIDENCE, "details": {"method": rail_a, "extra": 1}},
    )
    bad_value = event(
        agreement,
        EVENT_SETTLEMENT_COMPLETION,
        "c1",
        bob,
        outcome_value=outcome(
            rail_a,
            extent=EXTENT_CLAIMED_COMPLETE,
            value={"kind": "monetary", "amount": {"coefficient": 1, "scale": 0}, "currency_code": "usd"},
        ),
    )
    empty_reference = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice, outcome_value=outcome(rail_a, reference=""))
    long_reference = event(agreement, EVENT_SETTLEMENT_ATTEMPT, "c1", alice, outcome_value=outcome(rail_a, reference="x" * 1025))
    refund_no_causal = event(agreement, EVENT_SETTLEMENT_REFUND, "c1", bob, outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE))
    refund_multi_causal = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE),
        related_records=sort_set((record_ref(complete_a).to_value(), record_ref(partial).to_value())),
    )
    wrong_causal_refund = event(
        agreement,
        EVENT_SETTLEMENT_REFUND,
        "c1",
        bob,
        outcome_value=outcome(rail_a, extent=EXTENT_CLAIMED_COMPLETE),
        related_records=(record_ref(attempt).to_value(),),
    )
    unsupported_event = event(agreement, f"{BASE}/event/not-a-settlement-event", "c1", bob)
    add_case(
        "causal-target-wrong-type-is-indeterminate",
        (SE(attempt, True, True, True), SE(wrong_causal_refund, True, True, True)),
    )

    negative("commitment-not-found", settlement_payload([], commitment_id="missing"), "COMMITMENT_NOT_FOUND")
    negative("agreement-required", settlement_payload([], agreement_record=intent), "AGREEMENT_REQUIRED")
    negative("wrong-target-commitment", settlement_payload([event_item(wrong_target)]), "SETTLEMENT_EVENT_TARGET")
    negative("duplicate-evidence-context-conflict", settlement_payload([
        event_item(complete_a, True, True, True),
        event_item(complete_a, True, False, True),
    ]), "DUPLICATE_EVIDENCE_CONTEXT_CONFLICT")
    negative("settlement-event-multiple-targets", settlement_payload([event_item(multi_target)]), "SETTLEMENT_EVENT_TARGET")
    negative("settlement-outcome-required", settlement_payload([event_item(missing_outcome)]), "SETTLEMENT_OUTCOME_REQUIRED")
    negative("invalid-settlement-details", settlement_payload([event_item(bad_details)]), "INVALID_SETTLEMENT_DETAILS")
    negative("invalid-rail-method-uri", settlement_payload([event_item(bad_method)]), "INVALID_URI")
    negative("invalid-settlement-extent", settlement_payload([event_item(bad_extent)]), "INVALID_SETTLEMENT_EXTENT")
    negative("settlement-extent-required", settlement_payload([event_item(missing_extent)]), "SETTLEMENT_EXTENT_REQUIRED")
    negative("settlement-extent-forbidden", settlement_payload([event_item(forbidden_extent)]), "SETTLEMENT_EXTENT_FORBIDDEN")
    negative("invalid-settlement-value", settlement_payload([event_item(bad_value)]), "INVALID_CURRENCY")
    negative("empty-settlement-reference", settlement_payload([event_item(empty_reference)]), "INVALID_SETTLEMENT_REFERENCE")
    negative("oversized-settlement-reference", settlement_payload([event_item(long_reference)]), "INVALID_SETTLEMENT_REFERENCE")
    negative("refund-causal-target-required", settlement_payload([event_item(refund_no_causal)]), "SETTLEMENT_CAUSAL_TARGET")
    negative("refund-causal-target-cardinality", settlement_payload([event_item(refund_multi_causal)]), "SETTLEMENT_CAUSAL_TARGET")
    negative("invalid-evaluation-method-uri", settlement_payload([event_item(complete_a)], method="not-a-uri"), "INVALID_URI")
    negative(
        "unsupported-evaluation-method",
        settlement_payload([event_item(complete_a)], method="https://example.test/settlement/evaluation/other"),
        "UNSUPPORTED_SETTLEMENT_EVALUATION_METHOD",
    )
    negative(
        "invalid-settlement-acceptance-flags",
        settlement_payload([{
            "record": projected_record(complete_a),
            "attribution_accepted": "yes",
            "authority_accepted": True,
            "rail_evidence_accepted": True,
        }]),
        "INVALID_EVIDENCE_ACCEPTANCE",
    )
    negative(
        "settlement-evidence-resource-limit",
        settlement_payload([event_item(complete_a), event_item(failure)], max_evidence=1),
        "RESOURCE_LIMIT_EXCEEDED",
    )
    negative(
        "invalid-understood-critical-uri",
        settlement_payload([event_item(complete_a)], understood=["not-a-uri"]),
        "INVALID_URI",
    )
    negative("market-event-required", settlement_payload([event_item(intent)]), "MARKET_EVENT_REQUIRED")
    negative(
        "invalid-dispute-relationship",
        settlement_payload([event_item(complete_a)], relationships=[relationship_item(complete_a, True)]),
        "INVALID_OLP_RELATIONSHIP",
    )
    negative(
        "invalid-dispute-acceptance-flag",
        settlement_payload(
            [event_item(complete_a)],
            relationships=[{"record": projected_record(dispute), "accepted_for_method": "yes"}],
        ),
        "INVALID_EVIDENCE_ACCEPTANCE",
    )
    negative(
        "unsupported-event-is-not-core-settlement-event",
        {
            "kind": "event_validation",
            "agreement": projected_record(agreement),
            "commitment_id": "c1",
            "event": projected_record(unsupported_event),
        },
        "UNSUPPORTED_SETTLEMENT_EVENT",
    )

    return {
        "format": "marketplace-settlement-interfaces-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "cases": cases,
        "negative_cases": negative_cases,
        "identities": {
            "agreement": record_identity_text(agreement),
            "attempt": record_identity_text(attempt),
            "complete": record_identity_text(complete_a),
            "reversal": record_identity_text(reversal_full),
        },
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    for key, value in data["identities"].items():
        print(key, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
