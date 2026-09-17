from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpProposalReadinessTests(unittest.TestCase):
    def test_proposal_submit_starts_disabled_with_live_readiness_status(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="proposal-readiness"', text)
        readiness = text.split('id="proposal-readiness"', 1)[1].split("</p>", 1)[0]
        self.assertIn('aria-live="polite"', readiness)
        submit = text.split('id="submit-response"', 1)[1].split("</button>", 1)[0]
        self.assertIn("disabled", submit)

    def test_readiness_requires_listing_parent_valid_uris_and_subject_match(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("function proposalDraftLooksReady() {", 1)[1].split("function renderProposalDraftReadiness", 1)[0]
        self.assertIn("selectedProductListingSubjectUri(state.selectedRecord)", block)
        self.assertIn("state.selectedId === null", block)
        for field_id in ("proposal-buyer-principal", "proposal-subject-uri", "proposal-action-uri"):
            self.assertIn(f'reviewedProposalUri(byId("{field_id}").value)', block)
        self.assertIn("submittedSubjectUri === parentSubjectUri", block)
        self.assertNotIn("apiFetch", block)

    def test_readiness_controls_submit_and_rerenders_on_relevant_changes(self):
        text = APP.read_text(encoding="utf-8")
        render = text.split("function renderProposalDraftReadiness() {", 1)[1].split("function proposalJsonBody", 1)[0]
        self.assertIn("responseButton.disabled = !ready", render)
        self.assertIn('"author.proposalDraftReady"', render)
        self.assertIn('"author.proposalDraftIncomplete"', render)
        self.assertIn('byId(id).addEventListener("input", renderProposalDraftReadiness)', text)
        detail = text.split("function renderDetail() {", 1)[1].split("function renderResponseLoading", 1)[0]
        self.assertIn("renderProposalDraftReadiness()", detail)
        example = text.split("function fillSyntheticProposalExample() {", 1)[1].split("async function createProductListing", 1)[0]
        self.assertIn("renderProposalDraftReadiness()", example)

    def test_readiness_copy_is_bilingual_and_dynamic(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('"author.proposalDraftIncomplete": [', text)
        self.assertIn('"author.proposalDraftReady": [', text)
        dynamic = text.split("const DYNAMIC_IDS = new Set([", 1)[1].split("]);", 1)[0]
        self.assertIn('"proposal-readiness"', dynamic)


if __name__ == "__main__":
    unittest.main()
