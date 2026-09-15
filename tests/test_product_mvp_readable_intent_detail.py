from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"


class MarketplaceMvpReadableIntentDetailTests(unittest.TestCase):
    def summary_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function renderSelectedRecordSummary(record) {", 1)[1].split("\nfunction renderProposalParentGuidance", 1)[0]

    def detail_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function renderDetail() {", 1)[1].split("\nfunction renderResponseItems", 1)[0]

    def test_detail_shell_keeps_identity_summary_and_raw_json_separate(self):
        html = INDEX.read_text(encoding="utf-8")
        record_id = html.index('id="selected-record-id"')
        summary = html.index('id="selected-record-summary"')
        raw_json = html.index('id="selected-record-json"')
        self.assertLess(record_id, summary)
        self.assertLess(summary, raw_json)
        self.assertIn('id="selected-record-summary" class="intent-card" hidden', html)

    def test_summary_reuses_fail_closed_listing_and_proposal_parsers(self):
        block = self.summary_block()
        self.assertIn("proposalResponseSummary(record)", block)
        self.assertIn("productListingSummary(record)", block)
        self.assertIn('i18n.t("responses.proposal")', block)
        self.assertIn('i18n.t("browse.proposalMetadata"', block)
        self.assertIn('displayText(record, "/term/title", i18n.t("browse.fallback"))', block)
        self.assertIn('i18n.t("browse.listingMetadata"', block)
        self.assertIn("selectedRecordSummary.hidden = false", block)

    def test_summary_adds_no_io_or_protocol_translation(self):
        block = self.summary_block()
        self.assertNotIn("apiFetch(", block)
        self.assertNotIn("fetch(", block)
        self.assertNotIn("innerHTML", block)
        self.assertNotIn("localStorage", block)
        self.assertNotIn("sessionStorage", block)
        self.assertNotIn("translateRecord", block)
        self.assertNotIn("translateUri", block)

    def test_detail_keeps_exact_record_id_and_raw_json_audit_view(self):
        block = self.detail_block()
        self.assertIn('selectedRecordId.textContent = state.selectedId ?? i18n.t("detail.none")', block)
        self.assertIn("renderSelectedRecordSummary(record)", block)
        self.assertIn("JSON.stringify(record, null, 2)", block)

    def test_language_change_rerenders_detail_from_cached_state(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("i18n.onChange(() => {", 1)[1].split("});", 1)[0]
        self.assertIn("renderDetail()", block)
        self.assertNotIn("apiFetch(", block)


if __name__ == "__main__":
    unittest.main()
