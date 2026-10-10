from __future__ import annotations

import base64
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "product-browser-auth-bootstrap.md"


class ProductBrowserAuthBootstrapTests(unittest.TestCase):
    def test_exact_reviewed_module_composition(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        for marker in (
            './client_session.js',
            './auth_ed25519_key_creation.js',
            './auth_ed25519_proof_provider.js',
            './auth_establishment.js',
            './agreement_ed25519_assent_provider.js',
            './agreement_assent_client.js',
            './proposal_acceptance_client.js',
        ):
            self.assertIn(marker, text)

    def test_public_carrier_bridge_preserves_exact_key_bytes(self) -> None:
        browser_prefix = "mkpk1_"
        evidence_prefix = "mkp1_"
        public_bytes = bytes(range(32))
        payload = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
        self.assertEqual(len(payload), 43)
        browser = browser_prefix + payload
        evidence = evidence_prefix + payload
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('const BROWSER_PUBLIC_KEY_PREFIX = "mkpk1_"', text)
        self.assertIn('const EVIDENCE_PUBLIC_KEY_PREFIX = "mkp1_"', text)
        self.assertIn("return EVIDENCE_PUBLIC_KEY_PREFIX + payload", text)
        self.assertEqual(browser[6:], evidence[5:])

    def test_private_authority_and_bearer_never_leave_bootstrap_dependencies(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("privateKey: keyResult.privateKey", text)
        self.assertNotIn("session_token", text)
        self.assertNotIn("Bearer ", text)
        start = text.index("return Object.freeze({", text.index("evidencePublicKeyValue"))
        end = text.index("async function establishSession", start)
        self.assertNotIn("privateKey:", text[start:end])

    def test_no_persistence_background_or_automatic_key_creation(self) -> None:
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        for marker in (
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "serviceWorker", "setTimeout", "setInterval", "Worker(",
            "BroadcastChannel", "WebSocket", "EventSource",
        ):
            self.assertNotIn(marker, bootstrap)
        app = APP.read_text(encoding="utf-8")
        self.assertEqual(app.count('import("./auth_bootstrap.js")'), 1)
        self.assertIn('authLoadButton.addEventListener("click"', app)
        self.assertIn('authGenerateKeyButton.addEventListener("click"', app)
        self.assertNotIn('import "./auth_bootstrap.js"', app)

    def test_agreement_assent_composition_stays_private_while_page_selects_explicit_signing(self) -> None:
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("function agreementAssentClient()", bootstrap)
        self.assertIn('stableBootstrapError("AGREEMENT_ASSENT_AUTH_REQUIRED")', bootstrap)
        self.assertIn("keyResult === null", bootstrap)
        self.assertIn("!session.isActive", bootstrap)
        self.assertIn("activeVerificationMethod === null", bootstrap)
        self.assertEqual(
            bootstrap.count("createMarketplaceWebAgreementEd25519AssentProvider"),
            2,
        )
        self.assertEqual(
            bootstrap.count("createMarketplaceWebAgreementAssentClient"),
            2,
        )
        self.assertNotIn("signAndSubmit(", bootstrap)
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        for marker in (
            "agreement_ed25519_assent_provider.js",
            "agreement_assent_client.js",
        ):
            self.assertNotIn(marker, index)
            self.assertNotIn(marker, app)
        self.assertEqual(app.count("agreementAssentClient()"), 2)
        self.assertEqual(app.count(".formationStatus("), 1)
        self.assertEqual(app.count(".signAndSubmit("), 1)
        self.assertNotIn("createAgreementAssentSignature(", app)
        self.assertIn('id="sign-agreement-assent" type="button" disabled', index)
        self.assertIn('signAgreementAssentButton.addEventListener("click"', app)

    def test_proposal_acceptance_client_is_composed_but_bearer_stays_private(self) -> None:
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("function proposalAcceptanceClient()", bootstrap)
        self.assertIn('stableBootstrapError("PROPOSAL_ACCEPTANCE_AUTH_REQUIRED")', bootstrap)
        self.assertEqual(
            bootstrap.count("createMarketplaceWebProposalAcceptanceClient"),
            2,
        )
        self.assertNotIn("Bearer ", bootstrap)
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        self.assertIn('id="accept-proposal" type="button" disabled', index)
        self.assertIn('acceptProposalButton.addEventListener("click"', app)
        self.assertNotIn("proposal_acceptance_client.js", index)
        self.assertNotIn("proposal_acceptance_client.js", app)

    def test_bootstrap_route_is_authenticated_localhost_only(self) -> None:
        site = SITE_HOST.read_text(encoding="utf-8")
        localhost = LOCALHOST.read_text(encoding="utf-8")
        self.assertIn('"/auth_bootstrap.js"', site)
        self.assertIn('("/auth_bootstrap.js", "web/auth_bootstrap.js")', localhost)
        self.assertIn("web_modules: tuple[tuple[str, bytes], ...] = ()", site)

    def test_document_records_manual_provisioning_and_reset_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "HIGH authentication",
            "mkpk1_",
            "mkp1_",
            "startup-provisioned",
            "Keeping this page open",
            "relaunched/restarted",
            "does not perform or authorize",
            "memory-only",
            "explicit user action",
            "no mutable enrollment API",
            "Reset in-memory authentication",
            "Agreement assent composition",
            "agreementAssentClient()",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
