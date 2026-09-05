from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT / "web" / "index.html"
WEB_APP = ROOT / "web" / "app.js"
ANDROID = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
ANDROID_APP = ANDROID / "MarketplaceApp.kt"
ANDROID_CLIENT = ANDROID / "MarketplaceApiClient.kt"
ANDROID_STATE = ANDROID / "MarketplaceState.kt"
DOC = ROOT / "docs" / "m17-1s-structured-client-authoring.md"

FIELDS = (
    "seller_principal", "subject_uri", "title", "description",
    "consideration_coefficient", "consideration_scale", "currency_code",
    "quantity_coefficient", "quantity_scale", "unit_uri",
    "latitude_e6", "longitude_e6",
)


class M17StructuredClientAuthoringArtifactTests(unittest.TestCase):
    def test_web_root_listing_form_exposes_exact_structured_fields(self):
        text = WEB_INDEX.read_text(encoding="utf-8")
        for field in FIELDS:
            self.assertIn(f'id="create-{field.replace("_", "-")}"', text)
        self.assertNotIn('id="create-record-json"', text)

    def test_web_root_create_targets_structured_route_and_preserves_raw_response(self):
        text = WEB_APP.read_text(encoding="utf-8")
        self.assertIn('const API_PRODUCT_LISTINGS = "/api/product-listings";', text)
        self.assertIn("function productListingJsonBody", text)
        self.assertIn("async function createProductListing", text)
        self.assertIn("apiFetch(API_PRODUCT_LISTINGS", text)
        create_start = text.index("async function createProductListing")
        proposal_start = text.index("async function createProposal", create_start)
        create_block = text[create_start:proposal_start]
        self.assertNotIn("API_INTENTS", create_block)
        proposal_block = text[proposal_start:text.index("async function runSyncAction", proposal_start)]
        self.assertIn("PROPOSALS_SUFFIX", proposal_block)
        self.assertIn("API_INTENTS", proposal_block)
        self.assertIn("RESPONSES_SUFFIX", text)

    def test_web_encoder_uses_exact_field_names_and_integer_tokens(self):
        text = WEB_APP.read_text(encoding="utf-8")
        for field in FIELDS:
            self.assertIn(f'"{field}"', text)
        self.assertIn("canonicalIntegerJsonToken", text)
        self.assertIn(r"/^(0|-?[1-9][0-9]*)$/", text)
        self.assertIn("JSON.stringify", text)
        self.assertNotIn("Number.parseInt", text)
        self.assertNotIn("parseFloat", text)

    def test_android_declares_exact_structured_input_contract(self):
        text = ANDROID_CLIENT.read_text(encoding="utf-8")
        self.assertIn('private const val API_PRODUCT_LISTINGS = "/api/product-listings"', text)
        self.assertIn("data class ProductListingInput", text)
        for field in FIELDS:
            self.assertIn(field, text)

    def test_android_state_and_ui_use_structured_root_create_only(self):
        client = ANDROID_CLIENT.read_text(encoding="utf-8")
        state = ANDROID_STATE.read_text(encoding="utf-8")
        app = ANDROID_APP.read_text(encoding="utf-8")
        self.assertIn("suspend fun createProductListing", client)
        self.assertIn("ApiRequest(\"POST\", API_PRODUCT_LISTINGS", client)
        self.assertIn("suspend fun createProductListing", state)
        self.assertIn("client.createProductListing", state)
        self.assertIn("onCreateProductListing", app)
        self.assertIn("ProductListingInput", app)
        self.assertNotIn("onCreateIntent", app)
        self.assertNotIn("state.createIntent", state)
        self.assertIn("respondToIntent", client)
        self.assertIn("rawRecordJson", client)
        self.assertNotIn("client.respondToIntent", state)
        self.assertIn("createProposal", state + app)

    def test_android_encoder_preserves_integer_text_until_json_serialization(self):
        text = ANDROID_CLIENT.read_text(encoding="utf-8")
        self.assertIn("structuredProductListingJson", text)
        self.assertIn("canonicalIntegerJsonToken", text)
        self.assertIn('Regex("0|-?[1-9][0-9]*")', text)
        self.assertIn("jsonString", text)
        self.assertNotIn("toDouble()", text)
        self.assertNotIn("toFloat()", text)

    def test_document_records_parity_and_explicit_non_authority(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "POST /api/product-listings", "Web", "Android",
            "raw response", "M17.1Q/M72", "no browser launch",
            "no Android build", "No runtime activation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
