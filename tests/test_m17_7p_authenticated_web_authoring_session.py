
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "web" / "client_session.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
DOC = ROOT / "docs" / "m17-7p-authenticated-web-authoring-session.md"


class M177PAuthenticatedWebAuthoringSessionTests(unittest.TestCase):
    def test_session_client_can_bind_exact_existing_memory_session(self) -> None:
        text = SESSION.read_text(encoding="utf-8")
        start = text.index("function createMarketplaceSessionClient(")
        end = text.index("async function request", start)
        block = text[start:end]
        self.assertIn("session = new MarketplaceMemorySession()", block)
        self.assertIn("!(session instanceof MarketplaceMemorySession)", block)
        self.assertNotIn("const session = new MarketplaceMemorySession()", block)

    def test_bootstrap_exposes_only_structured_authoring_on_shared_session(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("createMarketplaceSessionClient,", text)
        start = text.index("function structuredAuthoringClient()")
        end = text.index("function proposalAcceptanceClient()", start)
        block = text[start:end]
        for marker in (
            "!session.isActive",
            'stableBootstrapError("STRUCTURED_AUTHORING_AUTH_REQUIRED")',
            "createMarketplaceSessionClient(",
            "reviewedTransport,",
            "session,",
            "createProductListing: client.createProductListing",
            "createProposal: client.createProposal",
        ):
            self.assertIn(marker, block)
        returned = block[block.index("return Object.freeze({"):]
        self.assertNotIn("session:", returned)
        self.assertNotIn("request:", returned)
        self.assertNotIn("Bearer ", text)
        self.assertNotIn("Authorization", text)

    def test_active_listing_authoring_uses_session_principal_and_bearer_client(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function createProductListing")
        end = text.index("async function createProposal", start)
        block = text[start:end]
        for marker in (
            "const authoring = structuredAuthoringSession();",
            "if (authoring === null)",
            "await apiFetch(API_PRODUCT_LISTINGS",
            "fields.seller_principal !== authoring.principal",
            'stableClientError("AUTH_PRINCIPAL_MISMATCH")',
            "delete fields.seller_principal",
            "await authoring.client.createProductListing(fields)",
        ):
            self.assertIn(marker, block)

    def test_active_proposal_authoring_uses_session_principal_and_bearer_client(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function createProposal")
        end = text.index("function reviewedMvpText", start)
        block = text[start:end]
        for marker in (
            "const authoring = structuredAuthoringSession();",
            "if (authoring === null)",
            "await apiFetch(`${API_INTENTS}/${encodeURIComponent(parentId)}${PROPOSALS_SUFFIX}`",
            "fields.buyer_principal !== authoring.principal",
            "delete fields.buyer_principal",
            "await authoring.client.createProposal(parentId, fields)",
        ):
            self.assertIn(marker, block)

    def test_app_keeps_bearer_private_and_anonymous_fallback_intact(self) -> None:
        app = APP.read_text(encoding="utf-8")
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertNotIn("Bearer ", app)
        self.assertNotIn("Authorization", app)
        self.assertNotIn("session_token", app)
        self.assertNotIn("Bearer ", bootstrap)
        self.assertNotIn("Authorization", bootstrap)
        self.assertIn("if (!snapshot.active) return null;", app)
        self.assertIn('credentials: "omit"', app)

    def test_milestone_records_live_finding_and_non_authority(self) -> None:
        text = " ".join(DOC.read_text(encoding="utf-8").split())
        for marker in (
            "MARKETPLACE_AUTHENTICATED_WEB_AUTHORING_SESSION_V1",
            "live PostgreSQL-backed browser acceptance",
            "AUTH_REQUIRED",
            "same established in-memory session",
            "anonymous database-free fallback",
            "no credential persistence",
            "no public-network exposure",
            "no payment or settlement authority",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
