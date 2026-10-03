from __future__ import annotations

import unittest

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref

from marketplace.reference.fulfillment_completion_evidence_v1 import (
    EVENT_COMMITMENT_ACCEPTANCE,
    EVENT_COMMITMENT_COMPLETION,
    EVENT_COMMITMENT_PERFORMANCE,
    OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionEvidenceError,
    build_claimed_complete_performance_event,
    build_commitment_acceptance_event,
    build_commitment_completion_event,
    fulfillment_event_target,
)
from marketplace.reference.record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    validate_market_record,
)


SELLER = "did:example:seller"
BUYER = "did:example:buyer"
AUDITOR = "did:example:auditor"
COMMITMENT_ID = "seller-delivery"
ACTION_SELL = f"{BASE}/action/sell"
SUBJECT = {"uri": "urn:example:item:moon-widget"}


def _canonical(values):
    return tuple(sorted(values, key=olp_encode))


def agreement() -> RecordV1:
    seller = {"principal": SELLER}
    buyer = {"principal": BUYER}
    record = RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_AGREEMENT,
            "content": {
                "version": 1,
                "parties": list(_canonical((seller, buyer))),
                "subjects": [SUBJECT],
                "actions": [{"id": ACTION_SELL}],
                "terms": {},
                "commitments": [
                    {
                        "id": COMMITMENT_ID,
                        "party": seller,
                        "action": {"id": ACTION_SELL},
                        "subjects": [SUBJECT],
                    }
                ],
            },
            "profiles": [CORE_PROFILE],
        }
    )
    validate_market_record(record)
    return record


class M177AReferenceFulfillmentCompletionEvidenceTests(unittest.TestCase):
    def test_profile_and_constants_are_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_EVIDENCE_V1",
        )
        self.assertEqual(
            EVENT_COMMITMENT_PERFORMANCE,
            f"{BASE}/event/commitment-performance",
        )
        self.assertEqual(
            EVENT_COMMITMENT_ACCEPTANCE,
            f"{BASE}/event/commitment-acceptance",
        )
        self.assertEqual(
            EVENT_COMMITMENT_COMPLETION,
            f"{BASE}/event/commitment-completion-assertion",
        )
        self.assertEqual(
            OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
            f"{BASE}/outcome/performance-claimed-complete",
        )

    def test_claimed_complete_performance_is_exact_and_bound_to_agreement(self) -> None:
        source = agreement()
        event = build_claimed_complete_performance_event(
            agreement=source,
            commitment_id=COMMITMENT_ID,
            issuer=SELLER,
        )

        self.assertIs(type(event), RecordV1)
        validate_market_record(event)
        self.assertEqual(event.type, TYPE_EVENT)
        self.assertEqual(event.profiles, (CORE_PROFILE,))
        self.assertEqual(
            set(event.content),
            {"version", "issuer", "event", "commitment_refs", "outcome"},
        )
        self.assertEqual(event.content["issuer"], {"principal": SELLER})
        self.assertEqual(event.content["event"], EVENT_COMMITMENT_PERFORMANCE)
        self.assertEqual(
            event.content["outcome"],
            {"type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE},
        )
        self.assertEqual(
            fulfillment_event_target(event),
            (record_identity_text(source), COMMITMENT_ID),
        )
        refs = event.content["commitment_refs"]
        self.assertIsInstance(refs, tuple)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["id"], COMMITMENT_ID)
        self.assertEqual(refs[0]["record"], record_ref(source).to_value())

    def test_acceptance_and_completion_preserve_caller_issuer_without_role_inference(
        self,
    ) -> None:
        source = agreement()
        cases = (
            (
                build_commitment_acceptance_event,
                BUYER,
                EVENT_COMMITMENT_ACCEPTANCE,
            ),
            (
                build_commitment_completion_event,
                AUDITOR,
                EVENT_COMMITMENT_COMPLETION,
            ),
        )
        for builder, issuer, expected_event in cases:
            with self.subTest(expected_event=expected_event):
                event = builder(
                    agreement=source,
                    commitment_id=COMMITMENT_ID,
                    issuer=issuer,
                )
                self.assertEqual(
                    set(event.content),
                    {"version", "issuer", "event", "commitment_refs"},
                )
                self.assertEqual(event.content["issuer"], {"principal": issuer})
                self.assertEqual(event.content["event"], expected_event)
                self.assertNotIn("outcome", event.content)
                self.assertEqual(
                    fulfillment_event_target(event),
                    (record_identity_text(source), COMMITMENT_ID),
                )

    def test_performance_requires_exact_commitment_party_issuer(self) -> None:
        source = agreement()
        with self.assertRaises(
            MarketplaceFulfillmentCompletionEvidenceError
        ) as caught:
            build_claimed_complete_performance_event(
                agreement=source,
                commitment_id=COMMITMENT_ID,
                issuer=BUYER,
            )
        self.assertEqual(caught.exception.code, "FULFILLMENT_PERFORMER_MISMATCH")
        self.assertEqual(
            str(caught.exception),
            "Marketplace fulfillment completion evidence operation failed",
        )

    def test_invalid_agreement_commitment_and_issuer_fail_closed(self) -> None:
        source = agreement()
        cases = (
            (
                object(),
                COMMITMENT_ID,
                SELLER,
                "FULFILLMENT_AGREEMENT_REQUIRED",
            ),
            (
                source,
                "missing",
                SELLER,
                "FULFILLMENT_COMMITMENT_NOT_FOUND",
            ),
            (
                source,
                "bad/id",
                SELLER,
                "FULFILLMENT_COMMITMENT_ID_INVALID",
            ),
            (
                source,
                COMMITMENT_ID,
                "not a uri",
                "FULFILLMENT_ISSUER_INVALID",
            ),
        )
        for reviewed_agreement, commitment_id, issuer, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(
                    MarketplaceFulfillmentCompletionEvidenceError
                ) as caught:
                    build_claimed_complete_performance_event(
                        agreement=reviewed_agreement,  # type: ignore[arg-type]
                        commitment_id=commitment_id,
                        issuer=issuer,
                    )
                self.assertEqual(caught.exception.code, code)

    def test_target_extractor_rejects_unrelated_and_wrong_outcome_events(self) -> None:
        source = agreement()
        target = {
            "record": record_ref(source).to_value(),
            "id": COMMITMENT_ID,
        }
        unrelated = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_EVENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": SELLER},
                    "event": f"{BASE}/event/commitment-delivery",
                    "commitment_refs": [target],
                    "outcome": {
                        "type": OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
                    },
                },
                "profiles": [CORE_PROFILE],
            }
        )
        validate_market_record(unrelated)
        with self.assertRaises(
            MarketplaceFulfillmentCompletionEvidenceError
        ) as caught:
            fulfillment_event_target(unrelated)
        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_EVIDENCE_EVENT_UNSUPPORTED",
        )

        wrong_outcome = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_EVENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": SELLER},
                    "event": EVENT_COMMITMENT_PERFORMANCE,
                    "commitment_refs": [target],
                    "outcome": {
                        "type": f"{BASE}/outcome/performance-partial",
                    },
                },
                "profiles": [CORE_PROFILE],
            }
        )
        validate_market_record(wrong_outcome)
        with self.assertRaises(
            MarketplaceFulfillmentCompletionEvidenceError
        ) as caught:
            fulfillment_event_target(wrong_outcome)
        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_EVIDENCE_SHAPE_INVALID",
        )

    def test_target_extractor_rejects_generic_valid_event_with_extra_field(self) -> None:
        source = agreement()
        event = build_commitment_acceptance_event(
            agreement=source,
            commitment_id=COMMITMENT_ID,
            issuer=BUYER,
        )
        content = dict(event.content)
        content["occurred_at"] = "2026-10-03T10:00:00Z"
        widened = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_EVENT,
                "content": content,
                "profiles": [CORE_PROFILE],
            }
        )
        validate_market_record(widened)
        with self.assertRaises(
            MarketplaceFulfillmentCompletionEvidenceError
        ) as caught:
            fulfillment_event_target(widened)
        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_EVIDENCE_SHAPE_INVALID",
        )


if __name__ == "__main__":
    unittest.main()
