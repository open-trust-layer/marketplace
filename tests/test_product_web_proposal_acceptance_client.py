from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "proposal_acceptance_client.js"
SESSION = ROOT / "web" / "client_session.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "product-browser-proposal-acceptance.md"


class ProductWebProposalAcceptanceClientTests(unittest.TestCase):
    def test_source_is_delivered_only_through_authenticated_module_bundle(self) -> None:
        self.assertTrue(SOURCE.is_file())
        marker = "proposal_acceptance_client.js"
        self.assertIn(f'"/{marker}"', SITE_HOST.read_text(encoding="utf-8"))
        self.assertIn(f'"web/{marker}"', LOCALHOST.read_text(encoding="utf-8"))
        self.assertNotIn(marker, INDEX.read_text(encoding="utf-8"))
        self.assertNotIn(marker, APP.read_text(encoding="utf-8"))
        self.assertEqual(BOOTSTRAP.read_text(encoding="utf-8").count(f'from "./{marker}"'), 1)

    def test_client_uses_exact_empty_authenticated_post(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"/api/intents/" + encodeURIComponent(proposalRecordId) + "/acceptance"', text)
        self.assertIn('authorizationFor("POST", path)', text)
        self.assertIn('method: "POST"', text)
        self.assertIn('Accept: "application/json"', text)
        self.assertNotIn('"Content-Type"', text)
        self.assertNotIn("body:", text)
        self.assertNotIn("seller_principal", text)

    def test_client_uses_exact_authenticated_get_for_resolution(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        start = text.index("async function resolveAcceptance")
        end = text.index("async function acceptProposal", start)
        block = text[start:end]
        self.assertIn('authorizationFor("GET", path)', block)
        self.assertIn('method: "GET"', block)
        self.assertIn('Accept: "application/json"', block)
        self.assertNotIn('"Content-Type"', block)
        self.assertNotIn("body:", block)
        self.assertIn("decodeResolutionResponse", block)
        self.assertIn(
            '["proposal_record_id", "record_id"]',
            text,
        )
        self.assertIn("proposalRecordId !== expectedProposalRecordId", text)

    def test_response_is_exact_bounded_publication_metadata(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('["change_seq", "disposition", "record_id"]', text)
        self.assertIn('["STORED", "DUPLICATE"]', text)
        self.assertIn("Number.isSafeInteger(value.change_seq)", text)
        self.assertIn("recordId", text)
        self.assertIn("changeSeq", text)

    def test_session_route_scope_includes_only_exact_acceptance_tail(self) -> None:
        text = SESSION.read_text(encoding="utf-8")
        self.assertIn('tail === "acceptance"', text)
        self.assertIn('parts.length !== 2', text)
        self.assertIn('parts[0].includes("?") || parts[0].includes("#")', text)

    def test_bootstrap_requires_active_session_and_never_exposes_bearer(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("function proposalAcceptanceClient()", text)
        self.assertIn("if (!session.isActive)", text)
        self.assertIn('stableBootstrapError("PROPOSAL_ACCEPTANCE_AUTH_REQUIRED")', text)
        self.assertNotIn("Bearer ", text)

    def test_active_page_requires_exact_seller_and_explicit_click(self) -> None:
        text = APP.read_text(encoding="utf-8")
        self.assertIn("authSnapshot.principal !== parentListing.sellerPrincipal", text)
        self.assertIn('acceptProposalButton.addEventListener("click"', text)
        self.assertIn("authBootstrap.proposalAcceptanceClient()", text)
        self.assertIn("client.acceptProposal(proposalId)", text)
        self.assertIn("state.proposalAcceptanceResults.set(proposalId, result)", text)

    def test_no_persistence_background_retry_or_agreement_signing_in_acceptance_path(self) -> None:
        source = SOURCE.read_text(encoding="utf-8").lower()
        app = APP.read_text(encoding="utf-8")
        start = app.index("async function acceptSelectedProposal()")
        end = app.index("function renderAgreementFormationHandoff(record)", start)
        acceptance_handler = app[start:end].lower()
        combined = source + "\n" + acceptance_handler
        for forbidden in (
            "localstorage", "sessionstorage", "indexeddb", "document.cookie",
            "serviceworker", "setinterval", "settimeout", "websocket",
            "eventsource", "retry", "signandsubmit(", "createagreementassentsignature(",
        ):
            self.assertNotIn(forbidden, combined)

    def test_document_records_explicit_click_and_semantic_boundary(self) -> None:
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_PROPOSAL_ACCEPTANCE_CLIENT_V1",
            "explicit user click",
            "exact authenticated seller",
            "empty POST",
            "memory-only",
            "does not form an Agreement",
            "no payment",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
