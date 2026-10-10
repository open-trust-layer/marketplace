from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_launch_policy_nonce_ed25519_v1.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_6u_reference_auth_enrollment_launch_policy_nonce_ed25519.py"
)
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_6u_reference_auth_enrollment_launch_policy_nonce_ed25519_artifacts.py"
)
DOC = (
    ROOT
    / "docs"
    / "m17-6u-reference-auth-enrollment-launch-policy-nonce-ed25519.md"
)
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_launch_policy_nonce_v1.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "org"
    / "opentrustlayer"
    / "marketplace"
    / "MainActivity.kt",
)


class M176UReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519ArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6u_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_t_s_and_exact_graph_types(self) -> None:
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
                "dataclasses",
                "typing",
                "application.auth_launch",
                "auth_enrollment_approval_policy_v1",
                "auth_enrollment_attestor_ed25519_v1",
                "auth_enrollment_launch_policy_nonce_v1",
            },
        )
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_'
            'LAUNCH_POLICY_NONCE_ED25519_V1"',
            text,
        )

    def test_source_constructs_exactly_one_t_then_one_s(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        ]
        self.assertEqual(
            names.count(
                "MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor"
            ),
            1,
        )
        self.assertEqual(
            names.count(
                "build_reference_authentication_enrollment_launch_policy_nonce"
            ),
            1,
        )
        self.assertIn("private_key_bytes=private_key_bytes", text)
        self.assertIn("attestor=attestor", text)
        self.assertIn("self.launch.attestor is not self.attestor", text)
        self.assertIn("self.launch.launch.attestor is not self.attestor", text)

    def test_source_has_no_direct_crypto_signing_generation_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "Ed25519PrivateKey",
            "from cryptography",
            "import cryptography",
            ".sign(",
            ".generate(",
            ".private_bytes(",
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

    def test_existing_s_runtime_uvicorn_web_and_android_do_not_select_u(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "auth_enrollment_launch_policy_nonce_ed25519_v1",
                text,
                str(path),
            )
            self.assertNotIn(
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
                "LAUNCH_POLICY_NONCE_ED25519_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = (
            "marketplace/reference/"
            "auth_enrollment_launch_policy_nonce_ed25519_v1.py"
        )
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_t_to_s_private_key_nonselection_and_rollback(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
            "LAUNCH_POLICY_NONCE_ED25519_V1",
            "HIGH security/privacy",
            "T → S",
            "32-byte",
            "must not retain",
            "zero signing",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
