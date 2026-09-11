from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_establishment.js"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
CLIENT_SESSION = ROOT / "web" / "client_session.js"
ANDROID_MAIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"
DOC = ROOT / "docs" / "m17-6a-web-auth-establishment.md"


class M176AWebAuthEstablishmentArtifactTests(unittest.TestCase):
    def test_exact_four_artifacts_exist(self) -> None:
        self.assertTrue(SOURCE.is_file())
        self.assertTrue(DOC.is_file())

    def test_new_web_seam_remains_unselected(self) -> None:
        for path in (INDEX, APP, CLIENT_SESSION, ANDROID_MAIN):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_establishment.js", text, str(path))
            self.assertNotIn("createMarketplaceWebAuthEstablishment", text, str(path))

    def test_source_has_no_concrete_key_custody_or_browser_crypto(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        forbidden = (
            "crypto.subtle", "window.crypto", "navigator.credentials", "WebAuthn",
            "privateKey", "private_key", "mnemonic", "seedPhrase", "keystore",
            "wallet", "extension", "localStorage", "sessionStorage", "indexedDB",
            "document.cookie", "caches.open", "serviceWorker",
        )
        for marker in forbidden:
            self.assertNotIn(marker, text)
    def test_source_has_no_retry_refresh_timer_background_or_cross_origin_seam(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
        for marker in (
            "settimeout", "setinterval", "retry", "refresh", "websocket", "eventsource",
            "location.href", "window.open", "postmessage", "broadcastchannel", "worker(",
            "fetch(\"http://", "fetch('http://", "fetch(\"https://", "fetch('https://",
        ):
            self.assertNotIn(marker, text)
        self.assertIn('"/api/auth/challenges"', text)
        self.assertIn('"/api/auth/sessions"', text)

    def test_errors_are_stable_and_nonreflective(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('new Error("Marketplace Web authentication operation failed")', text)
        self.assertNotIn("console.log", text)
        self.assertNotIn("console.error", text)
        self.assertNotIn("JSON.stringify(error", text)
        self.assertNotIn("error.message", text)

    def test_document_records_authority_and_later_gates(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1",
            "HIGH security/privacy",
            "unselected",
            "purpose-specific injected proof provider",
            "no WebCrypto",
            "no browser wallet",
            "no credential persistence",
            "no active Web UI selection",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
