from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_nonce_authority_v1.py"
TESTS = ROOT / "tests" / "test_m17_6r_reference_auth_enrollment_launch_nonce_authority.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6r_reference_auth_enrollment_launch_nonce_authority_artifacts.py"
DOC = ROOT / "docs" / "m17-6r-reference-auth-enrollment-launch-nonce-authority.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176RReferenceAuthenticationEnrollmentLaunchNonceAuthorityArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6r_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_q_o_and_caller_contract_dependencies(self) -> None:
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
                "application.auth_enrollment_authority",
                "application.auth_enrollment_policy",
                "application.auth_launch",
                "auth_enrollment_launch_v1",
                "auth_enrollment_nonce_authority_v1",
            },
        )
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1"',
            text,
        )

    def test_source_builds_exactly_one_q_and_one_o(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "build_reference_authentication_enrollment_nonce_authority",
                "build_reference_authentication_enrollment_launch",
            }
        ]
        self.assertEqual(
            calls.count("build_reference_authentication_enrollment_nonce_authority"),
            1,
        )
        self.assertEqual(
            calls.count("build_reference_authentication_enrollment_launch"),
            1,
        )
        self.assertIn("nonce_authority=nonce.nonce_authority", text)
        self.assertIn(
            "self.launch.nonce_authority is not self.nonce.nonce_authority",
            text,
        )

    def test_source_has_no_runtime_signing_persistence_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "run_marketplace_authentication_enrollment_foreground",
            "UvicornLoopbackServerProvider",
            "socket",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "subprocess",
            "psycopg",
            "sqlite",
            "private_key",
            "Ed25519PrivateKey",
            "token_bytes",
        ):
            self.assertNotIn(marker, text)

    def test_runtime_uvicorn_web_and_android_do_not_select_r(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_launch_nonce_authority_v1", text, str(path))
            self.assertNotIn(
                "build_reference_authentication_enrollment_launch_nonce_authority",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_launch_nonce_authority_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_q_to_o_unselected_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1",
            "HIGH security/privacy",
            "Q → O",
            "zero entropy",
            "caller-supplied",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
