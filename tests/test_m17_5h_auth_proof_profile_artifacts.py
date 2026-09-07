from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_proof_profile.py"
DOC = ROOT / "docs" / "m17-5h-auth-proof-profile.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceClientSession.kt",
)


class M17AuthProofProfileArtifactTests(unittest.TestCase):
    def test_source_uses_only_stdlib_and_existing_marketplace_auth_contracts(self):
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
                "base64",
                "dataclasses",
                "json",
                "re",
                "typing",
                "auth",
                "auth_challenge",
            },
        )
        for forbidden in (
            "cryptography",
            "nacl",
            "ed25519",
            "olp.",
            "private_key",
            "mnemonic",
            "passphrase",
            "keystore",
            "WebCrypto",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "pathlib",
            "logging",
            "os.environ",
        ):
            self.assertNotIn(forbidden, text)

    def test_profile_performs_no_signing_verification_or_key_operation(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        called_names = {
            node.func.id
            for node in calls
            if isinstance(node.func, ast.Name)
        }
        called_attributes = {
            node.func.attr
            for node in calls
            if isinstance(node.func, ast.Attribute)
        }
        for forbidden in (
            "sign",
            "verify",
            "sign_authentication_proof",
            "generate_key",
            "import_key",
            "export_key",
            "delete_key",
            "rotate_key",
        ):
            self.assertNotIn(forbidden, called_names)
            self.assertNotIn(forbidden, called_attributes)

    def test_signer_protocol_is_purpose_specific_and_not_generic_or_key_bearing(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        signer = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AuthenticationProofSigner"
        )
        methods = [node for node in signer.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual([node.name for node in methods], ["sign_authentication_proof"])
        method = methods[0]
        self.assertEqual([arg.arg for arg in method.args.args], ["self", "request"])
        self.assertNotIn("bytes", [arg.arg for arg in method.args.args])
        source_text = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), signer) or ""
        for forbidden in ("private_key", "seed", "mnemonic", "passphrase", "key_handle", "def sign("):
            self.assertNotIn(forbidden, source_text)

    def test_profile_is_not_olp_proof_impersonation(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('AUTH_PROOF_TYPE: Final = "MarketplaceAuthenticationProof"', text)
        self.assertIn(
            '"https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1"',
            text,
        )
        self.assertNotIn('AUTH_PROOF_TYPE: Final = "OLPProof"', text)
        self.assertNotIn('AUTH_PROOF_CRYPTOSUITE: Final = "eddsa-ed25519-v1"', text)
        self.assertNotIn("recordCommitment", text)
        self.assertNotIn("proof_input", text)
        self.assertNotIn("create_proof", text)
        self.assertNotIn("verify_proof", text)

    def test_profile_remains_unselected_by_runtime_and_clients(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            entry_text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_proof_profile", entry_text)
            self.assertNotIn("AuthenticationProofSigner", entry_text)
            self.assertNotIn("MarketplaceAuthenticationProof", entry_text)

    def test_dependency_workflow_and_android_surfaces_are_unchanged_in_kind(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        android = (ROOT / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        self.assertNotIn("cryptography", pyproject)
        self.assertNotIn("nacl", pyproject)
        self.assertNotIn("auth_proof_profile", pyproject)
        self.assertNotIn("auth_proof_profile", workflow)
        self.assertNotIn("auth_proof_profile", android)
        self.assertNotIn("security-crypto", android)
        self.assertNotIn("tink", android.lower())

    def test_document_records_exact_authority_and_non_authority_boundaries(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_PROOF_TRANSCRIPT_V1",
            "69f339386fe7889e1c1a4ab27985125ddec2ef8f",
            "MarketplaceAuthenticationProof",
            "mks1_",
            "64-byte",
            "MARKETPLACE-AUTH",
            "purpose-specific signer",
            "not a generic signing oracle",
            "no concrete signing",
            "no concrete verification",
            "no private-key",
            "no runtime activation",
            "no resolver/provider/network activity",
            "no Android build",
            "no dependency widening",
            "OLPProof",
            "recordCommitment",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
