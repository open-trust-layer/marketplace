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
        block = text.split("async function renderResponses(recordId) {", 1)[1].split("\nfunction selectIntent", 1)[0]
        self.assertIn("state.responseParentId = recordId", block)
        self.assertIn("void inspectIntent(id)", block)
        self.assertEqual(block.count("apiFetch("), 1)

    def test_direct_selection_and_clear_drop_transient_parent_navigation(self):
        text = APP.read_text(encoding="utf-8")
        select_block = text.split("function selectIntent(recordId) {", 1)[1].split("\nasync function inspectIntent", 1)[0]
        self.assertIn("state.responseParentId = null", select_block)
        clear_block = text.split('byId("clear-selection").addEventListener("click", () => {', 1)[1].split("});", 1)[0]
        self.assertIn("state.responseParentId = null", clear_block)

    def test_return_prefers_synced_parent_and_falls_back_to_reviewed_fetch(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split('returnParentButton.addEventListener("click", () => {', 1)[1].split('byId("clear-selection")', 1)[0]
        self.assertIn("const parentId = state.responseParentId", block)
        self.assertIn("state.records.has(parentId)", block)
        self.assertIn("selectIntent(parentId)", block)
        self.assertIn("void inspectIntent(parentId)", block)
        self.assertNotIn("fetch(", block)

    def test_back_button_visibility_is_navigation_only(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("function renderDetail() {", 1)[1].split("\nasync function renderResponses", 1)[0]
        self.assertIn("state.responseParentId !== null", block)
        self.assertIn("state.selectedId !== state.responseParentId", block)
        self.assertIn("returnParentButton.hidden = !canReturnToParent", block)
        self.assertIn("returnParentButton.disabled = !canReturnToParent", block)


if __name__ == "__main__":
    unittest.main()
