from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "web" / "client_session.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7k-select-web-publication-fulfillment-clients.md"


class M177KSelectWebPublicationFulfillmentClientsTests(unittest.TestCase):
    def test_session_admits_only_exact_new_post_route_shapes(self) -> None:
        text = SESSION.read_text(encoding="utf-8")
        for marker in (
            "function reviewedAgreementPublicationRoute(path)",
            "function reviewedFulfillmentCompletionRoute(path)",
            'parts.length !== 1',
            'parts.length !== 4',
            'parts[1] !== "commitments"',
            'parts[3] !== "completion-evidence"',
            '/^[A-Za-z][A-Za-z0-9._-]{0,63}$/.test(parts[2])',
            "reviewedAgreementPublicationRoute(path)",
            "reviewedFulfillmentCompletionRoute(path)",
        ):
            self.assertIn(marker, text)
        start = text.index("function reviewedAuthenticatedRoute")
        end = text.index("class MarketplaceMemorySession", start)
        block = text[start:end]
        self.assertIn('if (method !== "POST") return false;', block)
        self.assertNotIn('method === "PUT"', block)
        self.assertNotIn('method === "PATCH"', block)
        self.assertNotIn('method === "DELETE"', block)

    def test_reviewed_module_allowlists_include_exact_clients(self) -> None:
        site = SITE_HOST.read_text(encoding="utf-8")
        localhost = LOCALHOST.read_text(encoding="utf-8")
        for route, relative in (
            (
                "/agreement_publication_client.js",
                "web/agreement_publication_client.js",
            ),
            (
                "/fulfillment_completion_client.js",
                "web/fulfillment_completion_client.js",
            ),
        ):
            self.assertEqual(site.count(f'"{route}"'), 1)
            self.assertEqual(
                localhost.count(f'("{route}", "{relative}")'),
                1,
            )

    def test_bootstrap_composes_clients_only_for_active_session(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        for marker in (
            './agreement_publication_client.js',
            './fulfillment_completion_client.js',
            "function agreementPublicationClient()",
            "function fulfillmentCompletionClient()",
            'stableBootstrapError("AGREEMENT_PUBLICATION_AUTH_REQUIRED")',
            'stableBootstrapError("FULFILLMENT_COMPLETION_AUTH_REQUIRED")',
            "createMarketplaceWebAgreementPublicationClient",
            "createMarketplaceWebFulfillmentCompletionClient",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("publishAgreement(", text)
        self.assertNotIn("publishEvidence(", text)
        self.assertNotIn("Bearer ", text)

    def test_active_page_remains_unselected(self) -> None:
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        for marker in (
            "agreement_publication_client.js",
            "fulfillment_completion_client.js",
            "agreementPublicationClient()",
            "fulfillmentCompletionClient()",
            "completion-evidence",
            "publish-agreement",
            "claim-delivery-complete",
        ):
            self.assertNotIn(marker, index)
            self.assertNotIn(marker, app)

    def test_no_public_network_runtime_or_automatic_background_capability(self) -> None:
        combined = (
            SESSION.read_text(encoding="utf-8")
            + "\n"
            + BOOTSTRAP.read_text(encoding="utf-8")
        ).lower()
        for forbidden in (
            "websocket",
            "eventsource",
            "setinterval",
            "serviceworker",
            "broadcastchannel",
            "public network",
            "0.0.0.0",
        ):
            self.assertNotIn(forbidden, combined)

    def test_document_records_explicit_nonselection_and_semantics(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_PUBLICATION_FULFILLMENT_CLIENT_SELECTION_V1",
            "MODERATE authenticated browser capability selection",
            "no Agreement publication button",
            "no fulfillment evidence button",
            "no automatic publication after assent",
            "does not establish fulfillment",
            "No public-network exposure",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
