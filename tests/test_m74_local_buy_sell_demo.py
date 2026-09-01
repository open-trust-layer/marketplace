from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from marketplace.application import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.reference.local_demo_v1 import (
    LocalBuySellDemoError,
    LocalBuySellDemoResult,
    run_local_buy_sell_demo,
)


BUY_ACTION = "https://example.test/actions/buy"


def seller_listing() -> ProductListingDraft:
    return ProductListingDraft(
        seller_principal="did:example:seller",
        subject_uri="urn:example:product:bicycle-1",
        title="City bicycle",
        description="One carefully maintained bicycle.",
        consideration=ExactDecimal(12500, 2),
        currency_code="EUR",
        quantity=ExactDecimal(1, 0),
        unit_uri=UNIT_ITEM,
        latitude_e6=52_520_000,
        longitude_e6=13_405_000,
    )


class M74LocalBuySellDemoTests(unittest.TestCase):
    def test_genuine_local_sell_listing_and_buy_request_complete_one_demo(self):
        result = run_local_buy_sell_demo(
            seller_listing=seller_listing(),
            buyer_principal="did:example:buyer",
            buyer_action_uri=BUY_ACTION,
        )

        self.assertIs(type(result), LocalBuySellDemoResult)
        self.assertTrue(result.seller_record_id.startswith("r1_"))
        self.assertTrue(result.buyer_record_id.startswith("r1_"))
        self.assertNotEqual(result.seller_record_id, result.buyer_record_id)
        self.assertEqual(result.discovered_seller_record_ids, (result.seller_record_id,))
        self.assertEqual(result.match_conclusion, "COMPATIBLE_UNDER_METHOD")
        self.assertFalse(result.protocol_truth)
        self.assertFalse(result.creates_agreement)
        self.assertEqual(result.discovery_global_completeness, "UNKNOWN")
        self.assertFalse(result.discovery_absence_is_negative_evidence)
        self.assertIn("City bicycle", result.seller_listing_html)
        self.assertIn("Offline listing coordinate map", result.seller_listing_html)
        self.assertNotIn("did:example:buyer", result.seller_listing_html)

    def test_result_is_immutable_and_retains_no_live_record_objects(self):
        result = run_local_buy_sell_demo(
            seller_listing=seller_listing(),
            buyer_principal="did:example:buyer",
            buyer_action_uri=BUY_ACTION,
        )

        with self.assertRaises(FrozenInstanceError):
            result.match_conclusion = "AGREEMENT"
        self.assertFalse(hasattr(result, "__dict__"))
        for field_name in result.__dataclass_fields__:
            value = getattr(result, field_name)
            self.assertNotEqual(type(value).__name__, "RecordV1")

    def test_invalid_buyer_action_fails_with_stable_demo_error(self):
        with self.assertRaises(LocalBuySellDemoError) as raised:
            run_local_buy_sell_demo(
                seller_listing=seller_listing(),
                buyer_principal="did:example:buyer",
                buyer_action_uri="not-an-absolute-uri",
            )
        self.assertEqual(raised.exception.code, "BUYER_RECORD_INVALID")
        self.assertNotIn("not-an-absolute-uri", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
