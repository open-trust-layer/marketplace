"""L2 source-only delivery lifecycle evidence projection adversarial tests."""
from __future__ import annotations

import unittest

from olp import RecordV1
from olp.evidence import record_ref

from marketplace.logistics.agreement_link_v1 import PROFILE_DELIVERY_V1
from marketplace.logistics.lifecycle_projection_v1 import (
    _EVENT_TYPES,
    DeliveryProjectionError,
    ReviewedDeliveryEvent,
    project_delivery_events,
)
from marketplace.reference.record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_EVENT,
    validate_market_record,
)
from tests.test_logistics_l1_agreement_link import (
    BUYER,
    COURIER,
    SELLER,
    delivery,
    purchase,
)

STAGES = (
    "REQUESTED", "QUOTED", "ASSIGNED", "PICKUP_READY", "PICKED_UP",
    "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "CONFIRMED",
)


def event(agreement, step, principal, *, target=None, event_uri=None, extra=None):
    content = {
        "version": 1,
        "issuer": {"principal": principal},
        "event": _EVENT_TYPES[step] if event_uri is None else event_uri,
        "commitment_refs": [{
            "record": record_ref(agreement).to_value(),
            "id": "courier-transport" if target is None else target,
        }],
    }
    if extra:
        content.update(extra)
    result = RecordV1.from_mapping({
        "envelope_version": 1,
        "type": TYPE_EVENT,
        "content": content,
        "profiles": sorted((CORE_PROFILE, PROFILE_DELIVERY_V1)),
    })
    validate_market_record(result)
    return result


def actor(step):
    return {
        "REQUESTED": SELLER, "QUOTED": COURIER, "ASSIGNED": SELLER,
        "PICKUP_READY": SELLER, "PICKED_UP": COURIER,
        "IN_TRANSIT": COURIER, "OUT_FOR_DELIVERY": COURIER,
        "DELIVERED": COURIER, "CONFIRMED": BUYER,
    }.get(step, COURIER)


def reviewed(agreement, steps, *, trust=True):
    return tuple(
        ReviewedDeliveryEvent(
            event(agreement, step, actor(step)),
            i,
            trust,
            trust,
        )
        for i, step in enumerate(steps, 1)
    )


class DeliveryLifecycleProjectionTests(unittest.TestCase):
    def setUp(self):
        self.purchase = purchase()
        self.delivery = delivery(self.purchase)

    def project(self, rows):
        return project_delivery_events(
            purchase_agreement=self.purchase,
            delivery_agreement=self.delivery,
            buyer_principal=BUYER,
            reviewed_events=rows,
        )

    def assert_error(self, code, rows=None, **changes):
        kwargs = {
            "purchase_agreement": self.purchase,
            "delivery_agreement": self.delivery,
            "buyer_principal": BUYER,
            "reviewed_events": rows if rows is not None else (),
        }
        kwargs.update(changes)
        with self.assertRaises(DeliveryProjectionError) as e:
            project_delivery_events(**kwargs)
        self.assertEqual(e.exception.code, code)
        self.assertEqual(str(e.exception), "Marketplace delivery evidence projection failed")

    def test_only_explicit_buyer_confirmation_after_delivery(self):
        events = reviewed(self.delivery, STAGES)
        result = self.project(events)
        self.assertEqual(result.stage, "CONFIRMED")
        self.assertEqual(result.status, "PROVISIONAL")
        self.assertEqual(len(result.admitted_event_ids), 9)
        self.assertEqual(result.exception_codes, ())
        self.assertEqual(result.conflicting_event_ids, ())
        self.assertNotEqual(result.admitted_event_ids[7], result.admitted_event_ids[8])

    def test_carrier_delivery_is_not_buyer_confirmation(self):
        result = self.project(reviewed(self.delivery, STAGES[:-1]))
        self.assertEqual(result.stage, "DELIVERED")
        self.assertEqual(result.status, "PROVISIONAL")

    def test_no_evidence_or_untrusted_evidence_cannot_advance(self):
        self.assertEqual(self.project(()).status, "INSUFFICIENT")
        one = reviewed(self.delivery, STAGES[:1], trust=False)
        result = self.project(one)
        self.assertEqual(result.stage, "UNKNOWN")
        self.assertEqual(len(result.excluded_event_ids), 1)
        self.assertFalse(result.admitted_event_ids)

    def test_gaps_are_conflicts_not_implicit_status(self):
        result = self.project(reviewed(self.delivery, ("REQUESTED", "ASSIGNED")))
        self.assertEqual(result.stage, "REQUESTED")
        self.assertEqual(result.status, "CONFLICT")
        self.assertEqual(len(result.conflicting_event_ids), 1)

    def test_pre_confirmation_claim_cannot_skip_pickup(self):
        result = self.project(reviewed(self.delivery, ("CONFIRMED",)))
        self.assertEqual(result.stage, "UNKNOWN")
        self.assertEqual(result.status, "CONFLICT")

    def test_wrong_issuer_buyer_cannot_claim_courier_delivery(self):
        wrong = ReviewedDeliveryEvent(event(self.delivery, "DELIVERED", BUYER), 1, True, True)
        self.assert_error("LOGISTICS_EVENT_ACTOR_INVALID", (wrong,))
        wrong_confirm = ReviewedDeliveryEvent(
            event(self.delivery, "CONFIRMED", COURIER), 1, True, True
        )
        self.assert_error("LOGISTICS_EVENT_ACTOR_INVALID", (wrong_confirm,))

    def test_mismatched_agreement_or_commitment_is_rejected(self):
        bad = ReviewedDeliveryEvent(
            event(self.delivery, "REQUESTED", SELLER, target="wrong"), 1, True, True
        )
        self.assert_error("LOGISTICS_EVENT_TARGET_MISMATCH", (bad,))
        another = delivery(self.purchase, carrier=SELLER)
        bad = ReviewedDeliveryEvent(event(another, "REQUESTED", SELLER), 1, True, True)
        self.assert_error("LOGISTICS_EVENT_TARGET_MISMATCH", (bad,))

    def test_unknown_event_fail_closed(self):
        unknown = ReviewedDeliveryEvent(
            event(
                self.delivery, "REQUESTED", SELLER,
                event_uri=f"{BASE}/event/logistics-unknown",
            ), 1, True, True
        )
        self.assert_error("LOGISTICS_EVENT_KIND_UNSUPPORTED", (unknown,))

    def test_public_payload_with_location_is_not_an_l2_event(self):
        sensitive = ReviewedDeliveryEvent(
            event(
                self.delivery, "REQUESTED", SELLER,
                extra={"occurred_at": "2026-10-18T00:00:00Z"},
            ), 1, True, True
        )
        self.assert_error("LOGISTICS_EVENT_SHAPE_INVALID", (sensitive,))

    def test_repeated_evidence_or_sequence_fails_closed(self):
        source = event(self.delivery, "REQUESTED", SELLER)
        a = ReviewedDeliveryEvent(source, 1, True, True)
        b = ReviewedDeliveryEvent(source, 2, True, True)
        self.assert_error("LOGISTICS_EVIDENCE_DUPLICATE", (a, b))
        c = ReviewedDeliveryEvent(event(self.delivery, "QUOTED", COURIER), 1, True, True)
        self.assert_error("LOGISTICS_SEQUENCE_CONFLICT", (a, c))

    def test_exception_is_preserved_not_promoted_to_delivery(self):
        base = list(reviewed(self.delivery, STAGES[:4]))
        base.append(ReviewedDeliveryEvent(
            event(self.delivery, "FAILED_PICKUP", COURIER), 5, True, True
        ))
        result = self.project(tuple(base))
        self.assertEqual(result.stage, "PICKUP_READY")
        self.assertIn("FAILED_PICKUP", result.exception_codes)
        self.assertEqual(result.status, "EXCEPTION")

    def test_impossible_exception_is_conflict(self):
        result = self.project((
            ReviewedDeliveryEvent(event(self.delivery, "FAILED_PICKUP", COURIER), 1, True, True),
        ))
        self.assertEqual(result.stage, "UNKNOWN")
        self.assertEqual(result.status, "CONFLICT")

    def test_failed_pickup_cannot_resume_without_remedy_evidence(self):
        rows = list(reviewed(self.delivery, STAGES[:4]))
        rows.append(ReviewedDeliveryEvent(
            event(self.delivery, "FAILED_PICKUP", COURIER), 5, True, True
        ))
        rows.append(ReviewedDeliveryEvent(
            event(self.delivery, "PICKED_UP", COURIER), 6, True, True
        ))
        result = self.project(tuple(rows))
        self.assertEqual(result.stage, "PICKUP_READY")
        self.assertEqual(result.status, "CONFLICT")
        self.assertIn("FAILED_PICKUP", result.exception_codes)
        self.assertEqual(len(result.conflicting_event_ids), 1)

    def test_dispute_after_buyer_confirmation_is_not_clean_success(self):
        rows = list(reviewed(self.delivery, STAGES))
        rows.append(ReviewedDeliveryEvent(
            event(self.delivery, "DISPUTED", BUYER), 10, True, True
        ))
        result = self.project(tuple(rows))
        self.assertEqual(result.stage, "CONFIRMED")
        self.assertEqual(result.status, "EXCEPTION")
        self.assertEqual(result.exception_codes, ("DISPUTED",))

    def test_refund_request_after_assignment_needs_separate_authority(self):
        rows = list(reviewed(self.delivery, STAGES[:3]))
        rows.append(ReviewedDeliveryEvent(
            event(self.delivery, "REFUND_REQUESTED", BUYER), 4, True, True
        ))
        result = self.project(tuple(rows))
        self.assertEqual(result.status, "EXCEPTION")
        self.assertIn("REFUND_REQUESTED", result.exception_codes)

    def test_cancellation_blocks_late_claim_of_fulfillment(self):
        rows = list(reviewed(self.delivery, STAGES[:3]))
        rows.append(ReviewedDeliveryEvent(event(self.delivery, "CANCELLED", SELLER), 4, True, True))
        rows.append(ReviewedDeliveryEvent(event(self.delivery, "PICKUP_READY", SELLER), 5, True, True))
        result = self.project(tuple(rows))
        self.assertEqual(result.stage, "ASSIGNED")
        self.assertEqual(result.status, "CONFLICT")
        self.assertIn("CANCELLED", result.exception_codes)

    def test_courier_cannot_unilaterally_cancel_or_request_buyer_refund(self):
        for kind in ("CANCELLED", "REFUND_REQUESTED"):
            with self.subTest(kind=kind):
                claim = ReviewedDeliveryEvent(
                    event(self.delivery, kind, COURIER), 1, True, True
                )
                self.assert_error("LOGISTICS_EVENT_ACTOR_INVALID", (claim,))

    def test_delivery_issuer_cannot_self_certify_receipt_even_if_assessed(self):
        rows = list(reviewed(self.delivery, STAGES[:-1]))
        rows.append(ReviewedDeliveryEvent(
            event(self.delivery, "CONFIRMED", COURIER), len(rows) + 1, True, True
        ))
        self.assert_error("LOGISTICS_EVENT_ACTOR_INVALID", tuple(rows))

    def test_separate_attribution_or_authority_gate_blocks_progress(self):
        source = event(self.delivery, "REQUESTED", SELLER)
        for attribution, authority in ((False, True), (True, False)):
            with self.subTest(attribution=attribution, authority=authority):
                result = self.project((
                    ReviewedDeliveryEvent(source, 1, attribution, authority),
                ))
                self.assertEqual(result.stage, "UNKNOWN")
                self.assertEqual(result.status, "INSUFFICIENT")

    def test_malformed_review_flags_and_buyer_fail_closed(self):
        source = event(self.delivery, "REQUESTED", SELLER)
        self.assert_error(
            "LOGISTICS_REVIEW_INVALID",
            (ReviewedDeliveryEvent(source, 1, 1, True),),
        )
        self.assert_error("LOGISTICS_BUYER_AMBIGUOUS", buyer_principal=COURIER)
        self.assert_error("LOGISTICS_REVIEW_SET_INVALID", rows=[])
        self.assert_error(
            "LOGISTICS_REVIEW_INVALID",
            (ReviewedDeliveryEvent(source, True, True, True),),
        )


if __name__ == "__main__":
    unittest.main()
