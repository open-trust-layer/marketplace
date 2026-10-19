"""Physical delivery responsibility proposal: source-only contract tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from marketplace.application.delivery_selection_v1 import (
    DeliverySelectionDraft,
    DeliverySelectionError,
    INDEPENDENT_COURIER,
    PARTNER_CARRIER,
    SELLER_DELIVERY,
    plan_delivery_selection,
)


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
COURIER = "urn:marketplace:test:courier"
CARRIER = "urn:marketplace:test:carrier"


class DeliverySelectionProposalTests(unittest.TestCase):
    def _draft(self, mode=SELLER_DELIVERY, provider=None, **changes):
        data = dict(
            mode=mode,
            seller_principal=SELLER,
            buyer_principal=BUYER,
            proposed_provider_principal=provider,
        )
        data.update(changes)
        return DeliverySelectionDraft(**data)

    def _fails(self, code, **fields):
        with self.assertRaises(DeliverySelectionError) as raised:
            self._draft(**fields)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(str(raised.exception), code)

    def test_seller_delivery_is_explicit_and_does_not_execute(self):
        plan = plan_delivery_selection(self._draft())
        self.assertEqual(plan.mode, SELLER_DELIVERY)
        self.assertEqual(plan.proposed_executor_principal, SELLER)
        self.assertEqual(plan.seller_product_commitment_principal, SELLER)
        self.assertEqual(plan.seller_product_commitment_id, "seller-delivery")
        self.assertFalse(plan.distinct_delivery_service_agreement_required)
        self.assertTrue(plan.quote_and_consent_required)
        self.assertEqual(plan.state, "PROPOSAL_ONLY")
        self.assertFalse(plan.dispatch_authorized)
        self.assertFalse(plan.payment_authorized)
        self.assertFalse(plan.seller_delivery_fulfilled)

    def test_independent_courier_requires_separate_consent(self):
        plan = plan_delivery_selection(self._draft(INDEPENDENT_COURIER, COURIER))
        self.assertEqual(plan.proposed_executor_principal, COURIER)
        self.assertEqual(plan.seller_product_commitment_principal, SELLER)
        self.assertTrue(plan.distinct_delivery_service_agreement_required)
        self.assertTrue(plan.quote_and_consent_required)
        self.assertFalse(plan.dispatch_authorized)
        self.assertFalse(plan.seller_delivery_fulfilled)

    def test_partner_carrier_does_not_call_external_provider(self):
        plan = plan_delivery_selection(self._draft(PARTNER_CARRIER, CARRIER))
        self.assertEqual(plan.proposed_executor_principal, CARRIER)
        self.assertTrue(plan.distinct_delivery_service_agreement_required)
        self.assertFalse(plan.payment_authorized)

    def test_review_is_deterministic_without_mutating_inputs(self):
        draft = self._draft(INDEPENDENT_COURIER, COURIER)
        self.assertEqual(plan_delivery_selection(draft), plan_delivery_selection(draft))
        self.assertEqual(draft.proposed_provider_principal, COURIER)
        with self.assertRaises(FrozenInstanceError):
            draft.mode = PARTNER_CARRIER

    def test_mode_required_and_exact(self):
        for invalid in (None, "", "courier", "Seller_Delivery", True, 1, [], {}):
            with self.subTest(invalid=repr(invalid)):
                self._fails("DELIVERY_MODE_UNSUPPORTED", mode=invalid)

    def test_seller_and_buyer_distinct(self):
        self._fails("DELIVERY_PARTIES_NOT_DISTINCT", buyer_principal=SELLER)
        self._fails("DELIVERY_PRINCIPAL_INVALID", seller_principal=None)

    def test_third_party_provider_required(self):
        for mode in (INDEPENDENT_COURIER, PARTNER_CARRIER):
            for provider in (None, "", "not-a-uri", False):
                with self.subTest(mode=mode, provider=repr(provider)):
                    self._fails("DELIVERY_PRINCIPAL_INVALID", mode=mode, provider=provider)

    def test_third_party_must_not_be_buyer_or_seller(self):
        for mode in (INDEPENDENT_COURIER, PARTNER_CARRIER):
            for principal in (SELLER, BUYER):
                with self.subTest(mode=mode, principal=principal):
                    self._fails(
                        "DELIVERY_THIRD_PARTY_NOT_DISTINCT",
                        mode=mode,
                        provider=principal,
                    )

    def test_seller_mode_cannot_hide_unreviewed_provider(self):
        self._fails("DELIVERY_SELLER_MODE_PROVIDER_FORBIDDEN", provider=COURIER)

    def test_rejects_unbounded_and_invalid_principals_without_echoing(self):
        for principal in (
            "urn:test:" + "x" * 2048,
            "urn:test:hello world",
            "urn:test:\ud800",
            "relative/path",
        ):
            with self.subTest(value=repr(principal)[:60]):
                self._fails("DELIVERY_PRINCIPAL_INVALID", seller_principal=principal)

    def test_requires_reviewed_exact_draft(self):
        for invalid in (None, {}, "seller_delivery"):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(DeliverySelectionError) as raised:
                    plan_delivery_selection(invalid)
                self.assertEqual(raised.exception.code, "DELIVERY_DRAFT_INVALID")


if __name__ == "__main__":
    unittest.main()
