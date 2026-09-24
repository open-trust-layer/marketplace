from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_assent_client.js"
SESSION = ROOT / "web" / "client_session.js"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "product-agreement-assent-web-client.md"


class ProductWebAgreementAssentClientArtifactTests(unittest.TestCase):
    def test_source_is_delivered_and_selected_only_by_auth_bootstrap(self) -> None:
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(DOC.is_file())
        marker = "agreement_assent_client.js"
        self.assertIn(f'"/{marker}"', SITE_HOST.read_text(encoding="utf-8"))
        self.assertIn(f'"web/{marker}"', LOCALHOST.read_text(encoding="utf-8"))
        self.assertNotIn(marker, INDEX.read_text(encoding="utf-8"))
        self.assertNotIn(marker, APP.read_text(encoding="utf-8"))
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertEqual(bootstrap.count(f'from "./{marker}"'), 1)
        self.assertEqual(
            bootstrap.count("createMarketplaceWebAgreementAssentClient"),
            2,
        )
        self.assertNotIn("signAndSubmit(", bootstrap)

    def test_web_session_authorizes_only_exact_assent_post_routes(self) -> None:
        text = SESSION.read_text(encoding="utf-8")
        for marker in (
            'path.startsWith("/api/agreements/")',
            'parts[1] !== "assent"',
            'parts[2] === "preparation" || parts[2] === "status"',
        ):
            self.assertIn(marker, text)

    def test_client_has_no_persistence_background_key_or_ambient_crypto_surface(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "localstorage",
            "sessionstorage",
            "indexeddb",
            "document.cookie",
            "caches.open",
            "serviceworker",
            "setinterval",
            "settimeout",
            "websocket",
            "eventsource",
            "generatekey",
            "importkey",
            "exportkey",
            "wrapkey",
            "unwrapkey",
            "window.crypto",
            "globalthis.crypto",
            "console.log",
            "console.error",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_document_records_unselected_source_only_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1",
            "strict OJVE",
            "exact bearer route scope",
            "not imported by app.js",
            "no browser activation",
            "no Agreement publication",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
