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
            'id="create-record-json"',
            'id="response-record-json"',
            'id="sync-status"',
        ):
            self.assertIn(marker, text)
    def test_api_client_uses_only_same_origin_product_routes(self):
        text = APP.read_text(encoding="utf-8")
        for marker in (
            '"/api/intents"',
            '"/api/sync"',
            '"/responses"',
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

    def test_authoring_remains_raw_reviewed_record_json_boundary(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("create-record-json", INDEX.read_text(encoding="utf-8"))
        self.assertIn("response-record-json", INDEX.read_text(encoding="utf-8"))
        self.assertIn('"Content-Type": "application/json"', text)
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
