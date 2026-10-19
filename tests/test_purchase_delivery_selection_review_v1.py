"""L3-A purchase-to-delivery proposal binding tests, no live operations."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft, INDEPENDENT_COURIER, PARTNER_CARRIER, SELLER_DELIVERY,
)
from marketplace.reference.purchase_delivery_selection_review_v1 import (
    PurchaseDeliverySelectionError, review_purchase_delivery_selection,
)
from marketplace.reference.record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, validate_market_record

SELLER = "did:example:seller"
BUYER = "did:example:buyer"
OTHER = "did:example:other"
COURIER = "did:example:courier"
CARRIER = "did:example:carrier"
ITEM = {"uri": "urn:example:item:physical-goods"}
ACTION = f"{BASE}/action/sell"


def purchase(*, seller=SELLER, buyer=BUYER, delivery_actor=SELLER, commitment_id="seller-delivery", terms=None):
    parties = sorted(({"principal": seller}, {"principal": buyer}), key=olp_encode)
    content = {
        "version": 1,
        "parties": parties,
        "subjects": [ITEM],
        "actions": [{"id": ACTION}],
        "terms": {} if terms is None else terms,
        "commitments": [{
            "id": commitment_id,
            "party": {"principal": delivery_actor},
            "action": {"id": ACTION},
            "subjects": [ITEM],
        }],
    }
    result = RecordV1.from_mapping({
        "envelope_version": 1,
        "type": TYPE_AGREEMENT,
        "content": content,
        "profiles": (CORE_PROFILE,),
    })
    validate_market_record(result)
    return result


def draft(mode=SELLER_DELIVERY, provider=None):
    return DeliverySelectionDraft(
        mode=mode,
        seller_principal=SELLER,
        buyer_principal=BUYER,
        proposed_provider_principal=provider,
    )


class PurchaseDeliverySelectionReviewTests(unittest.TestCase):
    def assert_rejected(self, code, *, agreement=None, choice=None):
        with self.assertRaises(PurchaseDeliverySelectionError) as caught:
            review_purchase_delivery_selection(
                delivery_draft=draft() if choice is None else choice,
                purchase_agreement=purchase() if agreement is None else agreement,
            )
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), "Marketplace purchase delivery selection review invalid")

    def test_explicit_seller_delivery_keeps_seller_obligation(self):
        agreement = purchase()
        result = review_purchase_delivery_selection(delivery_draft=draft(), purchase_agreement=agreement)
        self.assertEqual(result.purchase_agreement_id, record_identity_text(agreement))
        self.assertEqual(result.purchase_delivery_commitment_id, "seller-delivery")
        self.assertEqual(result.seller_principal, SELLER)
        self.assertEqual(result.proposed_delivery_executor, SELLER)
        self.assertFalse(result.distinct_logistics_agreement_required)
        self.assertEqual(result.state, "PROPOSAL_ONLY")
        self.assertFalse(result.dispatch_authorized)
        self.assertFalse(result.consent_verified)
        self.assertFalse(result.settlement_authorized)
        self.assertFalse(result.goods_fulfilled)

    def test_courier_and_partner_proposals_require_separate_agreement(self):
        for mode, provider in ((INDEPENDENT_COURIER, COURIER), (PARTNER_CARRIER, CARRIER)):
            with self.subTest(mode=mode):
                result = review_purchase_delivery_selection(
                    delivery_draft=draft(mode, provider), purchase_agreement=purchase(),
                )
                self.assertEqual(result.proposed_delivery_executor, provider)
                self.assertEqual(result.seller_principal, SELLER)
                self.assertTrue(result.distinct_logistics_agreement_required)
                self.assertEqual(result.state, "PROPOSAL_ONLY")
                self.assertFalse(result.dispatch_authorized)

    def test_different_purchase_parties_are_rejected(self):
        self.assert_rejected("PURCHASE_PARTIES_MISMATCH", agreement=purchase(buyer=OTHER))
        self.assert_rejected("PURCHASE_PARTIES_MISMATCH", agreement=purchase(seller=OTHER, delivery_actor=OTHER))

    def test_purchase_needs_exact_named_seller_delivery_commitment(self):
        self.assert_rejected("PURCHASE_SELLER_DELIVERY_MISSING", agreement=purchase(commitment_id="other"))
        self.assert_rejected("PURCHASE_SELLER_DELIVERY_ACTOR_MISMATCH", agreement=purchase(delivery_actor=BUYER))

    def test_source_agreement_and_draft_types_fail_closed(self):
        self.assert_rejected("PURCHASE_AGREEMENT_REQUIRED", agreement=object())
        self.assert_rejected("DELIVERY_DRAFT_REQUIRED", choice=object())

    def test_tampered_proposal_is_revalidated(self):
        choice = draft()
        object.__setattr__(choice, "proposed_provider_principal", COURIER)
        self.assert_rejected("DELIVERY_DRAFT_INVALID", choice=choice)

    def test_sensitive_purchase_terms_are_not_copied_to_review(self):
        secret = "PRIVATE_DELIVERY_LOCATION_DONT_DISCLOSE"
        agreement = purchase(terms={f"{BASE}/term/test-private-note": secret})
        result = review_purchase_delivery_selection(delivery_draft=draft(), purchase_agreement=agreement)
        self.assertNotIn(secret, repr(result))
        self.assertNotIn(secret, str(result))
        self.assertEqual(agreement.content["terms"][f"{BASE}/term/test-private-note"], secret)

    def test_repeated_review_is_deterministic_and_immutable(self):
        agreement = purchase()
        first = review_purchase_delivery_selection(delivery_draft=draft(), purchase_agreement=agreement)
        second = review_purchase_delivery_selection(delivery_draft=draft(), purchase_agreement=agreement)
        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.state = "READY_TO_DISPATCH"


if __name__ == "__main__":
    unittest.main()
