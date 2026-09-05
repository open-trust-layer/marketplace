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
DOC = ROOT / "docs" / "m17-1w-structured-proposal-clients.md"

PROPOSAL_FIELDS = ("buyer_principal", "subject_uri", "action_uri")


class M17StructuredProposalClientArtifactTests(unittest.TestCase):
    def test_web_product_form_uses_exact_structured_proposal_fields(self):
        text = WEB_INDEX.read_text(encoding="utf-8")
        for field in PROPOSAL_FIELDS:
            self.assertIn(f'id="proposal-{field.replace("_", "-")}"', text)
        self.assertNotIn('id="response-record-json"', text)
        self.assertIn("Create Proposal", text)

    def test_web_submits_only_structured_proposal_to_selected_parent(self):
        text = WEB_APP.read_text(encoding="utf-8")
        self.assertIn('const PROPOSALS_SUFFIX = "/proposals";', text)
        self.assertIn("function proposalJsonBody", text)
        self.assertIn("async function createProposal", text)
        block_start = text.index("async function createProposal")
        block_end = text.index("async function runSyncAction", block_start)
        block = text[block_start:block_end]
        self.assertIn("PROPOSALS_SUFFIX", block)
        self.assertIn("proposalJsonBody", block)
        self.assertNotIn("reviewedRecordJsonBody", block)
        self.assertIn("RESPONSES_SUFFIX", text)

    def test_web_encoder_contains_only_reviewed_proposal_fields(self):
        text = WEB_APP.read_text(encoding="utf-8")
        for field in PROPOSAL_FIELDS:
            self.assertIn(field, text)
        self.assertIn("JSON.stringify", text)
        self.assertIn("PROPOSAL_JSON_TOO_LARGE", text)

    def test_android_declares_structured_proposal_input_and_route(self):
        text = ANDROID_CLIENT.read_text(encoding="utf-8")
        self.assertIn('private const val PROPOSALS_SUFFIX = "/proposals"', text)
        self.assertIn("data class ProposalInput", text)
        for field in PROPOSAL_FIELDS:
            self.assertIn(f"val {field}: String", text)
        self.assertIn("suspend fun createProposal", text)
        self.assertIn("structuredProposalJson", text)
        self.assertIn("PROPOSALS_SUFFIX", text)

    def test_android_product_state_and_ui_use_structured_proposal_only(self):
        client = ANDROID_CLIENT.read_text(encoding="utf-8")
        state = ANDROID_STATE.read_text(encoding="utf-8")
        app = ANDROID_APP.read_text(encoding="utf-8")
        self.assertIn("suspend fun createProposal", state)
        self.assertIn("client.createProposal", state)
        self.assertNotIn("client.respondToIntent", state)
        self.assertIn("onCreateProposal", app)
        self.assertIn("ProposalInput", app)
        self.assertNotIn("responseJson", app)
        self.assertIn("suspend fun respondToIntent", client)
        self.assertIn("rawRecordJson", client)

    def test_android_encoder_is_exact_bounded_and_non_semantic(self):
        text = ANDROID_CLIENT.read_text(encoding="utf-8")
        self.assertIn("private fun structuredProposalJson", text)
        self.assertIn("PROPOSAL_JSON_TOO_LARGE", text)
        for field in PROPOSAL_FIELDS:
            self.assertIn(field, text)
        self.assertNotIn("ACTION_BUY", text)

    def test_document_records_parity_raw_boundary_and_non_authority(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "POST /api/intents/{parent_record_id}/proposals",
            "Web", "Android", "raw `/responses`", "caller-supplied `action_uri`",
            "no browser launch", "no Android build", "No runtime activation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
