from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"


class MarketplaceMvpResponseParentNavigationTests(unittest.TestCase):
    def test_detail_exposes_hidden_back_to_parent_control(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="return-parent"', html)
        self.assertIn('hidden>Back to parent listing</button>', html)

    def test_response_click_tracks_exact_rendered_parent_only_in_client_state(self):
        text = APP.read_text(encoding="utf-8")
        render_block = text.split("function renderResponseItems(recordId, ids) {", 1)[1].split("\nasync function renderResponses", 1)[0]
        fetch_block = text.split("async function renderResponses(recordId) {", 1)[1].split("\nfunction selectIntent", 1)[0]
        self.assertIn("state.responseParentId = recordId", render_block)
        self.assertIn("void inspectIntent(id)", render_block)
        self.assertNotIn("apiFetch(", render_block)
        self.assertEqual(fetch_block.count("apiFetch("), 1)

    def test_direct_selection_and_clear_drop_transient_parent_navigation(self):
        text = APP.read_text(encoding="utf-8")
        select_block = text.split("function selectIntent(recordId) {", 1)[1].split("\nasync function inspectIntent", 1)[0]
        self.assertIn("state.detailRequestSerial += 1", select_block)
        self.assertIn("state.responseParentId = null", select_block)
        clear_block = text.split('byId("clear-selection").addEventListener("click", () => {', 1)[1].split("});", 1)[0]
        self.assertIn("state.detailRequestSerial += 1", clear_block)
        self.assertIn("state.responseParentId = null", clear_block)

    def test_return_prefers_synced_parent_and_falls_back_to_reviewed_fetch(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split('returnParentButton.addEventListener("click", () => {', 1)[1].split('byId("clear-selection")', 1)[0]
        self.assertIn("const parentId = state.responseParentId", block)
        self.assertIn("state.records.has(parentId)", block)
        self.assertIn("selectIntent(parentId)", block)
        self.assertIn("void inspectIntent(parentId)", block)
        self.assertNotIn("fetch(", block)

    def test_response_refresh_ignores_stale_success_and_failure_results(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("async function renderResponses(recordId) {", 1)[1].split("\nfunction selectIntent", 1)[0]
        self.assertIn("const requestSerial = state.responseRequestSerial + 1", block)
        self.assertIn("state.responseRequestSerial = requestSerial", block)
        stale_guard = "if (state.selectedId !== recordId || state.responseRequestSerial !== requestSerial) return false;"
        self.assertEqual(block.count(stale_guard), 2)
        self.assertEqual(block.count("return true;"), 2)
        self.assertLess(block.index(stale_guard), block.index("state.responseIds = ids"))
        self.assertLess(block.rindex(stale_guard), block.index("state.responseErrorCode = error.code"))

    def test_detail_inspection_ignores_stale_success_and_failure_results(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("async function inspectIntent(recordId) {", 1)[1].split("\nasync function captureSyncWatermark", 1)[0]
        self.assertIn("const requestSerial = state.detailRequestSerial + 1", block)
        self.assertIn("state.detailRequestSerial = requestSerial", block)
        stale_guard = "if (state.detailRequestSerial !== requestSerial) return false;"
        self.assertEqual(block.count(stale_guard), 2)
        self.assertLess(block.index(stale_guard), block.index("state.selectedId = reviewed"))
        self.assertLess(block.rindex(stale_guard), block.index("state.selectedId = null"))
        self.assertEqual(block.count("return true;"), 2)

    def test_response_detail_surfaces_exact_parent_context_without_io(self):
        text = APP.read_text(encoding="utf-8")
        summary = text.split("function renderSelectedRecordSummary(record) {", 1)[1].split("\nfunction renderProposalParentGuidance", 1)[0]
        self.assertIn("state.responseParentId !== null", summary)
        self.assertIn("state.selectedId !== state.responseParentId", summary)
        self.assertIn('i18n.t("detail.responseParent", { recordId: state.responseParentId })', summary)
        self.assertIn("selectedRecordSummary.append(parent)", summary)
        self.assertNotIn("apiFetch(", summary)
        self.assertNotIn("fetch(", summary)

    def test_back_button_visibility_is_navigation_only(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("function renderDetail() {", 1)[1].split("\nasync function renderResponses", 1)[0]
        self.assertIn("state.responseParentId !== null", block)
        self.assertIn("state.selectedId !== state.responseParentId", block)
        self.assertIn("returnParentButton.hidden = !canReturnToParent", block)
        self.assertIn("returnParentButton.disabled = !canReturnToParent", block)


if __name__ == "__main__":
    unittest.main()
