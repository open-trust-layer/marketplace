from pathlib import Path
import unittest

from marketplace.application.listing import ExactDecimal, ProductListingDraft
from marketplace.application.proposal import BuyerRequestProposalDraft


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpGuidedAuthoringTests(unittest.TestCase):
    def test_shell_exposes_explicit_non_submitting_example_controls(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="fill-example-listing"', text)
        self.assertIn('id="fill-example-proposal"', text)
        self.assertEqual(text.count("Fill synthetic example"), 2)
        self.assertIn("identity → listing → publish → discover → verify → accept → agreement → completed", text)
        self.assertNotIn("Seller: ?", text)
        self.assertNotIn("Buyer: ?", text)

    def test_examples_are_synthetic_and_bounded_to_visible_fields(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            'seller_principal: "urn:open-layer-marketplace:demo:seller"',
            'buyer_principal: "urn:open-layer-marketplace:demo:buyer"',
            'subject_uri: "urn:open-layer-marketplace:demo:item:city-bicycle"',
            'currency_code: "EUR"',
            'latitude_e6: "52090700"',
            'longitude_e6: "5121400"',
        ):
            self.assertIn(marker, text)

    def test_fill_helpers_never_submit_or_call_the_api(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function fillSyntheticExample")
        end = text.index("async function createProductListing", start)
        block = text[start:end]
        self.assertIn('.value = value', block)
        self.assertIn("Review the fields, then submit manually.", block)
        self.assertNotIn("apiFetch", block)
        self.assertNotIn("fetch(", block)
        self.assertNotIn("submit()", block)
        self.assertNotIn("requestSubmit", block)
        self.assertNotIn("localStorage", block)
        self.assertNotIn("sessionStorage", block)

    def test_exact_example_values_are_valid_structured_drafts(self):
        ProductListingDraft(
            seller_principal="urn:open-layer-marketplace:demo:seller",
            subject_uri="urn:open-layer-marketplace:demo:item:city-bicycle",
            title="City bicycle",
            description="Synthetic local evaluator listing.",
            consideration=ExactDecimal(12500, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri="urn:open-layer-marketplace:demo:unit:item",
            latitude_e6=52090700,
            longitude_e6=5121400,
        )
        BuyerRequestProposalDraft(
            buyer_principal="urn:open-layer-marketplace:demo:buyer",
            subject_uri="urn:open-layer-marketplace:demo:item:city-bicycle",
            action_uri="urn:open-layer-marketplace:demo:action:buy",
            parent_record_id="r1_demo_parent",
        )


if __name__ == "__main__":
    unittest.main()
