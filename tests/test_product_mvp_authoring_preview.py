from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpAuthoringPreviewTests(unittest.TestCase):
    def test_listing_form_exposes_read_only_human_previews(self):
        text = INDEX.read_text(encoding="utf-8")
        for preview_id in ("create-price-preview", "create-quantity-preview", "create-location-preview"):
            self.assertIn(f'id="{preview_id}"', text)
            self.assertIn('aria-live="polite"', text.split(f'id="{preview_id}"', 1)[1].split("</p>", 1)[0])

    def test_preview_is_client_only_and_never_changes_transport_body(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function draftExactDecimalPresentation")
        end = text.index("function productListingJsonBody", start)
        block = text[start:end]
        self.assertIn("renderListingDraftPreview", block)
        self.assertIn('i18n.t("author.pricePreview"', block)
        self.assertIn('i18n.t("author.quantityPreview"', block)
        self.assertIn('i18n.t("author.locationPreview"', block)
        self.assertNotIn("apiFetch", block)
        self.assertNotIn("fetch(", block)
        body = text.split("function productListingJsonBody() {", 1)[1].split("function reviewedProposalUri", 1)[0]
        self.assertNotIn("preview", body.lower())

    def test_preview_requires_canonical_values_and_coordinate_bounds(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function draftExactDecimalPresentation")
        end = text.index("function productListingJsonBody", start)
        block = text[start:end]
        self.assertIn('/^(0|-?[1-9][0-9]*)$/.test(coefficientText)', block)
        self.assertIn("scale > 18", block)
        self.assertIn("priceValid", block)
        self.assertIn("quantityValid", block)
        self.assertIn("latitude >= -90000000", block)
        self.assertIn("latitude <= 90000000", block)
        self.assertIn("longitude >= -180000000", block)
        self.assertIn("longitude <= 180000000", block)
        self.assertIn('draftExactDecimalPresentation(latitudeText, "6")', block)
        self.assertIn('draftExactDecimalPresentation(longitudeText, "6")', block)

    def test_preview_rerenders_on_input_example_and_language_change(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('byId(id).addEventListener("input", renderListingDraftPreview)', text)
        example = text.split("function fillSyntheticListingExample() {", 1)[1].split("function fillSyntheticProposalExample", 1)[0]
        self.assertIn("renderListingDraftPreview()", example)
        language = text.split("i18n.onChange(() => {", 1)[1].split("renderMvpFlightState();", 1)[0]
        self.assertIn("renderListingDraftPreview()", language)
        self.assertGreaterEqual(text.count("renderListingDraftPreview();"), 3)


if __name__ == "__main__":
    unittest.main()
