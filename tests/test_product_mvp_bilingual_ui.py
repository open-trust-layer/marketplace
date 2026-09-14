from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
STYLE = ROOT / "web" / "styles.css"


class MarketplaceMvpBilingualUiTests(unittest.TestCase):
    def test_shell_keeps_localization_inside_reviewed_app_asset(self):
        html = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        self.assertNotIn('src="i18n.js"', html)
        self.assertEqual(html.count('<script src="app.js" defer></script>'), 1)
        self.assertLess(app.index('window.MarketplaceI18n = (() => {'), app.index('const API_INTENTS'))
        self.assertIn('<html lang="en">', html)

    def test_catalog_is_explicitly_bilingual(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('new Set(["en", "ru"])', text)
        self.assertIn('["Sync now", "Синхронизировать"]', text)
        self.assertIn('["Marketplace browser", "Обзор Marketplace"]', text)
        self.assertIn('["Create product listing", "Создать объявление"]', text)
        self.assertIn('["Buyer Proposal", "Предложение покупателя"]', text)
        self.assertIn('document.documentElement.lang = language', text)
    def test_switch_is_in_memory_and_dependency_free(self):
        text = APP.read_text(encoding="utf-8")
        localization = text.split('\n"use strict";\n\nconst API_INTENTS', 1)[0]
        for forbidden in (
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "fetch(", "XMLHttpRequest", "WebSocket", "innerHTML", "insertAdjacentHTML",
        ):
            self.assertNotIn(forbidden, localization)
        self.assertIn('english.textContent = "EN"', localization)
        self.assertIn('russian.textContent = "RU"', localization)
        self.assertIn('setLanguage("en")', localization)
        self.assertIn('setLanguage("ru")', localization)
        self.assertIn('aria-pressed', localization)

    def test_language_change_rerenders_dynamic_presentation_only(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("i18n.onChange(() => {", 1)[1].split("\n\nrenderSyncStatus();", 1)[0]
        for marker in (
            "renderSyncStatus()", "renderFormStatuses()", "renderList()",
            "renderDetail()", "renderResponseItems", "renderMvpFlightState()",
        ):
            self.assertIn(marker, block)
        self.assertNotIn("apiFetch(", block)
        self.assertNotIn("fullResync", block)

    def test_protocol_payload_builders_remain_language_neutral(self):
        text = APP.read_text(encoding="utf-8")
        listing = text.split("function productListingJsonBody() {", 1)[1].split("\nfunction reviewedProposalUri", 1)[0]
        proposal = text.split("function proposalJsonBody() {", 1)[1].split("\nfunction renderFormStatus", 1)[0]
        self.assertNotIn("i18n", listing)
        self.assertNotIn("i18n", proposal)
        self.assertIn("JSON.stringify(value)", listing)
        self.assertIn("reviewedProposalUri", proposal)
    def test_dynamic_statuses_store_translation_keys_not_rendered_language(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('setStatus("sync.done", { cursor: watermark }, "success")', text)
        self.assertIn('setFormStatus("create-status", "listing.submitting")', text)
        self.assertIn('setFormStatus("response-status", "proposal.submitting")', text)
        self.assertIn('setFormStatus("mvp-flight-status", "mvp.running")', text)
        self.assertIn('i18n.t(state.syncUi.key, state.syncUi.variables)', text)
        self.assertIn('i18n.t(ui.key, ui.variables)', text)

    def test_switch_styling_is_responsive_and_scoped(self):
        css = STYLE.read_text(encoding="utf-8")
        self.assertIn(".language-switch", css)
        self.assertIn("button.language-option", css)
        self.assertIn('button.language-option[aria-pressed="true"]', css)
        self.assertIn("flex-wrap: wrap", css)

    def test_no_translation_changes_reviewed_json_or_record_identity(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("JSON.stringify(record, null, 2)", text)
        self.assertIn("identity.textContent = recordId", text)
        self.assertIn("mvpFlightAudit.textContent", text)
        self.assertNotIn("translateRecord", text)
        self.assertNotIn("translateUri", text)


if __name__ == "__main__":
    unittest.main()
