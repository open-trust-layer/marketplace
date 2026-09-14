from pathlib import Path
import unittest

from marketplace.application.listing import ExactDecimal, ProductListingDraft, build_product_listing_mapping


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
I18N = APP
SUBJECT_URI = "urn:open-layer-marketplace:demo:item:custom-listing"


class MarketplaceMvpProposalParentGuidanceTests(unittest.TestCase):
    def test_shell_exposes_selected_parent_and_disables_example_until_selection(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="proposal-parent"', text)
        self.assertIn("Selected parent: none.", text)
        self.assertIn(
            'id="fill-example-proposal" type="button" class="secondary" disabled',
            text,
        )

    def test_listing_builder_exposes_one_canonical_subject_uri(self):
        mapping = build_product_listing_mapping(
            ProductListingDraft(
                seller_principal="urn:open-layer-marketplace:demo:seller",
                subject_uri=SUBJECT_URI,
                title="Custom listing",
                description="Synthetic parent-guidance fixture.",
                consideration=ExactDecimal(2500, 2),
                currency_code="EUR",
                quantity=ExactDecimal(1, 0),
                unit_uri="urn:open-layer-marketplace:demo:unit:item",
                latitude_e6=52090700,
                longitude_e6=5121400,
            )
        )
        self.assertEqual(mapping["content"]["subjects"], [{"uri": SUBJECT_URI}])

    def test_guided_proposal_uses_selected_product_listing_subject(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("profile.endsWith(\"/profile/product-listing-v1\")", text)
        self.assertNotIn("https://", text)
        self.assertIn("const subjects = record.content?.subjects", text)
        self.assertIn("subjects.length !== 1", text)
        self.assertIn("return reviewedProposalUri(subject.uri)", text)
        self.assertIn(
            'fillSyntheticExample("proposal", { ...SYNTHETIC_PROPOSAL_EXAMPLE, subject_uri: subjectUri })',
            text,
        )
        self.assertNotIn(
            'subject_uri: "urn:open-layer-marketplace:demo:item:city-bicycle",\n  action_uri:',
            text,
        )

    def test_guidance_fails_closed_without_a_valid_product_listing_subject(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("proposalExampleButton.disabled = subjectUri === null", text)
        self.assertIn('"proposal.exampleNeedsListing"', text)
        self.assertIn('i18n.t("author.parentNone")', text)
        self.assertIn('i18n.t("proposal.parentMissing"', text)
        self.assertIn('"proposal.exampleLoaded"', text)
        catalog = I18N.read_text(encoding="utf-8")
        self.assertIn("Selected parent: none.", catalog)
        self.assertIn("Родительская запись: не выбрана.", catalog)

    def test_mvp_running_status_uses_reviewed_readable_punctuation(self):
        text = I18N.read_text(encoding="utf-8")
        self.assertIn("Running bounded local two-user MVP journey…", text)
        self.assertIn("Запускаем ограниченный локальный сценарий MVP для двух пользователей…", text)
        self.assertNotIn("Running bounded local two-user MVP journey?", text)


if __name__ == "__main__":
    unittest.main()
