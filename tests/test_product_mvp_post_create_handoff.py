from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpPostCreateHandoffTests(unittest.TestCase):
    def test_new_listing_resolution_is_local_exact_and_ambiguity_safe(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function newlyCreatedProductListingId")
        end = text.index("function renderProposalParentGuidance", start)
        block = text[start:end]
        self.assertIn("previousIds instanceof Set", block)
        self.assertIn('typeof previousViewWasCurrent !== "boolean"', block)
        self.assertIn("if (!previousViewWasCurrent || state.truncated) return null", block)
        self.assertIn("state.records.entries()", block)
        self.assertIn("previousIds.has(recordId)", block)
        self.assertIn("selectedProductListingSubjectUri(record) === expectedSubjectUri", block)
        self.assertIn("candidates.length === 1 ? candidates[0] : null", block)
        self.assertNotIn("apiFetch", block)
        self.assertNotIn("fetch(", block)

    def test_create_snapshots_ids_resyncs_then_selects_only_resolved_listing(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function createProductListing")
        end = text.index("async function createProposal", start)
        block = text[start:end]
        self.assertIn('const submittedSubjectUri = byId("create-subject-uri").value;', block)
        self.assertIn("const previousIds = new Set(state.records.keys());", block)
        self.assertIn("const previousViewWasCurrent = state.syncCursor !== null && state.truncated === false;", block)
        self.assertIn('setFormStatus("create-status", "listing.submitting")', block)
        self.assertNotIn("\u00e2\u20ac\u00a6", block)
        self.assertIn('await apiFetch(API_PRODUCT_LISTINGS, { method: "POST", body });', block)
        self.assertIn("await fullResync();", block)
        self.assertIn(
            "const createdId = newlyCreatedProductListingId(previousIds, submittedSubjectUri, previousViewWasCurrent);",
            block,
        )
        self.assertIn("if (createdId !== null)", block)
        self.assertIn("selectIntent(createdId);", block)
        self.assertLess(block.index("await apiFetch"), block.index("await fullResync"))
        self.assertLess(block.index("await fullResync"), block.index("newlyCreatedProductListingId"))
        self.assertNotIn("API_INTENTS", block)
        self.assertNotIn("record_id", block)

    def test_create_distinguishes_accepted_refresh_failure_from_write_failure(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function createProductListing")
        end = text.index("async function createProposal", start)
        block = text[start:end]
        self.assertIn('"listing.refreshFailed"', block)
        self.assertIn('"warning"', block)
        self.assertIn('"listing.acceptedSelected"', block)
        self.assertIn('"listing.accepted"', block)
        self.assertIn('"listing.failed"', block)


if __name__ == "__main__":
    unittest.main()
