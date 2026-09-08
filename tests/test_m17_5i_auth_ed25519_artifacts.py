from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "tests" / "test_m17_5i_auth_ed25519_synthetic.py"
ARTIFACTS = ROOT / "tests" / "test_m17_5i_auth_ed25519_artifacts.py"
DOC = ROOT / "docs" / "m17-5i-auth-ed25519-synthetic.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceClientSession.kt",
)


class M17AuthEd25519SyntheticArtifactTests(unittest.TestCase):
    def test_exact_three_m17_5i_artifacts_exist(self):
        for path in (SYNTHETIC, ARTIFACTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_crypto_qualification_is_pinned_olp_test_only_and_purpose_specific(self):
        text = SYNTHETIC.read_text(encoding="utf-8")
        self.assertIn("from olp.crypto.ed25519 import", text)
        self.assertIn(
            "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
            text,
        )
        self.assertIn(
            "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
            text,
        )
        self.assertIn("EXPECTED_SIGNATURE_HEX", text)
        self.assertIn("sign_authentication_proof", text)
        self.assertNotIn("def sign(", text)
        self.assertNotIn("import cryptography", text)
        self.assertNotIn("from cryptography", text)
        self.assertNotIn("import nacl", text)
        self.assertNotIn("from nacl", text)

    def test_synthetic_crypto_has_no_random_external_secret_or_persistence_source(self):
        text = SYNTHETIC.read_text(encoding="utf-8")
        for forbidden in (
            "import secrets",
            "from secrets",
            "import random",
            "from random",
            "os.urandom",
            "uuid",
            "os.environ",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib.request",
            "psycopg",
            "keyring",
            "keystore",
            "WebCrypto",
            "localStorage",
            "sessionStorage",
            "document.cookie",
            "logging.",
            "print(",
        ):
            self.assertNotIn(forbidden, text)

    def test_marketplace_production_source_does_not_import_ed25519_provider(self):
        source_root = ROOT / "src" / "marketplace"
        files = tuple(source_root.rglob("*.py"))
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("olp.crypto.ed25519", text, str(path))
            self.assertNotIn("from cryptography", text, str(path))
            self.assertNotIn("import cryptography", text, str(path))
            self.assertNotIn("import nacl", text, str(path))
            self.assertNotIn("from nacl", text, str(path))

    def test_marketplace_dependency_and_workflow_boundaries_are_not_widened(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        gate = (ROOT / "tools" / "conformance_gate.py").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        self.assertNotIn("cryptography", pyproject)
        self.assertNotIn("nacl", pyproject)
        self.assertIn("41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c", workflow)
        self.assertNotIn("test_m17_5i", workflow)
        self.assertIn("unittest", gate)
        self.assertIn("test_*.py", gate)

    def test_runtime_web_and_android_entry_points_do_not_select_test_crypto(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("test_m17_5i", text, str(path))
            self.assertNotIn("SyntheticEd25519AuthenticationProofSigner", text, str(path))
            self.assertNotIn("SyntheticEd25519AuthenticationProofVerifier", text, str(path))
            self.assertNotIn("olp.crypto.ed25519", text, str(path))

        web_index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        android_main = UNSELECTED_ENTRY_POINTS[-2].read_text(encoding="utf-8")
        localhost = (ROOT / "tools" / "marketplace_localhost.py").read_text(encoding="utf-8")
        self.assertNotIn("client_session.js", web_index)
        self.assertNotIn("MarketplaceSessionClient", android_main)
        self.assertNotIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", localhost)

    def test_document_records_exact_authority_dependency_and_failure_boundaries(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ED25519_SYNTHETIC_V1",
            "8bab6c83f09e299f392cf6f994f1fa73406ae379",
            "Issue #276",
            "HIGH",
            "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c",
            "cryptography>=41.0",
            "RFC 8032",
            "fixed synthetic non-secret",
            "test-only",
            "mks1_",
            "AUTH_PROOF_INVALID",
            "AUTH_PROOF_VERIFIER_UNAVAILABLE",
            "PrincipalBindingVerifier",
            "no dependency widening",
            "no runtime activation",
            "no resolver/provider/network activity",
            "no Android build",
            "source-only rollback",
            "production verifier/dependency decision",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
