from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_evidence_trust_ed25519.py"
DOC = ROOT / "docs" / "m17-5m-auth-evidence-trust-ed25519.md"
PREDECESSOR = ROOT / "tests" / "test_m17_5i_auth_ed25519_artifacts.py"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceClientSession.kt",
)


class M17AuthEvidenceTrustArtifactTests(unittest.TestCase):
    def test_source_imports_only_public_verification_and_existing_l_contract(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
        self.assertEqual(
            modules,
            {
                "__future__",
                "collections.abc",
                "dataclasses",
                "hashlib",
                "re",
                "types",
                "typing",
                "cryptography.exceptions",
                "cryptography.hazmat.primitives.asymmetric.ed25519",
                "auth_verification_method_evidence",
            },
        )
        self.assertIn("Ed25519PublicKey.from_public_bytes", text)
        self.assertIn("public_key.verify(", text)
        self.assertEqual(text.count("except InvalidSignature:"), 1)
        for forbidden in (
            "olp.crypto.ed25519",
            "Ed25519PrivateKey",
            "private_key",
            "seed",
            "mnemonic",
            "passphrase",
            "generate",
            "def sign(",
            "sign_authentication_proof",
            "secrets",
            "random",
            "keyring",
            "keystore",
        ):
            self.assertNotIn(forbidden, text)

    def test_source_has_no_acquisition_persistence_or_runtime_authority(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "os.environ",
            "pathlib",
            "psycopg",
            "open(",
            "read_text(",
            "write_text(",
            "logging",
            "print(",
        ):
            self.assertNotIn(forbidden, text)
        tree = ast.parse(text)
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for forbidden_method in ("refresh", "reload", "retry", "fetch", "resolve", "download", "request"):
            self.assertNotIn(forbidden_method, method_names)

    def test_predecessor_crypto_allowlist_is_exactly_j_and_m(self):
        text = PREDECESSOR.read_text(encoding="utf-8")
        self.assertIn('source_root / "application" / "auth_verifier_ed25519.py"', text)
        self.assertIn('source_root / "application" / "auth_evidence_trust_ed25519.py"', text)
        self.assertIn("allowed_public_verifier_paths", text)
        self.assertIn("Ed25519PrivateKey", text)
        self.assertIn("olp.crypto.ed25519", text)
        self.assertIn("import nacl", text)
        self.assertIn("from nacl", text)

    def test_dependency_workflow_and_package_boundary_are_unchanged(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["optional-dependencies"]["auth-verify"], ["cryptography==50.0.1"])
        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        exact_install = (
            '& $env:MARKETPLACE_CI_PYTHON -m pip install --disable-pip-version-check "cryptography==50.0.1"'
        )
        self.assertEqual(workflow.count(exact_install), 1)
        package_gate = (ROOT / "tools" / "package_artifact_gate.py").read_text(encoding="utf-8")
        package_tests = (ROOT / "tests" / "test_package_artifact_gate.py").read_text(encoding="utf-8")
        member = "marketplace/application/auth_evidence_trust_ed25519.py"
        self.assertEqual(package_gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(package_tests.count(member), 2)
        self.assertIn("test_missing_auth_evidence_trust_ed25519_member_is_rejected", package_tests)

    def test_trust_verifier_is_unselected_by_runtime_web_android_and_auth_composition(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_evidence_trust_ed25519", text, str(path))
            self.assertNotIn("MarketplaceEd25519AuthenticationEvidenceTrustVerifier", text, str(path))
            self.assertNotIn("MarketplaceAuthenticationEvidenceTrustAnchorSnapshot", text, str(path))

    def test_document_records_high_risk_seven_file_scope_and_non_authority(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_EVIDENCE_ED25519_TRUST_V1",
            "c140e1f27824e59dc4c623f739d8f398fd5ab9f0",
            "Issue #284",
            "HIGH",
            "1..64",
            "64 raw bytes",
            "MARKETPLACE-AUTH-EVIDENCE",
            "cryptography==50.0.1",
            "seven-file",
            "test_m17_5i_auth_ed25519_artifacts.py",
            "no network",
            "no production private-key",
            "no runtime activation",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
