from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    ROOT / "src/marketplace/application/auth_challenge.py",
    ROOT / "src/marketplace/application/auth_session_http.py",
    ROOT / "src/marketplace/application/auth_session_asgi.py",
)


class M17SessionEstablishmentArtifactTests(unittest.TestCase):
    def test_source_slice_has_no_concrete_generator_provider_network_or_persistence_authority(self):
        forbidden = (
            "import secrets",
            "from secrets",
            "import random",
            "from random",
            "import socket",
            "import requests",
            "import httpx",
            "urllib.request",
            "psycopg",
            "subprocess",
            "os.environ",
        )
        for path in SOURCE_FILES:
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, f"{marker} unexpectedly present in {path.name}")

    def test_existing_runtime_composition_does_not_select_m17_5d_adapter(self):
        class_name = "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        legacy_asgi = (ROOT / "src/marketplace/application/asgi.py").read_text(encoding="utf-8")
        localhost = (ROOT / "tools/marketplace_localhost.py").read_text(encoding="utf-8")
        self.assertNotIn(class_name, legacy_asgi)
        self.assertNotIn(class_name, localhost)

    def test_m17_5d_source_is_injected_only_and_documented(self):
        http_text = SOURCE_FILES[1].read_text(encoding="utf-8")
        for marker in (
            "CredentialMaterialSource",
            "AuthenticationProofVerifier",
            "AUTH_REQUEST_MAX_BYTES = 64 * 1024",
            "MAX_PROOF_JSON_BYTES = 48 * 1024",
            "AUTH_CAPACITY_EXCEEDED",
        ):
            self.assertIn(marker, http_text)
        document = (ROOT / "docs/m17-5d-session-establishment.md").read_text(encoding="utf-8")
        self.assertIn("no runtime activation", document)
        self.assertIn("no credential persistence", document)


if __name__ == "__main__":
    unittest.main()
