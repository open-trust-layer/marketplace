from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_attestor_ed25519_v1.py"
TESTS = ROOT / "tests" / "test_m17_6t_reference_auth_enrollment_attestor_ed25519.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6t_reference_auth_enrollment_attestor_ed25519_artifacts.py"
DOC = ROOT / "docs" / "m17-6t-reference-auth-enrollment-attestor-ed25519.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_policy_nonce_v1.py",
    ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_v1.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176TReferenceAuthenticationEnrollmentEd25519AttestorArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6t_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_crypto_and_existing_transcript_boundary(self) -> None:
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
                "typing",
                "cryptography.hazmat.primitives.asymmetric.ed25519",
                "application.auth_evidence_trust_ed25519",
            },
        )
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1"',
            text,
        )
        self.assertIn("build_marketplace_authentication_evidence_trust_transcript", text)
        self.assertIn("Ed25519PrivateKey.from_private_bytes", text)
        self.assertIn("self._private_key.sign(reviewed)", text)

    def test_source_exposes_no_generic_signing_key_generation_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "def sign(",
            ".generate(",
            "private_bytes(",
            "token_bytes",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "keyring",
            "socket",
            "subprocess",
            "requests",
            "urlopen",
            "psycopg",
            "sqlite",
            "vault",
            "HSM",
        ):
            self.assertNotIn(marker, text)

    def test_existing_launch_runtime_web_and_android_do_not_select_t(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_attestor_ed25519_v1", text, str(path))
            self.assertNotIn(
                "MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_attestor_ed25519_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_private_key_nonselection_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1",
            "HIGH security/privacy",
            "32-byte",
            "purpose-specific",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
