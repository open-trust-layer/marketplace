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
    / "auth_enrollment_launch_policy_nonce_ed25519_keyfile_v1.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_6z_reference_auth_enrollment_launch_policy_nonce_ed25519_keyfile.py"
)
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_6z_reference_auth_enrollment_launch_policy_nonce_ed25519_keyfile_artifacts.py"
)
DOC = (
    ROOT
    / "docs"
    / "m17-6z-reference-auth-enrollment-launch-policy-nonce-ed25519-keyfile.md"
)
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_attestor_keyfile_v1.py",
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_launch_policy_nonce_ed25519_attestor_v1.py",
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_launch_policy_nonce_ed25519_v1.py",
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_runtime_v1.py",
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_runtime_uvicorn_v1.py",
    ROOT / "tools" / "marketplace_localhost.py",
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


class M176ZReferenceAuthenticationEnrollmentEd25519KeyfileArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6z_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_exact_x_y_u_and_graph_types(self) -> None:
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
                "typing",
                "application.auth_launch",
                "auth_enrollment_approval_policy_v1",
                "auth_enrollment_attestor_keyfile_v1",
                "auth_enrollment_launch_policy_nonce_ed25519_attestor_v1",
                "auth_enrollment_launch_policy_nonce_ed25519_v1",
            },
        )

    def test_source_calls_x_once_y_once_and_handles_no_raw_key(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertEqual(
            names.count(
                "load_reference_authentication_enrollment_ed25519_attestor"
            ),
            1,
        )
        self.assertEqual(
            names.count(
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor"
            ),
            1,
        )
        self.assertNotIn("private_key_bytes", text)
        self.assertNotIn(
            "MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(",
            text,
        )
        self.assertIn("attestor=attestor", text)
        self.assertIn("return result", text)

    def test_source_has_no_direct_filesystem_crypto_external_io_or_runtime(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "import os",
            "from os",
            "import stat",
            "from stat",
            "open(",
            "Path(",
            "lstat(",
            "fstat(",
            "realpath(",
            "Ed25519PrivateKey",
            "from cryptography",
            "import cryptography",
            ".sign(",
            ".generate(",
            ".private_bytes(",
            "token_bytes",
            "os.environ",
            "getenv(",
            "keyring",
            "keystore",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urlopen",
            "psycopg",
            "sqlite",
            "vault",
            "HSM",
            "UvicornLoopbackServerProvider",
            "run_marketplace_authentication_enrollment_foreground",
        ):
            self.assertNotIn(marker, text)

    def test_existing_x_y_u_v_w_entrypoints_web_and_android_do_not_select_z(
        self,
    ) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "auth_enrollment_launch_policy_nonce_ed25519_keyfile_v1",
                text,
                str(path),
            )
            self.assertNotIn(
                "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
                "LAUNCH_POLICY_NONCE_ED25519_KEYFILE_V1",
                text,
                str(path),
            )

    def test_package_controls_require_z_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = (
            "marketplace/reference/"
            "auth_enrollment_launch_policy_nonce_ed25519_keyfile_v1.py"
        )
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_x_to_y_nonselection_and_rollback(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
            "LAUNCH_POLICY_NONCE_ED25519_KEYFILE_V1",
            "HIGH security/privacy",
            "X → Y → existing U",
            "raw private-key bytes",
            "synthetic non-secret",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
