from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = WEB / "index.html"
APP = WEB / "app.js"
STYLE = WEB / "styles.css"
DOC = ROOT / "docs" / "m17-1c-web-application.md"


class M17WebApplicationArtifactTests(unittest.TestCase):
    def test_web_application_source_files_exist(self):
        for path in (INDEX, APP, STYLE, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_shell_exposes_map_list_detail_create_and_respond_surfaces(self):
        text = INDEX.read_text(encoding="utf-8")
        for marker in (
            'id="market-map"',
            'id="intent-list"',
            'id="intent-detail"',
            'id="create-seller-principal"',
            'id="proposal-buyer-principal"',
            'id="proposal-subject-uri"',
            'id="proposal-action-uri"',
            'id="sync-status"',
        ):
            self.assertIn(marker, text)
    def test_api_client_uses_only_same_origin_product_routes(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            '"/api/intents"',
            '"/api/sync"',
            '"/responses"',
            '"/proposals"',
            'credentials: "omit"',
            'cache: "no-store"',
            'redirect: "error"',
            'referrerPolicy: "no-referrer"',
        ):
            self.assertIn(marker, text)
        lowered = text.lower()
        for forbidden in (
            "http://",
            "https://",
            "websocket",
            "eventsource",
            "navigator.sendbeacon",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_web_client_does_not_persist_credentials_or_state(self):
        lowered = (INDEX.read_text(encoding="utf-8") + APP.read_text(encoding="utf-8")).lower()
        for forbidden in (
            "localstorage",
            "sessionstorage",
            "indexeddb",
            "document.cookie",
            "serviceworker",
        ):
            self.assertNotIn(forbidden, lowered)
    def test_hostile_record_text_uses_safe_dom_primitives(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("textContent", text)
        self.assertIn("replaceChildren", text)
        self.assertNotIn("innerHTML", text)
        self.assertNotIn("insertAdjacentHTML", text)
        self.assertNotIn("document.write", text)

    def test_sync_recovery_captures_snapshot_watermark_before_hydration(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "captureSyncWatermark",
            "fullResync",
            "SYNC_CURSOR_EXPIRED",
            "next_cursor",
            "syncCursor",
        ):
            self.assertIn(marker, text)
        capture = text.index("await captureSyncWatermark")
        hydrate = text.index("await hydrateCurrentIntents")
        self.assertLess(capture, hydrate)

    def test_full_resync_traverses_bounded_intent_pages_before_advancing_cursor(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "MAX_LIST_PAGES",
            "encodeURIComponent(cursor)",
            "INTENT_LIST_TRUNCATED",
            "seenCursors",
        ):
            self.assertIn(marker, text)
        hydrate = text.index("await hydrateCurrentIntents")
        advance = text.index("state.syncCursor = watermark", hydrate)
        self.assertLess(hydrate, advance)

    def test_sync_changes_refresh_root_index_without_classifying_records(self):
        text = APP.read_text(encoding="utf-8")
        apply_start = text.index("async function applySyncPage")
        sync_start = text.index("async function incrementalSync", apply_start)
        apply_block = text[apply_start:sync_start]
        self.assertNotIn("state.records.set(", apply_block)
        self.assertNotIn("state.records.delete(", apply_block)
        sync_end = text.index("function canonicalIntegerJsonToken", sync_start)
        sync_block = text[sync_start:sync_end]
        self.assertIn("browseDirty", sync_block)
        self.assertIn("await hydrateCurrentIntents()", sync_block)

    def test_response_identity_uses_separate_exact_detail_hydration(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("selectedRecord", text)
        self.assertIn("async function inspectIntent", text)
        self.assertIn('item.addEventListener("click", () => void inspectIntent(id));', text)
        inspect_start = text.index("async function inspectIntent")
        inspect_end = text.index("async function captureSyncWatermark", inspect_start)
        self.assertNotIn("state.records.set(", text[inspect_start:inspect_end])

    def test_incremental_sync_does_not_claim_complete_when_page_budget_is_exhausted(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function incrementalSync")
        end = text.index("function canonicalIntegerJsonToken", start)
        block = text[start:end]
        self.assertIn("let hasMore", block)
        self.assertIn("if (hasMore)", block)
        self.assertIn("more changes remain", block)
        bounded = block.index("if (hasMore)")
        success = block.index("Synchronized at local cursor")
        self.assertLess(bounded, success)

    def test_product_authoring_surfaces_are_structured(self):
        text = APP.read_text(encoding="utf-8")
        index = INDEX.read_text(encoding="utf-8")
        self.assertIn("create-seller-principal", index)
        self.assertNotIn("create-record-json", index)
        self.assertNotIn("response-record-json", index)
        self.assertIn("proposal-buyer-principal", index)
        self.assertIn('"/api/product-listings"', text)
        self.assertIn('"/proposals"', text)
        for forbidden in ("buildMarketIntent", "validateMarketIntent", "recordIdentity", "signRecord"):
            self.assertNotIn(forbidden, text)
    def test_web_design_document_preserves_authority_boundary(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.1C Web",
            "same-origin",
            "presentation-only",
            "snapshot watermark",
            "no browser launch",
            "no live HTTP server",
            "no local persistent storage",
            "M17.1D Android",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
