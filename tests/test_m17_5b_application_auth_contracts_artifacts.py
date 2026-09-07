from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class M17ApplicationAuthArtifactTests(unittest.TestCase):
    def test_source_remains_transport_neutral_and_generator_free(self):
        source = (ROOT / "src/marketplace/application/auth.py").read_text(encoding="utf-8-sig")
        forbidden = (
            "import secrets",
            "import jwt",
            "import requests",
            "authorization header",
            "set-cookie",
            "oauth",
            "oidc",
            "psycopg",
            "uvicorn",
        )
        lowered = source.lower()
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, lowered)
        self.assertIn("hashlib.sha256", source)
        self.assertIn("PrincipalBindingVerifier", source)

    def test_legacy_asgi_credential_boundary_remains_fail_closed(self):
        source = (ROOT / "src/marketplace/application/asgi.py").read_text(encoding="utf-8")
        self.assertIn('_SENSITIVE_REQUEST_HEADERS = frozenset({"cookie", "proxy-authorization"})', source)
        self.assertIn('if name == "authorization":', source)
        self.assertIn('if not allow_authorization:', source)
        self.assertIn('method, path, query, content_type, content_length, _authorization = _review_scope(scope)', source)
        self.assertIn('_FORBIDDEN_RESPONSE_HEADERS = frozenset({"set-cookie"})', source)
        self.assertIn("ASGI_SENSITIVE_HEADER_FORBIDDEN", source)

    def test_approved_retention_profile_is_documented(self):
        policy = (ROOT / "docs/RETENTION_POLICY.md").read_text(encoding="utf-8-sig")
        self.assertIn("MARKETPLACE_APPLICATION_AUTH_MVP", policy)
        self.assertIn("maximum 120 seconds", policy)
        self.assertIn("maximum 30 minutes", policy)
        self.assertIn("maximum 8 hours", policy)
        self.assertIn("process/memory only", policy)
        self.assertIn("Android offline content cache", policy)

    def test_m17_5b_document_preserves_semantic_and_runtime_boundaries(self):
        doc = (ROOT / "docs/m17-5b-application-auth-contracts.md").read_text(encoding="utf-8-sig")
        self.assertIn("application session        != OLP principal authority", doc)
        self.assertIn("There is deliberately no permissive default", doc)
        self.assertIn("No live credential/token issuance", doc)
        self.assertIn("HTTP/runtime activation is outside this slice", doc)


if __name__ == "__main__":
    unittest.main()
