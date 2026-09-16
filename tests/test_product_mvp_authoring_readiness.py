from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpAuthoringReadinessTests(unittest.TestCase):
    def test_listing_submit_starts_disabled_with_live_readiness_status(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="create-readiness"', text)
        readiness = text.split('id="create-readiness"', 1)[1].split("</p>", 1)[0]
        self.assertIn('aria-live="polite"', readiness)
        submit = text.split('id="create-submit"', 1)[1].split("</button>", 1)[0]
        self.assertIn("disabled", submit)

    def test_client_readiness_mirrors_bounded_listing_shape(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("function listingDraftLooksReady() {", 1)[1].split("function renderListingDraftReadiness", 1)[0]
        self.assertIn('absoluteUriReady("create-seller-principal")', block)
        self.assertIn('absoluteUriReady("create-subject-uri")', block)
        self.assertIn("MAX_LISTING_TITLE_BYTES", block)
        self.assertIn("MAX_LISTING_DESCRIPTION_BYTES", block)
        self.assertIn("0n, MAX_APPLICATION_INTEGER", block)
        self.assertIn("1n, MAX_APPLICATION_INTEGER", block)
        self.assertIn('/^[A-Z]{3}$/.test(byId("create-currency-code").value)', block)
        self.assertIn('absoluteUriReady("create-unit-uri")', block)
        self.assertIn("-90000000n, 90000000n", block)
        self.assertIn("-180000000n, 180000000n", block)
        self.assertNotIn("apiFetch", block)
        self.assertNotIn("fetch(", block)

    def test_readiness_controls_submit_and_invalid_submit_never_calls_api(self):
        text = APP.read_text(encoding="utf-8")
        render = text.split("function renderListingDraftReadiness() {", 1)[1].split("function renderListingDraftPreview", 1)[0]
        self.assertIn('byId("create-submit").disabled = !ready', render)
        self.assertIn('"author.draftReady"', render)
        self.assertIn('"author.draftIncomplete"', render)
        submit = text.split("async function createProductListing(event) {", 1)[1].split("async function createProposal", 1)[0]
        guard = submit.index("if (!listingDraftLooksReady())")
        request = submit.index("apiFetch(API_PRODUCT_LISTINGS")
        self.assertLess(guard, request)
        self.assertIn('setFormStatus("create-status", "listing.notReady"', submit[:request])

    def test_all_listing_inputs_and_language_changes_rerender_readiness(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("[...PRODUCT_LISTING_STRING_FIELDS, ...PRODUCT_LISTING_INTEGER_FIELDS]", text)
        self.assertIn('byId(id).addEventListener("input", renderListingDraftPreview)', text)
        language = text.split("i18n.onChange(() => {", 1)[1].split("renderMvpFlightState();", 1)[0]
        self.assertIn("renderListingDraftPreview()", language)


if __name__ == "__main__":
    unittest.main()
