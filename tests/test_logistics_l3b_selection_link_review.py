"""L3-B identity-only cross-check of L3-A proposal with L1 agreement link."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from olp.evidence import record_ref

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft, INDEPENDENT_COURIER, PARTNER_CARRIER,
    SELLER_DELIVERY,
)
from marketplace.logistics.agreement_link_v1 import TERM_PURCHASE_COMMITMENT
from marketplace.logistics.purchase_selection_link_review_v1 import (
    DeliverySelectionLinkReviewError, review_delivery_selection_link,
)
from marketplace.reference.record_v1 import BASE
from tests.test_logistics_l1_agreement_link import (
    BUYER, COURIER, SELLER, ITEM, SALE,
    changed, delivery, make_record, purchase,
)

OTHER = "did:example:other-carrier"


def choice(mode=INDEPENDENT_COURIER, provider=COURIER, *, buyer=BUYER):
    return DeliverySelectionDraft(
        mode=mode, seller_principal=SELLER, buyer_principal=buyer,
        proposed_provider_principal=provider,
    )


class DeliverySelectionAgreementCoherenceTests(unittest.TestCase):
    def assert_rejected(self, code, *, draft=None, source=None, service=None):
        parent = purchase() if source is None else source
        service = delivery(parent) if service is None else service
        with self.assertRaises(DeliverySelectionLinkReviewError) as got:
            review_delivery_selection_link(
                delivery_draft=choice() if draft is None else draft,
                purchase_agreement=parent,
                delivery_agreement=service,
            )
        self.assertEqual(got.exception.code, code)
        self.assertEqual(
            str(got.exception),
            "Marketplace logistics delivery selection link review invalid",
        )

    def test_independent_courier_matches_exact_link_and_remains_inert(self):
        p = purchase()
        d = delivery(p)
        result = review_delivery_selection_link(
            delivery_draft=choice(), purchase_agreement=p,
            delivery_agreement=d,
        )
        self.assertEqual(result.purchase_commitment_id, "seller-delivery")
        self.assertEqual(result.proposed_provider_principal, COURIER)
        self.assertEqual(result.seller_principal, SELLER)
        self.assertEqual(result.transport_commitment_id, "courier-transport")
        self.assertNotEqual(result.purchase_agreement_id, result.delivery_agreement_id)
        self.assertEqual(result.delivery_mode, INDEPENDENT_COURIER)
        self.assertEqual(result.status, "CONSISTENT_PROPOSAL_ONLY")
        self.assertTrue(result.separate_agreement_required)
        self.assertFalse(result.assent_verified)
        self.assertFalse(result.dispatch_authorized)
        self.assertFalse(result.settlement_authorized)
        self.assertFalse(result.goods_fulfilled)
        with self.assertRaises(FrozenInstanceError):
            result.dispatch_authorized = True

    def test_partner_carrier_can_match_its_own_separate_agreement(self):
        p = purchase()
        review = review_delivery_selection_link(
            delivery_draft=choice(PARTNER_CARRIER, OTHER),
            purchase_agreement=p, delivery_agreement=delivery(p, carrier=OTHER),
        )
        self.assertEqual(review.delivery_mode, PARTNER_CARRIER)
        self.assertEqual(review.proposed_provider_principal, OTHER)
        self.assertFalse(review.dispatch_authorized)

    def test_proposed_actor_must_match_transport_commitment_actor(self):
        self.assert_rejected(
            "PROPOSED_PROVIDER_MISMATCH",
            draft=choice(PARTNER_CARRIER, OTHER),
        )
        self.assert_rejected(
            "PROPOSED_PROVIDER_MISMATCH",
            service=delivery(purchase(), carrier=SELLER),
        )

    def test_self_managed_mode_does_not_implicitly_select_external_service(self):
        self.assert_rejected(
            "THIRD_PARTY_DELIVERY_REQUIRED",
            draft=choice(SELLER_DELIVERY, None),
        )

    def test_purchase_and_delivery_must_reference_same_immutable_agreement(self):
        p = purchase()
        different = changed(p, terms={f"{BASE}/term/test-basis": 1})
        self.assert_rejected(
            "DELIVERY_AGREEMENT_LINK_INVALID",
            source=different,
            service=delivery(p),
        )

    def test_exact_seller_delivery_commitment_not_another_purchase_commitment(self):
        p = purchase()
        content = dict(p.content)
        content["commitments"] = tuple(p.content["commitments"]) + ({
            "id": "other-purchase-work",
            "party": {"principal": SELLER},
            "action": {"id": SALE},
            "subjects": (ITEM,),
        },)
        content["commitments"] = tuple(sorted(content["commitments"], key=lambda entry: entry["id"].encode("utf-8")))
        extended = make_record(content)
        d = delivery(extended)
        term = dict(d.content["terms"])
        term[TERM_PURCHASE_COMMITMENT] = {
            "record": record_ref(extended).to_value(),
            "id": "other-purchase-work",
        }
        self.assert_rejected(
            "PURCHASE_COMMITMENT_MISMATCH",
            source=extended, service=changed(d, terms=term),
        )

    def test_draft_party_mismatch_rejected(self):
        self.assert_rejected(
            "PURCHASE_SELECTION_INVALID",
            draft=choice(buyer=OTHER),
        )

    def test_invalid_types_fail_closed_without_echoing_values(self):
        self.assert_rejected("PURCHASE_SELECTION_INVALID", draft=object())
        self.assert_rejected("PURCHASE_SELECTION_INVALID", source=object(), service=delivery(purchase()))
        self.assert_rejected("DELIVERY_AGREEMENT_LINK_INVALID", service=object())

    def test_wrong_delivery_profile_rejected(self):
        p = purchase()
        d = delivery(p)
        self.assert_rejected(
            "DELIVERY_AGREEMENT_LINK_INVALID",
            source=p,
            service=make_record(dict(d.content)),
        )

    def test_private_terms_are_not_disclosed(self):
        secret = "PRIVATE_ADDRESS_DO_NOT_ECHO"
        p = changed(purchase(), terms={f"{BASE}/term/internal-note": secret})
        d = delivery(p)
        result = review_delivery_selection_link(
            delivery_draft=choice(), purchase_agreement=p, delivery_agreement=d,
        )
        self.assertNotIn(secret, repr(result))
        self.assertNotIn(secret, str(result))
        self.assertEqual(
            p.content["terms"][f"{BASE}/term/internal-note"], secret,
        )

    def test_review_is_deterministic_and_does_not_mutate_records(self):
        p = purchase()
        d = delivery(p)
        original_purchase = repr(p)
        original_delivery = repr(d)
        first = review_delivery_selection_link(
            delivery_draft=choice(), purchase_agreement=p, delivery_agreement=d,
        )
        second = review_delivery_selection_link(
            delivery_draft=choice(), purchase_agreement=p, delivery_agreement=d,
        )
        self.assertEqual(first, second)
        self.assertEqual(repr(p), original_purchase)
        self.assertEqual(repr(d), original_delivery)


if __name__ == "__main__":
    unittest.main()
