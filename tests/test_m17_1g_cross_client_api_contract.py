from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "marketplace-application-http-v1.json"
HTTP = ROOT / "src" / "marketplace" / "application" / "http.py"
WEB = ROOT / "web" / "app.js"
ANDROID = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceApiClient.kt"
DOC = ROOT / "docs" / "m17-1g-cross-client-api-contract.md"


class M17CrossClientApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8")) if CONTRACT.is_file() else {}

    def test_required_parity_artifacts_exist(self):
        for path in (CONTRACT, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_fixture_preserves_reviewed_http_profile(self):
        self.assertEqual(self.contract["schema"], "marketplace-application-http-v1")
        self.assertEqual(self.contract["page_limit"], 64)
        self.assertEqual(self.contract["max_request_json_bytes"], 256 * 1024)
        self.assertEqual(self.contract["max_response_json_bytes"], 300 * 1024)
        self.assertEqual(self.contract["sync_cursor_scope"], "local-application-coordination-only")

    def test_fixture_routes_and_shapes_are_exact(self):
        routes = self.contract["routes"]
        self.assertEqual(
            routes,
            {
                "list_intents": {"method": "GET", "path": "/api/intents?limit={limit}", "cursor_path": "/api/intents?cursor={cursor}&limit={limit}", "response_keys": ["record_ids", "next_cursor"]},
                "create_intent": {"method": "POST", "path": "/api/intents", "response_keys": ["change_seq", "disposition"]},
                "get_intent": {"method": "GET", "path": "/api/intents/{record_id}"},
                "list_responses": {"method": "GET", "path": "/api/intents/{record_id}/responses?limit={limit}", "response_keys": ["record_ids"], "cursor": False},
                "respond": {"method": "POST", "path": "/api/intents/{record_id}/responses", "response_keys": ["change_seq", "disposition"]},
                "sync_watermark": {"method": "GET", "path": "/api/sync?limit={limit}"},
                "sync": {"method": "GET", "path": "/api/sync?cursor={cursor}&limit={limit}"},
            },
        )
        self.assertEqual(self.contract["write_dispositions"], ["STORED", "DUPLICATE"])
        self.assertEqual(self.contract["sync_change_keys"], ["change_kind", "record_id", "seq"])
        self.assertEqual(self.contract["sync_page_keys"], ["changes", "next_cursor", "has_more"])
        self.assertEqual(self.contract["sync_expired"], {"status": 409, "error_code": "SYNC_CURSOR_EXPIRED"})

    def test_python_binding_matches_fixture_bounds_and_fields(self):
        text = HTTP.read_text(encoding="utf-8")
        for marker in (
            "MAX_APPLICATION_HTTP_BODY_BYTES = 256 * 1024",
            "MAX_APPLICATION_HTTP_RESPONSE_BYTES = 300 * 1024",
            '"record_ids"', '"next_cursor"', '"change_seq"', '"disposition"',
            '"changes"', '"change_kind"', '"record_id"', '"seq"', '"has_more"',
            '"SYNC_CURSOR_EXPIRED"',
        ):
            self.assertIn(marker, text)

    def test_web_client_matches_shared_paths_and_response_bound(self):
        text = WEB.read_text(encoding="utf-8")
        for marker in (
            'const API_INTENTS = "/api/intents";',
            'const API_SYNC = "/api/sync";',
            'const RESPONSES_SUFFIX = "/responses";',
            "const PAGE_LIMIT = 64;",
            "const MAX_RESPONSE_JSON_BYTES = 300 * 1024;",
            'error.code === "SYNC_CURSOR_EXPIRED"',
        ):
            self.assertIn(marker, text)
        self.assertIn("new TextEncoder().encode(text).length > MAX_RESPONSE_JSON_BYTES", text)

    def test_android_client_matches_shared_paths_and_response_bound(self):
        text = ANDROID.read_text(encoding="utf-8")
        for marker in (
            'private const val API_INTENTS = "/api/intents"',
            'private const val API_SYNC = "/api/sync"',
            'private const val RESPONSES_SUFFIX = "/responses"',
            "private const val PAGE_LIMIT = 64",
            "private const val MAX_RESPONSE_JSON_BYTES = 300 * 1024",
            '"SYNC_CURSOR_EXPIRED"',
        ):
            self.assertIn(marker, text)

    def test_document_keeps_fixture_declarative_and_authority_neutral(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "M17.1G cross-client API contract parity",
            "declarative test fixture",
            "response listing remains non-cursor",
            "local application coordination only",
            "no Android build or dependency resolution authority",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
