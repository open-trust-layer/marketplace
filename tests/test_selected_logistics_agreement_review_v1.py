"""Synthetic L3-B selection/Agreement identity composition, never dispatch."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft,
    INDEPENDENT_COURIER,
    PARTNER_CARRIER,
    SELLER_DELIVERY,
)
from marketplace.reference.selected_logistics_agreement_review_v1 import (
    SelectedLogisticsLinkError,
    review_selected_logistics_agreement,
)
from tests.test_logistics_l1_agreement_link import (
    BUYER,
    COURIER,
    SELLER,
    changed,
    delivery,
    purchase,
)
from marketplace.reference.record_v1 import BASE

ALTERNATE = "did:example:alternate"
PRIVATE_VALUE = "PRIVATE_DELIVERY_ADDRESS_NOT_FOR_PUBLIC_RECORD"


def draft(mode=INDEPENDENT_COURIER, provider=COURIER):
    return DeliverySelectionDraft(
        mode=mode,
        seller_principal=SELLER,
        buyer_principal=BUYER,
        proposed_provider_principal=provider,
    )


class SelectedLogisticsAgreementReviewTests(unittest.TestCase):
    def review(self, *, choice=None, purchase_record=None, delivery_record=None):
        buy = purchase() if purchase_record is None else purchase_record
        return review_selected_logistics_agreement(
            delivery_draft=draft() if choice is None else choice,
            purchase_agreement=buy,
            delivery_agreement=delivery(buy) if delivery_record is None else delivery_record,
        )

    def rejected(self, code, **kwargs):
        with self.assertRaises(SelectedLogisticsLinkError) as caught:
            self.review(**kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), "Marketplace logistics selection link invalid")

    def test_explicit_courier_identity_link_is_only_a_review(self):
        buy = purchase()
        transport = delivery(buy)
        result = self.review(purchase_record=buy, delivery_record=transport)
        self.assertEqual(result.purchase_commitment_id, "seller-delivery")
        self.assertEqual(result.delivery_commitment_id, "courier-transport")
        self.assertEqual(result.proposed_transport_principal, COURIER)
        self.assertEqual(result.delivery_mode, INDEPENDENT_COURIER)
        self.assertNotEqual(result.purchase_agreement_id, result.delivery_agreement_id)
        self.assertEqual(result.status, "IDENTITY_MATCH_ONLY")
        for attr in (
            "consent_verified", "attribution_verified", "carrier_eligible",
            "dispatch_authorized", "settlement_authorized", "goods_fulfilled",
        ):
            self.assertIs(getattr(result, attr), False)
        with self.assertRaises(FrozenInstanceError):
            result.dispatch_authorized = True

    def test_partner_carrier_matches_exact_explicit_performer(self):
        buy = purchase()
        review = self.review(
            choice=draft(PARTNER_CARRIER, ALTERNATE),
            purchase_record=buy,
            delivery_record=delivery(buy, carrier=ALTERNATE),
        )
        self.assertEqual(review.delivery_mode, PARTNER_CARRIER)
        self.assertEqual(review.proposed_transport_principal, ALTERNATE)
        self.assertFalse(review.consent_verified)

    def test_carrier_substitution_fails_closed(self):
        buy = purchase()
        self.rejected(
            "LOGISTICS_SELECTION_TRANSPORTER_MISMATCH",
            purchase_record=buy,
            delivery_record=delivery(buy, carrier=ALTERNATE),
        )

    def test_cross_purchase_link_is_never_rebound(self):
        buy = purchase()
        other = changed(buy, terms={f"{BASE}/term/test-distinct-source": 1})
        self.rejected(
            "LOGISTICS_SELECTION_LINK_INVALID",
            purchase_record=other,
            delivery_record=delivery(buy),
        )

    def test_seller_managed_mode_cannot_be_misrepresented_as_external_agreement(self):
        self.rejected(
            "LOGISTICS_SELECTION_THIRD_PARTY_REQUIRED",
            choice=draft(SELLER_DELIVERY, None),
        )

    def test_no_assumed_proposal_from_invalid_or_tampered_draft(self):
        self.rejected("LOGISTICS_SELECTION_DRAFT_REQUIRED", choice=object())
        invalid = draft()
        object.__setattr__(invalid, "proposed_provider_principal", SELLER)
        self.rejected("LOGISTICS_SELECTION_PURCHASE_INVALID", choice=invalid)

    def test_bad_purchase_and_transport_records_fail_without_reflection(self):
        self.rejected("LOGISTICS_SELECTION_PURCHASE_INVALID", purchase_record=object())
        self.rejected("LOGISTICS_SELECTION_LINK_INVALID", delivery_record=object())
        self.rejected("LOGISTICS_SELECTION_LINK_INVALID", delivery_record=purchase())

    def test_sensitive_terms_are_neither_read_into_output_nor_error(self):
        buy = changed(purchase(), terms={f"{BASE}/term/test-private-note": PRIVATE_VALUE})
        good = self.review(purchase_record=buy)
        self.assertNotIn(PRIVATE_VALUE, repr(good))
        self.assertNotIn(PRIVATE_VALUE, str(good))
        bad = changed(delivery(buy), terms={f"{BASE}/term/test-private-note": PRIVATE_VALUE})
        with self.assertRaises(SelectedLogisticsLinkError) as caught:
            self.review(purchase_record=buy, delivery_record=bad)
        self.assertNotIn(PRIVATE_VALUE, repr(caught.exception))
        self.assertNotIn(PRIVATE_VALUE, str(caught.exception))

    def test_identical_inputs_have_identical_identity_only_results(self):
        buy = purchase()
        ship = delivery(buy)
        first = self.review(purchase_record=buy, delivery_record=ship)
        second = self.review(purchase_record=buy, delivery_record=ship)
        self.assertEqual(first, second)
        self.assertIsNone(getattr(first, "payment", None))


if __name__ == "__main__":
    unittest.main()
