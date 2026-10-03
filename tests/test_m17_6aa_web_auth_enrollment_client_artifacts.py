from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_enrollment_client.js"
SESSION = ROOT / "web" / "client_session.js"
SESSION_TESTS = ROOT / "tests" / "test_m17_5e_client_session_artifacts.py"
DOC = ROOT / "docs" / "m17-6aa-web-auth-enrollment-client.md"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
ANDROID = (
    ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "org"
    / "opentrustlayer"
    / "marketplace"
    / "MainActivity.kt"
)


class M176AAWebAuthenticationEnrollmentClientArtifactTests(unittest.TestCase):
    def test_exact_six_m17_6aa_paths_exist(self) -> None:
        for path in (SOURCE, SESSION, SESSION_TESTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_session_authorizes_only_two_exact_enrollment_post_paths(self) -> None:
        text = SESSION.read_text(encoding="utf-8")
        self.assertEqual(
            text.count('path === "/api/authentication-enrollment/nonces"'),
            1,
        )
        self.assertEqual(
            text.count('path === "/api/authentication-enrollment/evidence"'),
            1,
        )
        post_start = text.index('if (method !== "POST") return false;')
        post_block = text[post_start:text.index("class MarketplaceMemorySession", post_start)]
        self.assertIn('path === "/api/authentication-enrollment/nonces"', post_block)
        self.assertIn('path === "/api/authentication-enrollment/evidence"', post_block)
        get_block = text[text.index('if (method === "GET")'):post_start]
        self.assertNotIn("/api/authentication-enrollment/", get_block)

    def test_client_has_no_private_key_crypto_persistence_background_or_retry(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in (
            "privatekey", "private_key", "cryptography", "webcrypto",
            "subtle.", ".sign(", "generatekey", "exportkey", "importkey",
            "localstorage", "sessionstorage", "indexeddb", "document.cookie",
            "serviceworker", "settimeout", "setinterval", "worker(",
            "websocket", "eventsource", "retry", "indexeddb",
            "keyring", "vault", "hsm", "sqlite", "psycopg",
        ):
            self.assertNotIn(marker, lowered)

    def test_client_is_unselected_and_undistributed(self) -> None:
        marker = "auth_enrollment_client.js"
        for path in (BOOTSTRAP, APP, INDEX, SITE_HOST, LOCALHOST, ANDROID):
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))
        builder = "createMarketplaceWebAuthEnrollmentClient"
        for path in (BOOTSTRAP, APP, INDEX, SITE_HOST, LOCALHOST, ANDROID):
            self.assertNotIn(builder, path.read_text(encoding="utf-8"), str(path))

    def test_active_bootstrap_manual_provisioning_boundary_is_unchanged(self) -> None:
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        doc = (ROOT / "docs" / "product-browser-auth-bootstrap.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("auth_enrollment_client", bootstrap)
        self.assertIn("startup-provisioned", doc)
        self.assertIn("no mutable enrollment API", doc)

    def test_document_records_source_only_authenticated_enrollment_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_ENROLLMENT_CLIENT_V1",
            "HIGH authentication",
            "unselected and undistributed",
            "/api/authentication-enrollment/nonces",
            "/api/authentication-enrollment/evidence",
            "nonce remains internal",
            "startup-provisioned",
            "no UI activation",
            "no trust-store mutation",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
