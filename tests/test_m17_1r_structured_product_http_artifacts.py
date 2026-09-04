from __future__ import annotations

import json
from pathlib import Path
import unittest

from marketplace import application
from marketplace.application.api import IntentIndexPage
from marketplace.application.composition import compose_marketplace_application


ROOT = Path(__file__).resolve().parents[1]
HTTP = ROOT / "src" / "marketplace" / "application" / "http.py"
COMPOSITION = ROOT / "src" / "marketplace" / "application" / "composition.py"
LAUNCH = ROOT / "src" / "marketplace" / "application" / "launch.py"
DOC = ROOT / "docs" / "m17-1r-structured-product-http.md"


class MinimalStore:
    def initialize(self):
        raise AssertionError("M17.1R artifact composition must remain inert")


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage((), None)


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


class M17StructuredProductHttpArtifactTests(unittest.TestCase):
    def test_public_application_exports_creator_contract(self):
        self.assertTrue(hasattr(application, "ProductListingCreator"))
        self.assertIn("ProductListingCreator", application.__all__)

    def test_composition_wires_authoring_service_to_http_without_initialization(self):
        composition = compose_marketplace_application(
            store=MinimalStore(),
            intent_query=StaticIntentQuery(),
            prepare_record=lambda record: record,
            decode_record=lambda payload: payload,
            response_parent_ids=lambda record: (),
            is_intent_record=lambda record: True,
            decode_record_json=decode_json,
            encode_record_json=encode_json,
            build_product_listing_record=lambda draft: object(),
            index_html=b"<html></html>",
            app_js=b"console.log(1)",
            styles_css=b"body{}",
        )
        self.assertIs(composition.authoring._api, composition.api)
        self.assertIs(composition.http._create_product_listing.__self__, composition.authoring)

    def test_source_preserves_reference_and_runtime_authority_boundary(self):
        http = HTTP.read_text(encoding="utf-8")
        composition = COMPOSITION.read_text(encoding="utf-8")
        launch = LAUNCH.read_text(encoding="utf-8")
        self.assertIn('"/api/product-listings"', http)
        self.assertIn("ProductListingAuthoringFields", http)
        self.assertIn("MarketplaceProductListingAuthoringService", composition)
        self.assertIn("build_product_listing_record", composition)
        for text in (http, composition, launch):
            lowered = text.lower()
            for forbidden in (
                "marketplace.reference",
                "from ..reference",
                "import socket",
                "from socket",
                "subprocess",
                "os.environ",
                "psycopg",
            ):
                self.assertNotIn(forbidden, lowered)

    def test_document_records_route_raw_path_and_deferred_clients(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "POST /api/product-listings",
            "POST /api/intents",
            "PRODUCT_LISTING_REQUEST_INVALID",
            "ProductListingAuthoringFields",
            "does not modify `web/**` or `android/**`",
            "No live PostgreSQL connection",
            "Uvicorn/server/socket activation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
