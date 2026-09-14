from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpProposalBrowseSummaryTests(unittest.TestCase):
    def render_list_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function renderList() {", 1)[1].split("\nfunction selectedProductListingSubjectUri", 1)[0]

    def filtered_records_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function filteredRecords() {", 1)[1].split("\nfunction localizedIntentCount", 1)[0]

    def test_browse_reuses_fail_closed_proposal_summary(self):
        block = self.render_list_block()
        self.assertIn("const summary = proposalResponseSummary(record);", block)
        self.assertIn("if (summary === null)", block)
        self.assertIn('displayText(record, "/term/title", i18n.t("browse.fallback"))', block)

    def test_proposal_card_is_bilingual_and_readable(self):
        text = APP.read_text(encoding="utf-8")
        block = self.render_list_block()
        self.assertIn('i18n.t("responses.proposal")', block)
        self.assertIn('i18n.t("browse.proposalMetadata"', block)
        self.assertIn('"Buyer {buyer} · Subject {subject} · Action {action}"', text)
        self.assertIn('"Покупатель {buyer} · Предмет {subject} · Действие {action}"', text)

    def test_browse_summary_adds_no_fetch_or_unsafe_html(self):
        block = self.render_list_block()
        self.assertNotIn("apiFetch(", block)
        self.assertNotIn("fetch(", block)
        self.assertNotIn("innerHTML", block)
        self.assertIn('card.addEventListener("click", () => selectIntent(recordId));', block)

    def test_record_identity_remains_exact_and_separate(self):
        block = self.render_list_block()
        self.assertIn("identity.textContent = recordId", block)
        self.assertIn("card.append(title, metadata, identity);", block)
        self.assertNotIn("translateRecord", block)
        self.assertNotIn("translateUri", block)

    def test_filter_matches_the_same_visible_proposal_text_as_the_card(self):
        block = self.filtered_records_block()
        self.assertIn("const summary = proposalResponseSummary(record);", block)
        self.assertIn('i18n.t("responses.proposal")', block)
        self.assertIn('i18n.t("browse.proposalMetadata"', block)
        self.assertIn("[recordId, title, metadata].some", block)

    def test_filter_adds_no_fetch_write_or_protocol_translation(self):
        block = self.filtered_records_block()
        self.assertNotIn("apiFetch(", block)
        self.assertNotIn("fetch(", block)
        self.assertNotIn("innerHTML", block)
        self.assertNotIn("translateRecord", block)
        self.assertNotIn("translateUri", block)


if __name__ == "__main__":
    unittest.main()
