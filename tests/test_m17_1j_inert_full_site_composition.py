from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.composition import compose_marketplace_application
from marketplace.application.http import ApplicationHttpRequest
from marketplace.application.postgres_state import ExpiryResult


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-1j-inert-full-site-composition.md"
SOURCE = ROOT / "src" / "marketplace" / "application" / "composition.py"
INDEX = b"<!doctype html><title>Marketplace</title>"
APP_JS = b"console.log('marketplace');\n"
STYLES = b"body { margin: 0; }\n"


class MinimalStore:
    def __init__(self) -> None:
        self.initialize_calls = 0

    def initialize(self):
        self.initialize_calls += 1
        return ExpiryResult((), ())


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage(("r-root",), None)


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_composition():
    store = MinimalStore()
    composition = compose_marketplace_application(
        store=store,
        intent_query=StaticIntentQuery(),
        prepare_record=lambda record: record,
        decode_record=lambda payload: payload,
        response_parent_ids=lambda record: (),
        is_intent_record=lambda record: True,
        decode_record_json=decode_json,
        encode_record_json=encode_json,
        index_html=INDEX,
        app_js=APP_JS,
        styles_css=STYLES,
    )
    return composition, store


class M17InertFullSiteCompositionTests(unittest.TestCase):
    def test_composition_exposes_exact_same_http_adapter_through_site(self):
        composition, store = make_composition()
        self.assertIs(composition.site._application_http, composition.http)
        response = composition.site.handle(ApplicationHttpRequest("GET", "/api/intents", (), None, b""))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(store.initialize_calls, 0)

    def test_static_assets_are_exact_injected_bytes_without_initialization(self):
        composition, store = make_composition()
        for path, expected in (("/", INDEX), ("/index.html", INDEX), ("/app.js", APP_JS), ("/styles.css", STYLES)):
            with self.subTest(path=path):
                response = composition.site.handle(ApplicationHttpRequest("GET", path, (), None, b""))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.body, expected)
        self.assertEqual(store.initialize_calls, 0)

    def test_initialize_remains_explicit_and_shared_api_becomes_ready_once(self):
        composition, store = make_composition()
        self.assertEqual(composition.initialize(), ExpiryResult((), ()))
        response = composition.site.handle(ApplicationHttpRequest("GET", "/api/intents", (), None, b""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(decode_json(response.body)["record_ids"], ["r-root"])
        self.assertEqual(store.initialize_calls, 1)

    def test_composition_remains_frozen(self):
        composition, _ = make_composition()
        with self.assertRaises(FrozenInstanceError):
            composition.site = None

    def test_source_and_document_preserve_inert_authority_boundary(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in ("import socket", "from socket", "subprocess", "os.environ", "Path(", "open("):
            self.assertNotIn(forbidden, text)
        self.assertTrue(DOC.is_file())
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "inert full-site application composition",
            "caller-injected static bytes",
            "no live PostgreSQL connection",
            "no HTTP listener/server activation",
            "no runtime filesystem asset loading",
        ):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
