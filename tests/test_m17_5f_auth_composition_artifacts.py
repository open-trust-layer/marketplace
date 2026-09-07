from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "tests" / "test_m17_5f_auth_composition_synthetic.py"
ARTIFACTS = ROOT / "tests" / "test_m17_5f_auth_composition_artifacts.py"
DOC = ROOT / "docs" / "m17-5f-auth-composition-synthetic.md"
WEB_INDEX = ROOT / "web" / "index.html"
WEB_APP = ROOT / "web" / "app.js"
WEB_SESSION = ROOT / "web" / "client_session.js"
ANDROID = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
ANDROID_MAIN = ANDROID / "MainActivity.kt"
ANDROID_SESSION = ANDROID / "MarketplaceClientSession.kt"
ANDROID_CACHE = ANDROID / "MarketplaceOfflineCache.kt"
LEGACY_ASGI = ROOT / "src" / "marketplace" / "application" / "asgi.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"


class M175FSyntheticAuthCompositionArtifactTests(unittest.TestCase):
    def test_exact_m17_5f_artifacts_exist(self):
        for path in (SYNTHETIC, ARTIFACTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_synthetic_harness_has_no_concrete_generator_network_provider_or_persistence_authority(self):
        text = SYNTHETIC.read_text(encoding="utf-8")
        forbidden = (
            "import secrets",
            "from secrets",
            "import random",
            "from random",
            "import socket",
            "from socket",
            "import requests",
            "import httpx",
            "urllib.request",
            "psycopg",
            "subprocess",
            "os.environ",
            "cryptography",
            "private_key",
            "PrivateKey",
            "keystore",
            "localStorage",
            "sessionStorage",
            "document.cookie",
        )
        for marker in forbidden:
            self.assertNotIn(marker, text)
        self.assertIn("CHALLENGE", text)
        self.assertIn("TOKEN", text)
        self.assertIn("InProcessTransport", text)
        self.assertIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", text)

    def test_existing_runtime_and_client_entry_points_remain_unselected(self):
        web_index = WEB_INDEX.read_text(encoding="utf-8")
        web_app = WEB_APP.read_text(encoding="utf-8")
        android_main = ANDROID_MAIN.read_text(encoding="utf-8")
        legacy_asgi = LEGACY_ASGI.read_text(encoding="utf-8")
        localhost = LOCALHOST.read_text(encoding="utf-8")
        self.assertNotIn("client_session.js", web_index)
        self.assertNotIn("MarketplaceMemorySession", web_app)
        self.assertNotIn("Authorization", web_app)
        self.assertNotIn("MarketplaceSessionClient", android_main)
        self.assertNotIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", legacy_asgi)
        self.assertNotIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", localhost)

    def test_web_source_retains_exact_memory_session_route_and_logout_semantics(self):
        text = WEB_SESSION.read_text(encoding="utf-8")
        for marker in (
            "adoptEstablishedSession(principal, sessionToken)",
            'path === "/api/auth/session"',
            'path === "/api/auth/logout"',
            'path === "/api/product-listings"',
            'path === "/api/intents"',
            'tail === "responses"',
            'tail === "proposals"',
            "session.detachAuthorizationForLogout()",
            'code === "AUTH_SESSION_INVALID"',
            "seller_principal: session.requirePrincipal()",
            "buyer_principal: session.requirePrincipal()",
        ):
            self.assertIn(marker, text)

    def test_android_source_retains_exact_memory_session_route_logout_and_offline_boundary(self):
        session = ANDROID_SESSION.read_text(encoding="utf-8")
        cache = ANDROID_CACHE.read_text(encoding="utf-8").lower()
        for marker in (
            "adoptEstablishedSession(principal: String, sessionToken: String)",
            'path == "/api/auth/session"',
            'path == "/api/auth/logout"',
            'path == "/api/product-listings"',
            'path == "/api/intents"',
            'tail == "responses"',
            'tail == "proposals"',
            "session.detachAuthorizationForLogout()",
            'code == "AUTH_SESSION_INVALID"',
            "seller_principal = session.requirePrincipal()",
            "buyer_principal = session.requirePrincipal()",
        ):
            self.assertIn(marker, session)
        self.assertNotIn("bearer", cache)
        self.assertNotIn("authorization", cache)

    def test_synthetic_profile_is_documented_as_test_only_and_nonactivating(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_COMPOSITION_SYNTHETIC_V1",
            "HIGH",
            "deterministic",
            "in-process",
            "test-only",
            "actual Web and Android client code is not executed",
            "No runtime activation",
            "no credential persistence",
            "no Android build",
            "no private-key handling",
            "source-only rollback",
            "fad069fd973a7fc875dafecfba51e6e4a0bdc3f0",
        ):
            self.assertIn(marker, text)

    def test_m17_5f_test_fixture_is_not_selected_by_existing_runtime_surfaces(self):
        marker = "SyntheticMemorySessionClient"
        for path in (
            ROOT / "src" / "marketplace" / "application" / "asgi.py",
            ROOT / "src" / "marketplace" / "application" / "launch.py",
            ROOT / "src" / "marketplace" / "application" / "runtime_server.py",
            ROOT / "src" / "marketplace" / "runtime" / "composition.py",
            LOCALHOST,
            WEB_APP,
            ANDROID_MAIN,
        ):
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))


if __name__ == "__main__":
    unittest.main()
