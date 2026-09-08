from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_verifier_ed25519.py"
DOC = ROOT / "docs" / "m17-5j-auth-verifier.md"

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


class M17AuthEd25519VerifierArtifactTests(unittest.TestCase):
    def test_source_imports_only_direct_public_key_verification_boundary(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
        self.assertEqual(
            imported_modules,
            {
                "__future__",
                "hashlib",
                "typing",
                "cryptography.exceptions",
                "cryptography.hazmat.primitives.asymmetric.ed25519",
                "auth",
                "auth_proof_profile",
            },
        )
        self.assertIn("Ed25519PublicKey.from_public_bytes", text)
        self.assertIn("except InvalidSignature:", text)
        for forbidden in (
            "olp.crypto.ed25519",
            "Ed25519PrivateKey",
            "private_key",
            "seed",
            "mnemonic",
            "passphrase",
            "generate",
            "sign(",
            "sign_authentication_proof",
            "secrets",
            "random",
            "os.environ",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "keyring",
            "keystore",
            "WebCrypto",
            "logging",
            "print(",
        ):
            self.assertNotIn(forbidden, text)

    def test_verifier_catches_only_invalid_signature(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handlers = [handler for node in ast.walk(tree) if isinstance(node, ast.Try) for handler in node.handlers]
        self.assertEqual(len(handlers), 1)
        handler = handlers[0]
        self.assertIsInstance(handler.type, ast.Name)
        assert isinstance(handler.type, ast.Name)
        self.assertEqual(handler.type.id, "InvalidSignature")

    def test_key_source_protocol_is_purpose_specific_and_public_key_only(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        protocol = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AuthenticationVerificationKeySource"
        )
        methods = [node for node in protocol.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual([method.name for method in methods], ["verification_key_bytes"])
        self.assertEqual([arg.arg for arg in methods[0].args.args], ["self", "verification_method"])
        protocol_text = ast.get_source_segment(text, protocol) or ""
        for forbidden in ("private", "secret", "seed", "sign", "generate", "export", "delete", "rotate"):
            self.assertNotIn(forbidden, protocol_text.lower())

    def test_exact_optional_dependency_and_explicit_ci_install_are_reviewed(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["optional-dependencies"]["auth-verify"], ["cryptography==50.0.1"])
        self.assertNotIn("nacl", str(project["optional-dependencies"]).lower())

        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        exact_install = (
            '& $env:MARKETPLACE_CI_PYTHON -m pip install --disable-pip-version-check "cryptography==50.0.1"'
        )
        self.assertEqual(workflow.count(exact_install), 1)
        self.assertLess(workflow.index(exact_install), workflow.index("Install OLP reference dependency"))
        self.assertIn("runs-on: [self-hosted, Windows, X64, marketplace-ci]", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertEqual(workflow.count("persist-credentials: false"), 2)

    def test_verifier_is_unselected_by_runtime_web_android_and_auth_composition(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_verifier_ed25519", text, str(path))
            self.assertNotIn("MarketplaceEd25519AuthenticationProofVerifier", text, str(path))
            self.assertNotIn("AuthenticationVerificationKeySource", text, str(path))

    def test_document_records_exact_high_risk_authority_and_rollback_boundaries(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ED25519_VERIFIER_V1",
            "3764afd27a4ff8263ff502a6f4c86cabd7349d8f",
            "Issue #278",
            "HIGH",
            "cryptography==50.0.1",
            "dependencies = []",
            "AuthenticationVerificationKeySource",
            "Ed25519PublicKey",
            "AUTH_PROOF_INVALID",
            "AUTH_PROOF_VERIFIER_UNAVAILABLE",
            "PrincipalBindingVerifier",
            "no private-key",
            "no concrete resolver/provider",
            "no runtime activation",
            "no Android build",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
