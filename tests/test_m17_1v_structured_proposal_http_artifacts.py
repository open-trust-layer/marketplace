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
DOC = ROOT / "docs" / "m17-1v-structured-proposal-http.md"


class MinimalStore:
    def initialize(self):
        raise AssertionError("M17.1V composition must remain inert")


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage((), None)


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


class M17StructuredProposalHttpArtifactTests(unittest.TestCase):
    def test_public_application_exports_proposal_creator_contract(self):
        self.assertTrue(hasattr(application, "ProposalCreator"))
        self.assertIn("ProposalCreator", application.__all__)

    def test_composition_wires_proposal_authoring_without_initialization(self):
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
            build_proposal_record=lambda draft: object(),
            index_html=b"<html></html>",
            app_js=b"console.log(1)",
            styles_css=b"body{}",
        )
        self.assertIs(composition.proposal_authoring._api, composition.api)
        self.assertIs(
            composition.http._create_proposal.__self__,
            composition.proposal_authoring,
        )

    def test_source_preserves_reference_and_runtime_authority_boundary(self):
        http = HTTP.read_text(encoding="utf-8")
        composition = COMPOSITION.read_text(encoding="utf-8")
        launch = LAUNCH.read_text(encoding="utf-8")
        self.assertIn('"proposals"', http)
        self.assertIn("BuyerRequestProposalDraft", http)
        self.assertIn("MarketplaceProposalAuthoringService", composition)
        self.assertIn("build_proposal_record", launch)
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

    def test_document_records_route_and_semantic_exclusions(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "POST /api/intents/{parent_record_id}/proposals",
            "POST /api/intents/{parent_record_id}/responses",
            "PROPOSAL_REQUEST_INVALID",
            "BuyerRequestProposalDraft",
            "No universal `ACTION_BUY`",
            "No live PostgreSQL connection",
            "server/socket activation",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
