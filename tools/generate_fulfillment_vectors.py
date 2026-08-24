"""Generate Marketplace fulfillment and performance v1 conformance vectors."""
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
from marketplace_fulfillment_v1 import (
    EVENT_COMMITMENT_ACCEPTANCE,
    EVENT_COMMITMENT_COMPLETION,
    EVENT_COMMITMENT_DELIVERY,
    EVENT_COMMITMENT_FAILURE,
    EVENT_COMMITMENT_INSPECTION,
    EVENT_COMMITMENT_PERFORMANCE,
    EVENT_COMMITMENT_REJECTION,
    FULFILLMENT_METHOD_CORE,
    OUTCOME_CRITERION_OBSERVATION,
    OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
    OUTCOME_PERFORMANCE_PARTIAL,
    EventEvidence,
    RelationshipEvidence,
    evaluate_commitment_fulfillment,
    validate_fulfillment_event,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "fulfillment-performance-v1.json"


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
    value = {
        "envelope_version": record.envelope_version,
        "type": record.type,
        "content": record.content,
    }
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


def event_item(record: RecordV1, attribution: bool = True, authority: bool = True) -> dict:
    return {
        "record": projected_record(record),
        "attribution_accepted": attribution,
        "authority_accepted": authority,
    }


def relationship_item(record: RecordV1, accepted: bool = True) -> dict:
    return {
        "record": projected_record(record),
        "accepted_for_method": accepted,
    }


def build() -> dict:
    alice = {"principal": "did:example:alice", "role": "https://example.test/roles/requester"}
    bob = {"principal": "did:example:bob", "role": "https://example.test/roles/provider"}
    subject = {"uri": "urn:example:software-issue:42"}
    action = {"id": "https://example.test/actions/fix"}
    criterion_tests = {
        "criterion": "https://example.test/acceptance/tests-pass",
        "mode": "required",
        "parameters": {"https://example.test/acceptance/minimum": 100},
    }
    c1 = {"id": "c1", "party": bob, "action": action, "subjects": (subject,)}
    c2 = {
        "id": "c2",
        "party": bob,
        "action": action,
        "subjects": (subject,),
        "acceptance_criteria": (criterion_tests,),
    }

    agreement = market_record(
        TYPE_AGREEMENT,
        {
            "version": 1,
            "parties": sort_set((alice, bob)),
            "subjects": (subject,),
            "actions": (action,),
            "terms": {},
            "commitments": (c1, c2),
        },
    )

    def cref(commitment_id: str) -> dict:
        return {"record": record_ref(agreement).to_value(), "id": commitment_id}

    def event(
        event_type: str,
        commitment_id: str,
        issuer: dict,
        *,
        outcome: dict | None = None,
        extensions: dict | None = None,
        critical: tuple[str, ...] = (),
    ) -> RecordV1:
        content = {
            "version": 1,
            "issuer": issuer,
            "event": event_type,
            "commitment_refs": (cref(commitment_id),),
        }
        if outcome is not None:
            content["outcome"] = outcome
        if extensions is not None:
            content["extensions"] = extensions
        if critical:
            content["critical"] = critical
        return market_record(TYPE_EVENT, content)

    partial = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c1",
        bob,
        outcome={"type": OUTCOME_PERFORMANCE_PARTIAL, "details": {"progress": 50}},
    )
    delivery = event(
        EVENT_COMMITMENT_DELIVERY,
        "c1",
        bob,
        outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
    )
    complete = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c1",
        bob,
        outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
    )
    accept = event(EVENT_COMMITMENT_ACCEPTANCE, "c1", alice)
    reject = event(EVENT_COMMITMENT_REJECTION, "c1", alice)
    completion = event(EVENT_COMMITMENT_COMPLETION, "c1", bob)
    failure = event(EVENT_COMMITMENT_FAILURE, "c1", bob)

    complete_c2 = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c2",
        bob,
        outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
    )
    accept_c2 = event(EVENT_COMMITMENT_ACCEPTANCE, "c2", alice)

    def inspection(status: str, criterion: dict = criterion_tests) -> RecordV1:
        return event(
            EVENT_COMMITMENT_INSPECTION,
            "c2",
            alice,
            outcome={
                "type": OUTCOME_CRITERION_OBSERVATION,
                "details": {"criterion": criterion, "status": status},
            },
        )

    inspect_ok = inspection("SATISFIED")
    inspect_no = inspection("UNSATISFIED")
    inspect_unknown = inspection("UNKNOWN")
    critical_uri = "https://example.test/extensions/fulfillment-semantics"
    complete_critical = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c1",
        bob,
        outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
        extensions={critical_uri: True},
        critical=(critical_uri,),
    )
    settlement = event(f"{BASE}/event/settlement-completion", "c1", alice)
    dispute = relationship_record(
        "disputes",
        subject=record_ref(reject),
        objects=(record_ref(complete),),
    )

    cases: list[dict] = []
    result_keys = (
        "conclusion",
        "accepted_event_count",
        "ignored_nonfulfillment_event_count",
        "rejected_by_method_count",
        "partial_performance",
        "complete_performance",
        "acceptance_assertions",
        "rejection_assertions",
        "completion_assertions",
        "failure_assertions",
        "delivery_assertions",
        "duplicate_event_count",
    )
    result_keys += (
        "required_criteria",
        "criterion_satisfied",
        "criterion_unsatisfied",
        "criterion_unknown",
        "criterion_conflicts",
        "unsupported_critical_semantics",
        "disputed_event_ids",
        "universal_truth",
        "payment_or_settlement_evaluated",
    )

    def add_case(
        case_id: str,
        events: tuple[EventEvidence, ...],
        *,
        commitment_id: str = "c1",
        require_acceptance: bool = True,
        understood: tuple[str, ...] = (),
        relationships: tuple[RelationshipEvidence, ...] = (),
    ) -> None:
        result = evaluate_commitment_fulfillment(
            agreement,
            commitment_id,
            events,
            method=FULFILLMENT_METHOD_CORE,
            require_acceptance=require_acceptance,
            understood_critical=understood,
            disputes=relationships,
        )
        cases.append(
            {
                "id": case_id,
                "kind": "fulfillment",
                "agreement": projected_record(agreement),
                "commitment_id": commitment_id,
                "events": [
                    event_item(item.record, item.attribution_accepted, item.authority_accepted)
                    for item in events
                ],
                "method": FULFILLMENT_METHOD_CORE,
                "require_acceptance": require_acceptance,
                "understood_critical": list(understood),
                "relationships": [
                    relationship_item(item.record, item.accepted_for_method)
                    for item in relationships
                ],
                "expected": expected_subset(result, *result_keys),
            }
        )

    EE = EventEvidence
    RE = RelationshipEvidence
    add_case("no-evidence-is-indeterminate", ())
    add_case("partial-performance", (EE(partial, True, True),))
    add_case("partial-even-with-acceptance", (EE(partial, True, True), EE(accept, True, True)))
    add_case("completion-assertion-alone", (EE(completion, True, True),))
    add_case("acceptance-alone", (EE(accept, True, True),))
    add_case("complete-performance-awaits-acceptance", (EE(complete, True, True),))
    add_case("delivery-awaits-acceptance", (EE(delivery, True, True),))
    add_case("delivery-with-acceptance", (EE(delivery, True, True), EE(accept, True, True)))
    add_case("duplicate-evidence-deduplicated", (EE(complete, True, True), EE(complete, True, True), EE(accept, True, True)))
    add_case(
        "complete-performance-with-acceptance",
        (EE(complete, True, True), EE(accept, True, True)),
    )
    add_case(
        "complete-performance-method-without-acceptance-requirement",
        (EE(complete, True, True),),
        require_acceptance=False,
    )
    add_case("accepted-failure-assertion", (EE(failure, True, True),))
    add_case(
        "acceptance-rejection-conflict",
        (EE(complete, True, True), EE(accept, True, True), EE(reject, True, True)),
    )
    add_case(
        "completion-failure-conflict",
        (EE(complete, True, True), EE(completion, True, True), EE(failure, True, True)),
    )
    add_case(
        "unaccepted-performance-does-not-count",
        (EE(complete, True, False), EE(accept, True, True)),
    )
    add_case(
        "settlement-event-is-ignored-for-fulfillment",
        (EE(complete, True, True), EE(accept, True, True), EE(settlement, True, True)),
    )
    add_case(
        "duplicate-settlement-evidence-deduplicated",
        (EE(complete, True, True), EE(accept, True, True), EE(settlement, True, True), EE(settlement, True, True)),
    )
    add_case(
        "accepted-dispute-prevents-positive-conclusion",
        (EE(complete, True, True), EE(accept, True, True)),
        relationships=(RE(dispute, True),),
    )
    add_case(
        "required-criterion-missing",
        (EE(complete_c2, True, True), EE(accept_c2, True, True)),
        commitment_id="c2",
    )
    add_case(
        "required-criterion-satisfied",
        (EE(complete_c2, True, True), EE(accept_c2, True, True), EE(inspect_ok, True, True)),
        commitment_id="c2",
    )
    add_case(
        "required-criterion-unsatisfied",
        (EE(complete_c2, True, True), EE(accept_c2, True, True), EE(inspect_no, True, True)),
        commitment_id="c2",
    )
    add_case(
        "required-criterion-unknown",
        (EE(complete_c2, True, True), EE(accept_c2, True, True), EE(inspect_unknown, True, True)),
        commitment_id="c2",
    )
    add_case(
        "required-criterion-conflict",
        (EE(complete_c2, True, True), EE(accept_c2, True, True), EE(inspect_ok, True, True), EE(inspect_no, True, True)),
        commitment_id="c2",
    )
    add_case(
        "unknown-critical-fulfillment-semantics",
        (EE(complete_critical, True, True), EE(accept, True, True)),
    )
    add_case(
        "understood-critical-fulfillment-semantics",
        (EE(complete_critical, True, True), EE(accept, True, True)),
        understood=(critical_uri,),
    )

    negative_cases: list[dict] = []
    def negative(case_id: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, **payload, "expected_error": code})

    def fulfillment_payload(
        events: list[dict],
        *,
        agreement_record: RecordV1 = agreement,
        commitment_id: str = "c1",
        method: str = FULFILLMENT_METHOD_CORE,
        require_acceptance: object = True,
        understood: list[str] | None = None,
        relationships: list[dict] | None = None,
        max_evidence: int | None = None,
    ) -> dict:
        payload = {
            "kind": "fulfillment",
            "agreement": projected_record(agreement_record),
            "commitment_id": commitment_id,
            "events": events,
            "method": method,
            "require_acceptance": require_acceptance,
            "understood_critical": understood or [],
            "relationships": relationships or [],
        }
        if max_evidence is not None:
            payload["max_evidence"] = max_evidence
        return payload

    wrong_issuer = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c1",
        alice,
        outcome={"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
    )
    missing_extent = event(EVENT_COMMITMENT_PERFORMANCE, "c1", bob)
    bad_extent = event(
        EVENT_COMMITMENT_PERFORMANCE,
        "c1",
        bob,
        outcome={"type": "https://example.test/outcome/not-an-extent"},
    )
    inspection_no_outcome = event(EVENT_COMMITMENT_INSPECTION, "c2", alice)
    other_criterion = {
        "criterion": "https://example.test/acceptance/other",
        "mode": "required",
    }
    inspection_other = inspection("SATISFIED", other_criterion)
    inspection_bad_status = inspection("BROKEN")
    multi_target = market_record(
        TYPE_EVENT,
        {
            "version": 1,
            "issuer": bob,
            "event": EVENT_COMMITMENT_PERFORMANCE,
            "commitment_refs": sort_set((cref("c1"), cref("c2"))),
            "outcome": {"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
        },
    )

    intent = market_record(
        TYPE_INTENT,
        {
            "version": 1,
            "issuer": alice,
            "subjects": (subject,),
            "action": action,
            "terms": {},
        },
    )
    negative(
        "commitment-not-found",
        fulfillment_payload([], commitment_id="missing"),
        "COMMITMENT_NOT_FOUND",
    )
    negative(
        "agreement-required",
        fulfillment_payload([], agreement_record=intent),
        "AGREEMENT_REQUIRED",
    )
    negative(
        "wrong-target-commitment",
        fulfillment_payload([event_item(complete_c2)]),
        "FULFILLMENT_EVENT_TARGET",
    )
    negative(
        "performance-performer-mismatch",
        fulfillment_payload([event_item(wrong_issuer)]),
        "PERFORMER_MISMATCH",
    )
    negative(
        "duplicate-evidence-context-conflict",
        fulfillment_payload([event_item(complete, True, True), event_item(complete, True, False)]),
        "DUPLICATE_EVIDENCE_CONTEXT_CONFLICT",
    )
    negative(
        "performance-extent-required",
        fulfillment_payload([event_item(missing_extent)]),
        "PERFORMANCE_EXTENT_REQUIRED",
    )
    negative(
        "performance-extent-invalid",
        fulfillment_payload([event_item(bad_extent)]),
        "PERFORMANCE_EXTENT_REQUIRED",
    )
    negative(
        "inspection-outcome-required",
        fulfillment_payload([event_item(inspection_no_outcome)], commitment_id="c2"),
        "INSPECTION_OUTCOME_REQUIRED",
    )
    negative(
        "inspection-criterion-not-found",
        fulfillment_payload([event_item(inspection_other)], commitment_id="c2"),
        "CRITERION_NOT_FOUND",
    )
    negative(
        "inspection-invalid-status",
        fulfillment_payload([event_item(inspection_bad_status)], commitment_id="c2"),
        "INVALID_CRITERION_STATUS",
    )
    negative(
        "fulfillment-event-multiple-targets",
        fulfillment_payload([event_item(multi_target)]),
        "FULFILLMENT_EVENT_TARGET",
    )
    negative(
        "invalid-fulfillment-method-uri",
        fulfillment_payload([event_item(complete)], method="not-a-uri"),
        "INVALID_URI",
    )
    negative(
        "unsupported-fulfillment-method",
        fulfillment_payload([event_item(complete)], method="https://example.test/fulfillment/other-v1"),
        "UNSUPPORTED_FULFILLMENT_METHOD",
    )
    negative(
        "invalid-require-acceptance",
        fulfillment_payload([event_item(complete)], require_acceptance="yes"),
        "INVALID_METHOD_CONFIGURATION",
    )
    negative(
        "invalid-event-acceptance-flags",
        fulfillment_payload([
            {"record": projected_record(complete), "attribution_accepted": "yes", "authority_accepted": True}
        ]),
        "INVALID_EVIDENCE_ACCEPTANCE",
    )
    negative(
        "fulfillment-evidence-resource-limit",
        fulfillment_payload([event_item(complete), event_item(accept)], max_evidence=1),
        "RESOURCE_LIMIT_EXCEEDED",
    )
    negative(
        "invalid-understood-critical-uri",
        fulfillment_payload([event_item(complete)], understood=["not-a-uri"]),
        "INVALID_URI",
    )
    negative(
        "market-event-required",
        fulfillment_payload([event_item(intent)]),
        "MARKET_EVENT_REQUIRED",
    )
    negative(
        "invalid-dispute-relationship",
        fulfillment_payload(
            [event_item(complete), event_item(accept)],
            relationships=[relationship_item(accept, True)],
        ),
        "INVALID_OLP_RELATIONSHIP",
    )
    bad_observation_shape = event(
        EVENT_COMMITMENT_INSPECTION,
        "c2",
        alice,
        outcome={
            "type": OUTCOME_CRITERION_OBSERVATION,
            "details": {"status": "SATISFIED"},
        },
    )
    negative(
        "invalid-criterion-observation-shape",
        fulfillment_payload([event_item(bad_observation_shape)], commitment_id="c2"),
        "INVALID_CRITERION_OBSERVATION",
    )
    negative(
        "invalid-dispute-acceptance-flag",
        fulfillment_payload(
            [event_item(complete), event_item(accept)],
            relationships=[{"record": projected_record(dispute), "accepted_for_method": "yes"}],
        ),
        "INVALID_EVIDENCE_ACCEPTANCE",
    )
    negative(
        "unsupported-event-is-not-core-fulfillment-event",
        {
            "kind": "event_validation",
            "agreement": projected_record(agreement),
            "commitment_id": "c1",
            "event": projected_record(settlement),
        },
        "UNSUPPORTED_FULFILLMENT_EVENT",
    )

    return {
        "format": "marketplace-fulfillment-performance-v1-conformance-vectors",
        "marketplace_semantic_base": BASE,
        "olp_reference_source_commit": olp_commit(),
        "note": "record/ref/value fields use OLP implementation-neutral conformance projection; this JSON file is not a Marketplace wire format",
        "record_identities": {
            "agreement": record_identity_text(agreement),
            "partial": record_identity_text(partial),
            "complete": record_identity_text(complete),
            "accept": record_identity_text(accept),
            "reject": record_identity_text(reject),
        },
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    print(f"positive/evaluation cases: {len(data['cases'])}")
    print(f"negative cases: {len(data['negative_cases'])}")
    for name, identity in data["record_identities"].items():
        print(name, identity)


if __name__ == "__main__":
    main()
